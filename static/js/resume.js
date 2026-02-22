let currentJobDescription = '';
let currentAnalysis = null;

// Resume source state
let profileResumeData = null;
let uploadedResumeText = null;
let currentResumeSource = 'profile';

// =============================================
// Initialization
// =============================================

document.addEventListener('DOMContentLoaded', async function() {
    // Cover letter word count
    document.getElementById('cover-letter-text').addEventListener('input', updateWordCount);

    // Resume source radio buttons — one handler reads e.target.value
    document.querySelectorAll('[name="resume-source"]').forEach(radio => {
        radio.addEventListener('change', (e) => switchResumeSource(e.target.value));
    });

    // Upload dropzone drag-and-drop
    const dropzone = document.getElementById('upload-dropzone');
    dropzone.addEventListener('drop', handleResumeDrop);
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('border-green-400', 'bg-green-50');
    });
    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('border-green-400', 'bg-green-50');
    });

    // Upload file input
    document.getElementById('resume-file-input').addEventListener('change', function() {
        handleResumeFileSelect(this);
    });

    // Paste buttons
    document.getElementById('paste-job-btn').addEventListener('click', () => pasteFromClipboard('job-description'));
    document.getElementById('paste-resume-btn').addEventListener('click', () => pasteFromClipboard('resume-text'));

    // Action buttons in match/analysis results
    document.getElementById('save-to-app-btn').addEventListener('click', saveToApplication);
    document.getElementById('get-tailoring-btn').addEventListener('click', getTailoringSuggestions);
    document.getElementById('save-resume-text-btn').addEventListener('click', saveResumeTextToProfile);
    document.getElementById('save-uploaded-btn').addEventListener('click', saveUploadedToProfile);
    document.getElementById('clear-upload-btn').addEventListener('click', clearUpload);

    // Cover letter action buttons
    document.getElementById('copy-cover-btn').addEventListener('click', copyCoverLetter);
    document.getElementById('download-cover-btn').addEventListener('click', downloadCoverLetter);
    document.getElementById('open-save-app-btn').addEventListener('click', openSaveToAppModal);

    // Save to application modal
    document.getElementById('close-save-app-btn').addEventListener('click', closeSaveAppModal);
    document.getElementById('cancel-save-app-btn').addEventListener('click', closeSaveAppModal);
    document.getElementById('save-app-modal').addEventListener('click', function(e) {
        if (e.target === this) closeSaveAppModal();
    });

    // Escape closes modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeSaveAppModal();
    });

    // Form submissions
    document.getElementById('analyze-form').addEventListener('submit', handleAnalyzeSubmit);
    document.getElementById('match-form').addEventListener('submit', handleMatchSubmit);
    document.getElementById('cover-letter-form').addEventListener('submit', handleCoverLetterSubmit);
    document.getElementById('save-app-form').addEventListener('submit', handleSaveAppSubmit);

    // Initialize resume source UI
    loadProfileResume();
    switchResumeSource('profile');
    document.getElementById('tailoring-results').classList.remove('hidden');
});

// =============================================
// Toast Notifications
// =============================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');

    const bgColors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        info: 'bg-blue-500',
        warning: 'bg-yellow-500'
    };

    toast.className = `${bgColors[type]} text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 animate-fade-in`;

    const msgSpan = document.createElement('span');
    msgSpan.textContent = message;
    toast.appendChild(msgSpan);

    const closeBtn = document.createElement('button');
    closeBtn.className = 'ml-2 hover:opacity-75';
    closeBtn.innerHTML = '&times;';
    closeBtn.addEventListener('click', () => toast.remove());
    toast.appendChild(closeBtn);

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function setButtonLoading(button, loading) {
    if (loading) {
        button.disabled = true;
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = '<span class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span>Processing...';
    } else {
        button.disabled = false;
        button.innerHTML = button.dataset.originalText || button.innerHTML;
    }
}

// =============================================
// Clipboard / Steps
// =============================================

