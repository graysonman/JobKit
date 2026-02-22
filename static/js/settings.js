// Profile fields for completion tracking
const profileFields = [
    { id: 'profile-name', weight: 2, label: 'Name' },
    { id: 'profile-email', weight: 1, label: 'Email' },
    { id: 'profile-phone', weight: 0.5, label: 'Phone' },
    { id: 'profile-location', weight: 0.5, label: 'Location' },
    { id: 'profile-linkedin', weight: 1, label: 'LinkedIn' },
    { id: 'profile-title', weight: 2, label: 'Title' },
    { id: 'profile-school', weight: 1, label: 'School' },
    { id: 'profile-grad-year', weight: 0.5, label: 'Graduation Year' },
    { id: 'profile-experience', weight: 1, label: 'Experience' },
    { id: 'profile-skills', weight: 2, label: 'Skills' },
    { id: 'profile-roles', weight: 1.5, label: 'Target Roles' },
    { id: 'profile-preferred-locations', weight: 0.5, label: 'Preferred Locations' },
    { id: 'profile-salary', weight: 0.5, label: 'Salary Expectations' },
    { id: 'profile-pitch', weight: 2, label: 'Elevator Pitch' },
    { id: 'profile-resume', weight: 2, label: 'Resume Summary' }
];

// Auto-save debounce
let saveTimeout = null;
let pendingChanges = false;

// Import data storage
let importData = null;

// Current confirmation action
let pendingAction = null;

// Resume state
let resumeData = null;
let resumeChanged = false;

// Named handler for confirm-input — stored at module scope so removeEventListener
// can dedup across repeated calls to openClearModal('all').
function _handleConfirmInput() {
    const confirmBtn = document.getElementById('confirm-action-btn');
    const confirmInput = document.getElementById('confirm-input');
    if (confirmBtn && confirmInput) {
        confirmBtn.disabled = confirmInput.value !== 'DELETE';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    loadProfile();
    loadLastBackupDate();
    setupAutoSave();
    loadExistingResume();

    // Collapsible section headers
    document.querySelectorAll('.collapsible-header').forEach(btn => {
        btn.addEventListener('click', function() { toggleSection(this); });
    });

    // Profile preview modal
    document.getElementById('preview-profile-btn').addEventListener('click', openProfilePreview);
    document.getElementById('profile-preview-close-btn').addEventListener('click', closeProfilePreview);
    document.getElementById('profile-preview-close2-btn').addEventListener('click', closeProfilePreview);
    document.getElementById('profile-preview-modal').addEventListener('click', function(e) {
        if (e.target === this) closeProfilePreview();
    });

    // Confirm modal
    document.getElementById('confirm-cancel-btn').addEventListener('click', closeConfirmModal);
    document.getElementById('confirm-action-btn').addEventListener('click', executeConfirmedAction);
    document.getElementById('confirm-modal').addEventListener('click', function(e) {
        if (e.target === this) closeConfirmModal();
    });

    // Escape key closes all modals
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeProfilePreview();
            closeConfirmModal();
        }
    });

    // Resume file upload
    document.getElementById('resume-file-input').addEventListener('change', function() {
        handleResumeUpload(this);
    });

    // Resume paste section
    document.getElementById('parse-resume-btn').addEventListener('click', parseResumeText);
    document.getElementById('clear-resume-paste-btn').addEventListener('click', clearResumePaste);

    // Resume parsed section actions
    document.getElementById('preview-resume-btn').addEventListener('click', previewResume);
    document.getElementById('export-resume-btn').addEventListener('click', exportResumeText);
    document.getElementById('resume-summary').addEventListener('change', markResumeChanged);

    // Skill input — Enter key and Add button
    document.getElementById('resume-skill-input').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); addResumeSkill(); }
    });
    document.getElementById('add-resume-skill-btn').addEventListener('click', addResumeSkill);

    // Experience / Education add buttons
    document.getElementById('add-experience-btn').addEventListener('click', addExperienceEntry);
    document.getElementById('add-education-btn').addEventListener('click', addEducationEntry);
    document.getElementById('save-resume-btn').addEventListener('click', saveResumeToProfile);

    // Skill tags — delegate on container
    document.getElementById('resume-skills-container').addEventListener('click', function(e) {
        const btn = e.target.closest('[data-action="remove-skill"]');
        if (btn) removeResumeSkill(parseInt(btn.dataset.index, 10));
    });

    // Experience list — delegate change (inputs) and click (remove button)
    document.getElementById('resume-experience-list').addEventListener('change', function(e) {
        const el = e.target.closest('[data-action="update-experience"]');
        if (el) { updateExperience(parseInt(el.dataset.index, 10), el.dataset.field, el.value); return; }
        const bulletsEl = e.target.closest('[data-action="update-experience-bullets"]');
        if (bulletsEl) updateExperienceBullets(parseInt(bulletsEl.dataset.index, 10), bulletsEl.value);
    });
    document.getElementById('resume-experience-list').addEventListener('click', function(e) {
        const btn = e.target.closest('[data-action="remove-experience"]');
        if (btn) removeExperience(parseInt(btn.dataset.index, 10));
    });

    // Education list — delegate change and click
    document.getElementById('resume-education-list').addEventListener('change', function(e) {
        const el = e.target.closest('[data-action="update-education"]');
        if (el) updateEducation(parseInt(el.dataset.index, 10), el.dataset.field, el.value);
    });
    document.getElementById('resume-education-list').addEventListener('click', function(e) {
        const btn = e.target.closest('[data-action="remove-education"]');
        if (btn) removeEducation(parseInt(btn.dataset.index, 10));
    });

    // Export all data buttons
    document.getElementById('export-all-json-btn').addEventListener('click', () => exportAllData('json'));
    document.getElementById('export-all-csv-btn').addEventListener('click', () => exportAllData('csv'));

    // Export individual type buttons — delegate on container
    document.getElementById('export-individual-container').addEventListener('click', function(e) {
        const btn = e.target.closest('[data-type]');
        if (btn) exportData(btn.dataset.type, btn.dataset.format || 'json');
    });

    // Import file + buttons
    document.getElementById('import-file').addEventListener('change', function() {
        handleImportFile(this);
    });
    document.getElementById('confirm-import-btn').addEventListener('click', confirmImport);
    document.getElementById('cancel-import-btn').addEventListener('click', cancelImport);

    // Danger zone — delegate on container
    document.getElementById('danger-zone-container').addEventListener('click', function(e) {
        const btn = e.target.closest('[data-clear-type]');
        if (btn) openClearModal(btn.dataset.clearType);
    });
});

