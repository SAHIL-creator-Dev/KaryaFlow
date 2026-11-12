/**
 * KaryaFlow — Dashboard Client Interactions (dashboard.js)
 * Features:
 * - Mobile navigation sidebar drawer toggle & overlay
 * - Create Project modal dialog controller
 * - Instant task search filtering within My Tasks panel
 * - Task status toggle micro-interaction
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

  // 2. Create Project Modal Controller (on Dashboard)
  const createProjectModal = document.getElementById('modalCreateProject');
  const openCreateTriggers = document.querySelectorAll('.open-create-project-modal');

  if (createProjectModal && openCreateTriggers.length > 0) {
    const closeBtns = createProjectModal.querySelectorAll('.modal-close-trigger');

    function openCreateModal(e) {
      e.preventDefault();
      createProjectModal.classList.add('is-visible');
      document.body.style.overflow = 'hidden';
      const firstInput = createProjectModal.querySelector('input[name="name"]');
      firstInput?.focus();
    }

    function closeCreateModal() {
      createProjectModal.classList.remove('is-visible');
      document.body.style.overflow = '';
    }

    openCreateTriggers.forEach(btn => btn.addEventListener('click', openCreateModal));
    closeBtns.forEach(btn => btn.addEventListener('click', closeCreateModal));

    createProjectModal.addEventListener('click', (e) => {
      if (e.target === createProjectModal) {
        closeCreateModal();
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && createProjectModal.classList.contains('is-visible')) {
        closeCreateModal();
      }
    });

    const createProjectForm = createProjectModal.querySelector('form');
    if (createProjectForm) {
      createProjectForm.addEventListener('submit', (e) => {
        const nameInput = createProjectForm.querySelector('input[name="name"]');
        const errorMsg = document.getElementById('newProjectNameError');
        if (nameInput && !nameInput.value.trim()) {
          e.preventDefault();
          nameInput.classList.add('is-invalid');
          errorMsg?.classList.add('is-visible');
          nameInput.focus();
          return;
        }
        nameInput?.classList.remove('is-invalid');
        errorMsg?.classList.remove('is-visible');

        const submitBtn = createProjectForm.querySelector('button[type="submit"]');
        if (submitBtn && !submitBtn.classList.contains('is-submitting')) {
          submitBtn.classList.add('is-submitting');
          const submittingText = submitBtn.getAttribute('data-submitting-text');
          const labelSpan = submitBtn.querySelector('span');
          if (submittingText && labelSpan) {
            labelSpan.textContent = submittingText;
          }
        }
      });
    }
  }

  // 3. Instant Task Search Filter on Dashboard
  const taskSearchInput = document.getElementById('dashboardTaskSearch');
  const taskCards = document.querySelectorAll('#dashboardTasksList .task-item-card[data-task-title]');
  const taskQuickEmpty = document.getElementById('dashboardTaskQuickEmpty');

  if (taskSearchInput && taskCards.length > 0) {
    taskSearchInput.addEventListener('input', (e) => {
      const query = e.target.value.trim().toLowerCase();
      let visibleCount = 0;

      taskCards.forEach(card => {
        const title = card.getAttribute('data-task-title') || '';
        if (!query || title.includes(query)) {
          card.style.display = '';
          visibleCount++;
        } else {
          card.style.display = 'none';
        }
      });

      if (taskQuickEmpty) {
        taskQuickEmpty.style.display = visibleCount === 0 ? 'flex' : 'none';
      }
    });
  }

  // 4. Task Status Checkbox Toggle (Front-facing micro-interaction)
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

  // 5. Initialize Lucide Icons
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});