async function pasteFromClipboard(elementId) {
    try {
        const text = await navigator.clipboard.readText();
        document.getElementById(elementId).value = text;
        showToast('Pasted from clipboard', 'success');
    } catch (e) {
        showToast('Unable to access clipboard. Please paste manually.', 'warning');
    }
}

function updateSteps(completedStep) {
    for (let i = 1; i <= 3; i++) {
        const step = document.getElementById(`step-${i}`);
        step.classList.remove('active', 'completed');
        if (i < completedStep) {
            step.classList.add('completed');
        } else if (i === completedStep) {
            step.classList.add('active');
        }
    }
}

function unlockSections() {
    document.getElementById('match-overlay').classList.add('hidden');
    document.getElementById('cover-overlay').classList.add('hidden');
}

// =============================================
// Profile / Application Saving
// =============================================

async function saveResumeToProfile() {
    const resumeText = document.getElementById('resume-text').value;
    if (!resumeText.trim()) {
        showToast('Please enter your resume first', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/profile/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ resume_summary: resumeText })
        });

        if (response.ok) {
            showToast('Resume saved to profile', 'success');
        } else {
            throw new Error('Failed to save');
        }
    } catch (e) {
        showToast('Error saving resume to profile', 'error');
    }
}

async function saveToApplication() {
    const company = document.getElementById('cl-company').value || 'Unknown Company';
    const role = document.getElementById('cl-role').value || 'Unknown Role';

    document.getElementById('app-company').value = company;
    document.getElementById('app-title').value = role;
    document.getElementById('save-app-modal').classList.remove('hidden');
}

function openSaveToAppModal() {
    const company = document.getElementById('cl-company').value;
    const role = document.getElementById('cl-role').value;

    document.getElementById('app-company').value = company;
    document.getElementById('app-title').value = role;
    document.getElementById('save-app-modal').classList.remove('hidden');
}

function closeSaveAppModal() {
    document.getElementById('save-app-modal').classList.add('hidden');
}

async function handleSaveAppSubmit(e) {
    e.preventDefault();

    const company = document.getElementById('app-company').value;
    const title = document.getElementById('app-title').value;
    const url = document.getElementById('app-url').value;
    const includeCover = document.getElementById('app-include-cover').checked;
    const coverLetter = document.getElementById('cover-letter-text').value;

    let notes = '';
    if (includeCover && coverLetter) {
        notes = `Cover Letter:\n\n${coverLetter}`;
    }

    try {
        const response = await fetch('/api/applications/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                company_name: company,
                job_title: title,
                job_url: url || null,
                notes: notes || null,
                status: 'saved'
            })
        });

        if (response.ok) {
            showToast('Application saved successfully!', 'success');
            closeSaveAppModal();
        } else {
            throw new Error('Failed to save application');
        }
    } catch (e) {
        showToast('Error saving application', 'error');
    }
}

// =============================================
// Cover Letter Utilities
// =============================================

function downloadCoverLetter() {
    const text = document.getElementById('cover-letter-text').value;
    const company = document.getElementById('cl-company').value || 'Company';
    const role = document.getElementById('cl-role').value || 'Role';
    const filename = `Cover_Letter_${company.replace(/\s+/g, '_')}_${role.replace(/\s+/g, '_')}.txt`;

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);

    showToast('Cover letter downloaded', 'success');
}

function updateWordCount() {
    const text = document.getElementById('cover-letter-text').value;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    document.getElementById('word-count').textContent = `${words} words`;
}

async function copyCoverLetter() {
    try {
        const text = document.getElementById('cover-letter-text').value;
        await navigator.clipboard.writeText(text);
        showToast('Cover letter copied to clipboard!', 'success');
    } catch (e) {
        showToast('Failed to copy to clipboard', 'error');
    }
}

// =============================================
// Form Submit Handlers
// =============================================

