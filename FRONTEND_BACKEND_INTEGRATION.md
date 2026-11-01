# KaryaFlow Frontend — Django Backend Integration Contract

This document provides a comprehensive technical contract between the frontend interface of **KaryaFlow** and the upcoming Django backend implementation.

All frontend templates are designed with **dual-mode rendering**:
1. **Production Mode (Live Context):** When views pass real models/querysets, the templates seamlessly render live data, forms, and permission boundaries.
2. **Graceful Empty States:** When lists are empty, informative, well-designed empty states appear with relevant calls to action.
3. **Frontend Preview Mode (`preview_mode=True` or `?preview=true`):** Standalone design review data is isolated inside `{% elif preview_mode %}` blocks and is never exposed in production data rendering.

---

## 1. Registered URL Routes & Names

| Page | URL Pattern | URL Name | View Type | Recommended View Location |
|---|---|---|---|---|
| **Dashboard** | `/dashboard/` | `dashboard` | Function/CBV | `projects.views.dashboard_view` |
| **My Projects** | `/projects/` | `my_projects` | Function/CBV | `projects.views.my_projects_view` |
| **Project Details** | `/projects/<int:pk>/` | `project_detail` | Function/CBV | `projects.views.project_detail_view` |
| **My Tasks** | `/tasks/` | `my_tasks` | Function/CBV | `tasks.views.my_tasks_view` |
| **Profile & Settings**| `/profile/` | `profile` | Function/CBV | `accounts.views.profile_view` |
| **Sign In** | `/login/` | `login` | Function/CBV | `accounts.views.login_view` |
| **Sign Up** | `/register/` | `register` | Function/CBV | `accounts.views.register_view` |

---

## 2. Page Specifications & Context Variables

### Page A: My Projects (`templates/projects/my_projects.html`)
- **Route:** `path('projects/', views.my_projects_view, name='my_projects')`
- **Permissions:** `@login_required`

#### Required Context Variables:
```python
{
    'user': request.user,
    'can_create_project': True,  # Boolean: whether current user has permission to create new projects
    'projects': [
        {
            'id': 1,
            'name': 'KaryaFlow Platform Hardening',
            'description': 'Production stabilization and accessibility compliance.',
            'status': 'In Progress',       # 'In Progress', 'Planning', 'Completed', 'On Hold'
            'progress': 78,                # Integer 0-100
            'completed_tasks': 14,
            'total_tasks': 18,
            'member_count': 5,
            'user_role': 'leader',         # 'leader' or 'member'
            'is_leader': True,             # Boolean: True if user is the project leader
            'created_at': 'Oct 15, 2026',  # Formatted string or datetime object
        },
        ...
    ]
}
```

#### Forms Handled on this Page:
1. **Create Project Form** (`action="create_project"`):
   - `name` (CharField, required)
   - `description` (TextField, optional)
   - `status` (ChoiceField: `Planning`, `In Progress`, `On Hold`)
2. **Update Project Form** (`action="update_project"` - Leader only):
   - `project_id` (IntegerField, required)
   - `name` (CharField, required)
   - `status` (ChoiceField: `Planning`, `In Progress`, `Completed`, `On Hold`)
3. **Invite Member Form** (`action="invite_member"` - Leader only):
   - `identifier` (CharField: email address or username, required)
   - `role` (ChoiceField: `member`, `leader`)

---

### Page B: Project Details (`templates/projects/project_detail.html`)
- **Route:** `path('projects/<int:pk>/', views.project_detail_view, name='project_detail')`
- **Permissions:** `@login_required`, user must be a member or leader of the project.

#### Required Context Variables:
```python
{
    'user': request.user,
    'project': {
        'id': 1,
        'name': 'KaryaFlow Platform Hardening',
        'description': 'Production stabilization and accessibility compliance.',
        'status': 'In Progress',
        'progress': 78,
        'created_at': 'Oct 15, 2026',
    },
    'is_leader': True,       # Boolean: True if request.user is Leader in this specific project
    'user_role': 'leader',   # 'leader' or 'member'
    'stats': {
        'total_tasks': 18,
        'completed_tasks': 14,
        'in_progress_tasks': 3,
        'pending_tasks': 1,
    },
    'tasks': [
        {
            'id': 101,
            'title': 'Audit accessibility & responsive breakpoints',
            'description': 'Ensure contrast compliance for terracotta buttons.',
            'priority': 'high',              # 'high', 'medium', 'low'
            'status': 'in_progress',         # 'pending', 'in_progress', 'completed'
            'deadline': 'Tomorrow, 5:00 PM', # String or datetime
            'is_overdue': False,             # Boolean
            'assignee_name': 'Sahil Verma',
            'assignee_initials': 'SV',
            'assigned_to_user': True,        # Boolean: True if assigned to request.user
        },
        ...
    ],
    'members': [
        {
            'id': 1,
            'name': 'Sahil Verma',
            'email': 'sahil@karyaflow.io',
            'initials': 'SV',
            'role': 'leader',                # 'leader' or 'member'
            'is_leader': True,
            'joined_at': 'Oct 15, 2026',
        },
        ...
    ]
}
```

