/**
 * JobKit - Reset Password Page JavaScript
 */

let resetToken = null;

function showError(msg) {
    const el = document.getElementById('msg-error');
    el.textContent = msg;
    el.classList.remove('hidden');
    document.getElementById('msg-success').classList.add('hidden');
}

function showSuccess(msg) {
    const el = document.getElementById('msg-success');
    el.textContent = msg;
    el.classList.remove('hidden');
    document.getElementById('msg-error').classList.add('hidden');
}

async function handleForgot(e) {
    e.preventDefault();
    const btn = document.getElementById('forgot-btn');
    const email = document.getElementById('forgot-email').value;

    btn.disabled = true;
    btn.textContent = 'Sending...';

    try {
        await fetch('/auth/forgot-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email }),
        });

        // Always show success (server does too, to prevent enumeration)
        showSuccess('If an account exists with that email, a reset link has been sent. Check your inbox.');
        btn.textContent = 'Link Sent';
    } catch {
        showError('Something went wrong. Please try again.');
        btn.disabled = false;
        btn.textContent = 'Send Reset Link';
    }
}

async function handleReset(e) {
    e.preventDefault();
    const btn = document.getElementById('reset-btn');
    const password = document.getElementById('reset-password').value;
    const confirm = document.getElementById('reset-confirm').value;

    if (password !== confirm) {
        showError('Passwords do not match.');
        return;
    }

    if (password.length < 8) {
        showError('Password must be at least 8 characters.');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Resetting...';

    try {
        const res = await fetch('/auth/reset-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: resetToken, new_password: password }),
        });

        if (res.ok) {
            showSuccess('Password reset successfully! Redirecting to login...');
            setTimeout(() => { window.location.href = '/login'; }, 2000);
        } else {
            const err = await res.json();
            showError(err.detail || 'Reset failed. The link may have expired.');
            btn.disabled = false;
            btn.textContent = 'Reset Password';
        }
    } catch {
        showError('Something went wrong. Please try again.');
        btn.disabled = false;
        btn.textContent = 'Reset Password';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    resetToken = params.get('token');

    // Show the correct form based on URL
    if (resetToken) {
        document.getElementById('forgot-form').classList.add('hidden');
        document.getElementById('reset-form').classList.remove('hidden');
        document.getElementById('page-title').textContent = 'Set New Password';
    }

    // Bind form submits
    document.getElementById('forgot-form').addEventListener('submit', handleForgot);
    document.getElementById('reset-form').addEventListener('submit', handleReset);
});