async function handleAnalyzeSubmit(e) {
    e.preventDefault();

    const submitBtn = this.querySelector('button[type="submit"]');
    setButtonLoading(submitBtn, true);

    currentJobDescription = document.getElementById('job-description').value;

    try {
        const response = await fetch('/api/resume/analyze-job-ai', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_description: currentJobDescription })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to analyze job description');
        }

        const raw = await response.json();
        const result = raw.analysis || raw;
        currentAnalysis = result;

        document.getElementById('exp-level').textContent = result.experience_level;

        document.getElementById('required-skills').innerHTML = (result.required_skills || [])
            .map(s => `<span class="px-2 py-1 text-xs rounded bg-red-100 text-red-800">${s}</span>`).join('');

        document.getElementById('preferred-skills').innerHTML = (result.preferred_skills || [])
            .map(s => `<span class="px-2 py-1 text-xs rounded bg-yellow-100 text-yellow-800">${s}</span>`).join('');

        document.getElementById('keywords').innerHTML = (result.keywords || [])
            .map(s => `<span class="px-2 py-1 text-xs rounded bg-gray-100 text-gray-700">${s}</span>`).join('');

        document.getElementById('responsibilities').innerHTML = (result.key_responsibilities || [])
            .map(r => `<li>${r}</li>`).join('');

        document.getElementById('analysis-results').classList.remove('hidden');

        unlockSections();
        updateSteps(2);

        showToast('Job description analyzed successfully', 'success');
    } catch (e) {
        showToast(e.message || 'Error analyzing job description', 'error');
    } finally {
        setButtonLoading(submitBtn, false);
    }
}

async function handleMatchSubmit(e) {
    e.preventDefault();

    if (!currentJobDescription) {
        showToast('Please analyze a job description first', 'warning');
        return;
    }

    const submitBtn = this.querySelector('button[type="submit"]');
    setButtonLoading(submitBtn, true);

    const resumeText = await getResumeText();

    if (!resumeText || resumeText.length < 50) {
        showToast('Please provide your resume text (at least 50 characters)', 'warning');
        setButtonLoading(submitBtn, false);
        return;
    }

    try {
        const response = await fetch('/api/resume/match-resume', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                resume_text: resumeText,
                job_description: currentJobDescription
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to check resume match');
        }

        const result = await response.json();

        const scorePercent = Math.round(result.match_score * 100);
        document.getElementById('match-score').textContent = scorePercent + '%';
        document.getElementById('match-score').className = 'text-lg font-bold ' +
            (scorePercent >= 70 ? 'text-green-600' : scorePercent >= 50 ? 'text-yellow-600' : 'text-red-600');

        const matchBar = document.getElementById('match-bar');
        matchBar.style.width = scorePercent + '%';
        matchBar.className = 'h-2.5 rounded-full transition-all duration-500 ' +
            (scorePercent >= 70 ? 'bg-green-500' : scorePercent >= 50 ? 'bg-yellow-500' : 'bg-red-500');

        document.getElementById('matching-skills').innerHTML = result.matching_skills
            .map(s => `<span class="px-2 py-1 text-xs rounded bg-green-100 text-green-800">${s}</span>`).join('');

        document.getElementById('missing-skills').innerHTML = result.missing_skills
            .map(s => `<span class="px-2 py-1 text-xs rounded bg-red-100 text-red-800">${s}</span>`).join('');

        document.getElementById('suggestions').innerHTML = result.suggestions
            .map(s => `<li>${s}</li>`).join('');

        document.getElementById('match-results').classList.remove('hidden');
        updateSteps(3);

        showToast('Resume match analyzed', 'success');

        getTailoringSuggestions();
    } catch (e) {
        showToast(e.message || 'Error checking resume match', 'error');
    } finally {
        setButtonLoading(submitBtn, false);
    }
}

