/**
 * JobKit - Dashboard Page JavaScript
 */

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatFollowUpDate(dateStr) {
    const date = new Date(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const diff = Math.ceil((date - today) / (1000 * 60 * 60 * 24));

    if (diff < 0) return `${Math.abs(diff)} days overdue`;
    if (diff === 0) return 'Today';
    if (diff === 1) return 'Tomorrow';
    if (diff <= 7) return `In ${diff} days`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function isOverdue(dateStr) {
    const date = new Date(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return date < today;
}

function formatDaysSince(dateStr) {
    const date = new Date(dateStr);
    const today = new Date();
    const diff = Math.floor((today - date) / (1000 * 60 * 60 * 24));

    if (diff === 0) return 'Applied today';
    if (diff === 1) return 'Applied yesterday';
    if (diff < 7) return `Applied ${diff} days ago`;
    if (diff < 14) return 'Applied last week';
    return `Applied ${Math.floor(diff / 7)} weeks ago`;
}

function formatStatus(status) {
    const labels = {
        'saved': 'Saved',
        'applied': 'Applied',
        'phone_screen': 'Phone Screen',
        'technical': 'Technical',
        'onsite': 'Onsite',
        'offer': 'Offer!',
        'accepted': 'Accepted',
        'rejected': 'Rejected',
        'withdrawn': 'Withdrawn',
        'ghosted': 'Ghosted'
    };
    return labels[status] || status;
}

function getStatusColor(status) {
    const colors = {
        'saved': 'bg-gray-100 text-gray-700',
        'applied': 'bg-blue-100 text-blue-800',
        'phone_screen': 'bg-yellow-100 text-yellow-800',
        'technical': 'bg-purple-100 text-purple-800',
        'onsite': 'bg-indigo-100 text-indigo-800',
        'offer': 'bg-green-100 text-green-800',
        'accepted': 'bg-green-200 text-green-900',
        'rejected': 'bg-red-100 text-red-800',
        'withdrawn': 'bg-gray-200 text-gray-700',
        'ghosted': 'bg-gray-300 text-gray-600'
    };
    return colors[status] || 'bg-gray-100 text-gray-700';
}

async function snoozeFollowUp(contactId) {
    try {
        const snoozeDate = new Date();
        snoozeDate.setDate(snoozeDate.getDate() + 3);
        const dateStr = snoozeDate.toISOString().split('T')[0];

        await fetch(`/api/contacts/${contactId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ next_follow_up: dateStr })
        });

        window.location.reload();
    } catch (e) {
        console.error('Error snoozing follow-up:', e);
        alert('Failed to snooze follow-up');
    }
}

async function markFollowUpDone(contactId) {
    try {
        const today = new Date().toISOString().split('T')[0];

        await fetch(`/api/contacts/${contactId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                last_contacted: today,
                next_follow_up: null
            })
        });

        window.location.reload();
    } catch (e) {
        console.error('Error marking follow-up done:', e);
        alert('Failed to mark follow-up as done');
    }
}

function updateStreakDisplay(apps, contacts) {
    const streakEl = document.getElementById('stat-streak');
    const oneWeekAgo = new Date();
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);

    const recentApps = apps.filter(a => a.applied_date && new Date(a.applied_date) > oneWeekAgo).length;
    const recentContacts = contacts.filter(c => new Date(c.created_at) > oneWeekAgo).length;

    const totalActivity = recentApps + recentContacts;

    if (totalActivity >= 10) {
        streakEl.textContent = 'On fire this week!';
    } else if (totalActivity >= 5) {
        streakEl.textContent = 'Great progress!';
    } else if (totalActivity >= 1) {
        streakEl.textContent = 'Good start!';
    } else {
        streakEl.textContent = 'Let\'s get started!';
    }
}

