import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_FILE = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create Questions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            difficulty TEXT
        )
    ''')
    
    # Create TestCases Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER,
            input TEXT,
            expected_output TEXT,
            is_sample BOOLEAN,
            FOREIGN KEY (question_id) REFERENCES questions (id)
        )
    ''')
    
    # Create Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        # Seed initial users
        cursor.execute('''
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
        ''', ('admin', generate_password_hash('hashed_password'), 'admin'))
        
        cursor.execute('''
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
        ''', ('student1', generate_password_hash('hashed_password'), 'user'))
        
        questions_data = [
            {
                "title": "Longest Common Prefix",
                "description": "Write a function to find the longest common prefix string amongst an array of strings.\\n\\nThe input is expected as a space-separated list of words. Print the resulting prefix to stdout.\\n\\nExample: \"flower flow flight\" -> \"fl\"\\nExample: \"dog racecar car\" -> \"\"",
                "difficulty": "Easy",
                "test_cases": [
                    ("flower flow flight", "fl", True),
                    ("dog racecar car", "", True),
                    ("interspecies interstellar interstate", "inters", False),
                    ("throne throne", "throne", False),
                    ("apple ape april", "ap", False),
                    ("", "", False),
                    ("single", "single", False)
                ]
            },
            {
                "title": "Anagram Checker",
                "description": "Check whether two strings are anagrams.\\nIgnore spaces and case.\\n\\nInput format:\\nDormitory, dirty room\\n\\nOutput:\\nanagrams or not anagrams",
                "difficulty": "Easy",
                "test_cases": [
                    ("Dormitory, dirty room", "anagrams", True),
                    ("listen, silent", "anagrams", True),
                    ("hello, world", "not anagrams", False),
                    ("evil, vile", "anagrams", False),
                    ("test, best", "not anagrams", False),
                    ("triangle, integral", "anagrams", False),
                    ("apple, paple", "anagrams", False)
                ]
            },
            {
                "title": "Reverse Words",
                "description": "Reverse each word in the sentence while keeping word order.\\n\\nInput:\\nhello world\\nOutput:\\nolleh dlrow",
                "difficulty": "Easy",
                "test_cases": [
                    ("hello world", "olleh dlrow", True),
                    ("Python is fun", "nohtyP si nuf", True),
                    ("a b c", "a b c", False),
                    ("racecar level", "racecar level", False),
                    ("coding test", "gnidoc tset", False),
                    ("single", "elgnis", False),
                    ("empty string", "ytpme gnirts", False)
                ]
            },
            {
                "title": "Count Vowels",
                "description": "Count the number of vowels in the input string.\\n\\nInput:\\nhello\\nOutput:\\n2",
                "difficulty": "Easy",
                "test_cases": [
                    ("hello", "2", True),
                    ("programming", "3", True),
                    ("sky", "0", False),
                    ("AEIOU", "5", False),
                    ("ChatGPT", "1", False),
                    ("education", "5", False),
                    ("rhythm", "0", False)
                ]
            }
        ]
        
        for q in questions_data:
            cursor.execute('''
                INSERT INTO questions (title, description, difficulty)
                VALUES (?, ?, ?)
            ''', (q["title"], q["description"], q["difficulty"]))
            
            question_id = cursor.lastrowid
            
            for tc_input, tc_output, is_sample in q["test_cases"]:
                cursor.execute('''
                    INSERT INTO test_cases (question_id, input, expected_output, is_sample)
                    VALUES (?, ?, ?, ?)
                ''', (question_id, tc_input, tc_output, is_sample))

            
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully with new questions.")
