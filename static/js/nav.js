/**
 * JobKit - Navigation JavaScript
 * Handles user menu, mobile menu, and logout button bindings.
 */

// --- User menu toggle (multi-user mode) ---
(function() {
    const menuBtn = document.getElementById('user-menu-btn');
    const dropdown = document.getElementById('user-dropdown');
    if (menuBtn && dropdown) {
        menuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('hidden');
        });
        document.addEventListener('click', () => dropdown.classList.add('hidden'));
    }

    // Show user menu or keyboard hint based on auth mode
    document.addEventListener('DOMContentLoaded', async () => {
        const status = await Auth.getStatus();
        if (status.single_user_mode) {
            const hint = document.getElementById('single-user-hint');
            if (hint) hint.classList.remove('hidden');
        } else {
            const userMenu = document.getElementById('user-menu-container');
            if (userMenu) userMenu.classList.remove('hidden');
            userMenu.classList.add('flex');
            const mobileSignout = document.getElementById('mobile-signout');
            if (mobileSignout) mobileSignout.classList.remove('hidden');
        }
    });
})();

// Mobile menu toggle
const mobileMenuBtn = document.getElementById('mobile-menu-btn');
const mobileMenuClose = document.getElementById('mobile-menu-close');
const mobileMenu = document.getElementById('mobile-menu');
const mobileMenuBackdrop = document.getElementById('mobile-menu-backdrop');

function openMobileMenu() {
    mobileMenu.classList.add('open');
    mobileMenuBackdrop.classList.add('open');
    document.body.style.overflow = 'hidden';
}

function closeMobileMenu() {
    mobileMenu.classList.remove('open');
    mobileMenuBackdrop.classList.remove('open');
    document.body.style.overflow = '';
}

mobileMenuBtn.addEventListener('click', openMobileMenu);
mobileMenuClose.addEventListener('click', closeMobileMenu);
mobileMenuBackdrop.addEventListener('click', closeMobileMenu);

// Close on Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && mobileMenu.classList.contains('open')) {
        closeMobileMenu();
    }
});

// Highlight active mobile nav link
document.addEventListener('DOMContentLoaded', function() {
    const currentPath = window.location.pathname;
    const mobileNavLinks = document.querySelectorAll('.mobile-nav-link');

    mobileNavLinks.forEach(link => {
        const linkPath = link.getAttribute('href');
        if (linkPath === currentPath || (currentPath === '/' && linkPath === '/')) {
            link.classList.add('bg-blue-50', 'text-blue-600', 'font-medium');
            link.classList.remove('text-gray-700');
        }
    });
});

// Logout button bindings
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('logout-btn-desktop')?.addEventListener('click', () => Auth.logout());
    document.getElementById('logout-btn-mobile')?.addEventListener('click', () => Auth.logout());
});