document.addEventListener('DOMContentLoaded', async function() {
    let hasProfile = false;
    let hasContacts = false;
    let hasApplications = false;
    let hasCompanies = false;

    try {
        // Load user profile for welcome message
        const profileResp = await fetch('/api/profile/');
        if (profileResp.ok) {
            const profile = await profileResp.json();
            if (profile && profile.name) {
                hasProfile = true;
                document.getElementById('welcome-message').textContent = `Welcome back, ${profile.name}!`;

                const fields = ['email', 'linkedin_url', 'school', 'current_title', 'skills', 'target_roles', 'elevator_pitch'];
                const filled = fields.filter(f => profile[f] && profile[f].trim()).length;
                const completion = Math.round((filled / fields.length) * 100);

                if (completion < 70) {
                    document.getElementById('setup-profile-btn').classList.remove('hidden');
                }

                document.querySelector('#check-profile').classList.add('border-green-500', 'bg-green-100');
                document.querySelector('#check-profile svg').classList.remove('hidden');
            }
        }

        // Get application stats
        const statsResp = await fetch('/api/applications/stats');
        const stats = await statsResp.json();
        document.getElementById('stat-applications').textContent = stats.active || 0;
        document.getElementById('stat-response').textContent = (stats.response_rate || 0) + '%';
        document.getElementById('stat-weekly-apps').textContent = stats.applications_this_week || 0;

        if (stats.total > 0) {
            hasApplications = true;
            document.querySelector('#check-application').classList.add('border-green-500', 'bg-green-100');
            document.querySelector('#check-application svg').classList.remove('hidden');
        }

        // Get contacts
        const contactsResp = await fetch('/api/contacts/');
        const contacts = await contactsResp.json();
        document.getElementById('stat-contacts').textContent = contacts.length;

        const oneWeekAgo = new Date();
        oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
        const weeklyContacts = contacts.filter(c => new Date(c.created_at) > oneWeekAgo).length;
        document.getElementById('stat-weekly-contacts').textContent = weeklyContacts;

        if (contacts.length > 0) {
            hasContacts = true;
            document.querySelector('#check-contact').classList.add('border-green-500', 'bg-green-100');
            document.querySelector('#check-contact svg').classList.remove('hidden');
        }

        // Get follow-ups
        const followupsResp = await fetch('/api/contacts/?needs_follow_up=true');
        const followups = await followupsResp.json();
        document.getElementById('stat-followups').textContent = followups.length;

        // Render follow-up list
        const followupList = document.getElementById('followup-list');
        if (followups.length === 0) {
            followupList.innerHTML = `
                <div class="text-center py-8">
                    <svg class="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <p class="text-gray-500">All caught up! No pending follow-ups.</p>
                </div>
            `;
        } else {
            followupList.innerHTML = `
                <ul class="divide-y divide-gray-100">
                    ${followups.slice(0, 5).map(c => `
                        <li class="py-3 flex justify-between items-center hover:bg-gray-50 -mx-2 px-2 rounded">
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center gap-2">
                                    <span class="font-medium text-gray-900 truncate">${escapeHtml(c.name)}</span>
                                    ${c.is_alumni ? '<span class="px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">Alumni</span>' : ''}
                                </div>
                                <div class="flex items-center gap-2 mt-0.5">
                                    <span class="text-sm text-gray-500 truncate">${escapeHtml(c.company || 'No company')}</span>
                                    ${c.next_follow_up ? `
                                        <span class="text-xs text-gray-400">|</span>
                                        <span class="text-xs ${isOverdue(c.next_follow_up) ? 'text-red-600 font-medium' : 'text-gray-400'}">
                                            ${formatFollowUpDate(c.next_follow_up)}
                                        </span>
                                    ` : ''}
                                </div>
                            </div>
                            <div class="flex items-center gap-2 ml-4">
                                <button data-action="snooze" data-id="${c.id}" class="p-1.5 text-gray-400 hover:text-yellow-600 hover:bg-yellow-50 rounded" title="Snooze 3 days">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                    </svg>
                                </button>
                                <button data-action="mark-done" data-id="${c.id}" class="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded" title="Mark done">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                                    </svg>
                                </button>
                                <a href="/messages?contact=${c.id}" class="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200">
                                    Message
                                </a>
                            </div>
                        </li>
                    `).join('')}
                </ul>
            `;
        }

        // Set up follow-up action delegation
        document.getElementById('followup-list')?.addEventListener('click', e => {
            const btn = e.target.closest('[data-action]');
            if (!btn) return;
            const id = parseInt(btn.dataset.id, 10);
            if (btn.dataset.action === 'snooze') snoozeFollowUp(id);
            else if (btn.dataset.action === 'mark-done') markFollowUpDone(id);
        });

        // Get companies for checklist
        const companiesResp = await fetch('/api/companies/');
        const companies = await companiesResp.json();
        if (companies.length > 0) {
            hasCompanies = true;
            document.querySelector('#check-company').classList.add('border-green-500', 'bg-green-100');
            document.querySelector('#check-company svg').classList.remove('hidden');
        }

        // Get recent applications
        const appsResp = await fetch('/api/applications/?limit=5');
        const apps = await appsResp.json();
        const recentApps = document.getElementById('recent-applications');

        if (apps.length === 0) {
            recentApps.innerHTML = `
                <div class="text-center py-8">
                    <svg class="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                    </svg>
                    <p class="text-gray-500 mb-4">No applications tracked yet.</p>
                    <a href="/applications" class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                        </svg>
                        Add Your First Application
                    </a>
                </div>
            `;
        } else {
            recentApps.innerHTML = `
                <ul class="divide-y divide-gray-100">
                    ${apps.map(a => `
                        <li class="py-3 flex justify-between items-center hover:bg-gray-50 -mx-2 px-2 rounded">
                            <div class="flex-1 min-w-0">
                                <div class="font-medium text-gray-900 truncate">${escapeHtml(a.company_name)}</div>
                                <div class="flex items-center gap-2 mt-0.5">
                                    <span class="text-sm text-gray-500 truncate">${escapeHtml(a.role)}</span>
                                    ${a.applied_date ? `
                                        <span class="text-xs text-gray-400">|</span>
                                        <span class="text-xs text-gray-400">${formatDaysSince(a.applied_date)}</span>
                                    ` : ''}
                                </div>
                            </div>
                            <span class="px-2 py-1 text-xs rounded-full font-medium ${getStatusColor(a.status)}">${formatStatus(a.status)}</span>
                        </li>
                    `).join('')}
                </ul>
            `;
        }

        // Show onboarding if new user
        const completedCount = [hasProfile, hasContacts, hasApplications, hasCompanies].filter(Boolean).length;
        if (completedCount < 3) {
            document.getElementById('onboarding-checklist').classList.remove('hidden');
            document.getElementById('welcome-subtitle').textContent = 'Complete the checklist below to get started';
        } else {
            document.getElementById('welcome-subtitle').textContent = `You have ${stats.active || 0} active applications in progress`;
        }

        updateStreakDisplay(apps, contacts);

    } catch (e) {
        console.error('Error loading dashboard:', e);
    }
});
