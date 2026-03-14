import os
import sqlite3
import subprocess
import time
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'super_secret_auth_key'
DB_FILE = 'database.db'

# In-memory store for login attempts
login_attempts = {}
MAX_ATTEMPTS = 5
LOCKOUT_TIME = 90  # 1 minute 30 seconds

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/add-question', methods=['GET', 'POST'])
def add_question():
    if session.get('role') != 'admin':
        return "Access denied", 403

    conn = get_db_connection()
    success = False

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        difficulty = request.form.get('difficulty')
        
        # Validation
        if not title or not description or not difficulty:
            conn.close()
            return "Missing mandatory fields", 400
            
        cursor = conn.cursor()
        
        # 1. Insert Question
        cursor.execute('''
            INSERT INTO questions (title, description, difficulty)
            VALUES (?, ?, ?)
        ''', (title, description, difficulty))
        
        question_id = cursor.lastrowid
        
        # 2. Insert Sample Test Cases (2)
        for i in range(1, 3):
            in_val = request.form.get(f'sample_in_{i}')
            out_val = request.form.get(f'sample_out_{i}')
            if in_val and out_val:
                cursor.execute('''
                    INSERT INTO test_cases (question_id, input, expected_output, is_sample)
                    VALUES (?, ?, ?, ?)
                ''', (question_id, in_val, out_val, True))
                
        # 3. Insert Hidden Test Cases (5)
        for i in range(1, 6):
            in_val = request.form.get(f'hidden_in_{i}')
            out_val = request.form.get(f'hidden_out_{i}')
            if in_val and out_val:
                cursor.execute('''
                    INSERT INTO test_cases (question_id, input, expected_output, is_sample)
                    VALUES (?, ?, ?, ?)
                ''', (question_id, in_val, out_val, False))
                
        conn.commit()
        success = True
        
    questions = conn.execute('SELECT * FROM questions ORDER BY id DESC').fetchall()
    conn.close()
    
    return render_template('add_question.html', success=success, questions=questions)