async function handleCoverLetterSubmit(e) {
    e.preventDefault();

    if (!currentJobDescription) {
        showToast('Please analyze a job description first', 'warning');
        return;
    }

    const submitBtn = this.querySelector('button[type="submit"]');
    setButtonLoading(submitBtn, true);

    const companyName = document.getElementById('cl-company').value;
    const role = document.getElementById('cl-role').value;
    const tone = document.getElementById('cl-tone').value;
    const length = document.getElementById('cl-length').value;
    const pointsText = document.getElementById('cl-points').value;
    const customPoints = pointsText ? pointsText.split('\n').filter(p => p.trim()) : null;

    try {
        const response = await fetch('/api/resume/generate-cover-letter-ai', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_description: currentJobDescription,
                company_name: companyName,
                role: role,
                tone: tone,
                length: length,
                custom_points: customPoints
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error generating cover letter');
        }

        const result = await response.json();
        document.getElementById('cover-letter-text').value = result.cover_letter;
        document.getElementById('cover-letter-result').classList.remove('hidden');
        updateWordCount();

        showToast('Cover letter generated', 'success');
    } catch (e) {
        showToast(e.message || 'Error generating cover letter. Make sure you have set up your profile in Settings.', 'error');
    } finally {
        setButtonLoading(submitBtn, false);
    }
}

// =============================================
// Resume Source Handling
// =============================================

function switchResumeSource(source) {
    currentResumeSource = source;

    document.getElementById('resume-panel-profile').classList.add('hidden');
    document.getElementById('resume-panel-paste').classList.add('hidden');
    document.getElementById('resume-panel-upload').classList.add('hidden');

    document.getElementById(`resume-panel-${source}`).classList.remove('hidden');
}

async function loadProfileResume() {
    const loading = document.getElementById('profile-resume-loading');
    const empty = document.getElementById('profile-resume-empty');
    const content = document.getElementById('profile-resume-content');
    const status = document.getElementById('profile-resume-status');

    loading.classList.remove('hidden');
    empty.classList.add('hidden');
    content.classList.add('hidden');

    try {
        const response = await fetch('/api/resume/profile-resume');
        if (!response.ok) throw new Error('No profile');

        const data = await response.json();
        profileResumeData = data;

        const hasData = data.summary || (data.skills && data.skills.length) || (data.experience && data.experience.length);

        if (hasData) {
            document.getElementById('profile-summary-preview').textContent = data.summary || 'No summary';

            const skillsPreview = document.getElementById('profile-skills-preview');
            skillsPreview.innerHTML = (data.skills || []).slice(0, 8)
                .map(s => `<span class="px-2 py-0.5 text-xs rounded bg-blue-100 text-blue-800">${s}</span>`).join('');
            if (data.skills && data.skills.length > 8) {
                skillsPreview.innerHTML += `<span class="text-xs text-gray-500">+${data.skills.length - 8} more</span>`;
            }

            const expCount = data.experience ? data.experience.length : 0;
            document.getElementById('profile-experience-count').textContent =
                expCount > 0 ? `${expCount} experience entries` : '';

            content.classList.remove('hidden');
            status.textContent = 'Available';
            status.className = 'text-xs px-2 py-0.5 rounded bg-green-100 text-green-600';
        } else {
            empty.classList.remove('hidden');
            status.textContent = 'Not set up';
            status.className = 'text-xs px-2 py-0.5 rounded bg-yellow-100 text-yellow-600';
        }
    } catch (e) {
        empty.classList.remove('hidden');
        status.textContent = 'Not set up';
        status.className = 'text-xs px-2 py-0.5 rounded bg-yellow-100 text-yellow-600';
    } finally {
        loading.classList.add('hidden');
    }
}

async function getResumeText() {
    switch (currentResumeSource) {
        case 'profile':
            if (profileResumeData) {
                let parts = [];
                if (profileResumeData.summary) parts.push(profileResumeData.summary);
                if (profileResumeData.skills && profileResumeData.skills.length) {
                    parts.push('Skills: ' + profileResumeData.skills.join(', '));
                }
                if (profileResumeData.experience) {
                    for (const exp of profileResumeData.experience) {
                        parts.push(`${exp.title} at ${exp.company}`);
                        if (exp.bullets) parts.push(exp.bullets.join('\n'));
                    }
                }
                return parts.join('\n\n');
            }
            try {
                const resp = await fetch('/api/profile/resume/text');
                if (resp.ok) {
                    const data = await resp.json();
                    return data.text || '';
                }
            } catch (e) {}
            return '';

        case 'paste':
            return document.getElementById('resume-text').value || '';

        case 'upload':
            return uploadedResumeText || '';

        default:
            return '';
    }
}

