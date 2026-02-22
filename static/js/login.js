/**
 * JobKit - Login / Register Page JavaScript
 */

// ---- Tab switching ----
function switchTab(tab) {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');
    const errorEl = document.getElementById('auth-error');
    const successEl = document.getElementById('auth-success');

    errorEl.classList.add('hidden');
    successEl.classList.add('hidden');

    if (tab === 'login') {
        loginForm.classList.remove('hidden');
        registerForm.classList.add('hidden');
        tabLogin.className = tabLogin.className.replace('tab-inactive', 'tab-active');
        tabRegister.className = tabRegister.className.replace('tab-active', 'tab-inactive');
    } else {
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
        tabRegister.className = tabRegister.className.replace('tab-inactive', 'tab-active');
        tabLogin.className = tabLogin.className.replace('tab-active', 'tab-inactive');
    }
}

// ---- Password strength ----
function checkPasswordStrength() {
    const pw = document.getElementById('register-password').value;
    const checks = {
        length: pw.length >= 8,
        upper:  /[A-Z]/.test(pw),
        lower:  /[a-z]/.test(pw),
        digit:  /[0-9]/.test(pw),
    };

    document.getElementById('check-length').className = checks.length ? 'check-pass' : 'check-fail';
    document.getElementById('check-upper').className  = checks.upper  ? 'check-pass' : 'check-fail';
    document.getElementById('check-lower').className  = checks.lower  ? 'check-pass' : 'check-fail';
    document.getElementById('check-digit').className  = checks.digit  ? 'check-pass' : 'check-fail';

    const passed = Object.values(checks).filter(Boolean).length;
    const bar = document.getElementById('strength-bar');
    const pct = (passed / 4) * 100;
    bar.style.width = pct + '%';

    if (passed <= 1)      bar.className = 'h-full strength-bar rounded-full bg-red-400';
    else if (passed <= 2) bar.className = 'h-full strength-bar rounded-full bg-yellow-400';
    else if (passed <= 3) bar.className = 'h-full strength-bar rounded-full bg-blue-400';
    else                  bar.className = 'h-full strength-bar rounded-full bg-green-500';
}

// ---- Show error / success ----
function showError(msg) {
    const el = document.getElementById('auth-error');
    el.textContent = msg;
    el.classList.remove('hidden');
    document.getElementById('auth-success').classList.add('hidden');
}

function showSuccess(msg) {
    const el = document.getElementById('auth-success');
    el.textContent = msg;
    el.classList.remove('hidden');
    document.getElementById('auth-error').classList.add('hidden');
}

// ---- Login handler ----
async function handleLogin(e) {
    e.preventDefault();
    const btn = document.getElementById('login-btn');
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    btn.disabled = true;
    btn.textContent = 'Signing in...';

    try {
        await Auth.login(email, password);
        window.location.href = '/';
    } catch (err) {
        showError(err.message);
        btn.disabled = false;
        btn.textContent = 'Sign In';
    }
}

// ---- Register handler ----
async function handleRegister(e) {
    e.preventDefault();
    const btn = document.getElementById('register-btn');
    const name = document.getElementById('register-name').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const confirm = document.getElementById('register-confirm').value;

    if (password !== confirm) {
        showError('Passwords do not match.');
        return;
    }

    // Client-side strength check
    const checks = [password.length >= 8, /[A-Z]/.test(password), /[a-z]/.test(password), /[0-9]/.test(password)];
    if (!checks.every(Boolean)) {
        showError('Password must be at least 8 characters with uppercase, lowercase, and a number.');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Creating account...';

    try {
        await Auth.register(email, password, name);
        showSuccess('Account created! Check your email to verify your address.');
        setTimeout(() => { window.location.href = '/'; }, 2000);
    } catch (err) {
        showError(err.message);
        btn.disabled = false;
        btn.textContent = 'Create Account';
    }
}

// ---- DOMContentLoaded: bind events + check OAuth ----
document.addEventListener('DOMContentLoaded', async () => {
    // Tab buttons
    document.getElementById('tab-login').addEventListener('click', () => switchTab('login'));
    document.getElementById('tab-register').addEventListener('click', () => switchTab('register'));

    // Form submits
    document.getElementById('login-form').addEventListener('submit', handleLogin);
    document.getElementById('register-form').addEventListener('submit', handleRegister);

    // Password strength
    document.getElementById('register-password').addEventListener('input', checkPasswordStrength);

    // Check OAuth availability; redirect if single-user mode
    const status = await Auth.getStatus();

    if (status.single_user_mode) {
        window.location.href = '/';
        return;
    }

    if (status.oauth_providers) {
        const hasGoogle = status.oauth_providers.includes('google');
        const hasGithub = status.oauth_providers.includes('github');
        if (hasGoogle || hasGithub) {
            document.getElementById('oauth-section').classList.remove('hidden');
            if (!hasGoogle) document.getElementById('oauth-google').classList.add('hidden');
            if (!hasGithub) document.getElementById('oauth-github').classList.add('hidden');
        }
    }
});
