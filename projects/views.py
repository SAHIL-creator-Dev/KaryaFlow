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
from .models import Project, ProjectInvitation, ProjectMembership


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

    invited_user = form.cleaned_data['identifier']
    role = form.cleaned_data['role']

    # 1. Prevent inviting oneself
    if invited_user == request.user:
        messages.error(request, 'You cannot invite yourself to the project.')
        return

    with transaction.atomic():
        # 2. Prevent inviting users who are already active members
        if ProjectMembership.objects.filter(
            project=project,
            user=invited_user,
        ).exists():
            messages.error(request, 'That user is already an active member of this project.')
            return

        # 3. Prevent duplicate pending invitations for the same project and user
        if ProjectInvitation.objects.filter(
            project=project,
            invited_user=invited_user,
            status=ProjectInvitation.Status.PENDING,
        ).exists():
            messages.error(request, 'A pending invitation has already been sent to that user.')
            return

        try:
            with transaction.atomic():
                ProjectInvitation.objects.create(
                    project=project,
                    invited_by=request.user,
                    invited_user=invited_user,
                    role=role,
                    status=ProjectInvitation.Status.PENDING,
                )
        except IntegrityError:
            messages.error(request, 'A pending invitation has already been sent to that user.')
            return

    messages.success(request, f'Invitation sent to {invited_user.get_full_name() or invited_user.username}.')


def _create_task(request, project):
    form = ProjectTaskForm(request.POST, project=project)
    if not form.is_valid():
        _add_form_errors(request, form)
        return

    task = form.save(commit=False)
    task.creator = request.user
    task.save()
    messages.success(request, 'Task created and assigned to the selected team member.')


def _edit_task(request, project):
    try:
        task_id = int(request.POST.get('task_id', ''))
    except (TypeError, ValueError):
        raise Http404

    task = get_object_or_404(
        Task.objects.select_for_update(),
        pk=task_id,
        project=project,
    )
    form = ProjectTaskForm(request.POST, instance=task, project=project)
    if not form.is_valid():
        _add_form_errors(request, form)
        return

    form.save()
    messages.success(request, f'Task "{task.title}" updated successfully.')


def _delete_task(request, project):
    try:
        task_id = int(request.POST.get('task_id', ''))
    except (TypeError, ValueError):
        raise Http404

    task = get_object_or_404(
        Task.objects.select_for_update(),
        pk=task_id,
        project=project,
    )
    task_title = task.title
    task.delete()
    messages.success(request, f'Task "{task_title}" was deleted.')


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
    if membership.user_id == request.user.pk:
        messages.error(request, 'You cannot remove yourself from the project.')
        return

    if membership.role == ProjectMembership.Role.LEADER:
        messages.error(
            request,
            'Project leaders cannot be removed from the project.',
        )
        return

    member_name = membership.user.get_full_name() or membership.user.username
    membership.delete()
    messages.success(request, f'{member_name} has been removed from the project.')


