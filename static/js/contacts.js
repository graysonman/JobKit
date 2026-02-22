/**
 * JobKit - Contacts Page JavaScript
 */

let allContacts = [];
let filteredContacts = [];
let selectedContacts = new Set();
let currentPage = 1;
const pageSize = 25;
let currentSort = { field: 'name', direction: 'asc' };
let searchTimeout = null;

function setupURLParams() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('needs_follow_up') === 'true') {
        document.getElementById('filter-followup').checked = true;
    }
}

async function loadContacts() {
    const type = document.getElementById('filter-type').value;
    const status = document.getElementById('filter-status').value;
    const alumni = document.getElementById('filter-alumni').checked;
    const followup = document.getElementById('filter-followup').checked;

    let url = '/api/contacts/?';
    if (type) url += `contact_type=${type}&`;
    if (status) url += `connection_status=${status}&`;
    if (alumni) url += `is_alumni=true&`;
    if (followup) url += `needs_follow_up=true&`;

    const response = await fetch(url);
    allContacts = await response.json();

    applySearchFilter();
    updateClearFiltersButton();
}

function handleSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        applySearchFilter();
    }, 300);
}

function applySearchFilter() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase().trim();

    if (searchTerm) {
        filteredContacts = allContacts.filter(c =>
            (c.name && c.name.toLowerCase().includes(searchTerm)) ||
            (c.company && c.company.toLowerCase().includes(searchTerm)) ||
            (c.role && c.role.toLowerCase().includes(searchTerm)) ||
            (c.email && c.email.toLowerCase().includes(searchTerm))
        );
    } else {
        filteredContacts = [...allContacts];
    }

    sortContacts();
    currentPage = 1;
    renderContacts();
    updateResultsCount();
    updateClearFiltersButton();
}

function sortContacts() {
    const { field, direction } = currentSort;
    filteredContacts.sort((a, b) => {
        let aVal = a[field] || '';
        let bVal = b[field] || '';

        if (field === 'last_contacted') {
            aVal = aVal ? new Date(aVal).getTime() : 0;
            bVal = bVal ? new Date(bVal).getTime() : 0;
        } else {
            aVal = aVal.toString().toLowerCase();
            bVal = bVal.toString().toLowerCase();
        }

        if (aVal < bVal) return direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return direction === 'asc' ? 1 : -1;
        return 0;
    });

    document.querySelectorAll('[id^="sort-icon-"]').forEach(icon => {
        icon.classList.remove('text-blue-600');
        icon.classList.add('text-gray-400');
    });
    const activeIcon = document.getElementById(`sort-icon-${field}`);
    if (activeIcon) {
        activeIcon.classList.remove('text-gray-400');
        activeIcon.classList.add('text-blue-600');
    }
}

function sortTable(field) {
    if (currentSort.field === field) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.field = field;
        currentSort.direction = 'asc';
    }
    sortContacts();
    renderContacts();
}

function updateResultsCount() {
    const total = allContacts.length;
    const filtered = filteredContacts.length;
    const countEl = document.getElementById('results-count');

    if (total === 0) {
        countEl.textContent = 'No contacts yet';
    } else if (filtered === total) {
        countEl.textContent = `${total} contact${total !== 1 ? 's' : ''}`;
    } else {
        countEl.textContent = `Showing ${filtered} of ${total} contacts`;
    }
}

function updateClearFiltersButton() {
    const hasFilters =
        document.getElementById('filter-type').value ||
        document.getElementById('filter-status').value ||
        document.getElementById('filter-alumni').checked ||
        document.getElementById('filter-followup').checked ||
        document.getElementById('search-input').value.trim();

    document.getElementById('clear-filters-btn').classList.toggle('hidden', !hasFilters);
}

function clearFilters() {
    document.getElementById('filter-type').value = '';
    document.getElementById('filter-status').value = '';
    document.getElementById('filter-alumni').checked = false;
    document.getElementById('filter-followup').checked = false;
    document.getElementById('search-input').value = '';
    loadContacts();
}