@app.route('/edit-question/<int:id>', methods=['GET', 'POST'])
def edit_question(id):
    if session.get('role') != 'admin':
        return "Access denied", 403

    conn = get_db_connection()

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        difficulty = request.form.get('difficulty')
        
        if not title or not description or not difficulty:
            conn.close()
            return "Missing mandatory fields", 400
            
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE questions
            SET title=?, description=?, difficulty=?
            WHERE id=?
        ''', (title, description, difficulty, id))
        
        cursor.execute('DELETE FROM test_cases WHERE question_id=?', (id,))
        
        # 2. Insert Sample Test Cases (2)
        for i in range(1, 3):
            in_val = request.form.get(f'sample_in_{i}')
            out_val = request.form.get(f'sample_out_{i}')
            if in_val and out_val:
                cursor.execute('''
                    INSERT INTO test_cases (question_id, input, expected_output, is_sample)
                    VALUES (?, ?, ?, ?)
                ''', (id, in_val, out_val, True))
                
        # 3. Insert Hidden Test Cases (5)
        for i in range(1, 6):
            in_val = request.form.get(f'hidden_in_{i}')
            out_val = request.form.get(f'hidden_out_{i}')
            if in_val and out_val:
                cursor.execute('''
                    INSERT INTO test_cases (question_id, input, expected_output, is_sample)
                    VALUES (?, ?, ?, ?)
                ''', (id, in_val, out_val, False))
                
        conn.commit()
        conn.close()
        return redirect(url_for('add_question'))
        
    question = conn.execute('SELECT * FROM questions WHERE id = ?', (id,)).fetchone()
    if not question:
        conn.close()
        return "Question not found", 404
        
    test_cases = conn.execute('SELECT * FROM test_cases WHERE question_id = ?', (id,)).fetchall()
    conn.close()
    
    sample_cases = [tc for tc in test_cases if tc['is_sample']]
    hidden_cases = [tc for tc in test_cases if not tc['is_sample']]
    
    # Pad cases so the form always has 2 sample and 5 hidden inputs
    while len(sample_cases) < 2:
        sample_cases.append({'input': '', 'expected_output': ''})
    while len(hidden_cases) < 5:
        hidden_cases.append({'input': '', 'expected_output': ''})
        
    return render_template('edit_question.html', question=question, sample_cases=sample_cases, hidden_cases=hidden_cases)

@app.route('/delete-question/<int:id>', methods=['POST'])
def delete_question(id):
    if session.get('role') != 'admin':
        return "Access denied", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if question exists
    question = cursor.execute('SELECT id FROM questions WHERE id = ?', (id,)).fetchone()
    if not question:
        conn.close()
        return "Question not found", 404
        
    cursor.execute('DELETE FROM test_cases WHERE question_id=?', (id,))
    cursor.execute('DELETE FROM questions WHERE id=?', (id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('add_question'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
        
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', 'user') # default to user
    
    if not username or not password:
        return "Username and password required", 400
        
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                     (username, generate_password_hash(password), role))
        conn.commit()
    except sqlite3.IntegrityError:
        return "Username already exists", 400
    finally:
        conn.close()
        
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
        
    username = request.form.get('username')
    password = request.form.get('password')
    
    current_time = time.time()
    user_attempt = login_attempts.get(username, {'attempts': 0, 'locked_until': 0})
    
    if user_attempt['locked_until'] > current_time:
        remaining_time = int(user_attempt['locked_until'] - current_time)
        return render_template('login.html', error=f"Too many failed attempts. Please wait {remaining_time} seconds before trying again.")
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password'], password):
        if username in login_attempts:
            del login_attempts[username]
            
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        
        if user['role'] == 'admin':
            return redirect(url_for('add_question'))
        else:
            return redirect(url_for('index'))
            
    user_attempt['attempts'] += 1
    if user_attempt['attempts'] >= MAX_ATTEMPTS:
        user_attempt['locked_until'] = current_time + LOCKOUT_TIME
        user_attempt['attempts'] = 0
        login_attempts[username] = user_attempt
        error_msg = f"Too many failed attempts. Please wait {LOCKOUT_TIME} seconds before trying again."
    else:
        login_attempts[username] = user_attempt
        remaining_attempts = MAX_ATTEMPTS - user_attempt['attempts']
        error_msg = f"Wrong password. You have {remaining_attempts} chances left."
        
    return render_template('login.html', error=error_msg)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/questions')
def get_all_questions():
    conn = get_db_connection()
    questions = conn.execute('SELECT id, title, difficulty FROM questions ORDER BY id ASC').fetchall()
    conn.close()
    return jsonify([{"id": q["id"], "title": q["title"], "difficulty": q["difficulty"]} for q in questions])

@app.route('/api/question')
def get_question():
    conn = get_db_connection()
    question_id = request.args.get('id', type=int)
    if question_id:
        question = conn.execute('SELECT * FROM questions WHERE id = ?', (question_id,)).fetchone()
    else:
        question = conn.execute('SELECT * FROM questions ORDER BY RANDOM() LIMIT 1').fetchone()
    if not question:
        return jsonify({"error": "No questions found"}), 404
    
    test_cases = conn.execute('SELECT * FROM test_cases WHERE question_id = ?', (question['id'],)).fetchall()
    
    sample_cases = [{"input": tc["input"], "expected_output": tc["expected_output"]} for tc in test_cases if tc["is_sample"]]
    hidden_count = sum(1 for tc in test_cases if not tc["is_sample"])
    
    return jsonify({
        "id": question["id"],
        "title": question["title"],
        "description": question["description"],
        "difficulty": question["difficulty"],
        "sample_test_cases": sample_cases,
        "hidden_test_cases_count": hidden_count
    })

def execute_code(code, input_data, language='python'):
    if language == 'cpp':
        temp_file = 'temp_code.cpp'
        exe_file = 'temp_code.exe' if os.name == 'nt' else './temp_code.out'
        with open(temp_file, 'w') as f:
            f.write(code)
        
        # Check if g++ is in C:\TDM-GCC-64\bin\g++.exe
        gpp_cmd = 'g++'
        if os.name == 'nt' and os.path.exists(r'C:\TDM-GCC-64\bin\g++.exe'):
            gpp_cmd = r'C:\TDM-GCC-64\bin\g++.exe'
        
        try:
            compile_result = subprocess.run(
                [gpp_cmd, temp_file, '-o', exe_file.replace('./', '')],
                capture_output=True,
                text=True
            )
            if compile_result.returncode != 0:
                return {"error": "Compilation Error:\n" + compile_result.stderr}
            
            run_cmd = [exe_file.replace('./', '')] if os.name == 'nt' else [exe_file]
            result = subprocess.run(
                run_cmd,
                input=input_data,
                text=True,
                capture_output=True,
                timeout=3
            )
            if result.returncode != 0:
                return {"error": result.stderr}
            return {"output": result.stdout}
        except subprocess.TimeoutExpired:
            return {"error": "Execution Timeout (3s limit)"}
        except FileNotFoundError:
            return {"error": "C++ Compiler (g++) not found. Please install MinGW/g++ and add it to your system PATH."}
        except Exception as e:
            return {"error": str(e)}
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            exe_to_remove = exe_file.replace('./', '')
            if os.path.exists(exe_to_remove):
                os.remove(exe_to_remove)
    else:
        temp_file = 'temp_code.py'
        with open(temp_file, 'w') as f:
            f.write(code)
        
        try:
            result = subprocess.run(
                ['python', temp_file],
                input=input_data,
                text=True,
                capture_output=True,
                timeout=3
            )
            if result.returncode != 0:
                return {"error": result.stderr}
            return {"output": result.stdout}
        except subprocess.TimeoutExpired:
            return {"error": "Execution Timeout (3s limit)"}
        except Exception as e:
            return {"error": str(e)}
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

@app.route('/api/run', methods=['POST'])
def run_code():
    data = request.json
    code = data.get('code', '')
    custom_input = data.get('custom_input', '')
    language = data.get('language', 'python')
    
    result = execute_code(code, custom_input, language)
    return jsonify(result)

@app.route('/api/submit', methods=['POST'])
def submit_code():
    data = request.json
    code = data.get('code', '')
    question_id = data.get('question_id')
    language = data.get('language', 'python')
    
    conn = get_db_connection()
    test_cases = conn.execute('SELECT * FROM test_cases WHERE question_id = ?', (question_id,)).fetchall()
    
    results = []
    
    for tc in test_cases:
        test_input = tc["input"].replace('\\n', '\n') if tc["input"] else ""
        res = execute_code(code, test_input, language)
        is_pass = False
        actual_output = None
        error_msg = res.get("error")
        
        if "output" in res:
            # Replace literal '\\n' with actual newline for comparison
            actual_output = res["output"]
            expected = tc["expected_output"].replace('\\n', '\n') if tc["expected_output"] else ""
            
            # Normalize strings by stripping trailing/leading whitespace from each line
            actual_lines = [line.strip() for line in actual_output.strip().splitlines()]
            expected_lines = [line.strip() for line in expected.strip().splitlines()]
            
            if actual_lines == expected_lines:
                is_pass = True
        
        results.append({
            "id": tc["id"],
            "is_sample": bool(tc["is_sample"]),
            "input": tc["input"] if tc["is_sample"] else None,
            "expected_output": tc["expected_output"] if tc["is_sample"] else None,
            "actual_output": actual_output if tc["is_sample"] else None,
            "error": error_msg,
            "status": "PASS" if is_pass else "FAIL"
        })
        
    return jsonify({"results": results})

if __name__ == '__main__':
    from database import init_db
    init_db()
    app.run(debug=True, port=5000)
