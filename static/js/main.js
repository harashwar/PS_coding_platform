let editor;
let currentQuestionId = null;
let currentSampleCases = [];

// Initialize layout resizer
const resizer = document.getElementById('dragMe');
const leftPanel = document.querySelector('.left-panel');
const rightPanel = document.querySelector('.right-panel');

let isResizing = false;

resizer.addEventListener('mousedown', (e) => {
    isResizing = true;
    document.body.style.cursor = 'col-resize';
});

document.addEventListener('mousemove', (e) => {
    if (!isResizing) return;
    const containerWidth = document.body.clientWidth;
    const newLeftWidth = (e.clientX / containerWidth) * 100;

    if (newLeftWidth > 20 && newLeftWidth < 80) {
        leftPanel.style.flex = `0 0 ${newLeftWidth}%`;
        rightPanel.style.flex = `1 1 0%`;
        if (editor) editor.layout();
    }
});

document.addEventListener('mouseup', () => {
    isResizing = false;
    document.body.style.cursor = 'default';
});

// Default codes
const defaultCode = {
    'python': `# Write your python code here
import sys

def main():
    # Read from stdin
    input_data = sys.stdin.read().split()
    
    # Your logic here
    print("Hello", input_data)

if __name__ == "__main__":
    main()`,
    'cpp': `// Write your C++ code here
#include <iostream>
#include <string>

using namespace std;

int main() {
    string input_data;
    if (cin >> input_data) {
        cout << "Hello " << input_data << endl;
    } else {
        cout << "Hello " << endl;
    }
    return 0;
}
`
};

// Monaco setup
window.addEventListener('monacoReady', () => {
    editor = monaco.editor.create(document.getElementById('editorContainer'), {
        value: defaultCode['python'],
        language: 'python',
        theme: 'vs-dark',
        automaticLayout: true,
        fontSize: 14,
        fontFamily: "'JetBrains Mono', monospace",
        tabSize: 4,
        minimap: { enabled: false },
        lineNumbers: 'on',
        scrollBeyondLastLine: false,
        roundedSelection: false,
        padding: { top: 16, bottom: 16 }
    });
    
    const languageSelect = document.getElementById('languageSelect');
    if (languageSelect) {
        languageSelect.addEventListener('change', (e) => {
            const lang = e.target.value;
            monaco.editor.setModelLanguage(editor.getModel(), lang);
            editor.setValue(defaultCode[lang]);
        });
    }
    
    // Add reset button functionality
    const resetBtn = document.getElementById('resetCodeBtn');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            const lang = languageSelect ? languageSelect.value : 'python';
            editor.setValue(defaultCode[lang]);
        });
    }
});

// UI Tabs Logic
const tabs = document.querySelectorAll('.tab');
const tabContents = document.querySelectorAll('.tab-content');

tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));

        tab.classList.add('active');
        document.getElementById(tab.dataset.tab).classList.add('active');
    });
});

function switchToTab(tabId) {
    document.querySelector(`.tab[data-tab="${tabId}"]`).click();
}

// Fetch a specific question by ID
async function fetchQuestionById(id) {
    try {
        const res = await fetch(`/api/question?id=${id}`);
        const data = await res.json();
        if (data.error) {
            document.getElementById('questionTitle').textContent = 'Error loading question';
            return;
        }
        loadQuestionData(data);
    } catch (err) {
        console.error('Failed to fetch question by id:', err);
    }
}

// Load question data into the UI
function loadQuestionData(data) {
    currentQuestionId = data.id;
    currentSampleCases = data.sample_test_cases;
    document.getElementById('questionTitle').textContent = data.title;
    const descHtml = data.description.replace(/\\n/g, '<br>').replace(/\n/g, '<br>');
    document.getElementById('questionDescription').innerHTML = `<p>${descHtml}</p>`;

    const difficultyBadge = document.getElementById('difficultyBadge');
    difficultyBadge.textContent = data.difficulty;
    difficultyBadge.className = `difficulty ${data.difficulty.toLowerCase()}`;

    const sampleContainer = document.getElementById('sampleTestCases');
    sampleContainer.innerHTML = '';

    data.sample_test_cases.forEach((tc) => {
        const div = document.createElement('div');
        div.className = 'sample-case';
        const inputStr = tc.input || '';
        const outputStr = tc.expected_output || '';
        const formattedInput = inputStr.replace(/\\n/g, '<br>').replace(/\n/g, '<br>');
        const formattedOutput = outputStr.replace(/\\n/g, '<br>').replace(/\n/g, '<br>');
        div.innerHTML = `
            <strong>Input:</strong>
            <span>${formattedInput}</span>
            <strong>Output:</strong>
            <span>${formattedOutput}</span>
        `;
        sampleContainer.appendChild(div);
    });

    document.getElementById('hiddenCasesLabel').textContent = `Hidden Test Cases (${data.hidden_test_cases_count} cases)`;
    document.getElementById('testResultsSection').style.display = 'none';
}

// Fetch Question Data (random)
async function fetchQuestion() {
    try {
        const res = await fetch('/api/question');
        const data = await res.json();
        if (data.error) {
            document.getElementById('questionTitle').textContent = 'Error loading question';
            return;
        }
        loadQuestionData(data);
    } catch (err) {
        console.error('Failed to fetch question:', err);
    }
}

// Controls
const runBtn = document.getElementById('runBtn');
const submitBtn = document.getElementById('submitBtn');
const outputDisplay = document.getElementById('outputDisplay');
const resultsContainer = document.getElementById('resultsContainer');