function renderContacts() {
    const tbody = document.getElementById('contacts-table-body');
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    const pageContacts = filteredContacts.slice(start, end);

    if (filteredContacts.length === 0) {
        const emptyAction = allContacts.length === 0 ? 'open-add' : 'clear-filters';
        const emptyLabel = allContacts.length === 0 ? 'Add Your First Contact' : 'Clear Filters';
        const emptyIcon = allContacts.length === 0
            ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"/>'
            : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>';
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="px-6 py-12 text-center">
                    <div class="flex flex-col items-center">
                        <svg class="w-16 h-16 text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
                        </svg>
                        <p class="text-gray-500 mb-4">${allContacts.length === 0 ? 'No contacts yet. Start building your network!' : 'No contacts match your filters.'}</p>
                        <button data-action="${emptyAction}"
                                class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                ${emptyIcon}
                            </svg>
                            ${emptyLabel}
                        </button>
                    </div>
                </td>
            </tr>
        `;
        document.getElementById('pagination').classList.add('hidden');
        return;
    }

    tbody.innerHTML = pageContacts.map(c => `
        <tr class="hover:bg-gray-50 transition-colors ${selectedContacts.has(c.id) ? 'bg-blue-50' : ''}">
            <td class="px-4 py-4">
                <input type="checkbox" ${selectedContacts.has(c.id) ? 'checked' : ''}
                       data-action="toggle-select" data-id="${c.id}"
                       class="rounded border-gray-300 text-blue-600 focus:ring-blue-500">
            </td>
            <td class="px-6 py-4">
                <div class="flex items-center gap-2">
                    <div class="font-medium text-gray-900">${escapeHtml(c.name)}</div>
                    ${c.is_alumni ? '<span class="px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">Alumni</span>' : ''}
                </div>
                <div class="flex items-center gap-2 mt-1">
                    ${c.linkedin_url ? `<a href="${escapeHtml(c.linkedin_url)}" target="_blank" class="text-xs text-blue-500 hover:underline inline-flex items-center gap-1">
                        <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg>
                        LinkedIn
                    </a>` : ''}
                    ${c.email ? `<a href="mailto:${escapeHtml(c.email)}" class="text-xs text-gray-500 hover:underline">${escapeHtml(c.email)}</a>` : ''}
                </div>
            </td>
            <td class="px-6 py-4">
                <div class="text-gray-900">${escapeHtml(c.company) || '-'}</div>
                <div class="text-sm text-gray-500">${escapeHtml(c.role) || ''}</div>
            </td>
            <td class="px-6 py-4">
                <span class="px-2 py-1 text-xs rounded-full ${getTypeColor(c.contact_type)}">${formatType(c.contact_type)}</span>
            </td>
            <td class="px-6 py-4">
                <span class="px-2 py-1 text-xs rounded-full font-medium ${getStatusColor(c.connection_status)}">${formatStatus(c.connection_status)}</span>
            </td>
            <td class="px-6 py-4">
                <div class="text-sm text-gray-900">${c.last_contacted ? formatDate(c.last_contacted) : '-'}</div>
                ${c.next_follow_up ? `<div class="text-xs ${isOverdue(c.next_follow_up) ? 'text-red-600 font-medium' : 'text-gray-500'}">
                    Follow-up: ${formatDate(c.next_follow_up)}
                </div>` : ''}
            </td>
            <td class="px-6 py-4">
                <div class="flex items-center gap-2">
                    <button data-action="edit-contact" data-id="${c.id}" class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors" title="Edit">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                        </svg>
                    </button>
                    <a href="/messages?contact=${c.id}" class="p-1.5 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors" title="Send message">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
                        </svg>
                    </a>
                    <button data-action="delete-contact" data-id="${c.id}" class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors" title="Delete">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');

    updatePagination();
    updateBulkActionsBar();
}

function updatePagination() {
    const totalPages = Math.ceil(filteredContacts.length / pageSize);

    if (totalPages <= 1) {
        document.getElementById('pagination').classList.add('hidden');
        return;
    }

    document.getElementById('pagination').classList.remove('hidden');

    const start = (currentPage - 1) * pageSize + 1;
    const end = Math.min(currentPage * pageSize, filteredContacts.length);

    document.getElementById('page-start').textContent = start;
    document.getElementById('page-end').textContent = end;
    document.getElementById('total-count').textContent = filteredContacts.length;

    document.getElementById('prev-btn').disabled = currentPage === 1;
    document.getElementById('next-btn').disabled = currentPage === totalPages;

    const pageNumbers = document.getElementById('page-numbers');
    let pages = [];
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
            pages.push(i);
        } else if (pages[pages.length - 1] !== '...') {
            pages.push('...');
        }
    }

    pageNumbers.innerHTML = pages.map(p =>
        p === '...'
            ? '<span class="px-2 py-1 text-gray-500">...</span>'
            : `<button data-page="${p}" class="px-3 py-1 border rounded text-sm ${p === currentPage ? 'bg-blue-600 text-white border-blue-600' : 'hover:bg-gray-100'}">${p}</button>`
    ).join('');
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        renderContacts();
    }
}

