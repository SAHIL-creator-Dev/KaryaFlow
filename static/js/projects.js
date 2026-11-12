/**
 * KaryaFlow — Projects Client Interactions (projects.js)
 * Handles:
 * - Search filtering across project cards
 * - Role filter tabs (All, Leader, Member)
 * - Status filter dropdown
 * - Modal controls (Create Project, Add Task, Manage Members)
 * - Empty state toggle when search yields no results
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Projects Filter & Search (My Projects Page)
  const searchInput = document.getElementById('projectSearchInput');
  const roleTabs = document.querySelectorAll('.filter-tab-btn[data-role-filter]');
  const statusFilter = document.getElementById('projectStatusFilter');
  const projectCards = document.querySelectorAll('.project-card[data-project-role]');
  const searchEmptyState = document.getElementById('projectSearchEmptyState');
  const projectsGrid = document.querySelector('.projects-cards-grid');

  let currentRoleFilter = 'all';
  let currentStatusFilter = 'all';
  let currentSearchQuery = '';

  function applyProjectFilters() {
    let visibleCount = 0;

    projectCards.forEach(card => {
      const cardRole = (card.getAttribute('data-project-role') || '').toLowerCase();
      const cardStatus = (card.getAttribute('data-project-status') || '').toLowerCase();
      const cardTitle = (card.querySelector('.project-name')?.textContent || '').toLowerCase();
      const cardDesc = (card.querySelector('.project-description')?.textContent || '').toLowerCase();

      const matchesRole = currentRoleFilter === 'all' || cardRole === currentRoleFilter;
      const matchesStatus = currentStatusFilter === 'all' || cardStatus.includes(currentStatusFilter);
      const matchesSearch = !currentSearchQuery || 
        cardTitle.includes(currentSearchQuery) || 
        cardDesc.includes(currentSearchQuery);

      if (matchesRole && matchesStatus && matchesSearch) {
        card.style.display = '';
        visibleCount++;
      } else {
        card.style.display = 'none';
      }
    });

    if (searchEmptyState) {
      if (visibleCount === 0 && (projectCards.length > 0)) {
        searchEmptyState.style.display = 'flex';
        if (projectsGrid) projectsGrid.style.display = 'none';
      } else {
        searchEmptyState.style.display = 'none';
        if (projectsGrid) projectsGrid.style.display = '';
      }
    }
  }

  // Search Input Listener
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      currentSearchQuery = e.target.value.trim().toLowerCase();
      applyProjectFilters();
    });
  }

  // Role Tab Listeners
  if (roleTabs.length > 0) {
    roleTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        roleTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentRoleFilter = tab.getAttribute('data-role-filter') || 'all';
        applyProjectFilters();
      });
    });
  }

  // Status Select Listener
  if (statusFilter) {
    statusFilter.addEventListener('change', (e) => {
      currentStatusFilter = e.target.value.toLowerCase();
      applyProjectFilters();
    });
  }

  // Reset Search Button
  const resetSearchBtn = document.getElementById('btnResetProjectSearch');
  if (resetSearchBtn) {
    resetSearchBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      currentSearchQuery = '';
      currentRoleFilter = 'all';
      currentStatusFilter = 'all';
      roleTabs.forEach(t => t.classList.toggle('active', t.getAttribute('data-role-filter') === 'all'));
      if (statusFilter) statusFilter.value = 'all';
      applyProjectFilters();
    });
  }

  // 2. Priority Selector Pills Sync Helper
  function syncPriorityPillsForSelect(selectEl) {
    if (!selectEl || !selectEl.id) return;
    const grid = document.querySelector(`.priority-selector-grid[data-target-select="${selectEl.id}"]`);
    if (!grid) return;
    const pills = grid.querySelectorAll('.priority-option-pill');
    pills.forEach(pill => {
      const val = pill.getAttribute('data-priority-value');
      pill.classList.toggle('is-active', val === selectEl.value);
    });
  }

  document.querySelectorAll('.priority-selector-grid[data-target-select]').forEach(grid => {
    const targetId = grid.getAttribute('data-target-select');
    const selectEl = document.getElementById(targetId);
    if (!selectEl) return;

    grid.querySelectorAll('.priority-option-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        const val = pill.getAttribute('data-priority-value');
        if (val) {
          selectEl.value = val;
          syncPriorityPillsForSelect(selectEl);
        }
      });
    });

    selectEl.addEventListener('change', () => {
      syncPriorityPillsForSelect(selectEl);
    });
  });

  // 3. Task Date Range Validation & Min Constraint Sync
  document.querySelectorAll('.kf-task-form').forEach(form => {
    const startInput = form.querySelector('input[name="start_date"]');
    const deadlineInput = form.querySelector('input[name="deadline"]');
    const errorMsg = form.querySelector('.kf-date-error-msg');

    function validateDates() {
      if (!startInput || !deadlineInput) return true;
      if (startInput.value) {
        deadlineInput.min = startInput.value;
      } else {
        deadlineInput.removeAttribute('min');
      }
      const isInvalid = Boolean(startInput.value && deadlineInput.value && deadlineInput.value < startInput.value);
      deadlineInput.classList.toggle('is-invalid', isInvalid);
      if (errorMsg) {
        errorMsg.classList.toggle('is-visible', isInvalid);
      }
      return !isInvalid;
    }

    startInput?.addEventListener('change', validateDates);
    deadlineInput?.addEventListener('change', validateDates);

    form.addEventListener('submit', (e) => {
      if (!validateDates()) {
        e.preventDefault();
        deadlineInput?.focus();
      }
    });
  });

  // 4. Form Submission Loading State
  document.querySelectorAll('.kf-validated-form').forEach(form => {
    form.addEventListener('submit', (e) => {
      if (e.defaultPrevented || !form.checkValidity()) return;
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn && !submitBtn.classList.contains('is-submitting')) {
        submitBtn.classList.add('is-submitting');
        const submittingText = submitBtn.getAttribute('data-submitting-text');
        const labelSpan = submitBtn.querySelector('span');
        if (submittingText && labelSpan) {
          labelSpan.textContent = submittingText;
        }
      }
    });
  });

  // 5. Modal Controller Helper
  function setupModal(openTriggerSelector, modalId, closeTriggerSelector) {
    const triggers = document.querySelectorAll(openTriggerSelector);
    const modal = document.getElementById(modalId);
    if (!modal) return;
    const closeBtns = modal.querySelectorAll(closeTriggerSelector || '.modal-close-trigger');

    function openModal() {
      modal.classList.add('is-visible');
      document.body.style.overflow = 'hidden';
      const firstInput = modal.querySelector('input:not([type="hidden"]), select, textarea');
      firstInput?.focus();
    }

    function closeModal() {
      modal.classList.remove('is-visible');
      document.body.style.overflow = '';
    }

    triggers.forEach(t => t.addEventListener('click', (e) => {
      e.preventDefault();
      const projectId = t.getAttribute('data-project-id');
      const projectCard = t.closest('.project-card');
      if (modalId === 'modalManageProject' && projectCard) {
        const projectName = modal.querySelector('[name="name"]');
        const projectDescription = modal.querySelector('[name="description"]');
        const projectStatus = modal.querySelector('[name="status"]');
        const projectIdInput = modal.querySelector('[name="project_id"]');
        if (projectName) projectName.value = projectCard.getAttribute('data-project-name') || '';
        if (projectDescription) projectDescription.value = projectCard.getAttribute('data-project-description') || '';
        if (projectStatus) projectStatus.value = projectCard.getAttribute('data-project-status') || '';
        if (projectIdInput) projectIdInput.value = projectId || projectCard.getAttribute('data-project-id') || '';
      }
      if (modalId === 'modalManageMembers' && projectId) {
        const projectIdInput = modal.querySelector('[name="project_id"]');
        if (projectIdInput) projectIdInput.value = projectId;
      }
      if (modalId === 'modalEditTask') {
        const taskId = t.getAttribute('data-task-id');
        const taskTitle = t.getAttribute('data-task-title');
        const taskDesc = t.getAttribute('data-task-desc');
        const taskPriority = t.getAttribute('data-task-priority');
        const taskStatus = t.getAttribute('data-task-status');
        const taskStartDate = t.getAttribute('data-task-start-date');
        const taskDeadline = t.getAttribute('data-task-deadline');
        const taskAssignedTo = t.getAttribute('data-task-assigned-to');

        const idInput = modal.querySelector('#editTaskId');
        const titleInput = modal.querySelector('#editTaskTitleInput');
        const descInput = modal.querySelector('#editTaskDescInput');
        const priorityInput = modal.querySelector('#editTaskPrioritySelect');
        const statusInput = modal.querySelector('#editTaskStatusSelect');
        const startInput = modal.querySelector('#editTaskStartDateInput');
        const deadlineInput = modal.querySelector('#editTaskDeadlineInput');
        const assigneeInput = modal.querySelector('#editTaskAssigneeSelect');

        if (idInput) idInput.value = taskId || '';
        if (titleInput) titleInput.value = taskTitle || '';
        if (descInput) descInput.value = taskDesc || '';
        if (priorityInput && taskPriority) {
          priorityInput.value = taskPriority;
          syncPriorityPillsForSelect(priorityInput);
        }
        if (statusInput && taskStatus) statusInput.value = taskStatus;
        if (startInput) startInput.value = taskStartDate || '';
        if (deadlineInput) deadlineInput.value = taskDeadline || '';
        if (assigneeInput && taskAssignedTo) assigneeInput.value = taskAssignedTo;
      }
      openModal();
    }));

    closeBtns.forEach(btn => btn.addEventListener('click', closeModal));

    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modal.classList.contains('is-visible')) {
        closeModal();
      }
    });
  }

  // Connect Modals
  setupModal('.open-create-project-modal', 'modalCreateProject');
  setupModal('.open-create-task-modal', 'modalCreateTask');
  setupModal('.open-edit-task-modal', 'modalEditTask');
  setupModal('.open-manage-members-modal', 'modalManageMembers');
  setupModal('.open-manage-project-modal', 'modalManageProject');

  const taskModal = document.getElementById('modalCreateTask');
  if (taskModal && window.location.hash === '#create-task') {
    taskModal.classList.add('is-visible');
    document.body.style.overflow = 'hidden';
    taskModal.querySelector('input, select, textarea')?.focus();
  }

  // 6. Inline Task Status Selector Color Sync
  document.querySelectorAll('.project-task-status-select').forEach(selectEl => {
    selectEl.addEventListener('change', () => {
      selectEl.classList.remove(
        'status-pending',
        'status-in_progress',
        'status-in_review',
        'status-completed'
      );
      if (selectEl.value) {
        selectEl.classList.add(`status-${selectEl.value}`);
      }
    });
  });

  // Initialize Lucide icons
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});
