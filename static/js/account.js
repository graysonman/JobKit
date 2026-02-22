/**
 * JobKit - Account Settings Page JavaScript
 */

// Resend verification email
async function resendVerification() {
    const btn = document.getElementById('resend-btn');
    btn.disabled = true;
    btn.textContent = 'Sending...';
    try {
        const res = await fetch('/auth/send-verification', { method: 'POST' });
        if (res.ok) {
            btn.textContent = 'Sent!';
            btn.classList.replace('bg-yellow-600', 'bg-green-600');
            btn.classList.replace('hover:bg-yellow-700', 'hover:bg-green-700');
        } else {
            const err = await res.json();
            alert(err.detail || 'Failed to send verification email.');
            btn.textContent = 'Resend';
            btn.disabled = false;
        }
    } catch {
        btn.textContent = 'Resend';
        btn.disabled = false;
    }
}

// Profile update
async function handleProfileUpdate(e) {
    e.preventDefault();
    const btn = document.getElementById('profile-btn');
    const msgEl = document.getElementById('profile-msg');
    btn.disabled = true;

    try {
        const res = await fetch('/auth/me', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: document.getElementById('profile-name').value,
                email: document.getElementById('profile-email').value,
            }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Update failed' }));
            throw new Error(err.detail);
        }

        const user = await res.json();
        localStorage.setItem('jobkit_user_name', user.name || '');
        localStorage.setItem('jobkit_user_email', user.email || '');
        const nameEl = document.getElementById('user-display-name');
        if (nameEl) nameEl.textContent = user.name || '';

        msgEl.textContent = 'Profile updated successfully.';
        msgEl.className = 'text-sm rounded-lg p-3 bg-green-50 border border-green-200 text-green-700';
        msgEl.classList.remove('hidden');
    } catch (err) {
        msgEl.textContent = err.message;
        msgEl.className = 'text-sm rounded-lg p-3 bg-red-50 border border-red-200 text-red-700';
        msgEl.classList.remove('hidden');
    }
    btn.disabled = false;
}

// Password strength for account page
function checkNewPasswordStrength() {
    const pw = document.getElementById('new-password').value;
    const checks = {
        length: pw.length >= 8,
        upper: /[A-Z]/.test(pw),
        lower: /[a-z]/.test(pw),
        digit: /[0-9]/.test(pw),
    };
    document.getElementById('new-check-length').style.color = checks.length ? '#16a34a' : '#d1d5db';
    document.getElementById('new-check-upper').style.color = checks.upper ? '#16a34a' : '#d1d5db';
    document.getElementById('new-check-lower').style.color = checks.lower ? '#16a34a' : '#d1d5db';
    document.getElementById('new-check-digit').style.color = checks.digit ? '#16a34a' : '#d1d5db';

    const passed = Object.values(checks).filter(Boolean).length;
    const bar = document.getElementById('new-strength-bar');
    bar.style.width = (passed / 4 * 100) + '%';
    const colors = ['bg-red-400', 'bg-red-400', 'bg-yellow-400', 'bg-blue-400', 'bg-green-500'];
    bar.className = `h-full rounded-full transition-all duration-300 ${colors[passed]}`;
}

// Password change
async function handlePasswordChange(e) {
    e.preventDefault();
    const btn = document.getElementById('password-btn');
    const msgEl = document.getElementById('password-msg');
    const newPw = document.getElementById('new-password').value;
    const confirmPw = document.getElementById('confirm-new-password').value;

    if (newPw !== confirmPw) {
        msgEl.textContent = 'Passwords do not match.';
        msgEl.className = 'text-sm rounded-lg p-3 bg-red-50 border border-red-200 text-red-700';
        msgEl.classList.remove('hidden');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Changing...';

    try {
        const res = await fetch('/auth/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_password: document.getElementById('current-password').value,
                new_password: newPw,
            }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Password change failed' }));
            throw new Error(err.detail);
        }

        // Password changed — backend revokes all tokens, must re-login
        TokenStore.clear();
        window.location.href = '/login';
    } catch (err) {
        msgEl.textContent = err.message;
        msgEl.className = 'text-sm rounded-lg p-3 bg-red-50 border border-red-200 text-red-700';
        msgEl.classList.remove('hidden');
        btn.disabled = false;
        btn.textContent = 'Change Password';
    }
}

// Delete account modal
function showDeleteModal() {
    document.getElementById('delete-modal').classList.remove('hidden');
    document.getElementById('delete-confirm-input').value = '';
}
function hideDeleteModal() {
    document.getElementById('delete-modal').classList.add('hidden');
}

async function handleDeleteAccount() {
    const input = document.getElementById('delete-confirm-input').value;
    if (input !== 'DELETE') {
        alert('Please type DELETE to confirm.');
        return;
    }

    const passwordInput = document.getElementById('delete-password-input');
    const password = passwordInput ? passwordInput.value : null;
    if (passwordInput && !password) {
        alert('Please enter your password to confirm deletion.');
        return;
    }

    const btn = document.getElementById('delete-btn');
    btn.disabled = true;
    btn.textContent = 'Deleting...';

    try {
        const res = await fetch('/auth/account', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: password || null })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Delete failed' }));
            throw new Error(err.detail);
        }
        TokenStore.clear();
        window.location.href = '/login';
    } catch (err) {
        alert(err.message);
        btn.disabled = false;
        btn.textContent = 'Delete Forever';
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    // Load current user data
    try {
        const res = await fetch('/auth/me');
        if (res.ok) {
            const user = await res.json();
            document.getElementById('profile-name').value = user.name || '';
            document.getElementById('profile-email').value = user.email || '';

            if (user.is_verified === false) {
                document.getElementById('verify-banner').classList.remove('hidden');
            }

            // Hide password field for OAuth-only users
            if (!user.has_password) {
                const field = document.getElementById('delete-password-field');
                if (field) field.remove();
            }
        }
    } catch {}

    // Bind form submits and button clicks
    document.getElementById('resend-btn').addEventListener('click', resendVerification);
    document.getElementById('profile-form').addEventListener('submit', handleProfileUpdate);
    document.getElementById('password-form').addEventListener('submit', handlePasswordChange);
    document.getElementById('new-password').addEventListener('input', checkNewPasswordStrength);
    document.getElementById('delete-account-btn').addEventListener('click', showDeleteModal);
    document.getElementById('delete-modal-backdrop').addEventListener('click', hideDeleteModal);
    document.getElementById('delete-cancel-btn').addEventListener('click', hideDeleteModal);
    document.getElementById('delete-btn').addEventListener('click', handleDeleteAccount);
});
