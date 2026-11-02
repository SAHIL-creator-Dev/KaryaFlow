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
    for membership in memberships:
        project = membership.project
        total_tasks = membership.total_tasks
        completed_tasks = membership.completed_tasks
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
            'is_leader': membership.role == ProjectMembership.Role.LEADER,
        })

    context = {
        'current_date': timezone.localdate(),
        'stats': {
            'total_projects': len(projects),
            **task_stats,
        },
        'projects': projects,
        'tasks': task_queryset.select_related('project'),
    }
    return render(request, 'dashboard/dashboard.html', context)
