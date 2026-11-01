/**
 * KaryaFlow — Tasks Client Interactions (tasks.js)
 * Handles:
 * - Search filtering across user's assigned tasks
 * - Project, Status, and Priority dropdown filter controls
 * - Status ribbon quick filter clicks
 * - Interactive status update toggle via checkboxes & status dropdowns
 * - Empty search results state toggle
 */

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('taskSearchInput');
  const projectFilter = document.getElementById('taskProjectFilter');
  const statusFilter = document.getElementById('taskStatusFilter');
  const priorityFilter = document.getElementById('taskPriorityFilter');
  const taskRows = document.querySelectorAll('.my-task-row[data-task-status]');
  const ribbonCards = document.querySelectorAll('.status-ribbon-card[data-status-filter]');
  const searchEmptyState = document.getElementById('tasksSearchEmptyState');
  const tasksContainer = document.querySelector('.my-tasks-container');

  let currentSearchQuery = '';
  let currentProject = 'all';
  let currentStatus = 'all';
  let currentPriority = 'all';

  function applyTaskFilters() {
    let visibleCount = 0;

    taskRows.forEach(row => {
      const taskStatus = (row.getAttribute('data-task-status') || '').toLowerCase();
      const taskProject = (row.getAttribute('data-task-project') || '').toLowerCase();
      const taskPriority = (row.getAttribute('data-task-priority') || '').toLowerCase();
      const taskTitle = (row.querySelector('.my-task-title')?.textContent || '').toLowerCase();

      const matchesStatus = currentStatus === 'all' || taskStatus === currentStatus;
      const matchesProject = currentProject === 'all' || taskProject === currentProject;
      const matchesPriority = currentPriority === 'all' || taskPriority === currentPriority;
      const matchesSearch = !currentSearchQuery || taskTitle.includes(currentSearchQuery);

      if (matchesStatus && matchesProject && matchesPriority && matchesSearch) {
        row.style.display = '';
        visibleCount++;
      } else {
        row.style.display = 'none';
      }
    });

    // Update empty search state
    if (searchEmptyState) {
      if (visibleCount === 0 && taskRows.length > 0) {
        searchEmptyState.style.display = 'flex';
        if (tasksContainer) tasksContainer.style.display = 'none';
      } else {
        searchEmptyState.style.display = 'none';
        if (tasksContainer) tasksContainer.style.display = '';
      }
    }
  }

  // 1. Search Input
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      currentSearchQuery = e.target.value.trim().toLowerCase();
      applyTaskFilters();
    });
  }

  // 2. Select Filters
  if (projectFilter) {
    projectFilter.addEventListener('change', (e) => {
      currentProject = e.target.value.toLowerCase();
      applyTaskFilters();
    });
  }

  if (statusFilter) {
    statusFilter.addEventListener('change', (e) => {
      currentStatus = e.target.value.toLowerCase();
      // Sync with ribbon cards
      ribbonCards.forEach(c => {
        c.classList.toggle('active', c.getAttribute('data-status-filter') === currentStatus);
      });
      applyTaskFilters();
    });
  }

  if (priorityFilter) {
    priorityFilter.addEventListener('change', (e) => {
      currentPriority = e.target.value.toLowerCase();
      applyTaskFilters();
    });
  }

  // 3. Ribbon Card Clicks
  ribbonCards.forEach(card => {
    card.addEventListener('click', () => {
      const filter = card.getAttribute('data-status-filter') || 'all';
      currentStatus = filter;
      ribbonCards.forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      if (statusFilter) {
        statusFilter.value = filter;
      }
      applyTaskFilters();
    });
  });

  // 4. Quick Checkbox Status Toggle (Member micro-interaction)
  const taskCheckboxes = document.querySelectorAll('.my-task-checkbox');
  taskCheckboxes.forEach(chk => {
    chk.addEventListener('click', () => {
      const row = chk.closest('.my-task-row');
      if (!row) return;

      const dropdown = row.querySelector('.status-dropdown-member');
      const isCompleted = row.classList.contains('is-completed');

      if (isCompleted) {
        row.classList.remove('is-completed');
        row.setAttribute('data-task-status', 'in_progress');
        if (dropdown) {
          dropdown.value = 'in_progress';
          dropdown.className = 'status-dropdown-member in_progress';
        }
      } else {
        row.classList.add('is-completed');
        row.setAttribute('data-task-status', 'completed');
        if (dropdown) {
          dropdown.value = 'completed';
          dropdown.className = 'status-dropdown-member completed';
        }
      }
    });
  });

  // 5. Member Status Dropdown Change
  const statusDropdowns = document.querySelectorAll('.status-dropdown-member');
  statusDropdowns.forEach(dd => {
    dd.addEventListener('change', (e) => {
      const val = e.target.value;
      const row = dd.closest('.my-task-row');
      if (!row) return;

      row.setAttribute('data-task-status', val);
      dd.className = `status-dropdown-member ${val}`;

      if (val === 'completed') {
        row.classList.add('is-completed');
      } else {
        row.classList.remove('is-completed');
      }
    });
  });

  // 6. Reset Filters
  const resetBtn = document.getElementById('btnResetTasksSearch');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      if (projectFilter) projectFilter.value = 'all';
      if (statusFilter) statusFilter.value = 'all';
      if (priorityFilter) priorityFilter.value = 'all';
      currentSearchQuery = '';
      currentProject = 'all';
      currentStatus = 'all';
      currentPriority = 'all';
      ribbonCards.forEach(c => c.classList.toggle('active', c.getAttribute('data-status-filter') === 'all'));
      applyTaskFilters();
    });
  }

  // Initialize Lucide icons
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
});
