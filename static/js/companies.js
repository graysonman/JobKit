/**
 * JobKit - Companies Page JavaScript
 */

let allCompanies = [];
let filteredCompanies = [];
let allApplications = [];
let currentView = 'cards';
let currentSort = { field: 'priority', direction: 'desc' };
let searchTimeout = null;
let currentPriority = 0;

async function loadCompanies() {
    const size = document.getElementById('filter-size').value;
    const priority = document.getElementById('filter-priority').value;

    let url = '/api/companies/?';
    if (size) url += `size=${size}&`;
    if (priority) url += `min_priority=${priority}&`;

    const response = await fetch(url);
    allCompanies = await response.json();

    populateIndustryFilter();
    applyFilters();
}

async function loadApplicationsList() {
    const response = await fetch('/api/applications/');
    allApplications = await response.json();
}

function populateIndustryFilter() {
    const industries = [...new Set(allCompanies.map(c => c.industry).filter(Boolean))].sort();
    const select = document.getElementById('filter-industry');
    select.innerHTML = '<option value="">All Industries</option>' +
        industries.map(i => `<option value="${i}">${i}</option>`).join('');
}

function handleSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        applyFilters();
    }, 300);
}

function applyFilters() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase().trim();
    const industry = document.getElementById('filter-industry').value;

    filteredCompanies = allCompanies.filter(c => {
        if (searchTerm) {
            const matchesName = c.name && c.name.toLowerCase().includes(searchTerm);
            const matchesTech = c.tech_stack && c.tech_stack.toLowerCase().includes(searchTerm);
            const matchesIndustry = c.industry && c.industry.toLowerCase().includes(searchTerm);
            if (!matchesName && !matchesTech && !matchesIndustry) return false;
        }

        if (industry && c.industry !== industry) return false;

        return true;
    });

    sortCompanies();
    renderCompanies();
    updateResultsCount();
    updateClearFiltersButton();
}

function sortCompanies() {
    const { field, direction } = currentSort;
    filteredCompanies.sort((a, b) => {
        let aVal = a[field] || '';
        let bVal = b[field] || '';

        if (field === 'priority') {
            aVal = aVal || 0;
            bVal = bVal || 0;
        } else {
            aVal = aVal.toString().toLowerCase();
            bVal = bVal.toString().toLowerCase();
        }

        if (aVal < bVal) return direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return direction === 'asc' ? 1 : -1;
        return 0;
    });
}

function sortTable(field) {
    if (currentSort.field === field) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.field = field;
        currentSort.direction = field === 'priority' ? 'desc' : 'asc';
    }
    applyFilters();
}

function updateResultsCount() {
    const total = allCompanies.length;
    const filtered = filteredCompanies.length;
    const countEl = document.getElementById('results-count');

    if (total === 0) {
        countEl.textContent = 'No companies yet';
    } else if (filtered === total) {
        countEl.textContent = `${total} ${total === 1 ? 'company' : 'companies'}`;
    } else {
        countEl.textContent = `Showing ${filtered} of ${total} companies`;
    }
}

function updateClearFiltersButton() {
    const hasFilters =
        document.getElementById('filter-size').value ||
        document.getElementById('filter-industry').value ||
        document.getElementById('filter-priority').value ||
        document.getElementById('search-input').value.trim();

    document.getElementById('clear-filters-btn').classList.toggle('hidden', !hasFilters);
}

function clearFilters() {
    document.getElementById('filter-size').value = '';
    document.getElementById('filter-industry').value = '';
    document.getElementById('filter-priority').value = '';
    document.getElementById('search-input').value = '';
    loadCompanies();
}

function setView(view) {
    currentView = view;

    document.getElementById('view-cards-btn').classList.toggle('bg-blue-600', view === 'cards');
    document.getElementById('view-cards-btn').classList.toggle('text-white', view === 'cards');
    document.getElementById('view-cards-btn').classList.toggle('bg-white', view !== 'cards');
    document.getElementById('view-cards-btn').classList.toggle('text-gray-600', view !== 'cards');

    document.getElementById('view-list-btn').classList.toggle('bg-blue-600', view === 'list');
    document.getElementById('view-list-btn').classList.toggle('text-white', view === 'list');
    document.getElementById('view-list-btn').classList.toggle('bg-white', view !== 'list');
    document.getElementById('view-list-btn').classList.toggle('text-gray-600', view !== 'list');

    document.getElementById('cards-view').classList.toggle('hidden', view !== 'cards');
    document.getElementById('list-view').classList.toggle('hidden', view !== 'list');

    renderCompanies();
}

