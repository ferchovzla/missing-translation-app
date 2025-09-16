// TransQA Landing Page JavaScript

// Smooth scrolling for demo button
function scrollToDemo() {
    document.getElementById('demo').scrollIntoView({
        behavior: 'smooth'
    });
}

// DOM elements
const analysisForm = document.getElementById('analysisForm');
const resultsSection = document.getElementById('results');
const loadingSection = document.getElementById('loading');
const errorSection = document.getElementById('error');
const analyzeBtn = document.getElementById('analyzeBtn');

// Form submission handler
analysisForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(analysisForm);
    const requestData = {
        url: formData.get('url'),
        target_language: formData.get('language'),
        render_js: formData.has('renderJs')
    };
    
    // Validate form
    if (!requestData.url || !requestData.target_language) {
        showError('Please fill in all required fields.');
        return;
    }
    
    // Show loading state
    showLoading();
    
    try {
        // Make API request
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            showResults(result);
        } else {
            showError(result.error_message || 'Analysis failed for unknown reason.');
        }
        
    } catch (error) {
        console.error('Analysis error:', error);
        showError(`Failed to analyze URL: ${error.message}`);
    }
});

function showLoading() {
    hideAllSections();
    loadingSection.style.display = 'block';
    
    // Update button state
    analyzeBtn.innerHTML = `
        <div class="loading-spinner" style="width: 1rem; height: 1rem; margin-right: 0.5rem;"></div>
        <span>Analyzing...</span>
    `;
    analyzeBtn.disabled = true;
}

function showResults(result) {
    hideAllSections();
    resultsSection.style.display = 'block';
    
    // Reset button state
    resetButton();
    
    // Update results header
    document.querySelector('.results-url').textContent = result.url;
    
    // Update statistics
    document.getElementById('totalIssues').textContent = result.stats.total_issues;
    document.getElementById('processingTime').textContent = `${result.processing_time.toFixed(2)}s`;
    document.getElementById('targetPercentage').textContent = `${Math.round(result.stats.target_language_percentage)}%`;
    
    // Update issues list
    displayIssues(result.issues);
    
    // Update languages list
    displayLanguages(result.stats.detected_languages);
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function showError(message) {
    hideAllSections();
    errorSection.style.display = 'block';
    document.getElementById('errorMessage').textContent = message;
    
    // Reset button state
    resetButton();
    
    // Scroll to error
    errorSection.scrollIntoView({ behavior: 'smooth' });
}

function hideAllSections() {
    resultsSection.style.display = 'none';
    loadingSection.style.display = 'none';
    errorSection.style.display = 'none';
}

function resetButton() {
    analyzeBtn.innerHTML = `
        <i class="fas fa-search"></i>
        <span>Analyze Quality</span>
    `;
    analyzeBtn.disabled = false;
}

function displayIssues(issues) {
    const issuesList = document.getElementById('issuesList');
    
    if (issues.length === 0) {
        issuesList.innerHTML = `
            <div class="no-issues">
                <i class="fas fa-check-circle" style="color: var(--success-color); font-size: 2rem; margin-bottom: 1rem;"></i>
                <p>No translation quality issues detected! 🎉</p>
            </div>
        `;
        return;
    }
    
    issuesList.innerHTML = issues.map(issue => `
        <div class="issue-item severity-${issue.severity}">
            <div class="issue-header">
                <div class="issue-type">${formatIssueType(issue.type)}</div>
                <div class="issue-severity severity-${issue.severity}">${issue.severity}</div>
            </div>
            <div class="issue-message">${escapeHtml(issue.message)}</div>
            ${issue.suggestion ? `<div class="issue-suggestion"><strong>Suggestion:</strong> ${escapeHtml(issue.suggestion)}</div>` : ''}
            <div class="issue-snippet">${escapeHtml(issue.snippet)}</div>
            <div class="issue-meta">
                <small>Confidence: ${Math.round(issue.confidence * 100)}%</small>
            </div>
        </div>
    `).join('');
}

function displayLanguages(languages) {
    const languagesList = document.getElementById('languagesList');
    
    if (Object.keys(languages).length === 0) {
        languagesList.innerHTML = '<p>No language information available.</p>';
        return;
    }
    
    // Sort languages by percentage (descending)
    const sortedLanguages = Object.entries(languages)
        .sort(([,a], [,b]) => b - a);
    
    languagesList.innerHTML = sortedLanguages.map(([lang, percentage]) => `
        <div class="language-item">
            <div class="language-name">${getLanguageName(lang)}</div>
            <div class="language-percentage">${Math.round(percentage)}%</div>
        </div>
    `).join('');
}

function formatIssueType(type) {
    return type.replace(/_/g, ' ')
               .replace(/\b\w/g, l => l.toUpperCase());
}

function getLanguageName(code) {
    const languageNames = {
        'es': 'Spanish',
        'en': 'English',
        'nl': 'Dutch',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese',
        'ca': 'Catalan',
        'eu': 'Basque',
        'gl': 'Galician'
    };
    
    return languageNames[code] || code.toUpperCase();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Example URLs for quick testing
const exampleUrls = [
    'https://example.com',
    'https://www.wikipedia.org',
    'https://www.google.com',
    'https://github.com'
];

// Add some example URL suggestions (optional enhancement)
document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('url');
    
    // Add placeholder with rotating examples
    let exampleIndex = 0;
    setInterval(() => {
        if (!urlInput.value) {
            urlInput.placeholder = exampleUrls[exampleIndex % exampleUrls.length];
            exampleIndex++;
        }
    }, 3000);
    
    // Add form validation styling
    const inputs = analysisForm.querySelectorAll('input, select');
    inputs.forEach(input => {
        input.addEventListener('invalid', () => {
            input.classList.add('error');
        });
        
        input.addEventListener('input', () => {
            input.classList.remove('error');
        });
    });
});

// Add error styling for form validation
const style = document.createElement('style');
style.textContent = `
    .form-group input.error,
    .form-group select.error {
        border-color: var(--danger-color);
        box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
    }
    
    .no-issues {
        text-align: center;
        padding: 2rem;
        color: var(--gray-600);
    }
    
    .issue-suggestion {
        margin: 0.5rem 0;
        padding: 0.5rem;
        background: rgba(16, 185, 129, 0.1);
        border-left: 3px solid var(--success-color);
        border-radius: var(--border-radius);
        font-size: 0.875rem;
    }
    
    .issue-meta {
        margin-top: 0.5rem;
        padding-top: 0.5rem;
        border-top: 1px solid var(--gray-200);
    }
    
    .issue-meta small {
        color: var(--gray-500);
    }
`;
document.head.appendChild(style);