// =============================================
// Profile Functions
// =============================================

async function loadProfile() {
    try {
        const response = await fetch('/api/profile/');
        if (response.ok) {
            const profile = await response.json();
            document.getElementById('profile-name').value = profile.name || '';
            document.getElementById('profile-email').value = profile.email || '';
            document.getElementById('profile-phone').value = profile.phone_number || '';
            document.getElementById('profile-location').value = profile.location || '';
            document.getElementById('profile-linkedin').value = profile.linkedin_url || '';
            document.getElementById('profile-title').value = profile.current_title || '';
            document.getElementById('profile-school').value = profile.school || '';
            document.getElementById('profile-grad-year').value = profile.graduation_year || '';
            document.getElementById('profile-experience').value = profile.years_experience || '';
            document.getElementById('profile-skills').value = profile.skills || '';
            document.getElementById('profile-roles').value = profile.target_roles || '';
            document.getElementById('profile-preferred-locations').value = profile.preferred_locations || '';
            document.getElementById('profile-salary').value = profile.salary_expectations || '';
            document.getElementById('profile-pitch').value = profile.elevator_pitch || '';
            document.getElementById('profile-resume').value = profile.resume_summary || '';
        }
    } catch (e) {
        // Profile doesn't exist yet
    }
    updateCompletionIndicator();
}

function setupAutoSave() {
    const form = document.getElementById('profile-form');
    const inputs = form.querySelectorAll('input, textarea');

    inputs.forEach(input => {
        input.addEventListener('input', () => {
            pendingChanges = true;
            updateSaveStatus('saving');
            updateCompletionIndicator();

            clearTimeout(saveTimeout);
            saveTimeout = setTimeout(saveProfile, 1500);
        });
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        clearTimeout(saveTimeout);
        await saveProfile();
    });
}