def _handle_project_detail_post(request, project_id):
    action = request.POST.get('action')
    if action not in (
        'update_project',
        'invite_member',
        'create_task',
        'edit_task',
        'delete_task',
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
        elif action == 'edit_task':
            _edit_task(request, project)
        elif action == 'delete_task':
            _delete_task(request, project)
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
            in_review_tasks=Count(
                'tasks',
                filter=Q(tasks__status=Task.Status.IN_REVIEW),
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

    invitations = []
    if is_leader:
        invitations = list(
            ProjectInvitation.objects.filter(project=project)
            .select_related('invited_user', 'invited_by')
            .order_by('-created_at')
        )
        for inv in invitations:
            inv_name = inv.invited_user.get_full_name() or inv.invited_user.username
            inv.invited_user_name = inv_name
            inv.invited_user_initials = ''.join(part[0] for part in inv_name.split()[:2]).upper()

    return render(request, 'projects/project_detail.html', {
        'project': project,
        'members': members,
        'invitations': invitations,
        'tasks': tasks,
        'is_leader': is_leader,
        'user_role': current_membership.role,
        'stats': {
            'total_tasks': project.total_tasks,
            'completed_tasks': project.completed_tasks,
            'in_progress_tasks': project.in_progress_tasks,
            'pending_tasks': project.pending_tasks,
        },
        'in_review_tasks': project.in_review_tasks,
        'current_date': today,
        'task_status_choices': Task.Status.choices,
    })


@login_required
@require_http_methods(['GET'])
def my_invitations_view(request):
    """
    Displays invitations addressed to the authenticated user.
    """
    now = timezone.now()
    invitations = list(
        ProjectInvitation.objects.filter(invited_user=request.user)
        .select_related('project', 'invited_by')
        .order_by('-created_at')
    )

    # Process and mark expired invitations if applicable
    for inv in invitations:
        if (
            inv.status == ProjectInvitation.Status.PENDING
            and inv.expires_at is not None
            and inv.expires_at < now
        ):
            inv.status = ProjectInvitation.Status.EXPIRED
            inv.save(update_fields=['status'])
        
        inviter_name = inv.invited_by.get_full_name() or inv.invited_by.username
        inv.inviter_name = inviter_name
        inv.inviter_initials = ''.join(part[0] for part in inviter_name.split()[:2]).upper()

    pending_count = sum(1 for inv in invitations if inv.status == ProjectInvitation.Status.PENDING)

    return render(request, 'projects/my_invitations.html', {
        'invitations': invitations,
        'pending_count': pending_count,
        'current_date': timezone.localdate(),
    })


@login_required
@require_http_methods(['POST'])
def accept_invitation_view(request, invitation_id):
    """
    Allows an invited user to accept their pending project invitation.
    Atomically creates ProjectMembership (strictly Role.MEMBER) and marks invitation ACCEPTED.
    """
    now = timezone.now()
    with transaction.atomic():
        # Lock invitation and verify ownership
        invitation = get_object_or_404(
            ProjectInvitation.objects.select_for_update().select_related('project'),
            pk=invitation_id,
            invited_user=request.user,
        )

        # Check expiration
        if invitation.expires_at is not None and invitation.expires_at < now:
            invitation.status = ProjectInvitation.Status.EXPIRED
            invitation.save(update_fields=['status'])
            messages.error(request, 'This invitation has expired and can no longer be accepted.')
            return redirect('my_invitations')

        # Validate pending status
        if invitation.status != ProjectInvitation.Status.PENDING:
            messages.error(request, f'This invitation cannot be accepted because it is already {invitation.get_status_display().lower()}.')
            return redirect('my_invitations')

        # Verify user is not already a member
        if ProjectMembership.objects.filter(
            project=invitation.project,
            user=request.user,
        ).exists():
            invitation.status = ProjectInvitation.Status.ACCEPTED
            invitation.responded_at = now
            invitation.save(update_fields=['status', 'responded_at'])
            messages.info(request, f'You are already an active member of {invitation.project.name}.')
            return redirect('project_detail', pk=invitation.project_id)

        # Atomically create membership with normal Member role (never leader)
        try:
            ProjectMembership.objects.create(
                project=invitation.project,
                user=request.user,
                role=ProjectMembership.Role.MEMBER,
            )
        except IntegrityError:
            pass  # Already a member concurrently

        invitation.status = ProjectInvitation.Status.ACCEPTED
        invitation.responded_at = now
        invitation.save(update_fields=['status', 'responded_at'])

    messages.success(request, f'You have joined {invitation.project.name}!')
    return redirect('project_detail', pk=invitation.project_id)


@login_required
@require_http_methods(['POST'])
def reject_invitation_view(request, invitation_id):
    """
    Allows an invited user to reject their pending project invitation.
    """
    now = timezone.now()
    with transaction.atomic():
        invitation = get_object_or_404(
            ProjectInvitation.objects.select_for_update().select_related('project'),
            pk=invitation_id,
            invited_user=request.user,
        )

        # Check expiration
        if invitation.expires_at is not None and invitation.expires_at < now:
            invitation.status = ProjectInvitation.Status.EXPIRED
            invitation.save(update_fields=['status'])
            messages.error(request, 'This invitation has expired.')
            return redirect('my_invitations')

        if invitation.status != ProjectInvitation.Status.PENDING:
            messages.error(request, f'This invitation cannot be rejected because it is already {invitation.get_status_display().lower()}.')
            return redirect('my_invitations')

        invitation.status = ProjectInvitation.Status.REJECTED
        invitation.responded_at = now
        invitation.save(update_fields=['status', 'responded_at'])

    messages.info(request, f'You declined the invitation to join {invitation.project.name}.')
    return redirect('my_invitations')


@login_required
@require_http_methods(['POST'])
def cancel_invitation_view(request, invitation_id):
    """
    Allows the project leader to cancel a pending invitation.
    """
    with transaction.atomic():
        invitation = get_object_or_404(
            ProjectInvitation.objects.select_for_update().select_related('project'),
            pk=invitation_id,
        )

        # Verify that the requesting user is a leader of the project
        get_object_or_404(
            ProjectMembership.objects.select_for_update(),
            project=invitation.project,
            user=request.user,
            role=ProjectMembership.Role.LEADER,
        )

        if invitation.status != ProjectInvitation.Status.PENDING:
            messages.error(request, f'Cannot cancel an invitation that is already {invitation.get_status_display().lower()}.')
            return redirect('project_detail', pk=invitation.project_id)

        invitation.status = ProjectInvitation.Status.CANCELLED
        invitation.save(update_fields=['status'])

    messages.success(request, f'Invitation for {invitation.invited_user.get_full_name() or invitation.invited_user.username} cancelled.')
    return redirect('project_detail', pk=invitation.project_id)