function renderCompanies() {
    if (currentView === 'cards') {
        renderCardsView();
    } else {
        renderListView();
    }
}

function renderCardsView() {
    const grid = document.getElementById('companies-grid');

    if (filteredCompanies.length === 0) {
        const emptyAction = allCompanies.length === 0 ? 'open-add' : 'clear-filters';
        grid.innerHTML = `
            <div class="col-span-full">
                <div class="empty-state">
                    <svg class="empty-state-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
                    </svg>
                    <h3 class="empty-state-title">${allCompanies.length === 0 ? 'No companies yet' : 'No matching companies'}</h3>
                    <p class="empty-state-description">${allCompanies.length === 0 ? "Start researching companies you're interested in working for." : 'Try adjusting your search or filters.'}</p>
                    <button data-action="${emptyAction}" class="btn ${allCompanies.length === 0 ? 'btn-secondary' : 'btn-outline'}">
                        ${allCompanies.length === 0 ? 'Add Your First Company' : 'Clear Filters'}
                    </button>
                </div>
            </div>
        `;
        return;
    }

    grid.innerHTML = filteredCompanies.map(c => {
        const hasApplication = allApplications.some(a => a.company_name && a.company_name.toLowerCase() === c.name.toLowerCase());

        return `
            <div class="company-card bg-white rounded-lg shadow p-4 border border-gray-100 hover:border-purple-200">
                <div class="flex justify-between items-start mb-2">
                    <div class="flex-1">
                        <div class="flex items-center gap-2">
                            <h3 class="font-bold text-lg text-gray-900">${escapeHtml(c.name)}</h3>
                            ${hasApplication ? '<span class="badge badge-success text-xs">Applied</span>' : ''}
                        </div>
                        ${c.industry ? `<p class="text-sm text-gray-500">${escapeHtml(c.industry)}</p>` : ''}
                    </div>
                    <div class="flex items-center" data-nopropagate>
                        ${renderClickablePriorityStars(c.id, c.priority)}
                    </div>
                </div>
                ${c.size ? `<span class="badge badge-gray mb-2">${formatSize(c.size)}</span>` : ''}
                ${c.tech_stack ? `<p class="text-sm mb-2"><span class="font-medium text-gray-700">Tech:</span> <span class="text-gray-600">${escapeHtml(c.tech_stack)}</span></p>` : ''}
                ${c.glassdoor_rating ? `<p class="text-sm mb-2"><span class="font-medium text-gray-700">Glassdoor:</span> <span class="text-gray-600">${c.glassdoor_rating}/5</span></p>` : ''}
                ${c.salary_range ? `<p class="text-sm mb-2"><span class="font-medium text-gray-700">Salary:</span> <span class="text-gray-600">${escapeHtml(c.salary_range)}</span></p>` : ''}
                <div class="flex gap-3 mt-3">
                    ${c.website ? `<a href="${escapeHtml(c.website)}" target="_blank" class="text-xs text-purple-600 hover:underline inline-flex items-center gap-1">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/></svg>
                        Website
                    </a>` : ''}
                    ${c.linkedin_url ? `<a href="${escapeHtml(c.linkedin_url)}" target="_blank" class="text-xs text-purple-600 hover:underline inline-flex items-center gap-1">
                        <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg>
                        LinkedIn
                    </a>` : ''}
                </div>
                <div class="flex gap-2 mt-4 pt-3 border-t border-gray-100">
                    <button data-action="edit-company" data-id="${c.id}" class="flex-1 px-3 py-1.5 text-sm text-purple-600 hover:bg-purple-50 rounded-lg transition-colors">Edit</button>
                    ${!hasApplication ? `<a href="/applications?company=${encodeURIComponent(c.name)}" class="flex-1 px-3 py-1.5 text-sm text-center text-green-600 hover:bg-green-50 rounded-lg transition-colors">Apply</a>` : ''}
                    <button data-action="delete-company" data-id="${c.id}" class="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors">Delete</button>
                </div>
            </div>
        `;
    }).join('');
}

