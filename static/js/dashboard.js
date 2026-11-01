/**
 * KaryaFlow — Dashboard Client Interactions (dashboard.js)
 * Features:
 * - Mobile navigation sidebar drawer toggle & overlay
 * - Task status toggle interaction
 * - Notifications menu toggle
 * - Lucide icons initialization
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Mobile Sidebar Toggle
  const sidebar = document.getElementById('dashboardSidebar');
  const sidebarOverlay = document.getElementById('sidebarOverlay');
  const mobileToggleBtn = document.getElementById('topbarMobileToggle');
  const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');

  function openSidebar() {
    sidebar?.classList.add('mobile-open');
    sidebarOverlay?.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar?.classList.remove('mobile-open');
    sidebarOverlay?.classList.remove('active');
    document.body.style.overflow = '';
  }

  mobileToggleBtn?.addEventListener('click', openSidebar);
  sidebarCloseBtn?.addEventListener('click', closeSidebar);
  sidebarOverlay?.addEventListener('click', closeSidebar);

  // 2. Task Status Checkbox Toggle (Front-facing micro-interaction)
  const taskStatusButtons = document.querySelectorAll('.task-status-btn');
  taskStatusButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const taskCard = btn.closest('.task-item-card');
      if (!taskCard) return;

      const isCompleted = taskCard.classList.contains('is-completed');
      if (isCompleted) {
        taskCard.classList.remove('is-completed');
        const badge = taskCard.querySelector('.status-badge-tag');
        if (badge) {
          badge.textContent = 'In Progress';
          badge.className = 'status-badge-tag in-progress';
        }
      } else {
        taskCard.classList.add('is-completed');
        const badge = taskCard.querySelector('.status-badge-tag');
        if (badge) {
          badge.textContent = 'Completed';
          badge.className = 'status-badge-tag completed';
        }
      }

      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    });
  });

  // 3. Notification Button Micro-interaction
  const bellBtn = document.querySelector('.topbar-btn-bell');
  bellBtn?.addEventListener('click', () => {
    const badge = bellBtn.querySelector('.bell-badge');
    if (badge) {
      badge.style.display = 'none';
    }
  });

  // 4. Initialize Lucide Icons
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});
