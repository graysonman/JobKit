/**
 * JobKit - Messages Page JavaScript
 */

let contacts = [];
let templates = [];
let allHistory = [];
let filteredHistory = [];
let currentContactId = null;
let currentMessageType = null;
let currentLinkedInUrl = null;
let previewTemplateId = null;
let currentHistoryPage = 1;
const historyPerPage = 10;

const charLimits = {
    'connection_request': 300,
    'inmail': 1900,
    'follow_up': 8000,
    'thank_you': 8000,
    'cold_email': 1500,
    'referral_request': 500,
    'informational_interview': 400,
    'recruiter_reply': 600,
    'application_status': 300,
    'rejection_response': 300
};

async function loadContacts() {
    const response = await fetch('/api/contacts/');
    contacts = await response.json();
    const select = document.getElementById('msg-contact');
    select.innerHTML = '<option value="">No contact — use generic</option>' +
        contacts.map(c => `<option value="${c.id}">${escapeHtml(c.name)} ${c.company ? '(' + escapeHtml(c.company) + ')' : ''}</option>`).join('');
    const historySelect = document.getElementById('history-contact-filter');
    historySelect.innerHTML = '<option value="">All Contacts</option>' +
        contacts.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
}

function handleContactChange() {
    const contactId = document.getElementById('msg-contact').value;
    const preview = document.getElementById('contact-preview');
    if (!contactId) { preview.classList.add('hidden'); return; }
    const contact = contacts.find(c => c.id === parseInt(contactId));
    if (!contact) return;
    document.getElementById('contact-avatar').textContent = contact.name.substring(0, 2).toUpperCase();
    document.getElementById('contact-name').textContent = contact.name;
    document.getElementById('contact-info').textContent = [contact.role, contact.company].filter(Boolean).join(' at ') || 'No details';
    document.getElementById('contact-type').textContent = contact.contact_type || 'Contact';
    document.getElementById('contact-status').textContent = contact.connection_status ? `Status: ${contact.connection_status}` : '';
    currentLinkedInUrl = contact.linkedin_url;
    preview.classList.remove('hidden');
}

async function loadTemplates() {
    const response = await fetch('/api/messages/templates');
    templates = await response.json();
    renderTemplates(templates);
    updateTemplateDropdown();
}

function renderTemplates(templates) {
    const list = document.getElementById('templates-list');
    if (templates.length === 0) {
        list.innerHTML = `<div class="empty-state py-8"><svg class="empty-state-icon w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg><p class="text-gray-500 mb-3">No custom templates yet</p><button data-action="open-add-template" class="btn btn-sm btn-secondary">Create Template</button></div>`;
        return;
    }
    list.innerHTML = templates.map(t => `
        <div class="border border-gray-200 rounded-lg p-3 hover:border-purple-300 transition-colors cursor-pointer" data-action="preview-template" data-id="${t.id}">
            <div class="flex justify-between items-start">
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2"><span class="font-medium text-gray-900 truncate">${escapeHtml(t.name)}</span>${t.is_default ? '<span class="badge badge-primary text-xs">Default</span>' : ''}</div>
                    <div class="flex items-center gap-2 mt-1"><span class="text-xs text-gray-500">${formatMessageType(t.message_type)}</span><span class="text-xs text-gray-400">|</span><span class="text-xs text-gray-500">${formatTargetType(t.target_type)}</span>${t.usage_count ? `<span class="text-xs text-gray-400">| Used ${t.usage_count}x</span>` : ''}</div>
                </div>
                <div class="flex gap-1 ml-2" data-nopropagate>
                    <button data-action="edit-template" data-id="${t.id}" class="p-1.5 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded" title="Edit"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg></button>
                    <button data-action="duplicate-template" data-id="${t.id}" class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded" title="Duplicate"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg></button>
                    <button data-action="delete-template" data-id="${t.id}" class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded" title="Delete"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg></button>
                </div>
            </div>
            <p class="text-sm text-gray-600 mt-2 line-clamp-2">${escapeHtml(t.template.substring(0, 100))}...</p>
        </div>
    `).join('');
}

function formatMessageType(type) { return {'connection_request':'Connection','inmail':'InMail','follow_up':'Follow-up','thank_you':'Thank You','cold_email':'Cold Email','referral_request':'Referral','informational_interview':'Info Interview','recruiter_reply':'Recruiter Reply','application_status':'Status Check','rejection_response':'Rejection Response'}[type] || type; }
function formatTargetType(type) { return {'general':'General','recruiter':'Recruiter','developer':'Developer','alumni':'Alumni','hiring_manager':'Hiring Manager'}[type] || type; }

