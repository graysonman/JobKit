/**
 * JobKit - Applications Page JavaScript
 */

let allApplications = [];
let filteredApplications = [];
let currentView = 'table';
let currentSort = { field: 'applied_date', direction: 'desc' };
let searchTimeout = null;
let activeStageFilter = null;

function setupExcitementSlider() {
    const slider = document.getElementById('app-excitement');
    const label = document.getElementById('excitement-label');
    const labels = ['Not Excited', 'Slightly', 'Neutral', 'Excited', 'Very Excited'];

    slider.addEventListener('input', function() {
        label.textContent = labels[this.value - 1];
    });
}

async function loadApplications() {
    const status = document.getElementById('filter-status').value;
    const activeOnly = document.getElementById('filter-active').checked;
    const dateRange = document.getElementById('filter-date-range').value;

    let url = '/api/applications/?';
    if (status) url += `status=${status}&`;
    if (activeOnly && !activeStageFilter) url += `active_only=true&`;

    const response = await fetch(url);
    allApplications = await response.json();

    if (dateRange) {
        const now = new Date();
        let cutoff = new Date();
        if (dateRange === 'week') cutoff.setDate(now.getDate() - 7);
        else if (dateRange === 'month') cutoff.setDate(now.getDate() - 30);
        else if (dateRange === 'quarter') cutoff.setDate(now.getDate() - 90);

        allApplications = allApplications.filter(a => {
            if (!a.applied_date) return true;
            return new Date(a.applied_date) >= cutoff;
        });
    }

    applySearchFilter();
    updateCounts();
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
        filteredApplications = allApplications.filter(a =>
            (a.company_name && a.company_name.toLowerCase().includes(searchTerm)) ||
            (a.role && a.role.toLowerCase().includes(searchTerm))
        );
    } else {
        filteredApplications = [...allApplications];
    }

    if (activeStageFilter) {
        filteredApplications = filteredApplications.filter(a => {
            if (activeStageFilter === 'saved') return a.status === 'saved';
            if (activeStageFilter === 'applied') return a.status === 'applied';
            if (activeStageFilter === 'interviewing') return ['phone_screen', 'technical', 'onsite'].includes(a.status);
            if (activeStageFilter === 'offer') return ['offer', 'accepted'].includes(a.status);
            if (activeStageFilter === 'closed') return ['rejected', 'withdrawn', 'ghosted'].includes(a.status);
            return true;
        });
    }

    sortApplications();
    renderApplications();
    updateResultsCount();
    updateClearFiltersButton();
}

