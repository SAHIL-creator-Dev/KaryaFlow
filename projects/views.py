from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from tasks.models import Task

from .forms import InviteMemberForm, ProjectForm, ProjectTaskForm
from .models import Project, ProjectMembership


def _project_id_from_post(request):
    try:
        return int(request.POST.get('project_id', ''))
    except (TypeError, ValueError):
        raise Http404


def _locked_project_for_leader(request, project_id):
    project = get_object_or_404(
        Project.objects.select_for_update(),
        pk=project_id,
    )
    get_object_or_404(
        ProjectMembership.objects.select_for_update(),
        project=project,
        user=request.user,
        role=ProjectMembership.Role.LEADER,
    )
    return project


def _add_form_errors(request, form):
    for errors in form.errors.values():
        for error in errors:
            messages.error(request, error)


def _create_project(request):
    form = ProjectForm(request.POST)
    if not form.is_valid():
        _add_form_errors(request, form)
        return redirect('my_projects')

    with transaction.atomic():
        project = form.save(commit=False)
        project.creator = request.user
        project.save()
        ProjectMembership.objects.create(
            project=project,
            user=request.user,
            role=ProjectMembership.Role.LEADER,
        )

    messages.success(request, 'Project created. You are now its Leader.')
    return redirect('project_detail', pk=project.pk)


def _update_project(request, project):
    form = ProjectForm(request.POST, instance=project)
    if form.is_valid():
        form.save()
        messages.success(request, 'Project details updated.')
    else:
        _add_form_errors(request, form)


def _invite_member(request, project):
    form = InviteMemberForm(request.POST)
    if not form.is_valid():
        _add_form_errors(request, form)
        return

    with transaction.atomic():
        if ProjectMembership.objects.filter(
            project=project,
            user=form.cleaned_data['identifier'],
        ).exists():
            messages.error(request, 'That user is already a member of this project.')
            return
        try:
            with transaction.atomic():
                ProjectMembership.objects.create(
                    project=project,
                    user=form.cleaned_data['identifier'],
                    role=form.cleaned_data['role'],
                )
        except IntegrityError:
            messages.error(request, 'That user is already a member of this project.')
            return

    messages.success(request, 'Team member added to the project.')


def _create_task(request, project):
    form = ProjectTaskForm(request.POST, project=project)
    if not form.is_valid():
        _add_form_errors(request, form)
        return

    task = form.save(commit=False)
    task.creator = request.user
    task.save()
    messages.success(request, 'Task created and assigned to the selected team member.')


def _handle_project_list_post(request):
    action = request.POST.get('action')
    if action == 'create_project':
        return _create_project(request)

    if action in ('update_project', 'invite_member'):
        project_id = _project_id_from_post(request)
        with transaction.atomic():
            project = _locked_project_for_leader(request, project_id)
            if action == 'update_project':
                _update_project(request, project)
            else:
                _invite_member(request, project)
        return redirect('project_detail', pk=project.pk)

    messages.error(request, 'This project action is not available.')
    return redirect('my_projects')


def _project_cards(user, params):
    memberships = ProjectMembership.objects.filter(
        user=user,
    ).select_related('project').annotate(
        total_tasks=Count('project__tasks', distinct=True),
        completed_tasks=Count(
            'project__tasks',
            filter=Q(project__tasks__status=Task.Status.COMPLETED),
            distinct=True,
        ),
        member_count=Count('project__memberships', distinct=True),
    )

    role = params.get('role', 'all').lower()
    if role in ProjectMembership.Role.values:
        memberships = memberships.filter(role=role)
    else:
        role = 'all'

    status = params.get('status', 'all').lower()
    if status in Project.Status.values:
        memberships = memberships.filter(project__status=status)
    else:
        status = 'all'

    search = params.get('q', '').strip()
    if search:
        memberships = memberships.filter(
            Q(project__name__icontains=search)
            | Q(project__description__icontains=search)
        )

    cards = []
    for membership in memberships:
        project = membership.project
        total_tasks = membership.total_tasks
        completed_tasks = membership.completed_tasks
        cards.append({
            'id': project.pk,
            'name': project.name,
            'description': project.description,
            'status': project.get_status_display(),
            'status_code': project.status,
            'created_at': project.created_at,
            'progress': round(completed_tasks * 100 / total_tasks) if total_tasks else 0,
            'completed_tasks': completed_tasks,
            'total_tasks': total_tasks,
            'member_count': membership.member_count,
            'user_role': membership.role,
            'is_leader': membership.role == ProjectMembership.Role.LEADER,
        })
    return cards, role, status, search


@login_required
@require_http_methods(['GET', 'POST'])
def my_projects_view(request):
    if request.method == 'POST':
        return _handle_project_list_post(request)

    projects, role_filter, status_filter, search_query = _project_cards(
        request.user,
        request.GET,
    )
    return render(request, 'projects/my_projects.html', {
        'projects': projects,
        'can_create_project': True,
        'current_date': timezone.localdate(),
        'role_filter': role_filter,
        'status_filter': status_filter,
        'search_query': search_query,
    })