#### Role-Based UI Action Boundaries:
- **Leader:**
  - Can view and click: `Create Task`, `Edit Task`, `Delete Task`, `Project Settings`, `Invite Member`, `Remove Member`.
- **Member:**
  - Can view project overview, metrics, tasks list, and members list.
  - Can update task status **only** for tasks assigned to them (`assigned_to_user=True`).
  - Cannot edit task titles, descriptions, priorities, deadlines, or assignees.
  - Cannot see or access member invitation/removal or project settings.

#### Forms Handled on this Page:
1. **Create Task Form** (`action="create_task"` - Leader only):
   - `title` (CharField, required)
   - `description` (TextField, optional)
   - `priority` (ChoiceField: `low`, `medium`, `high`)
   - `deadline` (DateField, optional)
   - `assignee_id` (ForeignKey User ID, optional)
   - `status` (ChoiceField: `pending`, `in_progress`, `completed`)
2. **Invite Member Form** (`action="invite_member"` - Leader only):
   - `identifier` (Email or username, required)
   - `role` (ChoiceField: `member`, `leader`)
3. **Project Settings Form** (`action="update_project"` - Leader only):
   - `name` (CharField, required)
   - `description` (TextField, optional)
   - `status` (ChoiceField: `Planning`, `In Progress`, `Completed`, `On Hold`)

---

### Page C: My Tasks (`templates/tasks/my_tasks.html`)
- **Route:** `path('tasks/', views.my_tasks_view, name='my_tasks')`
- **Permissions:** `@login_required`

#### Required Context Variables:
```python
{
    'user': request.user,
    'stats': {
        'total_assigned': 4,
        'pending_count': 1,
        'in_progress_count': 2,
        'completed_count': 1,
    },
    'project_choices': [
        {'id': 1, 'name': 'KaryaFlow Platform Hardening'},
        {'id': 2, 'name': 'Marketing & Brand Guidelines'},
    ],
    'tasks': [
        {
            'id': 101,
            'title': 'Audit accessibility & responsive breakpoints',
            'project_name': 'KaryaFlow Platform Hardening',
            'priority': 'high',              # 'high', 'medium', 'low'
            'deadline': 'Today, 5:00 PM',
            'assigned_date': 'Oct 26, 2026',
            'is_overdue': True,              # Highlights red overdue pill
            'status': 'in_progress',         # 'pending', 'in_progress', 'completed'
        },
        ...
    ]
}
```

#### Permitted Actions:
- Members can update the status of their assigned tasks via the inline dropdown or quick checkbox.
- No editing of task titles, deadlines, priorities, or projects is presented to members.

#### Forms Handled on this Page:
- **Update Task Status Form** (`action="update_task_status"`):
  - `task_id` (IntegerField, required)
  - `status` (ChoiceField: `pending`, `in_progress`, `completed`)

---

### Page D: Profile & Settings (`templates/accounts/profile.html`)
- **Route:** `path('profile/', views.profile_view, name='profile')`
- **Permissions:** `@login_required`

#### Required Context Variables:
```python
{
    'user': request.user,  # Django User model instance (or custom user model)
    'messages': messages.get_messages(request),  # Django messages framework
}
```

#### Forms Handled on this Page:
1. **Update Profile Form** (`action="update_profile"`):
   - `first_name` (CharField, required)
   - `last_name` (CharField, optional)
   - `email` (EmailField, required)
   - `profile_image` (ImageField, optional, handled via file upload)
2. **Change Password Form** (`action="change_password"`):
   - `old_password` (CharField/PasswordInput, required)
   - `new_password1` (CharField/PasswordInput, required)
   - `new_password2` (CharField/PasswordInput, required)
   *(Backend should use `PasswordChangeForm` or `user.check_password` / `user.set_password` with `update_session_auth_hash`)*
