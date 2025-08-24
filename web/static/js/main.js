// Example TypeScript entry point with modular structure
export function enableAccessibility() {
    const btn = document.getElementById('accessibility-toggle');
    if (!btn)
        return;
    btn.addEventListener('click', () => {
        document.documentElement.classList.toggle('high-contrast');
    });
}
export function initProfileMenu() {
    const button = document.getElementById('profile-button');
    const dropdown = document.getElementById('profile-dropdown');
    if (!button || !dropdown)
        return;
    button.addEventListener('click', (ev) => {
        ev.stopPropagation();
        dropdown.classList.toggle('hidden');
    });
    document.addEventListener('click', () => {
        dropdown.classList.add('hidden');
    });
}

export function initAdminMenu() {
    const links = document.querySelectorAll('.admin-panel a[data-url]');
    const container = document.getElementById('admin-content');
    if (!links.length || !container)
        return;
    links.forEach((link) => {
        link.addEventListener('click', async (ev) => {
            ev.preventDefault();
            const url = link.getAttribute('data-url');
            if (!url)
                return;
            const resp = await fetch(url);
            if (resp.ok) {
                container.innerHTML = await resp.text();
            }
            else {
                container.innerHTML = '<p>Ошибка загрузки</p>';
            }
        });
    });
}
document.addEventListener('DOMContentLoaded', () => {
    enableAccessibility();
    initProfileMenu();
    initAdminMenu();
});