function nextPage() {
    const totalPages = Math.ceil(filteredContacts.length / pageSize);
    if (currentPage < totalPages) {
        currentPage++;
        renderContacts();
    }
}

function goToPage(page) {
    currentPage = page;
    renderContacts();
}

// Bulk selection
function toggleContactSelection(id) {
    if (selectedContacts.has(id)) {
        selectedContacts.delete(id);
    } else {
        selectedContacts.add(id);
    }
    renderContacts();
}

function toggleSelectAll() {
    const checkbox = document.getElementById('select-all-checkbox');
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    const pageContacts = filteredContacts.slice(start, end);

    if (checkbox.checked) {
        pageContacts.forEach(c => selectedContacts.add(c.id));
    } else {
        pageContacts.forEach(c => selectedContacts.delete(c.id));
    }
    renderContacts();
}

function selectAllContacts() {
    filteredContacts.forEach(c => selectedContacts.add(c.id));
    renderContacts();
}

function deselectAllContacts() {
    selectedContacts.clear();
    renderContacts();
}

function updateBulkActionsBar() {
    const bar = document.getElementById('bulk-actions-bar');
    if (selectedContacts.size > 0) {
        bar.classList.remove('hidden');
        document.getElementById('selected-count').textContent = selectedContacts.size;
    } else {
        bar.classList.add('hidden');
    }
}

