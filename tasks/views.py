from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods

from projects.models import ProjectMembership

from .models import Task


@login_required
@require_http_methods(['GET'])
def my_tasks_view(request):
    tasks = Task.objects.filter(
        assigned_to=request.user,
    ).select_related('project')
    stats = tasks.aggregate(
        total_assigned=Count('id'),
        pending_count=Count('id', filter=Q(status=Task.Status.TODO)),
        in_progress_count=Count('id', filter=Q(status=Task.Status.IN_PROGRESS)),
        completed_count=Count('id', filter=Q(status=Task.Status.COMPLETED)),
    )
    project_choices = (
        ProjectMembership.objects.filter(user=request.user)
        .select_related('project')
        .values('project__id', 'project__name')
        .order_by('project__name')
    )
    return render(request, 'tasks/my_tasks.html', {
        'tasks': tasks,
        'stats': stats,
        'project_choices': [
            {'id': project['project__id'], 'name': project['project__name']}
            for project in project_choices
        ],
        'current_date': timezone.localdate(),
    })


def _task_status_redirect(request, task):
    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect('project_detail', pk=task.project_id)


@login_required
@require_POST
def update_task_status(request, pk):
    task = get_object_or_404(
        Task.objects.select_related('project'),
        pk=pk,
    )
    membership = ProjectMembership.objects.filter(
        project_id=task.project_id,
        user=request.user,
    ).first()
    if membership is None:
        raise Http404

    is_project_leader = membership.role == ProjectMembership.Role.LEADER
    if task.assigned_to_id != request.user.pk and not is_project_leader:
        raise Http404

    new_status = request.POST.get('status')
    if new_status not in Task.Status.values:
        messages.error(request, 'Choose a valid task status.')
        return _task_status_redirect(request, task)

    if task.status != new_status:
        task.status = new_status
        task.save(update_fields=['status', 'updated_at'])
        messages.success(
            request,
            f'Task status updated to {task.get_status_display()}.',
        )
    else:
        messages.info(request, 'Task is already in that status.')
    return _task_status_redirect(request, task)
