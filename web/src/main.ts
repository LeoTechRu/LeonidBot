import { Layout, Table, Form, Notice } from '@ui';

export function initAdminPanel(): void {
  const panel = document.querySelector<HTMLElement>('.admin-panel');
  if (!panel) return;
  panel.querySelectorAll('a').forEach((link) => {
    link.classList.add('btn');
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initAdminPanel();
  console.log(Layout, Table, Form, Notice);
});