function updateTemplateDropdown() {
    const msgType = document.getElementById('msg-type').value;
    const filtered = templates.filter(t => t.message_type === msgType);
    document.getElementById('msg-template').innerHTML = '<option value="">Auto-select template</option>' + filtered.map(t => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join('');
}

async function loadMessageHistory() {
    const response = await fetch('/api/messages/history?limit=100');
    allHistory = await response.json();
    filterHistory();
}

function filterHistory() {
    const search = document.getElementById('history-search').value.toLowerCase();
    const contactFilter = document.getElementById('history-contact-filter').value;
    const typeFilter = document.getElementById('history-type-filter').value;
    filteredHistory = allHistory.filter(h => {
        const contact = contacts.find(c => c.id === h.contact_id);
        const contactName = contact ? contact.name.toLowerCase() : '';
        if (search && !h.message_content.toLowerCase().includes(search) && !contactName.includes(search)) return false;
        if (contactFilter && h.contact_id !== parseInt(contactFilter)) return false;
        if (typeFilter && h.message_type !== typeFilter) return false;
        return true;
    });
    currentHistoryPage = 1;
    renderHistory();
}

function renderHistory() {
    const container = document.getElementById('message-history');
    const pagination = document.getElementById('history-pagination');
    const totalPages = Math.ceil(filteredHistory.length / historyPerPage);
    const start = (currentHistoryPage - 1) * historyPerPage;
    const pageHistory = filteredHistory.slice(start, start + historyPerPage);

    if (filteredHistory.length === 0) {
        container.innerHTML = `<div class="empty-state py-12"><svg class="empty-state-icon w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg><h3 class="empty-state-title">${allHistory.length === 0 ? 'No messages sent yet' : 'No matching messages'}</h3><p class="empty-state-description">${allHistory.length === 0 ? 'Generate and send your first message to start building your network.' : 'Try adjusting your search or filters.'}</p></div>`;
        pagination.classList.add('hidden');
        return;
    }

    container.innerHTML = pageHistory.map(h => {
        const contact = contacts.find(c => c.id === h.contact_id);
        return `<div class="border border-gray-200 rounded-lg p-4 hover:border-purple-200 transition-colors"><div class="flex justify-between items-start"><div class="flex items-center gap-2"><span class="font-medium text-gray-900">${contact ? escapeHtml(contact.name) : 'Unknown Contact'}</span><span class="badge badge-gray text-xs">${formatMessageType(h.message_type) || 'message'}</span>${h.got_response ? '<span class="badge badge-success text-xs">Responded</span>' : ''}</div><div class="flex items-center gap-2"><span class="text-xs text-gray-500">${new Date(h.sent_at).toLocaleDateString()}</span><button data-action="follow-up" data-contact-id="${h.contact_id}" class="p-1 text-gray-400 hover:text-purple-600" title="Send follow-up"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"/></svg></button></div></div><p class="text-sm text-gray-600 mt-2 line-clamp-2">${escapeHtml(h.message_content.substring(0, 200))}${h.message_content.length > 200 ? '...' : ''}</p></div>`;
    }).join('');

    if (totalPages > 1) {
        pagination.classList.remove('hidden');
        document.getElementById('prev-page-btn').disabled = currentHistoryPage === 1;
        document.getElementById('next-page-btn').disabled = currentHistoryPage === totalPages;
        document.getElementById('page-info').textContent = `Page ${currentHistoryPage} of ${totalPages}`;
    } else {
        pagination.classList.add('hidden');
    }
}

function loadHistoryPage(page) {
    const totalPages = Math.ceil(filteredHistory.length / historyPerPage);
    if (page < 1 || page > totalPages) return;
    currentHistoryPage = page;
    renderHistory();
}

function followUpMessage(contactId) {
    document.getElementById('msg-contact').value = contactId;
    handleContactChange();
    document.getElementById('msg-type').value = 'follow_up';
    updateTemplateDropdown();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function updateCharLimit() {
    const msgType = document.getElementById('msg-type').value;
    document.getElementById('char-limit').textContent = charLimits[msgType] || 8000;
}

function updateCharCount() {
    const content = document.getElementById('msg-content').value;
    const limit = charLimits[currentMessageType || document.getElementById('msg-type').value] || 8000;
    const count = content.length;
    document.getElementById('char-count').textContent = count;
    document.getElementById('char-limit').textContent = limit;
    const charCountEl = document.querySelector('.char-count');
    const warningEl = document.getElementById('char-warning');
    if (count > limit) {
        charCountEl.classList.add('error'); charCountEl.classList.remove('warning');
        warningEl.classList.remove('hidden'); warningEl.querySelector('span').textContent = `${count - limit} characters over limit!`;
    } else if (count > limit * 0.9) {
        charCountEl.classList.add('warning'); charCountEl.classList.remove('error');
        warningEl.classList.remove('hidden'); warningEl.querySelector('span').textContent = `Only ${limit - count} characters remaining`;
    } else {
        charCountEl.classList.remove('warning', 'error');
        warningEl.classList.add('hidden');
    }
}

async function copyMessage() {
    await navigator.clipboard.writeText(document.getElementById('msg-content').value);
    showToast('Copied to clipboard!');
}

function openInLinkedIn() {
    if (currentLinkedInUrl) window.open(currentLinkedInUrl, '_blank');
}

async function markAsSent() {
    if (currentContactId) {
        await fetch('/api/messages/save-sent', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ contact_id: parseInt(currentContactId), message_type: currentMessageType, message_content: document.getElementById('msg-content').value })
        });
        loadMessageHistory();
    }
    showToast('Message marked as sent!');
    document.getElementById('generated-message').classList.add('hidden');
    document.getElementById('generate-form').reset();
    document.getElementById('contact-preview').classList.add('hidden');
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<svg class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg> ${message}`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function openTemplateModal() {
    document.getElementById('template-modal-title').textContent = 'Add Template';
    document.getElementById('template-form').reset();
    document.getElementById('tpl-id').value = '';
    document.getElementById('template-modal').classList.remove('hidden');
}

function closeTemplateModal() {
    document.getElementById('template-modal').classList.add('hidden');
}

function editTemplate(id) {
    const template = templates.find(t => t.id === id);
    if (!template) return;
    document.getElementById('template-modal-title').textContent = 'Edit Template';
    document.getElementById('tpl-id').value = template.id;
    document.getElementById('tpl-name').value = template.name;
    document.getElementById('tpl-msg-type').value = template.message_type;
    document.getElementById('tpl-target-type').value = template.target_type;
    document.getElementById('tpl-subject').value = template.subject || '';
    document.getElementById('tpl-template').value = template.template;
    closePreviewModal();
    document.getElementById('template-modal').classList.remove('hidden');
}

function editTemplateFromPreview() { editTemplate(previewTemplateId); }

async function duplicateTemplate(id) {
    const template = templates.find(t => t.id === id);
    if (!template) return;
    await fetch('/api/messages/templates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: template.name + ' (Copy)', message_type: template.message_type, target_type: template.target_type, subject: template.subject, template: template.template, is_default: false })
    });
    closePreviewModal();
    loadTemplates();
    showToast('Template duplicated!');
}

async function deleteTemplate(id) {
    if (!confirm('Delete this template?')) return;
    await fetch(`/api/messages/templates/${id}`, { method: 'DELETE' });
    loadTemplates();
}

async function submitTemplate() {
    const id = document.getElementById('tpl-id').value;
    const data = {
        name: document.getElementById('tpl-name').value,
        message_type: document.getElementById('tpl-msg-type').value,
        target_type: document.getElementById('tpl-target-type').value,
        subject: document.getElementById('tpl-subject').value || null,
        template: document.getElementById('tpl-template').value,
        is_default: false
    };
    await fetch(id ? `/api/messages/templates/${id}` : '/api/messages/templates', {
        method: id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    closeTemplateModal();
    loadTemplates();
    showToast(id ? 'Template updated!' : 'Template created!');
}

function previewTemplate(id) {
    const template = templates.find(t => t.id === id);
    if (!template) return;
    previewTemplateId = id;
    document.getElementById('preview-title').textContent = template.name;
    document.getElementById('preview-msg-type').textContent = formatMessageType(template.message_type);
    document.getElementById('preview-target-type').textContent = formatTargetType(template.target_type);
    document.getElementById('preview-usage').textContent = `Used ${template.usage_count || 0} times`;
    document.getElementById('preview-content').textContent = template.template;
    if (template.subject) {
        document.getElementById('preview-subject').textContent = template.subject;
        document.getElementById('preview-subject-container').classList.remove('hidden');
    } else {
        document.getElementById('preview-subject-container').classList.add('hidden');
    }
    document.getElementById('preview-modal').classList.remove('hidden');
}

function closePreviewModal() {
    document.getElementById('preview-modal').classList.add('hidden');
    previewTemplateId = null;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', function() {
    loadContacts();
    loadTemplates();
    loadMessageHistory();
    updateCharLimit();

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') { closeTemplateModal(); closePreviewModal(); }
    });

    // Contact & type selects
    document.getElementById('msg-contact').addEventListener('change', handleContactChange);
    document.getElementById('msg-type').addEventListener('change', function() {
        updateTemplateDropdown();
        updateCharLimit();
    });

    // Generate form submit
    document.getElementById('generate-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        const btn = document.getElementById('generate-btn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Generating...';
        currentContactId = document.getElementById('msg-contact').value;
        currentMessageType = document.getElementById('msg-type').value;
        const data = { message_type: currentMessageType };
        if (currentContactId) { data.contact_id = parseInt(currentContactId); }

        try {
            const response = await fetch('/api/messages/generate-ai', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (!response.ok) { const error = await response.json(); throw new Error(error.detail || 'Error generating message'); }
            const result = await response.json();
            document.getElementById('msg-recipient').textContent = result.contact_name || 'General Message';
            document.getElementById('msg-content').value = result.message;
            updateCharCount();
            if (result.subject) {
                document.getElementById('msg-subject').value = result.subject;
                document.getElementById('msg-subject-container').classList.remove('hidden');
            } else {
                document.getElementById('msg-subject-container').classList.add('hidden');
            }
            document.getElementById('linkedin-btn').classList.toggle('hidden', !currentLinkedInUrl);
            document.getElementById('generated-message').classList.remove('hidden');
        } catch (e) {
            alert('Error generating message: ' + e.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> Generate Message`;
        }
    });

    // Message content char count
    document.getElementById('msg-content').addEventListener('input', updateCharCount);

    // Generated message action buttons
    document.getElementById('copy-msg-btn').addEventListener('click', copyMessage);
    document.getElementById('linkedin-btn').addEventListener('click', openInLinkedIn);
    document.getElementById('mark-sent-btn').addEventListener('click', markAsSent);

    // History filters
    document.getElementById('history-search').addEventListener('input', filterHistory);
    document.getElementById('history-contact-filter').addEventListener('change', filterHistory);
    document.getElementById('history-type-filter').addEventListener('change', filterHistory);

    // History pagination
    document.getElementById('prev-page-btn').addEventListener('click', () => loadHistoryPage(currentHistoryPage - 1));
    document.getElementById('next-page-btn').addEventListener('click', () => loadHistoryPage(currentHistoryPage + 1));

    // Templates list delegation
    document.getElementById('add-template-btn').addEventListener('click', openTemplateModal);
    document.getElementById('templates-list').addEventListener('click', e => {
        // Stop propagation for action buttons inside a card
        if (e.target.closest('[data-nopropagate]')) {
            const btn = e.target.closest('[data-action]');
            if (!btn) return;
            const action = btn.dataset.action;
            const id = parseInt(btn.dataset.id, 10);
            if (action === 'edit-template') editTemplate(id);
            else if (action === 'duplicate-template') duplicateTemplate(id);
            else if (action === 'delete-template') deleteTemplate(id);
            return;
        }
        const card = e.target.closest('[data-action="preview-template"]');
        if (card) previewTemplate(parseInt(card.dataset.id, 10));
        const emptyBtn = e.target.closest('[data-action="open-add-template"]');
        if (emptyBtn) openTemplateModal();
    });

    // Message history delegation
    document.getElementById('message-history').addEventListener('click', e => {
        const btn = e.target.closest('[data-action="follow-up"]');
        if (btn) followUpMessage(parseInt(btn.dataset.contactId, 10));
    });

    // Template modal
    document.getElementById('template-modal').addEventListener('click', e => {
        if (e.target === e.currentTarget) closeTemplateModal();
    });
    document.getElementById('template-modal-inner').addEventListener('click', e => e.stopPropagation());
    document.getElementById('template-close-btn').addEventListener('click', closeTemplateModal);
    document.getElementById('template-cancel-btn').addEventListener('click', closeTemplateModal);
    document.getElementById('submit-template-btn').addEventListener('click', submitTemplate);

    // Preview modal
    document.getElementById('preview-modal').addEventListener('click', e => {
        if (e.target === e.currentTarget) closePreviewModal();
    });
    document.getElementById('preview-modal-inner').addEventListener('click', e => e.stopPropagation());
    document.getElementById('preview-close-btn').addEventListener('click', closePreviewModal);
    document.getElementById('duplicate-preview-btn').addEventListener('click', () => duplicateTemplate(previewTemplateId));
    document.getElementById('edit-preview-btn').addEventListener('click', editTemplateFromPreview);
});
