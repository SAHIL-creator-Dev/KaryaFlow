from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST, require_http_methods

from projects.models import Project, ProjectMembership

from .forms import TaskForm
from .models import Task


def _add_form_errors(request, form):
    for errors in form.errors.values():
        for error in errors:
            messages.error(request, error)


@login_required
@require_http_methods(['GET'])
def my_tasks_view(request):
    base_tasks = Task.objects.filter(
        assigned_to=request.user,
    ).select_related('project')

    today = timezone.localdate()
    stats = base_tasks.aggregate(
        total_assigned=Count('id'),
        pending_count=Count('id', filter=Q(status=Task.Status.TODO)),
        in_progress_count=Count('id', filter=Q(status=Task.Status.IN_PROGRESS)),
        in_review_count=Count('id', filter=Q(status=Task.Status.IN_REVIEW)),
        completed_count=Count('id', filter=Q(status=Task.Status.COMPLETED)),
    )

    tasks_qs = base_tasks

    # Filter by project (slug or id)
    project_filter = request.GET.get('project', 'all').strip().lower()
    if project_filter and project_filter != 'all':
        tasks_qs = tasks_qs.filter(
            Q(project__name__iexact=project_filter)
            | Q(project__id__iexact=project_filter)
        )

    # Filter by status
    status_filter = request.GET.get('status', 'all').strip().lower()
    if status_filter in Task.Status.values:
        tasks_qs = tasks_qs.filter(status=status_filter)
    else:
        status_filter = 'all'

    # Filter by priority
    priority_filter = request.GET.get('priority', 'all').strip().lower()
    if priority_filter in Task.Priority.values:
        tasks_qs = tasks_qs.filter(priority=priority_filter)
    else:
        priority_filter = 'all'

    # Search query
    search_query = request.GET.get('q', '').strip()
    if search_query:
        tasks_qs = tasks_qs.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )

    tasks_list = list(tasks_qs)
    for t in tasks_list:
        t.is_overdue = (
            t.deadline is not None
            and t.deadline < today
            and t.status != Task.Status.COMPLETED
        )

    project_choices = (
        ProjectMembership.objects.filter(user=request.user)
        .select_related('project')
        .values('project__id', 'project__name')
        .order_by('project__name')
    )

    return render(request, 'tasks/my_tasks.html', {
        'tasks': tasks_list,
        'stats': stats,
        'project_choices': [
            {'id': project['project__id'], 'name': project['project__name']}
            for project in project_choices
        ],
        'current_date': today,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'project_filter': project_filter,
        'search_query': search_query,
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


@login_required
@require_http_methods(['GET'])
def task_detail_view(request, pk):
    task = get_object_or_404(
        Task.objects.select_related('project', 'assigned_to', 'creator'),
        pk=pk,
    )
    membership = ProjectMembership.objects.filter(
        project=task.project,
        user=request.user,
    ).first()
    if membership is None:
        raise Http404

    today = timezone.localdate()
    is_leader = membership.role == ProjectMembership.Role.LEADER
    task.is_overdue = (
        task.deadline is not None
        and task.deadline < today
        and task.status != Task.Status.COMPLETED
    )

    return render(request, 'tasks/task_detail.html', {
        'task': task,
        'project': task.project,
        'is_leader': is_leader,
        'user_role': membership.role,
        'can_update_status': is_leader or task.assigned_to_id == request.user.pk,
        'task_status_choices': Task.Status.choices,
        'current_date': today,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def task_edit_view(request, pk):
    with transaction.atomic():
        task = get_object_or_404(
            Task.objects.select_for_update().select_related('project'),
            pk=pk,
        )
        # Only Leaders of this project can edit tasks
        get_object_or_404(
            ProjectMembership.objects.select_for_update(),
            project=task.project,
            user=request.user,
            role=ProjectMembership.Role.LEADER,
        )

        if request.method == 'POST':
            form = TaskForm(request.POST, instance=task, project=task.project)
            if form.is_valid():
                form.save()
                messages.success(request, f'Task "{task.title}" updated successfully.')
                next_url = request.POST.get('next', '')
                if next_url and url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)
                return redirect('task_detail', pk=task.pk)
            _add_form_errors(request, form)
        else:
            form = TaskForm(instance=task, project=task.project)

    return render(request, 'tasks/task_edit.html', {
        'task': task,
        'project': task.project,
        'form': form,
    })


@login_required
@require_POST
def task_delete_view(request, pk):
    with transaction.atomic():
        task = get_object_or_404(
            Task.objects.select_for_update().select_related('project'),
            pk=pk,
        )
        # Leader-only deletion
        get_object_or_404(
            ProjectMembership.objects.select_for_update(),
            project=task.project,
            user=request.user,
            role=ProjectMembership.Role.LEADER,
        )
        task_title = task.title
        project_id = task.project_id
        task.delete()
        messages.success(request, f'Task "{task_title}" was deleted.')

    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect('project_detail', pk=project_id)

