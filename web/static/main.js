import { Layout, Table, Form, Notice } from './ui/index.js';
export function initAdminPanel() {
    const panel = document.querySelector('.admin-panel');
    if (!panel)
        return;
    panel.querySelectorAll('a').forEach((link) => {
        link.classList.add('btn');
    });
}
document.addEventListener('DOMContentLoaded', () => {
    initAdminPanel();
    console.log(Layout, Table, Form, Notice);
});
