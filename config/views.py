from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from projects.models import ProjectMembership
from tasks.models import Task


@login_required
def dashboard_view(request):
    task_queryset = Task.objects.filter(assigned_to=request.user)
    task_stats = task_queryset.aggregate(
        active_tasks=Count(
            'id',
            filter=Q(status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS]),
        ),
        completed_tasks=Count('id', filter=Q(status=Task.Status.COMPLETED)),
        pending_tasks=Count('id', filter=Q(status=Task.Status.TODO)),
    )

    memberships = ProjectMembership.objects.filter(
        user=request.user,
    ).select_related('project').annotate(
        total_tasks=Count('project__tasks', distinct=True),
        completed_tasks=Count(
            'project__tasks',
            filter=Q(project__tasks__status=Task.Status.COMPLETED),
            distinct=True,
        ),
        member_count=Count('project__memberships', distinct=True),
    )
    projects = []
    leader_projects = 0
    for membership in memberships:
        project = membership.project
        total_tasks = membership.total_tasks
        completed_tasks = membership.completed_tasks
        is_leader = membership.role == ProjectMembership.Role.LEADER
        leader_projects += int(is_leader)
        projects.append({
            'id': project.pk,
            'name': project.name,
            'description': project.description,
            'status': project.get_status_display(),
            'progress': round(completed_tasks * 100 / total_tasks) if total_tasks else 0,
            'completed_tasks': completed_tasks,
            'total_tasks': total_tasks,
            'member_count': membership.member_count,
            'user_role': membership.role,
            'is_leader': is_leader,
        })

    context = {
        'current_date': timezone.localdate(),
        'can_create_project': True,
        'stats': {
            'total_projects': len(projects),
            'leader_projects': leader_projects,
            'member_projects': len(projects) - leader_projects,
            **task_stats,
        },
        'projects': projects,
        'tasks': task_queryset.select_related('project'),
        'task_status_choices': Task.Status.choices,
    }
    return render(request, 'dashboard/dashboard.html', context)