async function bulkUpdateStatus() {
    const status = document.getElementById('bulk-status-select').value;
    if (!status) return;

    const promises = Array.from(selectedContacts).map(id =>
        fetch(`/api/contacts/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ connection_status: status })
        })
    );

    await Promise.all(promises);
    selectedContacts.clear();
    loadContacts();
}

async function bulkDelete() {
    if (!confirm(`Are you sure you want to delete ${selectedContacts.size} contacts?`)) return;

    const promises = Array.from(selectedContacts).map(id =>
        fetch(`/api/contacts/${id}`, { method: 'DELETE' })
    );

    await Promise.all(promises);
    selectedContacts.clear();
    loadContacts();
}

// Helper functions
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatType(type) {
    const types = {
        'recruiter': 'Recruiter',
        'junior_dev': 'Junior Dev',
        'senior_dev': 'Senior Dev',
        'hiring_manager': 'Hiring Mgr',
        'other': 'Other'
    };
    return types[type] || type || '-';
}

function getTypeColor(type) {
    const colors = {
        'recruiter': 'bg-purple-100 text-purple-800',
        'junior_dev': 'bg-blue-100 text-blue-800',
        'senior_dev': 'bg-indigo-100 text-indigo-800',
        'hiring_manager': 'bg-green-100 text-green-800',
        'other': 'bg-gray-100 text-gray-800'
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
}

function formatStatus(status) {
    const statuses = {
        'not_connected': 'Not Connected',
        'pending': 'Pending',
        'connected': 'Connected',
        'messaged': 'Messaged'
    };
    return statuses[status] || status;
}

function getStatusColor(status) {
    const colors = {
        'not_connected': 'bg-gray-100 text-gray-700',
        'pending': 'bg-yellow-100 text-yellow-800',
        'connected': 'bg-green-100 text-green-800',
        'messaged': 'bg-blue-100 text-blue-800'
    };
    return colors[status] || 'bg-gray-100';
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function isOverdue(dateStr) {
    const date = new Date(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return date < today;
}

// Modal functions
function openAddModal() {
    document.getElementById('modal-title').textContent = 'Add Contact';
    document.getElementById('contact-form').reset();
    document.getElementById('contact-id').value = '';
    document.getElementById('contact-status').value = 'not_connected';
    document.getElementById('school-field').classList.add('hidden');
    clearValidationErrors();
    document.getElementById('contact-modal').classList.remove('hidden');
    document.getElementById('contact-name').focus();
}

function closeModal() {
    document.getElementById('contact-modal').classList.add('hidden');
    clearValidationErrors();
}

function toggleSchoolField() {
    const isAlumni = document.getElementById('contact-alumni').checked;
    document.getElementById('school-field').classList.toggle('hidden', !isAlumni);
}

async function editContact(id) {
    const contact = allContacts.find(c => c.id === id);
    if (!contact) return;

    document.getElementById('modal-title').textContent = 'Edit Contact';
    document.getElementById('contact-id').value = contact.id;
    document.getElementById('contact-name').value = contact.name || '';
    document.getElementById('contact-company').value = contact.company || '';
    document.getElementById('contact-role').value = contact.role || '';
    document.getElementById('contact-type').value = contact.contact_type || '';
    document.getElementById('contact-location').value = contact.location || '';
    document.getElementById('contact-email').value = contact.email || '';
    document.getElementById('contact-phone').value = contact.phone_number || '';
    document.getElementById('contact-linkedin').value = contact.linkedin_url || '';
    document.getElementById('contact-alumni').checked = contact.is_alumni || false;
    document.getElementById('contact-school').value = contact.school_name || '';
    document.getElementById('contact-status').value = contact.connection_status || 'not_connected';
    document.getElementById('contact-followup').value = contact.next_follow_up || '';
    document.getElementById('contact-notes').value = contact.notes || '';

    document.getElementById('school-field').classList.toggle('hidden', !contact.is_alumni);

    clearValidationErrors();
    document.getElementById('contact-modal').classList.remove('hidden');
}

async function deleteContact(id) {
    if (!confirm('Are you sure you want to delete this contact?')) return;

    await fetch(`/api/contacts/${id}`, { method: 'DELETE' });
    loadContacts();
}

function clearValidationErrors() {
    document.querySelectorAll('[id^="error-"]').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('input, select, textarea').forEach(el => el.classList.remove('border-red-500'));
}

function showValidationError(field, message) {
    const errorEl = document.getElementById(`error-${field}`);
    const inputEl = document.getElementById(`contact-${field}`);
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.remove('hidden');
    }
    if (inputEl) {
        inputEl.classList.add('border-red-500');
    }
}

function validateForm() {
    clearValidationErrors();
    let isValid = true;

    const name = document.getElementById('contact-name').value.trim();
    if (!name) {
        showValidationError('name', 'Name is required');
        isValid = false;
    }

    const email = document.getElementById('contact-email').value.trim();
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showValidationError('email', 'Please enter a valid email address');
        isValid = false;
    }

    const linkedin = document.getElementById('contact-linkedin').value.trim();
    if (linkedin && !linkedin.includes('linkedin.com')) {
        showValidationError('linkedin', 'Please enter a valid LinkedIn URL');
        isValid = false;
    }

    return isValid;
}

async function submitForm() {
    if (!validateForm()) return;

    const saveBtn = document.getElementById('save-btn');
    const saveBtnText = document.getElementById('save-btn-text');
    const saveBtnSpinner = document.getElementById('save-btn-spinner');

    saveBtn.disabled = true;
    saveBtnText.textContent = 'Saving...';
    saveBtnSpinner.classList.remove('hidden');

    try {
        const id = document.getElementById('contact-id').value;
        const data = {
            name: document.getElementById('contact-name').value,
            company: document.getElementById('contact-company').value || null,
            role: document.getElementById('contact-role').value || null,
            contact_type: document.getElementById('contact-type').value || null,
            location: document.getElementById('contact-location').value || null,
            email: document.getElementById('contact-email').value || null,
            phone_number: document.getElementById('contact-phone').value || null,
            linkedin_url: document.getElementById('contact-linkedin').value || null,
            is_alumni: document.getElementById('contact-alumni').checked,
            school_name: document.getElementById('contact-school').value || null,
            connection_status: document.getElementById('contact-status').value,
            next_follow_up: document.getElementById('contact-followup').value || null,
            notes: document.getElementById('contact-notes').value || null
        };

        const url = id ? `/api/contacts/${id}` : '/api/contacts/';
        const method = id ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save contact');
        }

        closeModal();
        loadContacts();
    } catch (e) {
        alert('Error saving contact: ' + e.message);
    } finally {
        saveBtn.disabled = false;
        saveBtnText.textContent = 'Save';
        saveBtnSpinner.classList.add('hidden');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    setupURLParams();
    loadContacts();

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') closeModal();
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            document.getElementById('search-input').focus();
        }
    });

    // Search, filters
    document.getElementById('search-input').addEventListener('input', handleSearch);
    document.getElementById('filter-type').addEventListener('change', loadContacts);
    document.getElementById('filter-status').addEventListener('change', loadContacts);
    document.getElementById('filter-alumni').addEventListener('change', loadContacts);
    document.getElementById('filter-followup').addEventListener('change', loadContacts);
    document.getElementById('clear-filters-btn').addEventListener('click', clearFilters);

    // Bulk actions
    document.getElementById('select-all-checkbox').addEventListener('change', toggleSelectAll);
    document.getElementById('select-all-contacts-btn').addEventListener('click', selectAllContacts);
    document.getElementById('deselect-all-btn').addEventListener('click', deselectAllContacts);
    document.getElementById('bulk-apply-btn').addEventListener('click', bulkUpdateStatus);
    document.getElementById('bulk-delete-btn').addEventListener('click', bulkDelete);

    // Sort header delegation on thead
    document.querySelector('thead').addEventListener('click', e => {
        const th = e.target.closest('[data-sort]');
        if (th) sortTable(th.dataset.sort);
    });

    // Pagination
    document.getElementById('prev-btn').addEventListener('click', prevPage);
    document.getElementById('next-btn').addEventListener('click', nextPage);
    document.getElementById('page-numbers').addEventListener('click', e => {
        const btn = e.target.closest('[data-page]');
        if (btn) goToPage(parseInt(btn.dataset.page, 10));
    });

    // Table body: click delegation for edit/delete/empty-state actions
    document.getElementById('contacts-table-body').addEventListener('click', e => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const action = btn.dataset.action;
        const id = parseInt(btn.dataset.id, 10);
        if (action === 'edit-contact') editContact(id);
        else if (action === 'delete-contact') deleteContact(id);
        else if (action === 'open-add') openAddModal();
        else if (action === 'clear-filters') clearFilters();
    });

    // Table body: change delegation for checkbox toggle
    document.getElementById('contacts-table-body').addEventListener('change', e => {
        const chk = e.target.closest('[data-action="toggle-select"]');
        if (chk) toggleContactSelection(parseInt(chk.dataset.id, 10));
    });

    // Modal backdrop / inner content
    document.getElementById('contact-modal').addEventListener('click', e => {
        if (e.target === e.currentTarget) closeModal();
    });
    document.getElementById('contact-modal-inner').addEventListener('click', e => e.stopPropagation());

    // Modal buttons
    document.getElementById('add-modal-btn').addEventListener('click', openAddModal);
    document.getElementById('modal-close-btn').addEventListener('click', closeModal);
    document.getElementById('modal-cancel-btn').addEventListener('click', closeModal);
    document.getElementById('save-btn').addEventListener('click', submitForm);
    document.getElementById('contact-alumni').addEventListener('change', toggleSchoolField);
});