// =============================================
// File Upload Handling
// =============================================

function handleResumeDrop(e) {
    e.preventDefault();
    e.target.classList.remove('border-green-400', 'bg-green-50');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        processResumeFile(files[0]);
    }
}

function handleResumeFileSelect(input) {
    if (input.files.length > 0) {
        processResumeFile(input.files[0]);
    }
}

async function processResumeFile(file) {
    const allowedTypes = ['.pdf', '.docx', '.doc', '.txt'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();

    if (!allowedTypes.includes(ext)) {
        showToast('Unsupported file type. Please use PDF, DOCX, or TXT.', 'error');
        return;
    }

    if (file.size > 5 * 1024 * 1024) {
        showToast('File too large. Maximum size is 5MB.', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        showToast('Parsing resume...', 'info');

        const response = await fetch('/api/resume/upload-resume', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const result = await response.json();

        let textParts = [];
        if (result.resume.summary) textParts.push(result.resume.summary);
        if (result.resume.skills && result.resume.skills.length) {
            textParts.push('Skills: ' + result.resume.skills.join(', '));
        }
        if (result.resume.experience) {
            for (const exp of result.resume.experience) {
                textParts.push(`${exp.title} at ${exp.company}`);
                if (exp.bullets) textParts.push(exp.bullets.join('\n'));
            }
        }
        uploadedResumeText = textParts.join('\n\n');

        document.getElementById('upload-filename').textContent = file.name;
        document.getElementById('upload-result').classList.remove('hidden');
        document.getElementById('upload-dropzone').classList.add('hidden');

        showToast('Resume parsed successfully!', 'success');
    } catch (e) {
        showToast('Error parsing resume: ' + e.message, 'error');
    }
}

function clearUpload() {
    uploadedResumeText = null;
    document.getElementById('upload-result').classList.add('hidden');
    document.getElementById('upload-dropzone').classList.remove('hidden');
    document.getElementById('resume-file-input').value = '';
}

async function saveUploadedToProfile() {
    if (!uploadedResumeText) {
        showToast('No resume to save', 'warning');
        return;
    }

    try {
        const parseResp = await fetch('/api/resume/parse-resume-text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ resume_text: uploadedResumeText })
        });

        if (!parseResp.ok) throw new Error('Parse failed');

        const parsed = await parseResp.json();

        const saveResp = await fetch('/api/resume/profile-resume', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(parsed)
        });

        if (saveResp.ok) {
            showToast('Resume saved to profile!', 'success');
            loadProfileResume();
        } else {
            throw new Error('Save failed');
        }
    } catch (e) {
        showToast('Error saving to profile', 'error');
    }
}

async function saveResumeTextToProfile() {
    const text = document.getElementById('resume-text').value;
    if (!text.trim()) {
        showToast('Please enter resume text first', 'warning');
        return;
    }

    try {
        const parseResp = await fetch('/api/resume/parse-resume-text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ resume_text: text })
        });

        if (!parseResp.ok) throw new Error('Parse failed');

        const parsed = await parseResp.json();

        const saveResp = await fetch('/api/resume/profile-resume', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(parsed)
        });

        if (saveResp.ok) {
            showToast('Resume saved to profile!', 'success');
            loadProfileResume();
        } else {
            throw new Error('Save failed');
        }
    } catch (e) {
        showToast('Error saving to profile', 'error');
    }
}

// =============================================
// Tailoring Suggestions
// =============================================