def _update_member_role(request, project):
    try:
        membership_id = int(request.POST.get('membership_id', ''))
    except (TypeError, ValueError):
        raise Http404
    role = request.POST.get('role')
    if role not in ProjectMembership.Role.values:
        messages.error(request, 'Choose a valid project role.')
        return

    membership = get_object_or_404(
        ProjectMembership.objects.select_for_update(),
        pk=membership_id,
        project=project,
    )
    if (
        membership.role == ProjectMembership.Role.LEADER
        and role != ProjectMembership.Role.LEADER
        and not ProjectMembership.objects.filter(
            project=project,
            role=ProjectMembership.Role.LEADER,
        ).exclude(pk=membership.pk).exists()
    ):
        messages.error(request, 'A project must always have at least one Leader.')
        return

    membership.role = role
    membership.save(update_fields=['role'])
    messages.success(request, 'Team member role updated.')


def _remove_member(request, project):
    try:
        membership_id = int(request.POST.get('membership_id', ''))
    except (TypeError, ValueError):
        raise Http404
    membership = get_object_or_404(
        ProjectMembership.objects.select_for_update().select_related('user'),
        pk=membership_id,
        project=project,
    )
    if (
        membership.user_id == project.creator_id
        and membership.role == ProjectMembership.Role.LEADER
    ):
        messages.error(
            request,
            'Reassign the project creator to Member before removing them.',
        )
        return
    if (
        membership.role == ProjectMembership.Role.LEADER
        and not ProjectMembership.objects.filter(
            project=project,
            role=ProjectMembership.Role.LEADER,
        ).exclude(pk=membership.pk).exists()
    ):
        messages.error(request, 'A project must always have at least one Leader.')
        return

    membership.delete()
    messages.success(request, 'Team member removed from the project.')


def _handle_project_detail_post(request, project_id):
    action = request.POST.get('action')
    if action not in (
        'update_project',
        'invite_member',
        'create_task',
        'update_member_role',
        'remove_member',
    ):
        messages.error(request, 'This project action is not available.')
        return redirect('project_detail', pk=project_id)

    with transaction.atomic():
        project = _locked_project_for_leader(request, project_id)
        if action == 'update_project':
            _update_project(request, project)
        elif action == 'invite_member':
            _invite_member(request, project)
        elif action == 'create_task':
            _create_task(request, project)
        elif action == 'update_member_role':
            _update_member_role(request, project)
        else:
            _remove_member(request, project)
    return redirect('project_detail', pk=project_id)


@login_required
@require_http_methods(['GET', 'POST'])
def project_detail_view(request, pk):
    if request.method == 'POST':
        return _handle_project_detail_post(request, pk)

    project = get_object_or_404(
        Project.objects.filter(memberships__user=request.user).annotate(
            total_tasks=Count('tasks', distinct=True),
            completed_tasks=Count(
                'tasks',
                filter=Q(tasks__status=Task.Status.COMPLETED),
                distinct=True,
            ),
            in_progress_tasks=Count(
                'tasks',
                filter=Q(tasks__status=Task.Status.IN_PROGRESS),
                distinct=True,
            ),
            pending_tasks=Count(
                'tasks',
                filter=Q(tasks__status=Task.Status.TODO),
                distinct=True,
            ),
            member_count=Count('memberships', distinct=True),
        ),
        pk=pk,
    )
    current_membership = get_object_or_404(
        ProjectMembership,
        project=project,
        user=request.user,
    )
    is_leader = current_membership.role == ProjectMembership.Role.LEADER
    total_tasks = project.total_tasks
    project.progress = (
        round(project.completed_tasks * 100 / total_tasks) if total_tasks else 0
    )

    members = list(
        ProjectMembership.objects.filter(project=project).select_related('user')
    )
    for membership in members:
        name = membership.user.get_full_name() or membership.user.username
        membership.name = name
        membership.email = membership.user.email
        membership.initials = ''.join(
            part[0] for part in name.split()[:2]
        ).upper()
        membership.is_leader = membership.role == ProjectMembership.Role.LEADER
        membership.is_creator = membership.user_id == project.creator_id

    tasks = list(
        Task.objects.filter(project=project).select_related('assigned_to')
    )
    today = timezone.localdate()
    for task in tasks:
        assignee_name = task.assigned_to.get_full_name() or task.assigned_to.username
        task.assigned_to_user = task.assigned_to_id == request.user.pk
        task.assignee_name = assignee_name
        task.assignee_initials = ''.join(
            part[0] for part in assignee_name.split()[:2]
        ).upper()
        task.is_overdue = (
            task.deadline is not None
            and task.deadline < today
            and task.status != Task.Status.COMPLETED
        )

    return render(request, 'projects/project_detail.html', {
        'project': project,
        'members': members,
        'tasks': tasks,
        'is_leader': is_leader,
        'user_role': current_membership.role,
        'stats': {
            'total_tasks': project.total_tasks,
            'completed_tasks': project.completed_tasks,
            'in_progress_tasks': project.in_progress_tasks,
            'pending_tasks': project.pending_tasks,
        },
        'current_date': today,
        'task_status_choices': Task.Status.choices,
    })