function renderListView() {
    const tbody = document.getElementById('companies-table-body');

    if (filteredCompanies.length === 0) {
        const emptyAction = allCompanies.length === 0 ? 'open-add' : 'clear-filters';
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-12 text-center">
                    <div class="empty-state">
                        <svg class="empty-state-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
                        </svg>
                        <h3 class="empty-state-title">${allCompanies.length === 0 ? 'No companies yet' : 'No matching companies'}</h3>
                        <button data-action="${emptyAction}" class="btn ${allCompanies.length === 0 ? 'btn-secondary' : 'btn-outline'}">
                            ${allCompanies.length === 0 ? 'Add Company' : 'Clear Filters'}
                        </button>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filteredCompanies.map(c => {
        const hasApplication = allApplications.some(a => a.company_name && a.company_name.toLowerCase() === c.name.toLowerCase());

        return `
            <tr class="hover:bg-gray-50 transition-colors">
                <td class="px-6 py-4">
                    <div class="flex items-center gap-2">
                        <span class="font-medium text-gray-900">${escapeHtml(c.name)}</span>
                        ${hasApplication ? '<span class="badge badge-success text-xs">Applied</span>' : ''}
                    </div>
                    <div class="flex gap-2 mt-1">
                        ${c.website ? `<a href="${escapeHtml(c.website)}" target="_blank" class="text-xs text-purple-600 hover:underline">Website</a>` : ''}
                        ${c.linkedin_url ? `<a href="${escapeHtml(c.linkedin_url)}" target="_blank" class="text-xs text-purple-600 hover:underline">LinkedIn</a>` : ''}
                    </div>
                </td>
                <td class="px-6 py-4 text-gray-600">${escapeHtml(c.industry) || '-'}</td>
                <td class="px-6 py-4"><span class="badge badge-gray">${formatSize(c.size) || '-'}</span></td>
                <td class="px-6 py-4 text-gray-600 text-sm max-w-xs truncate">${escapeHtml(c.tech_stack) || '-'}</td>
                <td class="px-6 py-4">${renderClickablePriorityStars(c.id, c.priority)}</td>
                <td class="px-6 py-4">
                    <div class="flex items-center gap-2">
                        <button data-action="edit-company" data-id="${c.id}" class="p-1.5 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors" title="Edit">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                            </svg>
                        </button>
                        <button data-action="delete-company" data-id="${c.id}" class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors" title="Delete">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function renderClickablePriorityStars(companyId, priority) {
    let stars = '';
    for (let i = 1; i <= 5; i++) {
        const filled = i <= priority;
        stars += `<button data-action="update-priority" data-company-id="${companyId}" data-priority="${i}" class="priority-star ${filled ? 'text-yellow-400' : 'text-gray-300'}" title="Set priority to ${i}">★</button>`;
    }
    return `<div class="flex">${stars}</div>`;
}

async function updatePriority(companyId, newPriority) {
    await fetch(`/api/companies/${companyId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ priority: newPriority })
    });

    const company = allCompanies.find(c => c.id === companyId);
    if (company) company.priority = newPriority;

    applyFilters();
}

