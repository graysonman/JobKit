/**
 * JobKit - Admin Panel JavaScript
 *
 * Auth guard, API wrappers, Chart.js charts, user management,
 * and table rendering with pagination for the admin panel.
 */

const AdminAPI = {
    async get(path) {
        const res = await fetch(`/api/admin${path}`);
        if (res.status === 403) {
            window.location.href = '/';
            throw new Error('Not authorized');
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Request failed: ${res.status}`);
        }
        return res.json();
    },

    async patch(path) {
        const res = await fetch(`/api/admin${path}`, { method: 'PATCH' });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Request failed: ${res.status}`);
        }
        return res.json();
    },
};


const AdminApp = {
    // =========================================================================
    // Auth Guard
    // =========================================================================
    async checkAdmin() {
        try {
            const status = await Auth.getStatus();
            if (status.single_user_mode) return;
            if (!Auth.isAuthenticated()) {
                window.location.href = '/login';
                return;
            }
            // Verify admin by fetching /auth/me
            const res = await fetch('/auth/me');
            if (!res.ok) { window.location.href = '/login'; return; }
            const user = await res.json();
            if (!user.is_admin) { window.location.href = '/'; return; }
            // Populate admin info in sidebar
            const nameEl = document.getElementById('admin-name');
            const avatarEl = document.getElementById('admin-avatar');
            const emailEl = document.getElementById('admin-email-display');
            if (nameEl) nameEl.textContent = user.name || user.email;
            if (avatarEl) avatarEl.textContent = (user.name || user.email || 'A')[0].toUpperCase();
            if (emailEl) emailEl.textContent = user.email;
        } catch {
            window.location.href = '/';
        }
    },

    // =========================================================================
    // Toast
    // =========================================================================
    toast(message, type = 'success') {
        const el = document.getElementById('admin-toast');
        if (!el) return;
        el.textContent = message;
        el.className = `toast toast-${type} show`;
        setTimeout(() => el.classList.remove('show'), 3000);
    },

    // =========================================================================
    // Confirmation Modal
    // =========================================================================
    _confirmResolve: null,

    confirm(title, message) {
        return new Promise(resolve => {
            this._confirmResolve = resolve;
            document.getElementById('confirm-title').textContent = title;
            document.getElementById('confirm-message').textContent = message;
            document.getElementById('confirm-modal').classList.remove('hidden');
            document.getElementById('confirm-btn').onclick = () => {
                this.closeModal();
                resolve(true);
            };
        });
    },

    closeModal() {
        document.getElementById('confirm-modal').classList.add('hidden');
        if (this._confirmResolve) {
            this._confirmResolve(false);
            this._confirmResolve = null;
        }
    },

    // =========================================================================
    // Dashboard
    // =========================================================================
    _signupsChart: null,
    _appStatusChart: null,

    async initDashboard() {
        await this.checkAdmin();
        // Load all dashboard data in parallel
        Promise.all([
            this.loadOverview(),
            this.loadEngagement(),
            this.loadGrowthChart('30d'),
            this.loadAppStatusChart(),
            this.loadDiagnosticCounts(),
        ]);

        // Growth period toggle buttons
        document.querySelectorAll('.growth-period-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.growth-period-btn').forEach(b => {
                    b.classList.remove('bg-blue-600', 'text-white', 'border-blue-600');
                });
                btn.classList.add('bg-blue-600', 'text-white', 'border-blue-600');
                this.loadGrowthChart(btn.dataset.period);
            });
        });
    },

    async loadOverview() {
        try {
            const data = await AdminAPI.get('/metrics/overview');
            document.getElementById('kpi-total-users').textContent = data.users.total;
            document.getElementById('kpi-signups-week').textContent = data.signups.week;

            const rate = data.users.total > 0
                ? Math.round(data.users.verified / data.users.total * 100) : 0;
            document.getElementById('kpi-verified-rate').textContent = rate + '%';

            // Records
            document.getElementById('records-contacts').textContent = data.records.contacts.toLocaleString();
            document.getElementById('records-applications').textContent = data.records.applications.toLocaleString();
            document.getElementById('records-companies').textContent = data.records.companies.toLocaleString();
            document.getElementById('records-messages').textContent = data.records.messages.toLocaleString();
        } catch (e) {
            console.error('Failed to load overview:', e);
        }
    },

    async loadEngagement() {
        try {
            const data = await AdminAPI.get('/metrics/engagement');
            document.getElementById('kpi-active-users').textContent = data.active_users.week;

            // Feature adoption
            const container = document.getElementById('feature-adoption');
            if (!container) return;
            container.innerHTML = '';
            const features = data.feature_adoption;
            const featureLabels = {
                contacts: 'Contacts',
                applications: 'Applications',
                companies: 'Companies',
                messages: 'Messages',
                profile: 'Profile',
                resume: 'Resume',
            };
            for (const [key, info] of Object.entries(features)) {
                const label = featureLabels[key] || key;
                container.innerHTML += `
                    <div class="text-center p-3 rounded-lg bg-gray-50">
                        <p class="text-lg font-bold text-gray-900">${info.pct}%</p>
                        <p class="text-xs text-gray-500">${label}</p>
                        <p class="text-xs text-gray-400">${info.users} users</p>
                    </div>`;
            }
        } catch (e) {
            console.error('Failed to load engagement:', e);
        }
    },

    async loadGrowthChart(period) {
        try {
            const data = await AdminAPI.get(`/metrics/growth?period=${period}`);
            const labels = data.data.map(d => {
                const dt = new Date(d.date);
                return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            });
            const values = data.data.map(d => d.signups);

            const ctx = document.getElementById('signups-chart');
            if (this._signupsChart) this._signupsChart.destroy();

            this._signupsChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [{
                        label: 'Signups',
                        data: values,
                        borderColor: '#7c3aed',
                        backgroundColor: 'rgba(124, 58, 237, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: period === '7d' ? 4 : 2,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, ticks: { stepSize: 1 } },
                        x: { ticks: { maxTicksLimit: period === '90d' ? 10 : 15 } },
                    },
                },
            });
        } catch (e) {
            console.error('Failed to load growth chart:', e);
        }
    },

    async loadAppStatusChart() {
        try {
            const data = await AdminAPI.get('/metrics/applications');
            const statuses = data.status_distribution;
            const labels = Object.keys(statuses);
            const values = Object.values(statuses);

            const colors = {
                saved: '#94a3b8', applied: '#3b82f6', phone_screen: '#8b5cf6',
                technical: '#a855f7', onsite: '#d946ef', offer: '#22c55e',
                accepted: '#16a34a', rejected: '#ef4444', withdrawn: '#f59e0b',
                ghosted: '#6b7280',
            };

            const ctx = document.getElementById('app-status-chart');
            if (this._appStatusChart) this._appStatusChart.destroy();

            this._appStatusChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels.map(l => l.replace('_', ' ')),
                    datasets: [{
                        data: values,
                        backgroundColor: labels.map(l => colors[l] || '#94a3b8'),
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'right', labels: { boxWidth: 12, font: { size: 11 } } },
                    },
                },
            });
        } catch (e) {
            console.error('Failed to load app status chart:', e);
        }
    },

    async loadDiagnosticCounts() {
        try {
            const [unverified, empty, stuck] = await Promise.all([
                AdminAPI.get('/diagnostics/unverified?days=7&per_page=1'),
                AdminAPI.get('/diagnostics/empty-profiles?per_page=1'),
                AdminAPI.get('/diagnostics/stuck-pipelines?per_page=1'),
            ]);
            document.getElementById('diag-unverified').textContent = unverified.total;
            document.getElementById('diag-empty').textContent = empty.total;
            document.getElementById('diag-stuck').textContent = stuck.total;
        } catch (e) {
            console.error('Failed to load diagnostics:', e);
        }
    },

    // =========================================================================
    // Users List
    // =========================================================================
    _usersState: { page: 1, filter: 'all', search: '', sort: 'created_at', order: 'desc' },

    async initUsers() {
        await this.checkAdmin();

        // Check URL params for initial filter
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('filter')) {
            this._usersState.filter = urlParams.get('filter');
            // Update active pill
            document.querySelectorAll('.user-filter-btn').forEach(btn => {
                btn.classList.remove('bg-gray-900', 'text-white');
                if (btn.dataset.filter === this._usersState.filter) {
                    btn.classList.add('bg-gray-900', 'text-white');
                }
            });
        }

        this.loadUsers();

        // Search with debounce
        let searchTimeout;
        document.getElementById('user-search').addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this._usersState.search = e.target.value;
                this._usersState.page = 1;
                this.loadUsers();
            }, 300);
        });

        // Sort
        document.getElementById('user-sort').addEventListener('change', (e) => {
            const [sort, order] = e.target.value.split(':');
            this._usersState.sort = sort;
            this._usersState.order = order;
            this._usersState.page = 1;
            this.loadUsers();
        });

        // Filter pills
        document.querySelectorAll('.user-filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.user-filter-btn').forEach(b => {
                    b.classList.remove('bg-gray-900', 'text-white');
                    b.classList.add('text-gray-600');
                });
                btn.classList.add('bg-gray-900', 'text-white');
                btn.classList.remove('text-gray-600');
                this._usersState.filter = btn.dataset.filter;
                this._usersState.page = 1;
                this.loadUsers();
            });
        });
    },

    async loadUsers() {
        const s = this._usersState;
        let params = `?page=${s.page}&sort_by=${s.sort}&sort_order=${s.order}&per_page=25`;
        if (s.search) params += `&search=${encodeURIComponent(s.search)}`;

        switch (s.filter) {
            case 'active': params += '&is_active=true'; break;
            case 'inactive': params += '&is_active=false'; break;
            case 'unverified': params += '&is_verified=false'; break;
            case 'admins': params += '&is_admin=true'; break;
        }

        try {
            const data = await AdminAPI.get(`/users${params}`);
            this.renderUsersTable(data);
        } catch (e) {
            console.error('Failed to load users:', e);
        }
    },

    renderUsersTable(data) {
        const tbody = document.getElementById('users-table-body');
        if (!data.users.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="px-4 py-8 text-center text-gray-500">No users found</td></tr>';
            document.getElementById('users-showing').textContent = 'Showing 0 users';
            document.getElementById('users-pagination').innerHTML = '';
            return;
        }

        tbody.innerHTML = data.users.map(u => `
            <tr class="hover:bg-gray-50">
                <td class="px-4 py-3">
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center text-purple-600 text-sm font-bold flex-shrink-0">
                            ${(u.name || u.email || '?')[0].toUpperCase()}
                        </div>
                        <div class="min-w-0">
                            <a href="/admin/users/${u.id}" class="text-sm font-medium text-gray-900 hover:text-purple-600 truncate block">${this.esc(u.name || 'No name')}</a>
                            <p class="text-xs text-gray-500 truncate">${this.esc(u.email)}</p>
                        </div>
                    </div>
                </td>
                <td class="px-4 py-3 hidden sm:table-cell">
                    <div class="flex flex-wrap gap-1">
                        ${u.is_active
                            ? '<span class="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700">Active</span>'
                            : '<span class="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700">Inactive</span>'}
                        ${u.is_verified
                            ? '<span class="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700">Verified</span>'
                            : '<span class="px-2 py-0.5 text-xs rounded-full bg-yellow-100 text-yellow-700">Unverified</span>'}
                        ${u.is_admin ? '<span class="px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-700">Admin</span>' : ''}
                    </div>
                </td>
                <td class="px-4 py-3 hidden md:table-cell">
                    <span class="text-sm text-gray-600">${u.records.contacts}c / ${u.records.applications}a / ${u.records.companies}co</span>
                </td>
                <td class="px-4 py-3 hidden lg:table-cell">
                    <span class="text-sm text-gray-500">${u.created_at ? new Date(u.created_at).toLocaleDateString() : '--'}</span>
                </td>
                <td class="px-4 py-3 text-right">
                    <a href="/admin/users/${u.id}" class="text-sm text-purple-600 hover:text-purple-800 font-medium">View</a>
                </td>
            </tr>
        `).join('');

        // Showing text
        const start = (data.page - 1) * data.per_page + 1;
        const end = Math.min(data.page * data.per_page, data.total);
        document.getElementById('users-showing').textContent = `Showing ${start}-${end} of ${data.total} users`;

        // Pagination
        this.renderPagination('users-pagination', data.page, data.pages, (p) => {
            this._usersState.page = p;
            this.loadUsers();
        });
    },

    // =========================================================================
    // User Detail
    // =========================================================================
    _detailUserId: null,

    async initUserDetail(userId) {
        await this.checkAdmin();
        this._detailUserId = userId;
        this.loadUserDetail();

        // Tab switching
        document.querySelectorAll('.detail-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.detail-tab').forEach(t => {
                    t.classList.remove('border-purple-600', 'text-purple-600');
                    t.classList.add('border-transparent', 'text-gray-500');
                });
                tab.classList.add('border-purple-600', 'text-purple-600');
                tab.classList.remove('border-transparent', 'text-gray-500');

                document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
                document.getElementById(`tab-content-${tab.dataset.tab}`).classList.remove('hidden');

                // Load tab data on first click
                const tabName = tab.dataset.tab;
                if (tabName !== 'overview') this.loadUserTab(tabName);
            });
        });
    },

    async loadUserDetail() {
        try {
            const user = await AdminAPI.get(`/users/${this._detailUserId}`);

            document.getElementById('detail-name').textContent = user.name || 'No name';
            document.getElementById('detail-email').textContent = user.email;
            document.getElementById('detail-avatar').textContent = (user.name || user.email || '?')[0].toUpperCase();
            document.getElementById('detail-joined').textContent = user.created_at ? new Date(user.created_at).toLocaleDateString() : '--';
            document.getElementById('detail-updated').textContent = user.updated_at ? new Date(user.updated_at).toLocaleDateString() : '--';

            // Badges
            const badges = document.getElementById('detail-badges');
            badges.innerHTML = '';
            if (user.is_active) badges.innerHTML += '<span class="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700">Active</span>';
            else badges.innerHTML += '<span class="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700">Inactive</span>';
            if (user.is_verified) badges.innerHTML += '<span class="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700">Verified</span>';
            else badges.innerHTML += '<span class="px-2 py-0.5 text-xs rounded-full bg-yellow-100 text-yellow-700">Unverified</span>';
            if (user.is_admin) badges.innerHTML += '<span class="px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-700">Admin</span>';

            // Stats
            document.getElementById('detail-contacts').textContent = user.records.contacts;
            document.getElementById('detail-applications').textContent = user.records.applications;
            document.getElementById('detail-companies').textContent = user.records.companies;
            document.getElementById('detail-messages').textContent = user.records.messages;

            // App statuses
            const statusDiv = document.getElementById('detail-app-statuses');
            const statuses = user.application_statuses || {};
            if (Object.keys(statuses).length === 0) {
                statusDiv.innerHTML = '<p class="text-sm text-gray-400">No applications</p>';
            } else {
                statusDiv.innerHTML = Object.entries(statuses).map(([s, c]) =>
                    `<span class="px-3 py-1 text-xs rounded-full bg-gray-100 text-gray-700">${s.replace('_', ' ')}: ${c}</span>`
                ).join('');
            }

            // Profile info
            this.loadUserProfile();

            // Action buttons
            this.renderDetailActions(user);
        } catch (e) {
            console.error('Failed to load user detail:', e);
            this.toast('Failed to load user', 'error');
        }
    },

    async loadUserProfile() {
        try {
            const data = await AdminAPI.get(`/users/${this._detailUserId}/profile`);
            const el = document.getElementById('detail-profile-info');
            if (!data.profile) {
                el.innerHTML = '<p class="text-gray-400">No profile created</p>';
                return;
            }
            const p = data.profile;
            el.innerHTML = `
                <div class="grid grid-cols-2 gap-2 text-sm">
                    <div><span class="text-gray-400">Title:</span> ${this.esc(p.current_title || '--')}</div>
                    <div><span class="text-gray-400">Location:</span> ${this.esc(p.location || '--')}</div>
                    <div><span class="text-gray-400">School:</span> ${this.esc(p.school || '--')}</div>
                    <div><span class="text-gray-400">Experience:</span> ${p.years_experience != null ? p.years_experience + ' years' : '--'}</div>
                    <div><span class="text-gray-400">Has Resume:</span> ${p.has_resume ? 'Yes' : 'No'}</div>
                    <div><span class="text-gray-400">Updated:</span> ${p.updated_at ? new Date(p.updated_at).toLocaleDateString() : '--'}</div>
                </div>`;
        } catch (e) {
            console.error('Failed to load profile:', e);
        }
    },

    renderDetailActions(user) {
        const container = document.getElementById('detail-actions');
        let html = '';

        if (user.is_active) {
            html += `<button onclick="AdminApp.userAction('deactivate', ${user.id})" class="px-3 py-1.5 text-xs font-medium rounded-lg border border-red-300 text-red-600 hover:bg-red-50">Deactivate</button>`;
        } else {
            html += `<button onclick="AdminApp.userAction('activate', ${user.id})" class="px-3 py-1.5 text-xs font-medium rounded-lg border border-green-300 text-green-600 hover:bg-green-50">Activate</button>`;
        }

        if (user.is_admin) {
            html += `<button onclick="AdminApp.userAction('demote', ${user.id})" class="px-3 py-1.5 text-xs font-medium rounded-lg border border-yellow-300 text-yellow-600 hover:bg-yellow-50">Demote</button>`;
        } else {
            html += `<button onclick="AdminApp.userAction('promote', ${user.id})" class="px-3 py-1.5 text-xs font-medium rounded-lg border border-purple-300 text-purple-600 hover:bg-purple-50">Promote</button>`;
        }

        if (!user.is_verified) {
            html += `<button onclick="AdminApp.userAction('verify', ${user.id})" class="px-3 py-1.5 text-xs font-medium rounded-lg border border-blue-300 text-blue-600 hover:bg-blue-50">Verify Email</button>`;
        }

        container.innerHTML = html;
    },

    async userAction(action, userId) {
        const actionLabels = {
            activate: 'Activate this user?',
            deactivate: 'Deactivate this user? They will be logged out and unable to access their account.',
            promote: 'Promote this user to admin? They will have full admin access.',
            demote: 'Remove admin privileges from this user?',
            verify: 'Force-verify this user\'s email?',
        };

        const confirmed = await this.confirm(
            action.charAt(0).toUpperCase() + action.slice(1) + ' User',
            actionLabels[action]
        );
        if (!confirmed) return;

        try {
            await AdminAPI.patch(`/users/${userId}/${action}`);
            this.toast(`User ${action}d successfully`);
            // Reload the page data
            if (this._detailUserId) this.loadUserDetail();
            else this.loadUsers();
        } catch (e) {
            this.toast(e.message, 'error');
        }
    },

    // =========================================================================
    // User Data Tabs (on detail page)
    // =========================================================================
    _tabPages: { applications: 1, contacts: 1, companies: 1, messages: 1 },

    async loadUserTab(tabName, page = 1) {
        this._tabPages[tabName] = page;
        try {
            const data = await AdminAPI.get(`/users/${this._detailUserId}/${tabName}?page=${page}&per_page=15`);
            const container = document.getElementById(`detail-${tabName}-table`);
            const paginationEl = document.getElementById(`detail-${tabName}-pagination`);

            if (!data.items.length) {
                container.innerHTML = `<p class="text-sm text-gray-400 py-4">No ${tabName} found</p>`;
                paginationEl.innerHTML = '';
                return;
            }

            container.innerHTML = this.renderDataTable(tabName, data.items);
            const totalPages = Math.ceil(data.total / data.per_page);
            this.renderPagination(paginationEl.id, page, totalPages, (p) => this.loadUserTab(tabName, p));
        } catch (e) {
            console.error(`Failed to load ${tabName}:`, e);
        }
    },

    renderDataTable(type, items) {
        switch (type) {
            case 'applications':
                return `<table class="w-full text-sm">
                    <thead><tr class="text-left text-xs text-gray-500 border-b">
                        <th class="pb-2">Company</th><th class="pb-2">Role</th><th class="pb-2">Status</th><th class="pb-2">Applied</th><th class="pb-2">Source</th>
                    </tr></thead>
                    <tbody>${items.map(a => `<tr class="border-b border-gray-100">
                        <td class="py-2">${this.esc(a.company_name)}</td>
                        <td class="py-2">${this.esc(a.role)}</td>
                        <td class="py-2"><span class="px-2 py-0.5 text-xs rounded-full bg-gray-100">${a.status || '--'}</span></td>
                        <td class="py-2 text-gray-500">${a.applied_date || '--'}</td>
                        <td class="py-2 text-gray-500">${a.source || '--'}</td>
                    </tr>`).join('')}</tbody></table>`;

            case 'contacts':
                return `<table class="w-full text-sm">
                    <thead><tr class="text-left text-xs text-gray-500 border-b">
                        <th class="pb-2">Name</th><th class="pb-2">Company</th><th class="pb-2">Type</th><th class="pb-2">Status</th>
                    </tr></thead>
                    <tbody>${items.map(c => `<tr class="border-b border-gray-100">
                        <td class="py-2">${this.esc(c.name)}</td>
                        <td class="py-2">${this.esc(c.company || '--')}</td>
                        <td class="py-2">${c.contact_type || '--'}</td>
                        <td class="py-2">${c.connection_status || '--'}</td>
                    </tr>`).join('')}</tbody></table>`;

            case 'companies':
                return `<table class="w-full text-sm">
                    <thead><tr class="text-left text-xs text-gray-500 border-b">
                        <th class="pb-2">Name</th><th class="pb-2">Industry</th><th class="pb-2">Size</th><th class="pb-2">Priority</th>
                    </tr></thead>
                    <tbody>${items.map(c => `<tr class="border-b border-gray-100">
                        <td class="py-2">${this.esc(c.name)}</td>
                        <td class="py-2">${this.esc(c.industry || '--')}</td>
                        <td class="py-2">${c.size || '--'}</td>
                        <td class="py-2">${c.priority != null ? c.priority : '--'}</td>
                    </tr>`).join('')}</tbody></table>`;

            case 'messages':
                return `<table class="w-full text-sm">
                    <thead><tr class="text-left text-xs text-gray-500 border-b">
                        <th class="pb-2">Type</th><th class="pb-2">Content</th><th class="pb-2">Sent</th><th class="pb-2">Response</th>
                    </tr></thead>
                    <tbody>${items.map(m => `<tr class="border-b border-gray-100">
                        <td class="py-2">${m.message_type || '--'}</td>
                        <td class="py-2 max-w-xs truncate">${this.esc(m.message_content || '--')}</td>
                        <td class="py-2 text-gray-500">${m.sent_at ? new Date(m.sent_at).toLocaleDateString() : '--'}</td>
                        <td class="py-2">${m.got_response ? '<span class="text-green-600">Yes</span>' : '<span class="text-gray-400">No</span>'}</td>
                    </tr>`).join('')}</tbody></table>`;

            default:
                return '';
        }
    },

    // =========================================================================
    // Audit Log
    // =========================================================================
    async initAuditLog() {
        await this.checkAdmin();
        this.loadAuditLog(1);
    },

    async loadAuditLog(page = 1) {
        let params = `?page=${page}&per_page=50`;

        const action = document.getElementById('audit-action-filter')?.value;
        const adminId = document.getElementById('audit-admin-filter')?.value;
        const targetId = document.getElementById('audit-target-filter')?.value;

        if (action) params += `&action=${action}`;
        if (adminId) params += `&admin_user_id=${adminId}`;
        if (targetId) params += `&target_user_id=${targetId}`;

        try {
            const data = await AdminAPI.get(`/audit-log${params}`);
            const tbody = document.getElementById('audit-table-body');

            if (!data.items.length) {
                tbody.innerHTML = '<tr><td colspan="6" class="px-4 py-8 text-center text-gray-500">No audit log entries</td></tr>';
                document.getElementById('audit-showing').textContent = '0 entries';
                document.getElementById('audit-pagination').innerHTML = '';
                return;
            }

            const actionColors = {
                activate_user: 'bg-green-100 text-green-700',
                deactivate_user: 'bg-red-100 text-red-700',
                promote_user: 'bg-purple-100 text-purple-700',
                demote_user: 'bg-yellow-100 text-yellow-700',
                verify_user: 'bg-blue-100 text-blue-700',
                view_user_data: 'bg-gray-100 text-gray-700',
            };

            tbody.innerHTML = data.items.map(e => `
                <tr class="hover:bg-gray-50">
                    <td class="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">${e.created_at ? new Date(e.created_at).toLocaleString() : '--'}</td>
                    <td class="px-4 py-3 text-sm">${this.esc(e.admin_email || `ID:${e.admin_user_id}`)}</td>
                    <td class="px-4 py-3">
                        <span class="px-2 py-0.5 text-xs rounded-full ${actionColors[e.action] || 'bg-gray-100 text-gray-700'}">${e.action.replace(/_/g, ' ')}</span>
                    </td>
                    <td class="px-4 py-3 text-sm hidden sm:table-cell">
                        ${e.target_user_id
                            ? `<a href="/admin/users/${e.target_user_id}" class="text-purple-600 hover:text-purple-800">${this.esc(e.target_email || `ID:${e.target_user_id}`)}</a>`
                            : '--'}
                    </td>
                    <td class="px-4 py-3 text-xs text-gray-500 hidden md:table-cell max-w-xs truncate">${e.details ? JSON.stringify(e.details) : '--'}</td>
                    <td class="px-4 py-3 text-xs text-gray-400 hidden lg:table-cell">${e.ip_address || '--'}</td>
                </tr>
            `).join('');

            const start = (data.page - 1) * data.per_page + 1;
            const end = Math.min(data.page * data.per_page, data.total);
            document.getElementById('audit-showing').textContent = `Showing ${start}-${end} of ${data.total} entries`;

            this.renderPagination('audit-pagination', data.page, data.pages, (p) => this.loadAuditLog(p));
        } catch (e) {
            console.error('Failed to load audit log:', e);
        }
    },

    // =========================================================================
    // Helpers
    // =========================================================================
    esc(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },

    renderPagination(containerId, current, total, onPageClick) {
        const container = document.getElementById(containerId);
        if (!container || total <= 1) {
            if (container) container.innerHTML = '';
            return;
        }

        let html = '';
        // Previous
        if (current > 1) {
            html += `<button class="px-3 py-1 text-sm border rounded-lg hover:bg-gray-50" data-page="${current - 1}">Prev</button>`;
        }

        // Page numbers (show max 5)
        let startPage = Math.max(1, current - 2);
        let endPage = Math.min(total, startPage + 4);
        if (endPage - startPage < 4) startPage = Math.max(1, endPage - 4);

        for (let i = startPage; i <= endPage; i++) {
            if (i === current) {
                html += `<button class="px-3 py-1 text-sm border rounded-lg bg-purple-600 text-white" disabled>${i}</button>`;
            } else {
                html += `<button class="px-3 py-1 text-sm border rounded-lg hover:bg-gray-50" data-page="${i}">${i}</button>`;
            }
        }

        // Next
        if (current < total) {
            html += `<button class="px-3 py-1 text-sm border rounded-lg hover:bg-gray-50" data-page="${current + 1}">Next</button>`;
        }

        container.innerHTML = html;

        // Attach click handlers
        container.querySelectorAll('button[data-page]').forEach(btn => {
            btn.addEventListener('click', () => onPageClick(parseInt(btn.dataset.page)));
        });
    },
};
