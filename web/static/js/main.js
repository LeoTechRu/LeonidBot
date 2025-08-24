// Example TypeScript entry point with modular structure
export function enableAccessibility() {
    const btn = document.getElementById('accessibility-toggle');
    if (!btn)
        return;
    btn.addEventListener('click', () => {
        document.documentElement.classList.toggle('high-contrast');
    });
}

export function setupProfileMenu() {
    const button = document.getElementById('profile-button');
    const menu = document.querySelector('.profile-menu');
    if (!button || !menu)
        return;
    button.addEventListener('click', () => {
        menu.classList.toggle('open');
    });
    document.addEventListener('click', (e) => {
        if (!menu.contains(e.target)) {
            menu.classList.remove('open');
        }
    });
}
document.addEventListener('DOMContentLoaded', () => {
    enableAccessibility();
    setupProfileMenu();
});
