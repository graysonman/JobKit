/**
 * JobKit - Authentication Module
 *
 * Token management, fetch interceptor, and auth state for the frontend.
 * Loaded before app.js on every page via base.html.
 *
 * In single-user mode (JOBKIT_SINGLE_USER_MODE=true), all auth is skipped
 * and the app works exactly as before — no login required.
 */

// ---------------------------------------------------------------------------
// Token Store — localStorage wrapper for JWT tokens
// ---------------------------------------------------------------------------
const TokenStore = {
    keys: {
        access:  'jobkit_access_token',
        refresh: 'jobkit_refresh_token',
        name:    'jobkit_user_name',
        email:   'jobkit_user_email',
        expires: 'jobkit_token_expires',
    },

    getAccess()  { return localStorage.getItem(this.keys.access); },
    getRefresh() { return localStorage.getItem(this.keys.refresh); },
    getName()    { return localStorage.getItem(this.keys.name); },
    getEmail()   { return localStorage.getItem(this.keys.email); },

    save(data) {
        // data = { access_token, refresh_token, expires_in, user? }
        localStorage.setItem(this.keys.access, data.access_token);
        localStorage.setItem(this.keys.refresh, data.refresh_token);
        if (data.expires_in) {
            const expiresAt = Date.now() + data.expires_in * 1000;
            localStorage.setItem(this.keys.expires, expiresAt.toString());
        }
        if (data.user) {
            if (data.user.name)  localStorage.setItem(this.keys.name, data.user.name);
            if (data.user.email) localStorage.setItem(this.keys.email, data.user.email);
        }
    },

    clear() {
        Object.values(this.keys).forEach(k => localStorage.removeItem(k));
    },

    isExpiringSoon() {
        const exp = localStorage.getItem(this.keys.expires);
        if (!exp) return false;
        // Refresh if less than 2 minutes remaining
        return Date.now() > (parseInt(exp, 10) - 120_000);
    },
};