runBtn.addEventListener('click', async () => {
    if (!editor) return;

    const code = editor.getValue();
    let customInput = document.getElementById('customInput').value;

    // Auto-fill random sample test case if input is empty
    if (!customInput || customInput.trim() === '') {
        if (currentSampleCases && currentSampleCases.length > 0) {
            const randomCase = currentSampleCases[Math.floor(Math.random() * currentSampleCases.length)];
            // Replace '\\n' from DB literal back to actual newline for input box
            customInput = randomCase.input ? randomCase.input.replace(/\\n/g, '\n') : '';
            document.getElementById('customInput').value = customInput;
        }
    }

    switchToTab('custom-out');
    outputDisplay.innerHTML = '<span class="placeholder">Executing code... <i class="fa-solid fa-circle-notch fa-spin"></i></span>';

    const languageSelect = document.getElementById('languageSelect');
    const language = languageSelect ? languageSelect.value : 'python';

    try {
        const res = await fetch('/api/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, custom_input: customInput, language })
        });
        const data = await res.json();

        outputDisplay.innerHTML = '';
        if (data.error) {
            const errSpan = document.createElement('span');
            errSpan.className = 'error-text';
            errSpan.textContent = data.error;
            outputDisplay.appendChild(errSpan);
        } else {
            const outSpan = document.createElement('span');
            outSpan.textContent = data.output || 'Program ran successfully without output.';
            outputDisplay.appendChild(outSpan);
        }
    } catch (e) {
        outputDisplay.innerHTML = `<span class="error-text">Network Error: ${e.message}</span>`;
    }
});

submitBtn.addEventListener('click', async () => {
    if (!editor || !currentQuestionId) return;

    const code = editor.getValue();

    document.getElementById('testResultsSection').style.display = 'block';
    resultsContainer.innerHTML = '<div class="placeholder" style="padding: 12px;">Running test cases... <i class="fa-solid fa-circle-notch fa-spin"></i></div>';


    const languageSelect = document.getElementById('languageSelect');
    const language = languageSelect ? languageSelect.value : 'python';

    try {
        const res = await fetch('/api/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, question_id: currentQuestionId, language })
        });
        const data = await res.json();

        resultsContainer.innerHTML = '';

        let allPassed = true;

        data.results.forEach((tc, index) => {
            if (tc.status === 'FAIL') allPassed = false;

            const card = document.createElement('div');
            card.className = `result-card ${tc.status.toLowerCase()}`;

            const label = tc.is_sample ? `Sample Test Case ${index + 1}` : `Hidden Test Case ${index + 1}`;

            card.innerHTML = `
                <div class="r-label"><i class="fa-solid ${tc.is_sample ? 'fa-vial' : 'fa-lock'}"></i> ${label}</div>
                <div class="r-status ${tc.status.toLowerCase()}">${tc.status === 'PASS' ? '🟢 PASS' : '🔴 FAIL'}</div>
            `;

            resultsContainer.appendChild(card);
        });

    } catch (e) {
        resultsContainer.innerHTML = `<span class="error-text" style="padding:12px;">Network Error: ${e.message}</span>`;
    }
});

// ─── Search Bar Logic ────────────────────────────────────
let allQuestions = [];

async function initSearchBar() {
    try {
        const res = await fetch('/api/questions');
        allQuestions = await res.json();
        document.getElementById('dropdownLoading').style.display = 'none';
        renderDropdown('');
    } catch (e) {
        console.error('Failed to load questions for search:', e);
    }
}

function renderDropdown(query) {
    const ul = document.getElementById('questionList');
    const emptyMsg = document.getElementById('dropdownEmpty');
    const q = query.toLowerCase().trim();
    const filtered = q
        ? allQuestions.filter(qn => qn.title.toLowerCase().includes(q))
        : allQuestions;

    ul.innerHTML = '';
    if (filtered.length === 0) {
        emptyMsg.style.display = 'flex';
        return;
    }
    emptyMsg.style.display = 'none';

    filtered.forEach(qn => {
        const li = document.createElement('li');
        li.innerHTML = `
            <span class="q-id">#${qn.id}</span>
            <span class="q-title">${qn.title}</span>
            <span class="q-diff ${qn.difficulty.toLowerCase()}">${qn.difficulty}</span>
        `;
        li.addEventListener('click', () => {
            closeDropdown();
            document.getElementById('questionSearchInput').value = '';
            fetchQuestionById(qn.id);
        });
        ul.appendChild(li);
    });
}

function openDropdown() {
    document.getElementById('questionDropdown').classList.add('open');
}

function closeDropdown() {
    document.getElementById('questionDropdown').classList.remove('open');
}

const searchInput = document.getElementById('questionSearchInput');

searchInput.addEventListener('focus', () => {
    openDropdown();
    renderDropdown(searchInput.value);
});

searchInput.addEventListener('input', () => {
    openDropdown();
    renderDropdown(searchInput.value);
});

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    const wrapper = document.getElementById('questionSearchWrapper');
    if (!wrapper.contains(e.target)) {
        closeDropdown();
    }
});

// Keyboard shortcut: Ctrl+K / Cmd+K to focus search
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        searchInput.focus();
        openDropdown();
    }
    if (e.key === 'Escape') {
        closeDropdown();
        searchInput.blur();
    }
});

// Load question on startup
document.addEventListener('DOMContentLoaded', () => {
    fetchQuestion();
    initSearchBar();
});