async function saveProfile() {
    const data = {
        name: document.getElementById('profile-name').value,
        email: document.getElementById('profile-email').value || null,
        phone_number: document.getElementById('profile-phone').value || null,
        location: document.getElementById('profile-location').value || null,
        linkedin_url: document.getElementById('profile-linkedin').value || null,
        current_title: document.getElementById('profile-title').value || null,
        school: document.getElementById('profile-school').value || null,
        graduation_year: parseInt(document.getElementById('profile-grad-year').value) || null,
        years_experience: parseInt(document.getElementById('profile-experience').value) || null,
        skills: document.getElementById('profile-skills').value || null,
        target_roles: document.getElementById('profile-roles').value || null,
        preferred_locations: document.getElementById('profile-preferred-locations').value || null,
        salary_expectations: document.getElementById('profile-salary').value || null,
        elevator_pitch: document.getElementById('profile-pitch').value || null,
        resume_summary: document.getElementById('profile-resume').value || null
    };

    try {
        await fetch('/api/profile/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        pendingChanges = false;
        updateSaveStatus('saved');
    } catch (e) {
        updateSaveStatus('error');
    }
}

function updateSaveStatus(status) {
    const statusEl = document.getElementById('save-status');
    const textEl = document.getElementById('save-text');

    switch (status) {
        case 'saving':
            textEl.innerHTML = '<span class="inline-block w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mr-2"></span>Saving...';
            statusEl.className = 'flex items-center text-sm text-blue-600';
            break;
        case 'saved':
            textEl.innerHTML = '<svg class="w-4 h-4 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>All changes saved';
            statusEl.className = 'flex items-center text-sm text-green-600';
            break;
        case 'error':
            textEl.innerHTML = '<svg class="w-4 h-4 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>Error saving';
            statusEl.className = 'flex items-center text-sm text-red-600';
            break;
    }
}

function updateCompletionIndicator() {
    let filledWeight = 0;
    let totalWeight = 0;
    const missing = [];

    profileFields.forEach(field => {
        totalWeight += field.weight;
        const el = document.getElementById(field.id);
        if (el && el.value.trim()) {
            filledWeight += field.weight;
        } else if (field.weight >= 1.5) {
            missing.push(field.label);
        }
    });

    const percent = Math.round((filledWeight / totalWeight) * 100);
    document.getElementById('completion-percent').textContent = percent + '%';
    document.getElementById('completion-bar').style.width = percent + '%';

    const bar = document.getElementById('completion-bar');
    if (percent < 40) {
        bar.style.backgroundColor = 'var(--color-red-500, #ef4444)';
    } else if (percent < 70) {
        bar.style.backgroundColor = 'var(--color-yellow-500, #eab308)';
    } else {
        bar.style.backgroundColor = 'var(--color-green-500, #22c55e)';
    }

    const hint = document.getElementById('completion-hint');
    if (percent === 100) {
        hint.textContent = 'Your profile is complete!';
    } else if (missing.length > 0) {
        hint.textContent = `Consider adding: ${missing.slice(0, 3).join(', ')}${missing.length > 3 ? '...' : ''}`;
    } else {
        hint.textContent = 'Complete your profile to personalize messages.';
    }
}

function toggleSection(button) {
    const content = button.nextElementSibling;
    const icon = button.querySelector('.collapsible-icon');
    const isExpanded = content.classList.contains('expanded');

    if (isExpanded) {
        content.classList.remove('expanded');
        icon.style.transform = 'rotate(-90deg)';
        button.setAttribute('aria-expanded', 'false');
    } else {
        content.classList.add('expanded');
        icon.style.transform = 'rotate(0deg)';
        button.setAttribute('aria-expanded', 'true');
    }
}

// =============================================
// Profile Preview
// =============================================

function openProfilePreview() {
    const name = document.getElementById('profile-name').value || '[Your Name]';
    const title = document.getElementById('profile-title').value || '[Your Title]';
    const school = document.getElementById('profile-school').value;
    const pitch = document.getElementById('profile-pitch').value || '[Your elevator pitch will appear here]';

    let connectionText = `Hi [Contact Name], I'm ${name}`;
    if (title) connectionText += `, a ${title}`;
    if (school) connectionText += ` and ${school} alum`;
    connectionText += `. I noticed you work at [Company] and would love to connect!`;

    let inmailText = `Hi [Contact Name],\n\nI came across your profile and was impressed by your work at [Company]. ${pitch}\n\nI'd love to learn more about opportunities on your team. Would you have time for a brief chat?\n\nBest,\n${name}`;

    document.getElementById('preview-connection').textContent = connectionText;
    document.getElementById('preview-inmail').style.whiteSpace = 'pre-line';
    document.getElementById('preview-inmail').textContent = inmailText;

    document.getElementById('profile-preview-modal').classList.remove('hidden');
}

function closeProfilePreview() {
    document.getElementById('profile-preview-modal').classList.add('hidden');
}

// =============================================
// Export / Import Functions
// =============================================

function loadLastBackupDate() {
    const lastBackup = localStorage.getItem('jobkit_last_backup');
    if (lastBackup) {
        document.getElementById('last-backup-info').classList.remove('hidden');
        const date = new Date(lastBackup);
        document.getElementById('last-backup-date').textContent = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }
}

async function exportAllData(format) {
    showToast('Preparing export...', 'info');

    try {
        const [contacts, applications, companies, templates, profile] = await Promise.all([
            fetch('/api/contacts/').then(r => r.json()),
            fetch('/api/applications/').then(r => r.json()),
            fetch('/api/companies/').then(r => r.json()),
            fetch('/api/templates/').then(r => r.json()),
            fetch('/api/profile/').then(r => r.ok ? r.json() : null)
        ]);

        const allData = { contacts, applications, companies, templates, profile, exportDate: new Date().toISOString() };

        if (format === 'json') {
            downloadFile(JSON.stringify(allData, null, 2), 'jobkit_backup.json', 'application/json');
        } else if (format === 'csv') {
            const zip = {
                'contacts.csv': arrayToCSV(contacts),
                'applications.csv': arrayToCSV(applications),
                'companies.csv': arrayToCSV(companies)
            };
            for (const [filename, content] of Object.entries(zip)) {
                downloadFile(content, filename, 'text/csv');
            }
        }

        localStorage.setItem('jobkit_last_backup', new Date().toISOString());
        loadLastBackupDate();
        showToast('Export complete!', 'success');
    } catch (e) {
        showToast('Export failed: ' + e.message, 'error');
    }
}

async function exportData(type, format) {
    try {
        const response = await fetch(`/api/${type}/`);
        const data = await response.json();

        if (format === 'csv') {
            downloadFile(arrayToCSV(data), `${type}_export.csv`, 'text/csv');
        } else {
            downloadFile(JSON.stringify(data, null, 2), `${type}_export.json`, 'application/json');
        }
        showToast(`${type} exported successfully!`, 'success');
    } catch (e) {
        showToast('Export failed: ' + e.message, 'error');
    }
}

function arrayToCSV(arr) {
    if (!arr || arr.length === 0) return '';
    const headers = Object.keys(arr[0]);
    const rows = arr.map(obj =>
        headers.map(h => {
            let val = obj[h];
            if (val === null || val === undefined) return '';
            if (typeof val === 'object') val = JSON.stringify(val);
            val = String(val).replace(/"/g, '""');
            return val.includes(',') || val.includes('"') || val.includes('\n') ? `"${val}"` : val;
        }).join(',')
    );
    return [headers.join(','), ...rows].join('\n');
}

function downloadFile(content, filename, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename.replace('.', '_' + new Date().toISOString().split('T')[0] + '.')}`;
    a.click();
    URL.revokeObjectURL(url);
}

function handleImportFile(input) {
    const file = input.files[0];
    if (!file) return;

    document.getElementById('import-filename').textContent = file.name;

    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            importData = JSON.parse(e.target.result);
            showImportPreview(importData);
        } catch (err) {
            showToast('Invalid JSON file', 'error');
            importData = null;
        }
    };
    reader.readAsText(file);
}

function showImportPreview(data) {
    const list = document.getElementById('import-preview-list');
    list.innerHTML = '';

    const counts = {
        contacts: data.contacts?.length || 0,
        applications: data.applications?.length || 0,
        companies: data.companies?.length || 0,
        templates: data.templates?.length || 0,
        profile: data.profile ? 1 : 0
    };

    for (const [type, count] of Object.entries(counts)) {
        if (count > 0) {
            const li = document.createElement('li');
            li.textContent = `${count} ${type}`;
            list.appendChild(li);
        }
    }

    if (data.exportDate) {
        const li = document.createElement('li');
        li.className = 'text-gray-400';
        li.textContent = `Exported: ${new Date(data.exportDate).toLocaleDateString()}`;
        list.appendChild(li);
    }

    document.getElementById('import-preview').classList.remove('hidden');
}

async function confirmImport() {
    if (!importData) return;

    showToast('Importing data...', 'info');

    try {
        if (importData.contacts) {
            for (const contact of importData.contacts) {
                delete contact.id;
                await fetch('/api/contacts/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(contact)
                });
            }
        }

        if (importData.companies) {
            for (const company of importData.companies) {
                delete company.id;
                await fetch('/api/companies/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(company)
                });
            }
        }

        if (importData.applications) {
            for (const app of importData.applications) {
                delete app.id;
                await fetch('/api/applications/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(app)
                });
            }
        }

        if (importData.templates) {
            for (const template of importData.templates) {
                delete template.id;
                await fetch('/api/templates/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(template)
                });
            }
        }

        if (importData.profile) {
            await fetch('/api/profile/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(importData.profile)
            });
            loadProfile();
        }

        showToast('Import complete!', 'success');
        cancelImport();
    } catch (e) {
        showToast('Import failed: ' + e.message, 'error');
    }
}

function cancelImport() {
    importData = null;
    document.getElementById('import-file').value = '';
    document.getElementById('import-filename').textContent = 'No file selected';
    document.getElementById('import-preview').classList.add('hidden');
}

// =============================================
// Clear Data Functions
// =============================================

function openClearModal(type) {
    const titles = {
        contacts: 'Clear All Contacts',
        applications: 'Clear All Applications',
        companies: 'Clear All Companies',
        history: 'Clear Message History',
        all: 'Clear All Data'
    };

    const messages = {
        contacts: 'This will permanently delete all your contacts.',
        applications: 'This will permanently delete all your job applications.',
        companies: 'This will permanently delete all your saved companies.',
        history: 'This will permanently delete all your message history.',
        all: 'This will permanently delete ALL your data including contacts, applications, companies, and message history.'
    };

    document.getElementById('confirm-title').textContent = titles[type];
    document.getElementById('confirm-message').textContent = messages[type];

    const inputWrapper = document.getElementById('confirm-input-wrapper');
    const confirmBtn = document.getElementById('confirm-action-btn');

    if (type === 'all') {
        inputWrapper.classList.remove('hidden');
        document.getElementById('confirm-text-required').textContent = 'DELETE';
        const confirmInput = document.getElementById('confirm-input');
        confirmInput.value = '';
        confirmBtn.disabled = true;
        // removeEventListener before add to prevent duplicate listeners across modal re-opens
        confirmInput.removeEventListener('input', _handleConfirmInput);
        confirmInput.addEventListener('input', _handleConfirmInput);
    } else {
        inputWrapper.classList.add('hidden');
        confirmBtn.disabled = false;
    }

    pendingAction = type;
    document.getElementById('confirm-modal').classList.remove('hidden');
}

function closeConfirmModal() {
    document.getElementById('confirm-modal').classList.add('hidden');
    pendingAction = null;
}

async function executeConfirmedAction() {
    if (!pendingAction) return;

    const type = pendingAction;
    closeConfirmModal();

    showToast('Deleting data...', 'info');

    try {
        if (type === 'all' || type === 'contacts') {
            const contacts = await fetch('/api/contacts/').then(r => r.json());
            for (const c of contacts) {
                await fetch(`/api/contacts/${c.id}`, { method: 'DELETE' });
            }
        }

        if (type === 'all' || type === 'applications') {
            const apps = await fetch('/api/applications/').then(r => r.json());
            for (const a of apps) {
                await fetch(`/api/applications/${a.id}`, { method: 'DELETE' });
            }
        }

        if (type === 'all' || type === 'companies') {
            const companies = await fetch('/api/companies/').then(r => r.json());
            for (const c of companies) {
                await fetch(`/api/companies/${c.id}`, { method: 'DELETE' });
            }
        }

        if (type === 'all' || type === 'history') {
            const history = await fetch('/api/history/').then(r => r.json());
            for (const h of history) {
                await fetch(`/api/history/${h.id}`, { method: 'DELETE' });
            }
        }

        showToast('Data cleared successfully', 'success');

        if (type === 'all') {
            setTimeout(() => location.reload(), 1000);
        }
    } catch (e) {
        showToast('Error clearing data: ' + e.message, 'error');
    }
}

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

// =============================================
// Resume Management Functions
// =============================================

async function handleResumeUpload(input) {
    const file = input.files[0];
    if (!file) return;

    const statusEl = document.getElementById('resume-upload-status');
    statusEl.innerHTML = '<span class="text-blue-600">Uploading...</span>';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/resume/upload-resume?save_to_profile=false', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const result = await response.json();
        resumeData = result.resume;
        displayParsedResume(resumeData);
        statusEl.innerHTML = `<span class="text-green-600">✓ ${file.name} parsed</span>`;
        showToast('Resume parsed successfully!', 'success');
    } catch (e) {
        statusEl.innerHTML = `<span class="text-red-600">Error: ${e.message}</span>`;
        showToast('Failed to parse resume: ' + e.message, 'error');
    }

    input.value = ''; // Reset file input
}

async function parseResumeText() {
    const text = document.getElementById('resume-paste-text').value.trim();
    if (!text || text.length < 50) {
        showToast('Please paste more resume text (at least 50 characters)', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/resume/parse-resume-text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ resume_text: text })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Parse failed');
        }

        resumeData = await response.json();
        displayParsedResume(resumeData);
        showToast('Resume text parsed successfully!', 'success');
    } catch (e) {
        showToast('Failed to parse resume: ' + e.message, 'error');
    }
}

function clearResumePaste() {
    document.getElementById('resume-paste-text').value = '';
}

function displayParsedResume(data) {
    document.getElementById('resume-parsed-section').classList.remove('hidden');
    document.getElementById('resume-summary').value = data.summary || '';
    renderSkillsTags(data.skills || []);
    renderExperienceList(data.experience || []);
    renderEducationList(data.education || []);
    resumeChanged = false;
    updateResumeSaveStatus('');
}

function renderSkillsTags(skills) {
    const container = document.getElementById('resume-skills-container');
    container.innerHTML = '';

    skills.forEach((skill, index) => {
        const tag = document.createElement('span');
        tag.className = 'inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm';
        // data-action delegated to #resume-skills-container click handler
        tag.innerHTML = `
            ${escapeHtml(skill)}
            <button type="button" data-action="remove-skill" data-index="${index}" class="hover:text-blue-600">&times;</button>
        `;
        container.appendChild(tag);
    });
}

function addResumeSkill() {
    const input = document.getElementById('resume-skill-input');
    const skill = input.value.trim();
    if (!skill) return;

    if (!resumeData) resumeData = { skills: [] };
    if (!resumeData.skills) resumeData.skills = [];

    if (!resumeData.skills.includes(skill)) {
        resumeData.skills.push(skill);
        renderSkillsTags(resumeData.skills);
        markResumeChanged();
    }

    input.value = '';
}

function removeResumeSkill(index) {
    if (resumeData && resumeData.skills) {
        resumeData.skills.splice(index, 1);
        renderSkillsTags(resumeData.skills);
        markResumeChanged();
    }
}

function renderExperienceList(experiences) {
    const container = document.getElementById('resume-experience-list');
    container.innerHTML = '';

    experiences.forEach((exp, index) => {
        const div = document.createElement('div');
        div.className = 'border rounded-lg p-3 bg-gray-50';
        // data-action attrs delegated to #resume-experience-list change/click handlers
        div.innerHTML = `
            <div class="flex items-start justify-between mb-2">
                <div class="flex-1 grid grid-cols-2 gap-2">
                    <input type="text" value="${escapeHtml(exp.title || '')}"
                        class="border rounded px-2 py-1 text-sm"
                        placeholder="Title"
                        data-action="update-experience" data-index="${index}" data-field="title">
                    <input type="text" value="${escapeHtml(exp.company || '')}"
                        class="border rounded px-2 py-1 text-sm"
                        placeholder="Company"
                        data-action="update-experience" data-index="${index}" data-field="company">
                </div>
                <button type="button" data-action="remove-experience" data-index="${index}" class="ml-2 text-red-500 hover:text-red-700">&times;</button>
            </div>
            <div class="grid grid-cols-3 gap-2 mb-2">
                <input type="text" value="${escapeHtml(exp.start_date || '')}"
                    class="border rounded px-2 py-1 text-sm"
                    placeholder="Start Date"
                    data-action="update-experience" data-index="${index}" data-field="start_date">
                <input type="text" value="${escapeHtml(exp.end_date || '')}"
                    class="border rounded px-2 py-1 text-sm"
                    placeholder="End Date"
                    data-action="update-experience" data-index="${index}" data-field="end_date">
                <input type="text" value="${escapeHtml(exp.location || '')}"
                    class="border rounded px-2 py-1 text-sm"
                    placeholder="Location"
                    data-action="update-experience" data-index="${index}" data-field="location">
            </div>
            <div>
                <label class="text-xs text-gray-500">Bullets (one per line)</label>
                <textarea rows="3" class="w-full border rounded px-2 py-1 text-sm"
                    placeholder="• Achievement or responsibility"
                    data-action="update-experience-bullets" data-index="${index}">${escapeHtml((exp.bullets || []).join('\n'))}</textarea>
            </div>
        `;
        container.appendChild(div);
    });
}

function addExperienceEntry() {
    if (!resumeData) resumeData = { experience: [] };
    if (!resumeData.experience) resumeData.experience = [];

    resumeData.experience.push({
        title: '',
        company: '',
        start_date: '',
        end_date: '',
        location: '',
        bullets: []
    });

    renderExperienceList(resumeData.experience);
    markResumeChanged();
}

function updateExperience(index, field, value) {
    if (resumeData && resumeData.experience && resumeData.experience[index]) {
        resumeData.experience[index][field] = value;
        markResumeChanged();
    }
}

function updateExperienceBullets(index, text) {
    if (resumeData && resumeData.experience && resumeData.experience[index]) {
        resumeData.experience[index].bullets = text.split('\n').filter(b => b.trim());
        markResumeChanged();
    }
}

function removeExperience(index) {
    if (resumeData && resumeData.experience) {
        resumeData.experience.splice(index, 1);
        renderExperienceList(resumeData.experience);
        markResumeChanged();
    }
}

function renderEducationList(education) {
    const container = document.getElementById('resume-education-list');
    container.innerHTML = '';

    education.forEach((edu, index) => {
        const div = document.createElement('div');
        div.className = 'border rounded-lg p-3 bg-gray-50';
        // data-action attrs delegated to #resume-education-list change/click handlers
        div.innerHTML = `
            <div class="flex items-start justify-between">
                <div class="flex-1 grid grid-cols-2 gap-2">
                    <input type="text" value="${escapeHtml(edu.school || '')}"
                        class="border rounded px-2 py-1 text-sm"
                        placeholder="School"
                        data-action="update-education" data-index="${index}" data-field="school">
                    <input type="text" value="${escapeHtml(edu.degree || '')}"
                        class="border rounded px-2 py-1 text-sm"
                        placeholder="Degree (e.g., B.S.)"
                        data-action="update-education" data-index="${index}" data-field="degree">
                    <input type="text" value="${escapeHtml(edu.field || '')}"
                        class="border rounded px-2 py-1 text-sm"
                        placeholder="Field of Study"
                        data-action="update-education" data-index="${index}" data-field="field">
                    <input type="text" value="${escapeHtml(edu.year || '')}"
                        class="border rounded px-2 py-1 text-sm"
                        placeholder="Year"
                        data-action="update-education" data-index="${index}" data-field="year">
                </div>
                <button type="button" data-action="remove-education" data-index="${index}" class="ml-2 text-red-500 hover:text-red-700">&times;</button>
            </div>
        `;
        container.appendChild(div);
    });
}

function addEducationEntry() {
    if (!resumeData) resumeData = { education: [] };
    if (!resumeData.education) resumeData.education = [];

    resumeData.education.push({
        school: '',
        degree: '',
        field: '',
        year: ''
    });

    renderEducationList(resumeData.education);
    markResumeChanged();
}

function updateEducation(index, field, value) {
    if (resumeData && resumeData.education && resumeData.education[index]) {
        resumeData.education[index][field] = value;
        markResumeChanged();
    }
}

function removeEducation(index) {
    if (resumeData && resumeData.education) {
        resumeData.education.splice(index, 1);
        renderEducationList(resumeData.education);
        markResumeChanged();
    }
}

function markResumeChanged() {
    resumeChanged = true;
    updateResumeSaveStatus('unsaved');
}

function updateResumeSaveStatus(status) {
    const el = document.getElementById('resume-save-status');
    switch (status) {
        case 'unsaved':
            el.innerHTML = '<span class="text-yellow-600">Unsaved changes</span>';
            break;
        case 'saving':
            el.innerHTML = '<span class="text-blue-600">Saving...</span>';
            break;
        case 'saved':
            el.innerHTML = '<span class="text-green-600">✓ Saved to profile</span>';
            break;
        default:
            el.innerHTML = '';
    }
}

async function saveResumeToProfile() {
    if (!resumeData) {
        showToast('No resume data to save', 'warning');
        return;
    }

    resumeData.summary = document.getElementById('resume-summary').value;
    updateResumeSaveStatus('saving');

    try {
        const response = await fetch('/api/resume/profile-resume', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(resumeData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Save failed');
        }

        resumeChanged = false;
        updateResumeSaveStatus('saved');
        showToast('Resume saved to profile!', 'success');

        if (resumeData.summary) {
            document.getElementById('profile-resume').value = resumeData.summary;
        }
        if (resumeData.skills && resumeData.skills.length > 0) {
            document.getElementById('profile-skills').value = resumeData.skills.join(', ');
        }
    } catch (e) {
        updateResumeSaveStatus('unsaved');
        showToast('Failed to save resume: ' + e.message, 'error');
    }
}

async function previewResume() {
    try {
        const response = await fetch('/api/profile/resume/text');
        if (!response.ok) throw new Error('No resume data');

        const data = await response.json();
        const text = data.text || 'No resume data available';

        // Build modal via DOM API to avoid inline onclick handlers (CSP compliance)
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });

        const inner = document.createElement('div');
        inner.className = 'bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-auto m-4';

        const header = document.createElement('div');
        header.className = 'sticky top-0 bg-white border-b px-4 py-3 flex items-center justify-between';

        const title = document.createElement('h3');
        title.className = 'font-semibold';
        title.textContent = 'Resume Preview';

        const closeBtn = document.createElement('button');
        closeBtn.className = 'text-gray-500 hover:text-gray-700';
        closeBtn.innerHTML = '&times;';
        closeBtn.addEventListener('click', () => modal.remove());

        header.appendChild(title);
        header.appendChild(closeBtn);

        const pre = document.createElement('pre');
        pre.className = 'p-4 text-sm whitespace-pre-wrap font-mono';
        pre.textContent = text; // textContent avoids XSS — no escapeHtml needed

        inner.appendChild(header);
        inner.appendChild(pre);
        modal.appendChild(inner);
        document.body.appendChild(modal);
    } catch (e) {
        showToast('No resume data to preview', 'warning');
    }
}

async function exportResumeText() {
    try {
        const response = await fetch('/api/profile/resume/text');
        if (!response.ok) throw new Error('No resume data');

        const data = await response.json();
        const text = data.text || '';

        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'resume_export.txt';
        a.click();
        URL.revokeObjectURL(url);

        showToast('Resume exported!', 'success');
    } catch (e) {
        showToast('Failed to export resume', 'error');
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function loadExistingResume() {
    try {
        const response = await fetch('/api/resume/profile-resume');
        if (response.ok) {
            const data = await response.json();
            if (data && (data.summary || data.experience?.length || data.skills?.length)) {
                resumeData = data;
                displayParsedResume(data);
            }
        }
    } catch (e) {
        // No existing resume data
    }
}