// ---------------------------------------------------------------------------
// Auth — login / register / refresh / logout
// ---------------------------------------------------------------------------
const Auth = {
    // Cached auth status from /auth/status
    _status: null,
    _singleUser: null,

    async getStatus() {
        if (this._status) return this._status;
        try {
            const res = await _originalFetch('/auth/status');
            this._status = await res.json();
            this._singleUser = this._status.single_user_mode;
            return this._status;
        } catch {
            // If status endpoint fails, assume single-user for safety
            this._singleUser = true;
            return { single_user_mode: true };
        }
    },

    isSingleUser() {
        return this._singleUser === true;
    },

    isAuthenticated() {
        return !!TokenStore.getAccess();
    },

    async login(email, password) {
        // Backend uses OAuth2PasswordRequestForm: form-urlencoded, field "username"
        const body = new URLSearchParams();
        body.append('username', email);
        body.append('password', password);

        const res = await _originalFetch('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: body,
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Login failed' }));
            throw new Error(err.detail || 'Login failed');
        }

        const data = await res.json();
        // LoginResponse: { user: {...}, token: { access_token, refresh_token, expires_in } }
        TokenStore.save({
            access_token:  data.token.access_token,
            refresh_token: data.token.refresh_token,
            expires_in:    data.token.expires_in,
            user:          data.user,
        });
        return data;
    },

    async register(email, password, name) {
        const res = await _originalFetch('/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, name }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
            throw new Error(err.detail || 'Registration failed');
        }

        const data = await res.json();
        // After registration, auto-login
        await this.login(email, password);
        return data;
    },

    async refreshToken() {
        const refreshToken = TokenStore.getRefresh();
        if (!refreshToken) return false;

        try {
            const res = await _originalFetch('/auth/refresh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: refreshToken }),
            });

            if (!res.ok) return false;

            const data = await res.json();
            // Token response: { access_token, refresh_token, expires_in }
            TokenStore.save({
                access_token:  data.access_token,
                refresh_token: data.refresh_token,
                expires_in:    data.expires_in,
            });
            return true;
        } catch {
            return false;
        }
    },

    async logout() {
        const refreshToken = TokenStore.getRefresh();
        if (refreshToken) {
            try {
                await _originalFetch('/auth/logout', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${TokenStore.getAccess()}`,
                    },
                    body: JSON.stringify({ refresh_token: refreshToken }),
                });
            } catch {
                // Best-effort — clear tokens regardless
            }
        }
        TokenStore.clear();
        window.location.href = '/login';
    },
};


// ---------------------------------------------------------------------------
// Fetch Interceptor — auto-inject Authorization header
// ---------------------------------------------------------------------------

// Keep reference to the real fetch before we override it
const _originalFetch = window.fetch.bind(window);

// Endpoints that should NOT receive auth headers
const AUTH_SKIP_PATHS = ['/auth/login', '/auth/register', '/auth/refresh', '/auth/status'];

// Refresh lock to prevent multiple simultaneous refresh attempts
let _isRefreshing = false;
let _refreshQueue = [];

function _processRefreshQueue(success) {
    _refreshQueue.forEach(({ resolve, reject }) => {
        if (success) resolve();
        else reject(new Error('Token refresh failed'));
    });
    _refreshQueue = [];
}

window.fetch = async function(url, options = {}) {
    const urlStr = typeof url === 'string' ? url : url.toString();

    // Skip auth injection for auth endpoints
    const shouldSkip = AUTH_SKIP_PATHS.some(path => urlStr.includes(path));

    if (!shouldSkip && Auth._singleUser !== true) {
        const token = TokenStore.getAccess();
        if (token) {
            options.headers = options.headers || {};
            // Handle both Headers object and plain object
            if (options.headers instanceof Headers) {
                if (!options.headers.has('Authorization')) {
                    options.headers.set('Authorization', `Bearer ${token}`);
                }
            } else {
                if (!options.headers['Authorization']) {
                    options.headers['Authorization'] = `Bearer ${token}`;
                }
            }
        }

        // Proactive refresh if token is expiring soon
        if (token && TokenStore.isExpiringSoon() && !_isRefreshing) {
            Auth.refreshToken(); // Fire-and-forget
        }
    }

    let response = await _originalFetch(url, options);

    // On 401 in multi-user mode: try token refresh once
    if (response.status === 401 && !shouldSkip && Auth._singleUser !== true) {
        if (!_isRefreshing) {
            _isRefreshing = true;
            const refreshed = await Auth.refreshToken();
            _isRefreshing = false;
            _processRefreshQueue(refreshed);

            if (refreshed) {
                // Retry the original request with the new token
                const newToken = TokenStore.getAccess();
                options.headers = options.headers || {};
                if (options.headers instanceof Headers) {
                    options.headers.set('Authorization', `Bearer ${newToken}`);
                } else {
                    options.headers['Authorization'] = `Bearer ${newToken}`;
                }
                response = await _originalFetch(url, options);
            } else {
                // Refresh failed — redirect to login
                TokenStore.clear();
                if (window.location.pathname !== '/login') {
                    window.location.href = '/login';
                }
            }
        } else {
            // Another refresh is in progress — wait for it
            await new Promise((resolve, reject) => {
                _refreshQueue.push({ resolve, reject });
            }).catch(() => {});

            // Retry with new token if refresh succeeded
            const newToken = TokenStore.getAccess();
            if (newToken) {
                options.headers = options.headers || {};
                if (options.headers instanceof Headers) {
                    options.headers.set('Authorization', `Bearer ${newToken}`);
                } else {
                    options.headers['Authorization'] = `Bearer ${newToken}`;
                }
                response = await _originalFetch(url, options);
            }
        }
    }

    return response;
};


// ---------------------------------------------------------------------------
// Page-Load Guard — redirect unauthenticated users to /login
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', async () => {
    const status = await Auth.getStatus();

    // Single-user mode: skip all auth, app works as before
    if (status.single_user_mode) return;

    const onLoginPage = window.location.pathname === '/login';

    if (onLoginPage) {
        // Already authenticated? Go to dashboard
        if (Auth.isAuthenticated()) {
            window.location.href = '/';
        }
        return;
    }

    // Not on login page — must be authenticated
    if (!Auth.isAuthenticated()) {
        window.location.href = '/login';
        return;
    }

    // Populate user display name in nav
    const userName = TokenStore.getName();
    const userNameEl = document.getElementById('user-display-name');
    if (userNameEl && userName) {
        userNameEl.textContent = userName;
    }
});
