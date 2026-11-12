from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Min, Q
from django.shortcuts import render
from django.utils import timezone

from projects.models import Project, ProjectInvitation, ProjectMembership
from tasks.models import Task


@login_required
def dashboard_view(request):
    today = timezone.localdate()
    now = timezone.now()

    # 1. Incoming pending invitations for the authenticated user
    raw_incoming_invitations = list(
        ProjectInvitation.objects.filter(
            invited_user=request.user,
            status=ProjectInvitation.Status.PENDING,
        )
        .select_related('project', 'invited_by')
        .order_by('-created_at')
    )
    incoming_invitations = []
    expired_invitation_ids = []
    for inv in raw_incoming_invitations:
        if inv.expires_at is not None and inv.expires_at < now:
            inv.status = ProjectInvitation.Status.EXPIRED
            expired_invitation_ids.append(inv.pk)
        else:
            inviter_name = inv.invited_by.get_full_name() or inv.invited_by.username
            inv.inviter_name = inviter_name
            inv.inviter_initials = (
                ''.join(part[0] for part in inviter_name.split()[:2]).upper()
                or inv.invited_by.username[:2].upper()
            )
            incoming_invitations.append(inv)

    if expired_invitation_ids:
        ProjectInvitation.objects.filter(pk__in=expired_invitation_ids).update(
            status=ProjectInvitation.Status.EXPIRED
        )

    pending_invitations_count = len(incoming_invitations)

    # 2. User's authorized project memberships with annotated task & team counts
    memberships = (
        ProjectMembership.objects.filter(user=request.user)
        .select_related('project')
        .annotate(
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
            overdue_tasks=Count(
                'project__tasks',
                filter=Q(project__tasks__deadline__lt=today)
                & ~Q(project__tasks__status=Task.Status.COMPLETED),
                distinct=True,
            ),
            next_deadline=Min(
                'project__tasks__deadline',
                filter=Q(project__tasks__deadline__isnull=False)
                & ~Q(project__tasks__status=Task.Status.COMPLETED),
            ),
            latest_deadline=Max('project__tasks__deadline'),
            member_count=Count('project__memberships', distinct=True),
        )
        .order_by('-project__created_at')
    )

    projects = []
    leader_projects = 0
    active_projects = 0
    completed_projects = 0
    on_hold_projects = 0
    user_project_ids = []
    leader_project_ids = []

    workspace_total_tasks = 0
    workspace_completed_tasks = 0
    workspace_pending_tasks = 0
    workspace_in_progress_tasks = 0
    workspace_in_review_tasks = 0
    workspace_overdue_tasks = 0

    for membership in memberships:
        project = membership.project
        user_project_ids.append(project.pk)
        total_tasks = membership.total_tasks
        completed_tasks = membership.completed_tasks
        pending_tasks = membership.pending_tasks
        in_progress_tasks = membership.in_progress_tasks
        in_review_tasks = membership.in_review_tasks
        overdue_tasks = membership.overdue_tasks
        remaining_tasks = max(0, total_tasks - completed_tasks)
        active_workload = pending_tasks + in_progress_tasks + in_review_tasks

        is_leader = membership.role == ProjectMembership.Role.LEADER
        leader_projects += int(is_leader)
        if is_leader:
            leader_project_ids.append(project.pk)

        if project.status == Project.Status.COMPLETED:
            completed_projects += 1
        elif project.status in (Project.Status.IN_PROGRESS, Project.Status.PLANNING):
            active_projects += 1
        elif project.status == Project.Status.ON_HOLD:
            on_hold_projects += 1

        progress = round(completed_tasks * 100 / total_tasks) if total_tasks else 0
        deadline = membership.next_deadline or membership.latest_deadline
        is_overdue = (
            deadline is not None
            and deadline < today
            and project.status != Project.Status.COMPLETED
            and remaining_tasks > 0
        )

        workspace_total_tasks += total_tasks
        workspace_completed_tasks += completed_tasks
        workspace_pending_tasks += pending_tasks
        workspace_in_progress_tasks += in_progress_tasks
        workspace_in_review_tasks += in_review_tasks
        workspace_overdue_tasks += overdue_tasks

        projects.append({
            'id': project.pk,
            'name': project.name,
            'description': project.description,
            'status': project.get_status_display(),
            'status_code': project.status,
            'created_at': project.created_at,
            'deadline': deadline,
            'is_overdue': is_overdue,
            'progress': progress,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'in_progress_tasks': in_progress_tasks,
            'in_review_tasks': in_review_tasks,
            'overdue_tasks': overdue_tasks,
            'total_tasks': total_tasks,
            'remaining_tasks': remaining_tasks,
            'active_workload': active_workload,
            'member_count': membership.member_count,
            'user_role': membership.role,
            'user_role_display': membership.get_role_display(),
            'is_leader': is_leader,
        })

    # 3. User's assigned tasks (restricted to authorized projects)
    task_queryset = Task.objects.filter(
        assigned_to=request.user,
        project_id__in=user_project_ids,
    )

    task_stats = task_queryset.aggregate(
        total_tasks=Count('id'),
        active_tasks=Count(
            'id',
            filter=Q(
                status__in=[
                    Task.Status.TODO,
                    Task.Status.IN_PROGRESS,
                    Task.Status.IN_REVIEW,
                ]
            ),
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

    # 4. Task list filtering for the My Tasks dashboard panel
    filtered_tasks = task_queryset.select_related('project')
    project_filter = request.GET.get('project', 'all').strip().lower()
    if project_filter and project_filter != 'all':
        filtered_tasks = filtered_tasks.filter(
            Q(project__name__iexact=project_filter)
            | Q(project__id__iexact=project_filter)
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

    # 5. Outgoing invitations for projects where the user is a Leader
    outgoing_invitations = []
    if leader_project_ids:
        raw_outgoing = list(
            ProjectInvitation.objects.filter(project_id__in=leader_project_ids)
            .select_related('project', 'invited_user', 'invited_by')
            .order_by('-created_at')[:10]
        )
        expired_outgoing_ids = []
        for inv in raw_outgoing:
            if (
                inv.status == ProjectInvitation.Status.PENDING
                and inv.expires_at is not None
                and inv.expires_at < now
            ):
                inv.status = ProjectInvitation.Status.EXPIRED
                expired_outgoing_ids.append(inv.pk)
            invitee_name = inv.invited_user.get_full_name() or inv.invited_user.username
            inv.invited_user_name = invitee_name
            inv.invited_user_initials = (
                ''.join(part[0] for part in invitee_name.split()[:2]).upper()
                or inv.invited_user.username[:2].upper()
            )
            outgoing_invitations.append(inv)
        if expired_outgoing_ids:
            ProjectInvitation.objects.filter(pk__in=expired_outgoing_ids).update(
                status=ProjectInvitation.Status.EXPIRED
            )

    # 6. Team Overview: Active members across the user's projects
    team_memberships = (
        ProjectMembership.objects.filter(project_id__in=user_project_ids)
        .exclude(user=request.user)
        .select_related('user', 'user__profile', 'project')
        .order_by('user__first_name', 'user__last_name', 'user__username')
    )

    team_members_dict = {}
    for tm in team_memberships:
        u = tm.user
        if u.pk not in team_members_dict:
            name = u.get_full_name() or u.username
            avatar_url = None
            try:
                if u.profile and u.profile.avatar_url:
                    avatar_url = u.profile.avatar_url
            except Exception:
                avatar_url = None

            team_members_dict[u.pk] = {
                'id': u.pk,
                'name': name,
                'initials': (
                    ''.join(part[0] for part in name.split()[:2]).upper()
                    or u.username[:2].upper()
                ),
                'avatar_url': avatar_url,
                'projects': [],
            }
        team_members_dict[u.pk]['projects'].append({
            'id': tm.project.pk,
            'name': tm.project.name,
            'role': tm.get_role_display(),
            'is_leader': tm.role == ProjectMembership.Role.LEADER,
        })

    team_members = list(team_members_dict.values())[:12]

    # 7. Analytics & Distribution Metrics (derived from actual database records)
    workspace_remaining_tasks = max(0, workspace_total_tasks - workspace_completed_tasks)
    workspace_active_workload = (
        workspace_pending_tasks + workspace_in_progress_tasks + workspace_in_review_tasks
    )
    workspace_completion_rate = (
        round(workspace_completed_tasks * 100 / workspace_total_tasks)
        if workspace_total_tasks
        else 0
    )

    for p in projects:
        p['workload_pct'] = (
            round(p['active_workload'] * 100 / workspace_active_workload)
            if workspace_active_workload
            else 0
        )

    user_total_tasks = task_stats['total_tasks'] or 0
    user_completed_tasks = task_stats['completed_tasks'] or 0
    user_remaining_tasks = max(0, user_total_tasks - user_completed_tasks)
    user_completion_rate = (
        round(user_completed_tasks * 100 / user_total_tasks)
        if user_total_tasks
        else 0
    )

    dist_total = workspace_total_tasks
    pending_pct = round(workspace_pending_tasks * 100 / dist_total) if dist_total else 0
    in_progress_pct = round(workspace_in_progress_tasks * 100 / dist_total) if dist_total else 0
    in_review_pct = round(workspace_in_review_tasks * 100 / dist_total) if dist_total else 0
    completed_pct = (
        max(0, 100 - pending_pct - in_progress_pct - in_review_pct)
        if dist_total and workspace_completed_tasks > 0
        else (round(workspace_completed_tasks * 100 / dist_total) if dist_total else 0)
    )

    analytics = {
        'workspace_total_tasks': workspace_total_tasks,
        'workspace_completed_tasks': workspace_completed_tasks,
        'workspace_remaining_tasks': workspace_remaining_tasks,
        'workspace_active_workload': workspace_active_workload,
        'workspace_pending_tasks': workspace_pending_tasks,
        'workspace_in_progress_tasks': workspace_in_progress_tasks,
        'workspace_in_review_tasks': workspace_in_review_tasks,
        'workspace_overdue_tasks': workspace_overdue_tasks,
        'workspace_completion_rate': workspace_completion_rate,
        'user_total_tasks': user_total_tasks,
        'user_completed_tasks': user_completed_tasks,
        'user_remaining_tasks': user_remaining_tasks,
        'user_completion_rate': user_completion_rate,
        'pending_pct': pending_pct,
        'in_progress_pct': in_progress_pct,
        'in_review_pct': in_review_pct,
        'completed_pct': completed_pct,
        'in_progress_offset': 100 - pending_pct,
        'in_review_offset': 100 - pending_pct - in_progress_pct,
        'completed_offset': 100 - pending_pct - in_progress_pct - in_review_pct,
    }

    # Base stats dict matching existing test suite requirements (6 keys)
    base_stats = {
        'total_projects': len(projects),
        'leader_projects': leader_projects,
        'member_projects': len(projects) - leader_projects,
        'active_tasks': task_stats['active_tasks'] or 0,
        'completed_tasks': task_stats['completed_tasks'] or 0,
        'pending_tasks': task_stats['pending_tasks'] or 0,
    }

    # Detailed 9-card overview statistics
    detailed_stats = {
        'total_projects': len(projects),
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'on_hold_projects': on_hold_projects,
        'leader_projects': leader_projects,
        'member_projects': len(projects) - leader_projects,
        'total_tasks': user_total_tasks,
        'active_tasks': task_stats['active_tasks'] or 0,
        'pending_tasks': task_stats['pending_tasks'] or 0,
        'in_progress_tasks': task_stats['in_progress_tasks'] or 0,
        'in_review_tasks': task_stats['in_review_tasks'] or 0,
        'completed_tasks': user_completed_tasks,
        'overdue_tasks': task_stats['overdue_tasks'] or 0,
    }

    context = {
        'current_date': today,
        'can_create_project': True,
        'stats': base_stats,
        'detailed_stats': detailed_stats,
        'analytics': analytics,
        'projects': projects,
        'tasks': tasks_list,
        'incoming_invitations': incoming_invitations,
        'outgoing_invitations': outgoing_invitations,
        'team_members': team_members,
        'pending_invitations_count': pending_invitations_count,
        'task_status_choices': Task.Status.choices,
        'task_priority_choices': Task.Priority.choices,
        'project_filter': project_filter,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
    }
    return render(request, 'dashboard/dashboard.html', context)