async function getTailoringSuggestions() {
    if (!currentJobDescription) {
        showToast('Please analyze a job description first', 'warning');
        return;
    }

    const loadingEl = document.getElementById('tailoring-loading');
    const contentEl = document.getElementById('tailoring-content');

    loadingEl.classList.remove('hidden');
    contentEl.classList.add('hidden');

    try {
        const resumeText = await getResumeText();
        if (!resumeText) throw new Error('No resume available');

        const response = await fetch('/api/resume/tailor-resume-ai', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_description: currentJobDescription,
                use_profile_resume: false,
                resume_text: resumeText
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get tailoring suggestions');
        }

        const raw = await response.json();
        const result = raw.analysis || raw;

        const skillsToAdd = document.getElementById('skills-to-add');
        if (result.skills_to_add && result.skills_to_add.length) {
            skillsToAdd.querySelector('div').innerHTML = result.skills_to_add
                .map(s => `<span class="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">${s}</span>`).join('');
            skillsToAdd.classList.remove('hidden');
        } else {
            skillsToAdd.classList.add('hidden');
        }

        const skillsToEmphasize = document.getElementById('skills-to-emphasize');
        if (result.skills_to_emphasize && result.skills_to_emphasize.length) {
            skillsToEmphasize.querySelector('div').innerHTML = result.skills_to_emphasize
                .map(s => `<span class="px-2 py-1 text-xs rounded bg-green-100 text-green-800">${s}</span>`).join('');
            skillsToEmphasize.classList.remove('hidden');
        } else {
            skillsToEmphasize.classList.add('hidden');
        }

        const suggestionsEl = document.getElementById('tailoring-suggestions');
        if (result.suggestions && result.suggestions.length) {
            suggestionsEl.querySelector('div').innerHTML = result.suggestions
                .map(s => {
                    const section = s.section || 'General';
                    const priority = s.priority || 'medium';
                    const suggestion = s.suggestion || s.suggested || 'No suggestion provided';
                    const current = s.current || null;
                    const example = s.example || null;
                    const reason = s.reason || null;

                    const priorityColors = {
                        high: 'border-red-200 bg-red-50',
                        medium: 'border-yellow-200 bg-yellow-50',
                        low: 'border-gray-200 bg-gray-50'
                    };
                    const priorityBadge = {
                        high: 'bg-red-100 text-red-700',
                        medium: 'bg-yellow-100 text-yellow-700',
                        low: 'bg-gray-100 text-gray-700'
                    };
                    return `
                        <div class="p-3 rounded border ${priorityColors[priority] || priorityColors.medium}">
                            <div class="flex items-start justify-between">
                                <span class="text-sm font-medium">${section}</span>
                                <span class="text-xs px-1.5 py-0.5 rounded ${priorityBadge[priority] || priorityBadge.medium}">${priority}</span>
                            </div>
                            <p class="text-sm text-gray-600 mt-1">${suggestion}</p>
                            ${current ? `
                                <div class="mt-2 p-2 bg-red-50 rounded border border-red-200">
                                    <span class="text-xs font-medium text-red-600">Current (replace this):</span>
                                    <p class="text-sm text-red-800 mt-0.5 line-through">"${current}"</p>
                                </div>
                            ` : ''}
                            ${example ? `
                                <div class="mt-2 p-2 bg-green-50 rounded border border-green-200">
                                    <span class="text-xs font-medium text-green-600">${current ? 'Replace with:' : 'Add this:'}</span>
                                    <p class="text-sm text-green-800 mt-0.5 font-medium">"${example}"</p>
                                </div>
                            ` : ''}
                            ${reason ? `<p class="text-xs text-gray-500 mt-2 italic">${reason}</p>` : ''}
                        </div>
                    `;
                }).join('');
            suggestionsEl.classList.remove('hidden');
        } else {
            suggestionsEl.classList.add('hidden');
        }

        contentEl.classList.remove('hidden');
        showToast('Tailoring suggestions loaded', 'success');
    } catch (e) {
        showToast(e.message || 'Error getting tailoring suggestions', 'error');
    } finally {
        loadingEl.classList.add('hidden');
    }
}
