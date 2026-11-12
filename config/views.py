from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from projects.models import ProjectInvitation, ProjectMembership
from tasks.models import Task


@login_required
def dashboard_view(request):
    today = timezone.localdate()

    # User's pending invitations count
    pending_invitations_count = ProjectInvitation.objects.filter(
        invited_user=request.user,
        status=ProjectInvitation.Status.PENDING,
    ).count()

    # User's assigned tasks
    task_queryset = Task.objects.filter(assigned_to=request.user)

    # Detailed Task Statistics
    task_stats = task_queryset.aggregate(
        total_tasks=Count('id'),
        active_tasks=Count(
            'id',
            filter=Q(status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS, Task.Status.IN_REVIEW]),
        ),
        pending_tasks=Count('id', filter=Q(status=Task.Status.TODO)),
        in_progress_tasks=Count('id', filter=Q(status=Task.Status.IN_PROGRESS)),
        in_review_tasks=Count('id', filter=Q(status=Task.Status.IN_REVIEW)),
        completed_tasks=Count('id', filter=Q(status=Task.Status.COMPLETED)),
        overdue_tasks=Count(
            'id',
            filter=Q(deadline__lt=today) & ~Q(status=Task.Status.COMPLETED),
        ),
    )

    # User's project memberships
    memberships = ProjectMembership.objects.filter(
        user=request.user,
    ).select_related('project').annotate(
        total_tasks=Count('project__tasks', distinct=True),
        completed_tasks=Count(
            'project__tasks',
            filter=Q(project__tasks__status=Task.Status.COMPLETED),
            distinct=True,
        ),
        in_progress_tasks=Count(
            'project__tasks',
            filter=Q(project__tasks__status=Task.Status.IN_PROGRESS),
            distinct=True,
        ),
        in_review_tasks=Count(
            'project__tasks',
            filter=Q(project__tasks__status=Task.Status.IN_REVIEW),
            distinct=True,
        ),
        pending_tasks=Count(
            'project__tasks',
            filter=Q(project__tasks__status=Task.Status.TODO),
            distinct=True,
        ),
        member_count=Count('project__memberships', distinct=True),
    ).order_by('-project__created_at')

    projects = []
    leader_projects = 0
    active_projects = 0
    completed_projects = 0
    user_project_ids = []

    for membership in memberships:
        project = membership.project
        user_project_ids.append(project.pk)
        total_tasks = membership.total_tasks
        completed_tasks = membership.completed_tasks
        is_leader = membership.role == ProjectMembership.Role.LEADER
        leader_projects += int(is_leader)

        if project.status == 'completed':
            completed_projects += 1
        elif project.status in ('in_progress', 'planning'):
            active_projects += 1

        progress = round(completed_tasks * 100 / total_tasks) if total_tasks else 0

        projects.append({
            'id': project.pk,
            'name': project.name,
            'description': project.description,
            'status': project.get_status_display(),
            'status_code': project.status,
            'created_at': project.created_at,
            'progress': progress,
            'completed_tasks': completed_tasks,
            'total_tasks': total_tasks,
            'remaining_tasks': max(0, total_tasks - completed_tasks),
            'member_count': membership.member_count,
            'user_role': membership.role,
            'is_leader': is_leader,
        })

    # Task list filtering (for My Tasks panel on dashboard)
    filtered_tasks = task_queryset.select_related('project')
    project_filter = request.GET.get('project', 'all').strip().lower()
    if project_filter and project_filter != 'all':
        filtered_tasks = filtered_tasks.filter(
            Q(project__name__iexact=project_filter) | Q(project__id__iexact=project_filter)
        )

    status_filter = request.GET.get('status', 'all').strip().lower()
    if status_filter in Task.Status.values:
        filtered_tasks = filtered_tasks.filter(status=status_filter)
    else:
        status_filter = 'all'

    priority_filter = request.GET.get('priority', 'all').strip().lower()
    if priority_filter in Task.Priority.values:
        filtered_tasks = filtered_tasks.filter(priority=priority_filter)
    else:
        priority_filter = 'all'

    tasks_list = list(filtered_tasks)
    for t in tasks_list:
        t.is_overdue = (
            t.deadline is not None
            and t.deadline < today
            and t.status != Task.Status.COMPLETED
        )

    # Authorized Team Overview: Distinct members belonging to user's projects
    team_memberships = (
        ProjectMembership.objects.filter(project_id__in=user_project_ids)
        .exclude(user=request.user)
        .select_related('user', 'project')
        .order_by('user__first_name', 'user__last_name', 'user__username')
    )

    team_members_dict = {}
    for tm in team_memberships:
        u = tm.user
        if u.pk not in team_members_dict:
            name = u.get_full_name() or u.username
            team_members_dict[u.pk] = {
                'id': u.pk,
                'name': name,
                'username': u.username,
                'email': u.email,
                'initials': ''.join(part[0] for part in name.split()[:2]).upper() or u.username[:2].upper(),
                'projects': [],
            }
        team_members_dict[u.pk]['projects'].append({
            'name': tm.project.name,
            'role': tm.get_role_display(),
            'is_leader': tm.role == ProjectMembership.Role.LEADER,
        })

    team_members = list(team_members_dict.values())[:8]  # Compact overview (up to 8 colleagues)

    # Base stats dict matching existing test suite requirements exactly (6 keys)
    base_stats = {
        'total_projects': len(projects),
        'leader_projects': leader_projects,
        'member_projects': len(projects) - leader_projects,
        'active_tasks': task_stats['active_tasks'] or 0,
        'completed_tasks': task_stats['completed_tasks'] or 0,
        'pending_tasks': task_stats['pending_tasks'] or 0,
    }

    # Extended metrics for the enhanced modern dashboard
    detailed_stats = {
        'total_projects': len(projects),
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'leader_projects': leader_projects,
        'member_projects': len(projects) - leader_projects,
        'total_tasks': task_stats['total_tasks'] or 0,
        'active_tasks': task_stats['active_tasks'] or 0,
        'pending_tasks': task_stats['pending_tasks'] or 0,
        'in_progress_tasks': task_stats['in_progress_tasks'] or 0,
        'in_review_tasks': task_stats['in_review_tasks'] or 0,
        'completed_tasks': task_stats['completed_tasks'] or 0,
        'overdue_tasks': task_stats['overdue_tasks'] or 0,
    }

    context = {
        'current_date': today,
        'can_create_project': True,
        'stats': base_stats,
        'detailed_stats': detailed_stats,
        'projects': projects,
        'tasks': tasks_list,
        'team_members': team_members,
        'pending_invitations_count': pending_invitations_count,
        'task_status_choices': Task.Status.choices,
        'task_priority_choices': Task.Priority.choices,
        'project_filter': project_filter,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
    }
    return render(request, 'dashboard/dashboard.html', context)
