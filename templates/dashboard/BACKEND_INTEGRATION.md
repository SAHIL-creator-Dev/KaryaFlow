# KaryaFlow Dashboard — Backend Integration Contract

This document outlines the context variables and contract expected by [`templates/dashboard/dashboard.html`](file:///e:/PROJECTS%20%28UTU%29/MINI%20PROJECT%205TH%20SEM/PROJECT/KaryaFlow/templates/dashboard/dashboard.html).

The template is **100% production-ready**: when real backend context is passed, it renders live models. If any section is empty, it displays graceful empty states. Additionally, for design review and standalone frontend validation without a database, a dedicated preview toggle (`?preview=true`) is supported.

---

## 1. Required View & Route
- **URL Name:** `dashboard` (e.g. `path('dashboard/', views.dashboard_view, name='dashboard')`)
- **Login Required:** `@login_required`

---

## 2. Context Variables Specification

### A. User Profile & Global Permissions
```python
{
    'user': request.user,  # Django User instance (first_name, username, email, etc.)
    'can_create_project': True,  # Boolean: True if user has permission to create new projects
    'current_date': "Friday, Oct 30, 2026",  # Optional string or datetime object (defaults to current date)
}
```

### B. Summary Statistics
```python
{
    'stats': {
        'total_projects': 4,       # Integer: count of projects user is a member/leader of
        'active_tasks': 8,         # Integer: count of pending/in-progress tasks assigned to user
        'completed_tasks': 14,     # Integer: count of completed tasks assigned to user
        'pending_tasks': 3,        # Integer: count of tasks yet to be started
    }
}
```

### C. My Projects (`projects`)
A list of project objects or dictionaries. **Critical:** Permissions are evaluated per-project, because a user can be a `Leader` in one project and a `Member` in another.

```python
{
    'projects': [
        {
            'id': 1,
            'name': 'KaryaFlow Platform Hardening',
            'description': 'Production stabilization, authentication workflows, and accessibility audit.',
            'status': 'In Progress',         # 'In Progress', 'Completed', 'Planning', 'On Hold'
            'progress': 78,                  # Integer 0-100
            'completed_tasks': 14,
            'total_tasks': 18,
            'member_count': 5,
            'user_role': 'leader',           # 'leader' or 'member' (case-insensitive)
            'is_leader': True,               # Convenience boolean (True if current user is project lead)
            'url': '/projects/1/',           # Optional project detail URL
        },
        {
            'id': 2,
            'name': 'Marketing & Brand Guidelines',
            'description': 'Design visual assets, illustrations, and landing page typography specs.',
            'status': 'In Progress',
            'progress': 45,
            'completed_tasks': 5,
            'total_tasks': 11,
            'member_count': 4,
            'user_role': 'member',           # Ordinary member role
            'is_leader': False,
            'url': '/projects/2/',
        }
    ]
}
```

#### Project Actions Triggered by Role:
- When `project.is_leader` (or `project.user_role == 'leader'`):
  - Displays: **Leader** badge (terracotta warm pill)
  - Actions: **Manage Project**, **Manage Members**, **Create Task**
- When `not project.is_leader` (or `project.user_role == 'member'`):
  - Displays: **Member** badge (sand/slate neutral pill)
  - Actions: **View Project** (no administrative or task creation controls)

---

### D. My Tasks (`tasks`)
A list of tasks assigned to `request.user`.

```python
{
    'tasks': [
        {
            'id': 101,
            'title': 'Audit accessibility & responsive breakpoints',
            'project_name': 'KaryaFlow Platform Hardening',
            'project_id': 1,
            'priority': 'high',             # 'high', 'medium', 'low'
            'deadline': 'Tomorrow, 5:00 PM', # String or datetime
            'status': 'in_progress',        # 'pending', 'in_progress', 'completed'
            'can_update_status': True,      # Boolean: user can toggle status
        },
        {
            'id': 102,
            'title': 'Export brand logo variants in SVG format',
            'project_name': 'Marketing & Brand Guidelines',
            'project_id': 2,
            'priority': 'medium',
            'deadline': 'Nov 04',
            'status': 'pending',
            'can_update_status': True,
        }
    ]
}
```

---

### E. Recent Activity (`activities`)
```python
{
    'activities': [
        {
            'icon': 'check-circle-2',        # Lucide icon name
            'title': 'Task completed',
            'description': 'Aanya R. completed "Design role permission matrix"',
            'project_name': 'KaryaFlow Platform Hardening',
            'timestamp': '25 minutes ago',
        },
        {
            'icon': 'folder-plus',
            'title': 'New project created',
            'description': 'You created "Sprint 05: API Integration"',
            'project_name': 'Sprint 05: API Integration',
            'timestamp': '2 hours ago',
        }
    ]
}
```

---

### F. Unread Notifications Count
```python
{
    'unread_notifications_count': 2
}
```

---

## 3. Empty States Handled Gracefully
If `projects` is empty (`{% if not projects %}`), an empty state appears encouraging the user to create or join a project.
If `tasks` is empty (`{% if not tasks %}`), an empty state confirms all tasks are up to date.
If `activities` is empty, a clean "No recent activity" placeholder is shown.