function sortApplications() {
    const { field, direction } = currentSort;
    filteredApplications.sort((a, b) => {
        let aVal = a[field] || '';
        let bVal = b[field] || '';

        if (field === 'applied_date') {
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
        currentSort.direction = field === 'applied_date' ? 'desc' : 'asc';
    }
    sortApplications();
    renderApplications();
}

function updateResultsCount() {
    const total = allApplications.length;
    const filtered = filteredApplications.length;
    const countEl = document.getElementById('results-count');

    if (total === 0) {
        countEl.textContent = 'No applications yet';
    } else if (filtered === total) {
        countEl.textContent = `${total} application${total !== 1 ? 's' : ''}`;
    } else {
        countEl.textContent = `Showing ${filtered} of ${total} applications`;
    }
}

function updateClearFiltersButton() {
    const hasFilters =
        document.getElementById('filter-status').value ||
        document.getElementById('filter-date-range').value ||
        !document.getElementById('filter-active').checked ||
        document.getElementById('search-input').value.trim() ||
        activeStageFilter;

    document.getElementById('clear-filters-btn').classList.toggle('hidden', !hasFilters);
}

function clearFilters() {
    document.getElementById('filter-status').value = '';
    document.getElementById('filter-date-range').value = '';
    document.getElementById('filter-active').checked = true;
    document.getElementById('search-input').value = '';
    activeStageFilter = null;

    document.querySelectorAll('[data-stage]').forEach(btn => {
        btn.classList.remove('ring-2', 'ring-offset-2', 'ring-blue-500');
    });

    loadApplications();
}

function filterByStage(stage) {
    if (activeStageFilter === stage) {
        activeStageFilter = null;
        document.querySelectorAll('[data-stage]').forEach(btn => {
            btn.classList.remove('ring-2', 'ring-offset-2', 'ring-blue-500');
        });
    } else {
        activeStageFilter = stage;
        document.querySelectorAll('[data-stage]').forEach(btn => {
            btn.classList.remove('ring-2', 'ring-offset-2', 'ring-blue-500');
        });
        document.querySelector(`[data-stage="${stage}"]`).classList.add('ring-2', 'ring-offset-2', 'ring-blue-500');
    }

    document.getElementById('filter-status').value = '';
    document.getElementById('filter-active').checked = false;

    applySearchFilter();
}

async function updateCounts() {
    const response = await fetch('/api/applications/stats');
    const stats = await response.json();

    const saved = stats.by_status.saved || 0;
    const applied = stats.by_status.applied || 0;
    const interviewing = (stats.by_status.phone_screen || 0) + (stats.by_status.technical || 0) + (stats.by_status.onsite || 0);
    const offers = (stats.by_status.offer || 0) + (stats.by_status.accepted || 0);
    const closed = (stats.by_status.rejected || 0) + (stats.by_status.withdrawn || 0) + (stats.by_status.ghosted || 0);

    document.getElementById('count-saved').textContent = saved;
    document.getElementById('count-applied').textContent = applied;
    document.getElementById('count-interviewing').textContent = interviewing;
    document.getElementById('count-offer').textContent = offers;
    document.getElementById('count-closed').textContent = closed;

    const totalApplied = applied + interviewing + offers + closed;
    if (totalApplied > 0) {
        const interviewRate = Math.round((interviewing + offers) / totalApplied * 100);
        const offerRate = Math.round(offers / totalApplied * 100);

        document.getElementById('rate-applied').textContent = '';
        document.getElementById('rate-interviewing').textContent = interviewRate > 0 ? `${interviewRate}% interview` : '';
        document.getElementById('rate-offer').textContent = offerRate > 0 ? `${offerRate}% offer` : '';

        document.getElementById('conversion-summary').textContent =
            `${interviewRate}% interview rate | ${offerRate}% offer rate`;
    }
}

function setView(view) {
    currentView = view;

    document.getElementById('view-table-btn').classList.toggle('bg-blue-600', view === 'table');
    document.getElementById('view-table-btn').classList.toggle('text-white', view === 'table');
    document.getElementById('view-table-btn').classList.toggle('bg-white', view !== 'table');
    document.getElementById('view-table-btn').classList.toggle('text-gray-600', view !== 'table');

    document.getElementById('view-kanban-btn').classList.toggle('bg-blue-600', view === 'kanban');
    document.getElementById('view-kanban-btn').classList.toggle('text-white', view === 'kanban');
    document.getElementById('view-kanban-btn').classList.toggle('bg-white', view !== 'kanban');
    document.getElementById('view-kanban-btn').classList.toggle('text-gray-600', view !== 'kanban');

    document.getElementById('table-view').classList.toggle('hidden', view !== 'table');
    document.getElementById('kanban-view').classList.toggle('hidden', view !== 'kanban');

    renderApplications();
}

function renderApplications() {
    if (currentView === 'table') {
        renderTableView();
    } else {
        renderKanbanView();
    }
}

function renderTableView() {
    const tbody = document.getElementById('applications-table-body');

    if (filteredApplications.length === 0) {
        const emptyAction = allApplications.length === 0 ? 'open-add' : 'clear-filters';
        const emptyLabel = allApplications.length === 0 ? 'Track Your First Application' : 'Clear Filters';
        const emptyIcon = allApplications.length === 0
            ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>'
            : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>';
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="px-6 py-12 text-center">
                    <div class="flex flex-col items-center">
                        <svg class="w-16 h-16 text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                        </svg>
                        <p class="text-gray-500 mb-4">${allApplications.length === 0 ? 'No applications yet. Start tracking your job search!' : 'No applications match your filters.'}</p>
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
        return;
    }

    tbody.innerHTML = filteredApplications.map(a => `
        <tr class="hover:bg-gray-50 transition-colors">
            <td class="px-6 py-4">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center text-gray-500 font-semibold text-sm">
                        ${escapeHtml(a.company_name.substring(0, 2).toUpperCase())}
                    </div>
                    <div>
                        <div class="font-medium text-gray-900">${escapeHtml(a.company_name)}</div>
                        ${a.job_url ? `<a href="${escapeHtml(a.job_url)}" target="_blank" class="text-xs text-blue-500 hover:underline">View posting</a>` : ''}
                    </div>
                </div>
            </td>
            <td class="px-6 py-4">
                <div class="text-gray-900">${escapeHtml(a.role)}</div>
                ${a.location ? `<div class="text-xs text-gray-500">${escapeHtml(a.location)}</div>` : ''}
            </td>
            <td class="px-6 py-4">
                <select data-action="update-status" data-id="${a.id}" class="text-xs border rounded-lg px-2 py-1.5 font-medium ${getStatusBg(a.status)} cursor-pointer focus:ring-2 focus:ring-blue-500">
                    <option value="saved" ${a.status === 'saved' ? 'selected' : ''}>Saved</option>
                    <option value="applied" ${a.status === 'applied' ? 'selected' : ''}>Applied</option>
                    <option value="phone_screen" ${a.status === 'phone_screen' ? 'selected' : ''}>Phone Screen</option>
                    <option value="technical" ${a.status === 'technical' ? 'selected' : ''}>Technical</option>
                    <option value="onsite" ${a.status === 'onsite' ? 'selected' : ''}>Onsite</option>
                    <option value="offer" ${a.status === 'offer' ? 'selected' : ''}>Offer</option>
                    <option value="accepted" ${a.status === 'accepted' ? 'selected' : ''}>Accepted</option>
                    <option value="rejected" ${a.status === 'rejected' ? 'selected' : ''}>Rejected</option>
                    <option value="withdrawn" ${a.status === 'withdrawn' ? 'selected' : ''}>Withdrawn</option>
                    <option value="ghosted" ${a.status === 'ghosted' ? 'selected' : ''}>Ghosted</option>
                </select>
            </td>
            <td class="px-6 py-4">
                ${a.applied_date ? `
                    <div class="text-gray-900">${formatDate(a.applied_date)}</div>
                    <div class="text-xs ${getDaysSinceColor(a.applied_date, a.status)}">${getDaysSinceText(a.applied_date)}</div>
                ` : '<span class="text-gray-400">-</span>'}
            </td>
            <td class="px-6 py-4">
                ${a.next_step ? `
                    <div class="text-gray-900">${escapeHtml(a.next_step)}</div>
                    ${a.next_step_date ? `<div class="text-xs text-gray-500">${formatDate(a.next_step_date)}</div>` : ''}
                ` : '<span class="text-gray-400">-</span>'}
            </td>
            <td class="px-6 py-4">
                ${renderExcitementStars(a.excitement_level || 3)}
            </td>
            <td class="px-6 py-4">
                <div class="flex items-center gap-2">
                    <button data-action="edit-application" data-id="${a.id}" class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors" title="Edit">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                        </svg>
                    </button>
                    <button data-action="delete-application" data-id="${a.id}" class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors" title="Delete">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function renderKanbanView() {
    const saved = filteredApplications.filter(a => a.status === 'saved');
    const applied = filteredApplications.filter(a => a.status === 'applied');
    const interviewing = filteredApplications.filter(a => ['phone_screen', 'technical', 'onsite'].includes(a.status));
    const offers = filteredApplications.filter(a => ['offer', 'accepted'].includes(a.status));

    document.getElementById('kanban-count-saved').textContent = `(${saved.length})`;
    document.getElementById('kanban-count-applied').textContent = `(${applied.length})`;
    document.getElementById('kanban-count-interviewing').textContent = `(${interviewing.length})`;
    document.getElementById('kanban-count-offers').textContent = `(${offers.length})`;

    document.getElementById('kanban-saved').innerHTML = renderKanbanCards(saved);
    document.getElementById('kanban-applied').innerHTML = renderKanbanCards(applied);
    document.getElementById('kanban-interviewing').innerHTML = renderKanbanCards(interviewing);
    document.getElementById('kanban-offers').innerHTML = renderKanbanCards(offers);
}

function renderKanbanCards(apps) {
    if (apps.length === 0) {
        return '<div class="text-center text-gray-400 text-sm py-4">No applications</div>';
    }

    return apps.map(a => `
        <div class="bg-white rounded-lg p-3 shadow-sm hover:shadow-md transition-shadow cursor-pointer" data-action="edit-application" data-id="${a.id}">
            <div class="font-medium text-gray-900 truncate">${escapeHtml(a.company_name)}</div>
            <div class="text-sm text-gray-500 truncate">${escapeHtml(a.role)}</div>
            ${a.applied_date ? `<div class="text-xs ${getDaysSinceColor(a.applied_date, a.status)} mt-2">${getDaysSinceText(a.applied_date)}</div>` : ''}
            ${a.next_step ? `<div class="text-xs text-gray-400 mt-1">Next: ${escapeHtml(a.next_step)}</div>` : ''}
        </div>
    `).join('');
}

function renderExcitementStars(level) {
    const stars = [];
    for (let i = 1; i <= 5; i++) {
        const filled = i <= level;
        stars.push(`<svg class="w-4 h-4 ${filled ? 'text-yellow-400' : 'text-gray-300'}" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
        </svg>`);
    }
    return `<div class="flex">${stars.join('')}</div>`;
}

function getDaysSinceText(dateStr) {
    const date = new Date(dateStr);
    const today = new Date();
    const diff = Math.floor((today - date) / (1000 * 60 * 60 * 24));

    if (diff === 0) return 'Today';
    if (diff === 1) return '1 day ago';
    if (diff < 7) return `${diff} days ago`;
    if (diff < 14) return '1 week ago';
    if (diff < 30) return `${Math.floor(diff / 7)} weeks ago`;
    return `${Math.floor(diff / 30)} month${Math.floor(diff / 30) > 1 ? 's' : ''} ago`;
}

function getDaysSinceColor(dateStr, status) {
    if (['accepted', 'rejected', 'withdrawn', 'ghosted'].includes(status)) {
        return 'text-gray-500';
    }

    const date = new Date(dateStr);
    const today = new Date();
    const diff = Math.floor((today - date) / (1000 * 60 * 60 * 24));

    if (diff < 7) return 'text-green-600';
    if (diff < 14) return 'text-yellow-600';
    return 'text-red-600';
}

function getStatusBg(status) {
    const colors = {
        'saved': 'bg-gray-100 text-gray-700',
        'applied': 'bg-blue-100 text-blue-700',
        'phone_screen': 'bg-yellow-100 text-yellow-700',
        'technical': 'bg-purple-100 text-purple-700',
        'onsite': 'bg-indigo-100 text-indigo-700',
        'offer': 'bg-green-100 text-green-700',
        'accepted': 'bg-green-200 text-green-800',
        'rejected': 'bg-red-100 text-red-700',
        'withdrawn': 'bg-gray-200 text-gray-700',
        'ghosted': 'bg-gray-300 text-gray-700'
    };
    return colors[status] || 'bg-gray-100 text-gray-700';
}

async function updateStatus(id, status) {
    await fetch(`/api/applications/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
    });

    showToast('Status updated successfully');
    loadApplications();
}

function showToast(message) {
    const toast = document.getElementById('toast');
    document.getElementById('toast-message').textContent = message;

    toast.classList.remove('hidden');
    setTimeout(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
    }, 10);

    setTimeout(() => {
        toast.classList.add('translate-y-2', 'opacity-0');
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 300);
    }, 3000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function openAddModal() {
    document.getElementById('modal-title').textContent = 'Track Application';
    document.getElementById('application-form').reset();
    document.getElementById('app-id').value = '';
    document.getElementById('app-status').value = 'saved';
    document.getElementById('app-excitement').value = 3;
    document.getElementById('excitement-label').textContent = 'Neutral';
    document.getElementById('application-modal').classList.remove('hidden');
    document.getElementById('app-company').focus();
}

function closeModal() {
    document.getElementById('application-modal').classList.add('hidden');
}

async function editApplication(id) {
    const app = allApplications.find(a => a.id === id);
    if (!app) return;

    document.getElementById('modal-title').textContent = 'Edit Application';
    document.getElementById('app-id').value = app.id;
    document.getElementById('app-company').value = app.company_name || '';
    document.getElementById('app-role').value = app.role || '';
    document.getElementById('app-location').value = app.location || '';
    document.getElementById('app-source').value = app.source || '';
    document.getElementById('app-url').value = app.job_url || '';
    document.getElementById('app-status').value = app.status || 'saved';
    document.getElementById('app-date').value = app.applied_date || '';
    document.getElementById('app-next-step').value = app.next_step || '';
    document.getElementById('app-next-date').value = app.next_step_date || '';
    document.getElementById('app-excitement').value = app.excitement_level || 3;
    document.getElementById('app-salary-min').value = app.salary_min || '';
    document.getElementById('app-salary-max').value = app.salary_max || '';
    document.getElementById('app-salary').value = app.salary_offered || '';
    document.getElementById('app-description').value = app.job_description || '';
    document.getElementById('app-notes').value = app.notes || '';

    const labels = ['Not Excited', 'Slightly', 'Neutral', 'Excited', 'Very Excited'];
    document.getElementById('excitement-label').textContent = labels[(app.excitement_level || 3) - 1];

    document.getElementById('application-modal').classList.remove('hidden');
}

async function deleteApplication(id) {
    if (!confirm('Are you sure you want to delete this application?')) return;

    await fetch(`/api/applications/${id}`, { method: 'DELETE' });
    showToast('Application deleted');
    loadApplications();
}

async function submitForm() {
    const saveBtn = document.getElementById('save-btn');
    const saveBtnText = document.getElementById('save-btn-text');
    const saveBtnSpinner = document.getElementById('save-btn-spinner');

    saveBtn.disabled = true;
    saveBtnText.textContent = 'Saving...';
    saveBtnSpinner.classList.remove('hidden');

    try {
        const id = document.getElementById('app-id').value;
        const data = {
            company_name: document.getElementById('app-company').value,
            role: document.getElementById('app-role').value,
            location: document.getElementById('app-location').value || null,
            source: document.getElementById('app-source').value || null,
            job_url: document.getElementById('app-url').value || null,
            status: document.getElementById('app-status').value,
            applied_date: document.getElementById('app-date').value || null,
            next_step: document.getElementById('app-next-step').value || null,
            next_step_date: document.getElementById('app-next-date').value || null,
            excitement_level: parseInt(document.getElementById('app-excitement').value),
            salary_min: document.getElementById('app-salary-min').value ? parseInt(document.getElementById('app-salary-min').value) : null,
            salary_max: document.getElementById('app-salary-max').value ? parseInt(document.getElementById('app-salary-max').value) : null,
            salary_offered: document.getElementById('app-salary').value || null,
            job_description: document.getElementById('app-description').value || null,
            notes: document.getElementById('app-notes').value || null
        };

        const url = id ? `/api/applications/${id}` : '/api/applications/';
        const method = id ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save application');
        }

        closeModal();
        showToast(id ? 'Application updated' : 'Application added');
        loadApplications();
    } catch (e) {
        alert('Error saving application: ' + e.message);
    } finally {
        saveBtn.disabled = false;
        saveBtnText.textContent = 'Save';
        saveBtnSpinner.classList.add('hidden');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    loadApplications();
    setupExcitementSlider();

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
    document.getElementById('filter-status').addEventListener('change', loadApplications);
    document.getElementById('filter-date-range').addEventListener('change', loadApplications);
    document.getElementById('filter-active').addEventListener('change', loadApplications);
    document.getElementById('clear-filters-btn').addEventListener('click', clearFilters);

    // View toggle
    document.getElementById('view-table-btn').addEventListener('click', () => setView('table'));
    document.getElementById('view-kanban-btn').addEventListener('click', () => setView('kanban'));

    // Add button
    document.getElementById('add-modal-btn').addEventListener('click', openAddModal);

    // Pipeline stage buttons (delegation on the pipeline grid)
    document.querySelector('.grid.grid-cols-2').addEventListener('click', e => {
        const btn = e.target.closest('[data-stage]');
        if (btn) filterByStage(btn.dataset.stage);
    });

    // Sort header delegation on thead
    document.querySelector('thead').addEventListener('click', e => {
        const th = e.target.closest('[data-sort]');
        if (th) sortTable(th.dataset.sort);
    });

    // Table body: click delegation for edit/delete/empty-state
    document.getElementById('applications-table-body').addEventListener('click', e => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const action = btn.dataset.action;
        const id = parseInt(btn.dataset.id, 10);
        if (action === 'edit-application') editApplication(id);
        else if (action === 'delete-application') deleteApplication(id);
        else if (action === 'open-add') openAddModal();
        else if (action === 'clear-filters') clearFilters();
    });

    // Table body: change delegation for status select
    document.getElementById('applications-table-body').addEventListener('change', e => {
        const sel = e.target.closest('[data-action="update-status"]');
        if (sel) updateStatus(parseInt(sel.dataset.id, 10), sel.value);
    });

    // Kanban: click delegation for editing cards
    document.getElementById('kanban-view').addEventListener('click', e => {
        const card = e.target.closest('[data-action="edit-application"]');
        if (card) editApplication(parseInt(card.dataset.id, 10));
    });

    // Modal
    document.getElementById('application-modal').addEventListener('click', e => {
        if (e.target === e.currentTarget) closeModal();
    });
    document.getElementById('application-modal-inner').addEventListener('click', e => e.stopPropagation());
    document.getElementById('modal-close-btn').addEventListener('click', closeModal);
    document.getElementById('modal-cancel-btn').addEventListener('click', closeModal);
    document.getElementById('save-btn').addEventListener('click', submitForm);
});
