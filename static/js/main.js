let editor;
let currentQuestionId = null;

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

// Monaco setup
window.addEventListener('monacoReady', () => {
    editor = monaco.editor.create(document.getElementById('editorContainer'), {
        value: `# Write your python code here
import sys

def main():
    # Read from stdin
    input_data = sys.stdin.read().split()
    
    # Your logic here
    print("Hello", input_data)

if __name__ == "__main__":
    main()`,
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

// Fetch Question Data
async function fetchQuestion() {
    try {
        const res = await fetch('/api/question');
        const data = await res.json();

        if (data.error) {
            document.getElementById('questionTitle').textContent = 'Error loading question';
            return;
        }

        currentQuestionId = data.id;
        document.getElementById('questionTitle').textContent = data.title;
        document.getElementById('questionDescription').innerHTML = `<p>${data.description.replace(/\\n/g, '<br>')}</p>`;

        const difficultyBadge = document.getElementById('difficultyBadge');
        difficultyBadge.textContent = data.difficulty;
        difficultyBadge.className = `difficulty ${data.difficulty.toLowerCase()}`;

        // Populate sample test cases
        const sampleContainer = document.getElementById('sampleTestCases');
        // Clear skeletons / placeholders
        sampleContainer.innerHTML = '';

        data.sample_test_cases.forEach((tc, idx) => {
            const div = document.createElement('div');
            div.className = 'sample-case';
            div.innerHTML = `
                <strong>Input:</strong>
                <span>${tc.input}</span>
                <strong>Output:</strong>
                <span>${tc.expected_output}</span>
            `;
            sampleContainer.appendChild(div);
        });

        document.getElementById('hiddenCasesLabel').textContent = `Hidden Test Cases (${data.hidden_test_cases_count} cases)`;
        document.getElementById('testResultsSection').style.display = 'none';

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
    const customInput = document.getElementById('customInput').value;

    switchToTab('custom-out');
    outputDisplay.innerHTML = '<span class="placeholder">Executing code... <i class="fa-solid fa-circle-notch fa-spin"></i></span>';

    try {
        const res = await fetch('/api/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, custom_input: customInput })
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


    try {
        const res = await fetch('/api/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, question_id: currentQuestionId })
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

// Load question on startup
document.addEventListener('DOMContentLoaded', fetchQuestion);