function formatSize(size) {
    const sizes = {
        'startup': 'Startup',
        'small': 'Small',
        'medium': 'Medium',
        'large': 'Large',
        'enterprise': 'Enterprise'
    };
    return sizes[size] || size;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function openAddModal() {
    document.getElementById('modal-title').textContent = 'Add Company';
    document.getElementById('company-form').reset();
    document.getElementById('company-id').value = '';
    currentPriority = 0;
    updatePriorityStars(0);
    document.getElementById('company-modal').classList.remove('hidden');
    document.getElementById('company-name').focus();
}

function closeModal() {
    document.getElementById('company-modal').classList.add('hidden');
}

function setPriority(value) {
    currentPriority = value;
    document.getElementById('company-priority').value = value;
    updatePriorityStars(value);
}

function updatePriorityStars(value) {
    const stars = document.querySelectorAll('#priority-stars .priority-star');
    const labels = ['Not set', 'Low', 'Medium-Low', 'Medium', 'High', 'Top Priority'];

    stars.forEach((star, index) => {
        if (index < value) {
            star.classList.remove('text-gray-300');
            star.classList.add('text-yellow-400');
        } else {
            star.classList.remove('text-yellow-400');
            star.classList.add('text-gray-300');
        }
    });

    document.getElementById('priority-label').textContent = labels[value];
}

async function editCompany(id) {
    const company = allCompanies.find(c => c.id === id);
    if (!company) return;

    document.getElementById('modal-title').textContent = 'Edit Company';
    document.getElementById('company-id').value = company.id;
    document.getElementById('company-name').value = company.name || '';
    document.getElementById('company-website').value = company.website || '';
    document.getElementById('company-linkedin').value = company.linkedin_url || '';
    document.getElementById('company-size').value = company.size || '';
    document.getElementById('company-industry').value = company.industry || '';
    document.getElementById('company-tech').value = company.tech_stack || '';
    document.getElementById('company-priority').value = company.priority || 0;
    currentPriority = company.priority || 0;
    updatePriorityStars(currentPriority);
    document.getElementById('company-culture').value = company.culture_notes || '';
    document.getElementById('company-interview').value = company.interview_process || '';
    document.getElementById('company-rating').value = company.glassdoor_rating || '';
    document.getElementById('company-salary').value = company.salary_range || '';
    document.getElementById('company-notes').value = company.notes || '';

    document.getElementById('company-modal').classList.remove('hidden');
}

async function deleteCompany(id) {
    if (!confirm('Are you sure you want to delete this company?')) return;

    await fetch(`/api/companies/${id}`, { method: 'DELETE' });
    loadCompanies();
}

async function submitForm() {
    const saveBtn = document.getElementById('save-btn');
    const saveBtnText = document.getElementById('save-btn-text');
    const saveBtnSpinner = document.getElementById('save-btn-spinner');

    saveBtn.disabled = true;
    saveBtnText.textContent = 'Saving...';
    saveBtnSpinner.classList.remove('hidden');

    try {
        const id = document.getElementById('company-id').value;
        const data = {
            name: document.getElementById('company-name').value,
            website: document.getElementById('company-website').value || null,
            linkedin_url: document.getElementById('company-linkedin').value || null,
            size: document.getElementById('company-size').value || null,
            industry: document.getElementById('company-industry').value || null,
            tech_stack: document.getElementById('company-tech').value || null,
            priority: parseInt(document.getElementById('company-priority').value) || 0,
            culture_notes: document.getElementById('company-culture').value || null,
            interview_process: document.getElementById('company-interview').value || null,
            glassdoor_rating: parseFloat(document.getElementById('company-rating').value) || null,
            salary_range: document.getElementById('company-salary').value || null,
            notes: document.getElementById('company-notes').value || null
        };

        const url = id ? `/api/companies/${id}` : '/api/companies/';
        const method = id ? 'PATCH' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save company');
        }

        closeModal();
        loadCompanies();
    } catch (e) {
        alert('Error saving company: ' + e.message);
    } finally {
        saveBtn.disabled = false;
        saveBtnText.textContent = 'Save';
        saveBtnSpinner.classList.add('hidden');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    loadCompanies();
    loadApplicationsList();

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') closeModal();
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            document.getElementById('search-input').focus();
        }
    });

    // Search & filters
    document.getElementById('search-input').addEventListener('input', handleSearch);
    document.getElementById('filter-size').addEventListener('change', loadCompanies);
    document.getElementById('filter-industry').addEventListener('change', applyFilters);
    document.getElementById('filter-priority').addEventListener('change', loadCompanies);
    document.getElementById('clear-filters-btn').addEventListener('click', clearFilters);

    // View toggle
    document.getElementById('view-cards-btn').addEventListener('click', () => setView('cards'));
    document.getElementById('view-list-btn').addEventListener('click', () => setView('list'));

    // Add button
    document.getElementById('add-modal-btn').addEventListener('click', openAddModal);

    // Sort header delegation on list thead
    const thead = document.querySelector('#list-view thead');
    if (thead) {
        thead.addEventListener('click', e => {
            const th = e.target.closest('[data-sort]');
            if (th) sortTable(th.dataset.sort);
        });
    }

    // Priority stars in modal
    document.getElementById('priority-stars').addEventListener('click', e => {
        const star = e.target.closest('[data-star]');
        if (star) setPriority(parseInt(star.dataset.star, 10));
    });

    // Cards/list grid delegation for edit, delete, empty-state, priority
    const cardsView = document.getElementById('cards-view');
    const listView = document.getElementById('list-view');

    function handleCompanyAction(e) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const action = btn.dataset.action;
        const id = parseInt(btn.dataset.id, 10);
        if (action === 'edit-company') editCompany(id);
        else if (action === 'delete-company') deleteCompany(id);
        else if (action === 'open-add') openAddModal();
        else if (action === 'clear-filters') clearFilters();
        else if (action === 'update-priority') {
            const companyId = parseInt(btn.dataset.companyId, 10);
            const priority = parseInt(btn.dataset.priority, 10);
            updatePriority(companyId, priority);
        }
    }

    cardsView.addEventListener('click', handleCompanyAction);
    listView.addEventListener('click', handleCompanyAction);

    // Modal
    document.getElementById('company-modal').addEventListener('click', e => {
        if (e.target === e.currentTarget) closeModal();
    });
    document.getElementById('company-modal-inner').addEventListener('click', e => e.stopPropagation());
    document.getElementById('modal-close-btn').addEventListener('click', closeModal);
    document.getElementById('modal-cancel-btn').addEventListener('click', closeModal);
    document.getElementById('save-btn').addEventListener('click', submitForm);
});
