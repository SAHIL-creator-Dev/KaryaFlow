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

  // 2. Modal Controller Helper
  function setupModal(openTriggerSelector, modalId, closeTriggerSelector) {
    const triggers = document.querySelectorAll(openTriggerSelector);
    const modal = document.getElementById(modalId);
    if (!modal) return;
    const closeBtn = modal.querySelector(closeTriggerSelector || '.modal-close-trigger');

    function openModal() {
      modal.classList.add('is-visible');
      document.body.style.overflow = 'hidden';
      const firstInput = modal.querySelector('input, select, textarea');
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
      openModal();
    }));

    closeBtn?.addEventListener('click', closeModal);

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
  setupModal('.open-manage-members-modal', 'modalManageMembers');
  setupModal('.open-manage-project-modal', 'modalManageProject');

  const taskModal = document.getElementById('modalCreateTask');
  if (taskModal && window.location.hash === '#create-task') {
    taskModal.classList.add('is-visible');
    document.body.style.overflow = 'hidden';
    taskModal.querySelector('input, select, textarea')?.focus();
  }

  // Initialize Lucide icons
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});
