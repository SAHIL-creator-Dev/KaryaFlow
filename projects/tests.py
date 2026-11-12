from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from tasks.models import Task

from .models import Project, ProjectInvitation, ProjectMembership


class ProjectManagementTests(TestCase):
    def setUp(self):
        self.leader = User.objects.create_user(
            username='leader',
            email='leader@example.com',
            password='StrongPassword123!',
        )
        self.member = User.objects.create_user(
            username='member',
            email='member@example.com',
            password='StrongPassword123!',
        )
        self.outsider = User.objects.create_user(
            username='outsider',
            email='outsider@example.com',
            password='StrongPassword123!',
        )
        self.project = self.create_project('First project', self.leader)
        ProjectMembership.objects.create(
            project=self.project,
            user=self.member,
            role=ProjectMembership.Role.MEMBER,
        )
        self.client.force_login(self.leader)

    def create_project(self, name, creator):
        project = Project.objects.create(name=name, creator=creator)
        ProjectMembership.objects.create(
            project=project,
            user=creator,
            role=ProjectMembership.Role.LEADER,
        )
        return project

    def post_project_detail(self, action, **data):
        return self.client.post(
            reverse('project_detail', args=[self.project.pk]),
            {'action': action, **data},
        )

    def test_project_creation_makes_creator_a_leader(self):
        response = self.client.post(reverse('my_projects'), {
            'action': 'create_project',
            'name': 'New workspace',
            'description': 'Project description',
            'status': Project.Status.PLANNING,
        })

        project = Project.objects.get(name='New workspace')
        membership = ProjectMembership.objects.get(project=project)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('project_detail', args=[project.pk]))
        self.assertEqual(project.creator, self.leader)
        self.assertEqual(membership.user, self.leader)
        self.assertEqual(membership.role, ProjectMembership.Role.LEADER)

    def test_anonymous_user_cannot_create_project(self):
        self.client.logout()

        response = self.client.post(reverse('my_projects'), {
            'action': 'create_project',
            'name': 'Private project',
            'status': Project.Status.PLANNING,
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Project.objects.filter(name='Private project').exists())

    def test_invalid_project_data_is_rejected(self):
        response = self.client.post(reverse('my_projects'), {
            'action': 'create_project',
            'name': '',
            'status': Project.Status.PLANNING,
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Project.objects.count(), 1)

    def test_my_projects_filters_memberships_by_role_status_and_search(self):
        member_project = self.create_project('Planning work', self.outsider)
        Project.objects.filter(pk=member_project.pk).update(status=Project.Status.PLANNING)
        ProjectMembership.objects.create(
            project=member_project,
            user=self.leader,
            role=ProjectMembership.Role.MEMBER,
        )
        Project.objects.filter(pk=self.project.pk).update(status=Project.Status.COMPLETED)

        response = self.client.get(reverse('my_projects'), {
            'role': 'member',
            'status': 'planning',
            'q': 'Planning',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual([project['name'] for project in response.context['projects']], ['Planning work'])

    def test_member_can_view_details_and_nonmember_cannot(self):
        response = self.client.get(reverse('project_detail', args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user_role'], ProjectMembership.Role.LEADER)
        self.assertEqual(response.context['stats']['total_tasks'], 0)

        self.client.force_login(self.member)
        response = self.client.get(reverse('project_detail', args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user_role'], ProjectMembership.Role.MEMBER)

        self.client.force_login(self.outsider)
        response = self.client.get(reverse('project_detail', args=[self.project.pk]))
        self.assertEqual(response.status_code, 404)

    def test_project_detail_shows_task_counts_and_progress(self):
        for title, status in (
            ('To do', Task.Status.TODO),
            ('In progress', Task.Status.IN_PROGRESS),
            ('Completed', Task.Status.COMPLETED),
        ):
            Task.objects.create(
                project=self.project,
                assigned_to=self.member,
                title=title,
                status=status,
            )

        response = self.client.get(reverse('project_detail', args=[self.project.pk]))

        self.assertEqual(response.context['stats'], {
            'total_tasks': 3,
            'completed_tasks': 1,
            'in_progress_tasks': 1,
            'pending_tasks': 1,
        })
        self.assertEqual(response.context['project'].progress, 33)

    def test_project_list_excludes_nonmember_projects(self):
        self.create_project('Outsider workspace', self.outsider)

        response = self.client.get(reverse('my_projects'))

        self.assertEqual(
            {project['name'] for project in response.context['projects']},
            {'First project'},
        )

    def test_leader_can_send_invitation_by_username_or_email(self):
        invited_user = User.objects.create_user(
            username='invited-person',
            email='invited-person@example.com',
            password='StrongPassword123!',
        )
        response = self.post_project_detail(
            'invite_member',
            identifier='outsider',
            role=ProjectMembership.Role.MEMBER,
        )
        self.assertEqual(response.status_code, 302)
        invitation = ProjectInvitation.objects.get(project=self.project, invited_user=self.outsider)
        self.assertEqual(invitation.status, ProjectInvitation.Status.PENDING)
        self.assertEqual(invitation.role, ProjectMembership.Role.MEMBER)
        self.assertEqual(invitation.invited_by, self.leader)
        # Verify not yet a member
        self.assertFalse(
            ProjectMembership.objects.filter(project=self.project, user=self.outsider).exists()
        )

        response = self.post_project_detail(
            'invite_member',
            identifier='invited-person@example.com',
            role=ProjectMembership.Role.MEMBER,
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ProjectInvitation.objects.filter(
                project=self.project,
                invited_user=invited_user,
                status=ProjectInvitation.Status.PENDING,
            ).exists()
        )

    def test_member_cannot_send_invitation(self):
        self.client.force_login(self.member)

        response = self.post_project_detail(
            'invite_member',
            identifier='outsider',
            role=ProjectMembership.Role.MEMBER,
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            ProjectInvitation.objects.filter(project=self.project, invited_user=self.outsider).exists()
        )

    def test_duplicate_and_unknown_invites_are_rejected(self):
        duplicate = self.post_project_detail(
            'invite_member',
            identifier='member',
            role=ProjectMembership.Role.MEMBER,
        )
        unknown = self.post_project_detail(
            'invite_member',
            identifier='missing-account',
            role=ProjectMembership.Role.MEMBER,
        )

        self.assertEqual(duplicate.status_code, 302)
        self.assertEqual(unknown.status_code, 302)
        self.assertEqual(
            ProjectMembership.objects.filter(project=self.project, user=self.member).count(),
            1,
        )
        self.assertFalse(
            ProjectInvitation.objects.filter(project=self.project, invited_user=self.member).exists()
        )
        self.assertFalse(
            ProjectInvitation.objects.filter(project=self.project, invited_user=self.outsider).exists()
        )

    def test_leader_can_update_project_and_member_cannot(self):
        response = self.post_project_detail(
            'update_project',
            name='Updated project',
            description='Updated description',
            status=Project.Status.ON_HOLD,
        )
        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'Updated project')
        self.assertEqual(self.project.status, Project.Status.ON_HOLD)

        self.client.force_login(self.member)
        response = self.post_project_detail(
            'update_project',
            name='Unauthorized edit',
            description='',
            status=Project.Status.PLANNING,
        )
        self.assertEqual(response.status_code, 404)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'Updated project')

    def test_leader_can_create_task_assigned_to_project_member(self):
        response = self.post_project_detail(
            'create_task',
            title='Prepare release notes',
            description='Summarize the release.',
            priority='high',
            deadline='2026-12-01',
            assigned_to=str(self.member.pk),
            status=Task.Status.IN_PROGRESS,
        )

        task = Task.objects.get(title='Prepare release notes')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(task.project, self.project)
        self.assertEqual(task.assigned_to, self.member)
        self.assertEqual(task.creator, self.leader)
        self.assertEqual(task.priority, Task.Priority.HIGH)
        self.assertEqual(task.status, Task.Status.IN_PROGRESS)

    def test_task_creation_rejects_nonmember_assignees_and_invalid_input(self):
        nonmember_response = self.post_project_detail(
            'create_task',
            title='Invalid assignment',
            assigned_to=str(self.outsider.pk),
            status=Task.Status.TODO,
            priority=Task.Priority.MEDIUM,
        )
        invalid_response = self.post_project_detail(
            'create_task',
            title='',
            assigned_to=str(self.member.pk),
            status=Task.Status.TODO,
            priority='urgent',
        )

        self.assertEqual(nonmember_response.status_code, 302)
        self.assertEqual(invalid_response.status_code, 302)
        self.assertFalse(Task.objects.exists())

    def test_project_member_cannot_create_task(self):
        self.client.force_login(self.member)

        response = self.post_project_detail(
            'create_task',
            title='Unauthorized task',
            assigned_to=str(self.member.pk),
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Task.objects.exists())

    def test_leader_can_change_membership_role_and_remove_member(self):
        membership = ProjectMembership.objects.get(project=self.project, user=self.member)

        response = self.post_project_detail(
            'update_member_role',
            membership_id=membership.pk,
            role=ProjectMembership.Role.LEADER,
        )
        self.assertEqual(response.status_code, 302)
        membership.refresh_from_db()
        self.assertEqual(membership.role, ProjectMembership.Role.LEADER)

        response = self.post_project_detail(
            'update_member_role',
            membership_id=membership.pk,
            role=ProjectMembership.Role.MEMBER,
        )
        self.assertEqual(response.status_code, 302)
        membership.refresh_from_db()
        self.assertEqual(membership.role, ProjectMembership.Role.MEMBER)

        response = self.post_project_detail(
            'remove_member',
            membership_id=membership.pk,
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ProjectMembership.objects.filter(pk=membership.pk).exists())

    def test_member_cannot_remove_another_member(self):
        self.client.force_login(self.member)
        outsider_membership = ProjectMembership.objects.create(
            project=self.project,
            user=self.outsider,
            role=ProjectMembership.Role.MEMBER,
        )

        response = self.post_project_detail(
            'remove_member',
            membership_id=outsider_membership.pk,
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(ProjectMembership.objects.filter(pk=outsider_membership.pk).exists())

    def test_last_leader_cannot_be_demoted_or_removed(self):
        leader_membership = ProjectMembership.objects.get(
            project=self.project,
            user=self.leader,
        )
        demote = self.post_project_detail(
            'update_member_role',
            membership_id=leader_membership.pk,
            role=ProjectMembership.Role.MEMBER,
        )
        remove = self.post_project_detail(
            'remove_member',
            membership_id=leader_membership.pk,
        )

        self.assertEqual(demote.status_code, 302)
        self.assertEqual(remove.status_code, 302)
        leader_membership.refresh_from_db()
        self.assertEqual(leader_membership.role, ProjectMembership.Role.LEADER)

    def test_invalid_membership_role_is_rejected(self):
        membership = ProjectMembership.objects.get(project=self.project, user=self.member)

        response = self.post_project_detail(
            'update_member_role',
            membership_id=membership.pk,
            role='administrator',
        )

        self.assertEqual(response.status_code, 302)
        membership.refresh_from_db()
        self.assertEqual(membership.role, ProjectMembership.Role.MEMBER)

    def test_creator_must_be_reassigned_before_removal(self):
        second_leader = ProjectMembership.objects.create(
            project=self.project,
            user=self.outsider,
            role=ProjectMembership.Role.LEADER,
        )
        creator_membership = ProjectMembership.objects.get(
            project=self.project,
            user=self.leader,
        )

        rejected = self.post_project_detail(
            'remove_member',
            membership_id=creator_membership.pk,
        )
        self.assertEqual(rejected.status_code, 302)
        self.assertTrue(ProjectMembership.objects.filter(pk=creator_membership.pk).exists())

        reassigned = self.post_project_detail(
            'update_member_role',
            membership_id=creator_membership.pk,
            role=ProjectMembership.Role.MEMBER,
        )
        self.assertEqual(reassigned.status_code, 302)
        self.client.force_login(self.outsider)
        removed = self.post_project_detail(
            'remove_member',
            membership_id=creator_membership.pk,
        )
        self.assertEqual(removed.status_code, 302)
        self.assertFalse(ProjectMembership.objects.filter(pk=creator_membership.pk).exists())
        self.assertTrue(ProjectMembership.objects.filter(pk=second_leader.pk).exists())

    def test_user_cannot_change_membership_for_another_project(self):
        other_project = self.create_project('Other workspace', self.outsider)
        other_membership = ProjectMembership.objects.get(
            project=other_project,
            user=self.outsider,
        )

        response = self.post_project_detail(
            'remove_member',
            membership_id=other_membership.pk,
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(ProjectMembership.objects.filter(pk=other_membership.pk).exists())


class ProjectInvitationTests(TestCase):
    def setUp(self):
        self.leader = User.objects.create_user(
            username='leader',
            email='leader@example.com',
            password='StrongPassword123!',
        )
        self.member = User.objects.create_user(
            username='member',
            email='member@example.com',
            password='StrongPassword123!',
        )
        self.invitee = User.objects.create_user(
            username='invitee',
            email='invitee@example.com',
            password='StrongPassword123!',
        )
        self.bystander = User.objects.create_user(
            username='bystander',
            email='bystander@example.com',
            password='StrongPassword123!',
        )
        self.outsider = User.objects.create_user(
            username='outsider',
            email='outsider@example.com',
            password='StrongPassword123!',
        )
        self.project = Project.objects.create(name='Alpha Project', creator=self.leader)
        ProjectMembership.objects.create(
            project=self.project,
            user=self.leader,
            role=ProjectMembership.Role.LEADER,
        )
        ProjectMembership.objects.create(
            project=self.project,
            user=self.member,
            role=ProjectMembership.Role.MEMBER,
        )

    def test_leader_sending_invitation_creates_pending_invitation(self):
        self.client.force_login(self.leader)
        response = self.client.post(
            reverse('project_detail', args=[self.project.pk]),
            {'action': 'invite_member', 'identifier': 'invitee', 'role': 'member'},
        )
        self.assertEqual(response.status_code, 302)
        invitation = ProjectInvitation.objects.get(project=self.project, invited_user=self.invitee)
        self.assertEqual(invitation.status, ProjectInvitation.Status.PENDING)
        self.assertEqual(invitation.invited_by, self.leader)
        # Invitee is NOT yet a project member
        self.assertFalse(
            ProjectMembership.objects.filter(project=self.project, user=self.invitee).exists()
        )

    def test_invitee_receives_invitation_in_my_invitations(self):
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            invited_by=self.leader,
            invited_user=self.invitee,
            role=ProjectMembership.Role.MEMBER,
            status=ProjectInvitation.Status.PENDING,
        )
        self.client.force_login(self.invitee)
        response = self.client.get(reverse('my_invitations'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alpha Project')
        self.assertContains(response, 'leader')
        self.assertContains(response, 'Accept &amp; Join')
        self.assertEqual(response.context['pending_count'], 1)

    def test_invitee_can_accept_pending_invitation(self):
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            invited_by=self.leader,
            invited_user=self.invitee,
            role=ProjectMembership.Role.MEMBER,
            status=ProjectInvitation.Status.PENDING,
        )
        self.client.force_login(self.invitee)
        response = self.client.post(reverse('accept_invitation', args=[invitation.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('project_detail', args=[self.project.pk]))

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProjectInvitation.Status.ACCEPTED)
        self.assertIsNotNone(invitation.responded_at)

        # Now an active member with role MEMBER
        membership = ProjectMembership.objects.get(project=self.project, user=self.invitee)
        self.assertEqual(membership.role, ProjectMembership.Role.MEMBER)

    def test_acceptance_strictly_assigns_normal_member_role_never_leader(self):
        # Even if role on invitation was maliciously or accidentally set, acceptance enforces MEMBER
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            invited_by=self.leader,
            invited_user=self.invitee,
            role=ProjectMembership.Role.LEADER,
            status=ProjectInvitation.Status.PENDING,
        )
        self.client.force_login(self.invitee)
        response = self.client.post(reverse('accept_invitation', args=[invitation.pk]))
        self.assertEqual(response.status_code, 302)

        membership = ProjectMembership.objects.get(project=self.project, user=self.invitee)
        self.assertEqual(membership.role, ProjectMembership.Role.MEMBER)

    def test_invitee_can_reject_pending_invitation(self):
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            invited_by=self.leader,
            invited_user=self.invitee,
            role=ProjectMembership.Role.MEMBER,
            status=ProjectInvitation.Status.PENDING,
        )
        self.client.force_login(self.invitee)
        response = self.client.post(reverse('reject_invitation', args=[invitation.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('my_invitations'))

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProjectInvitation.Status.REJECTED)
        self.assertIsNotNone(invitation.responded_at)

        # No membership created
        self.assertFalse(
            ProjectMembership.objects.filter(project=self.project, user=self.invitee).exists()
        )

    def test_leader_can_cancel_pending_invitation(self):
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            invited_by=self.leader,
            invited_user=self.invitee,
            role=ProjectMembership.Role.MEMBER,
            status=ProjectInvitation.Status.PENDING,
        )
        self.client.force_login(self.leader)
        response = self.client.post(reverse('cancel_invitation', args=[invitation.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('project_detail', args=[self.project.pk]))

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProjectInvitation.Status.CANCELLED)

    def test_cannot_cancel_already_accepted_or_rejected_invitation(self):
        accepted_inv = ProjectInvitation.objects.create(
            project=self.project,
            invited_by=self.leader,
            invited_user=self.invitee,
            role=ProjectMembership.Role.MEMBER,
            status=ProjectInvitation.Status.ACCEPTED,
        )
        self.client.force_login(self.leader)
        response = self.client.post(reverse('cancel_invitation', args=[accepted_inv.pk]))
        self.assertEqual(response.status_code, 302)
        accepted_inv.refresh_from_db()
        self.assertEqual(accepted_inv.status, ProjectInvitation.Status.ACCEPTED)

    def test_member_cannot_cancel_invitation(self):
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            invited_by=self.leader,
            invited_user=self.invitee,
            role=ProjectMembership.Role.MEMBER,
            status=ProjectInvitation.Status.PENDING,
        )
        self.client.force_login(self.member)
        response = self.client.post(reverse('cancel_invitation', args=[invitation.pk]))
        self.assertEqual(response.status_code, 404)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProjectInvitation.Status.PENDING)

    def test_user_cannot_respond_to_another_users_invitation(self):
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            invited_by=self.leader,
            invited_user=self.invitee,
            role=ProjectMembership.Role.MEMBER,
            status=ProjectInvitation.Status.PENDING,
        )
        # Bystander attempts to accept invitee's invitation
        self.client.force_login(self.bystander)
        accept_resp = self.client.post(reverse('accept_invitation', args=[invitation.pk]))
        self.assertEqual(accept_resp.status_code, 404)

        reject_resp = self.client.post(reverse('reject_invitation', args=[invitation.pk]))
        self.assertEqual(reject_resp.status_code, 404)

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProjectInvitation.Status.PENDING)
        self.assertFalse(
            ProjectMembership.objects.filter(project=self.project, user=self.bystander).exists()
        )

    def test_duplicate_pending_invitations_are_prevented(self):
        self.client.force_login(self.leader)
        self.client.post(
            reverse('project_detail', args=[self.project.pk]),
            {'action': 'invite_member', 'identifier': 'invitee', 'role': 'member'},
        )
        self.assertEqual(
            ProjectInvitation.objects.filter(project=self.project, invited_user=self.invitee, status='pending').count(),
            1,
        )
        # Attempt second invitation
        response = self.client.post(
            reverse('project_detail', args=[self.project.pk]),
            {'action': 'invite_member', 'identifier': 'invitee', 'role': 'member'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            ProjectInvitation.objects.filter(project=self.project, invited_user=self.invitee, status='pending').count(),
            1,
        )

    def test_cannot_invite_existing_member(self):
        self.client.force_login(self.leader)
        response = self.client.post(
            reverse('project_detail', args=[self.project.pk]),
            {'action': 'invite_member', 'identifier': 'member', 'role': 'member'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            ProjectInvitation.objects.filter(project=self.project, invited_user=self.member).exists()
        )

    def test_leader_cannot_invite_themselves(self):
        self.client.force_login(self.leader)
        response = self.client.post(
            reverse('project_detail', args=[self.project.pk]),
            {'action': 'invite_member', 'identifier': 'leader', 'role': 'member'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            ProjectInvitation.objects.filter(project=self.project, invited_user=self.leader).exists()
        )

    def test_expired_invitation_cannot_be_accepted(self):
        from datetime import timedelta
        from django.utils import timezone

        expired_time = timezone.now() - timedelta(days=2)
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            invited_by=self.leader,
            invited_user=self.invitee,
            role=ProjectMembership.Role.MEMBER,
            status=ProjectInvitation.Status.PENDING,
            expires_at=expired_time,
        )
        self.client.force_login(self.invitee)
        response = self.client.post(reverse('accept_invitation', args=[invitation.pk]))
        self.assertEqual(response.status_code, 302)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProjectInvitation.Status.EXPIRED)
        self.assertFalse(
            ProjectMembership.objects.filter(project=self.project, user=self.invitee).exists()
        )

    def test_pending_invitations_do_not_affect_project_member_count(self):
        ProjectInvitation.objects.create(
            project=self.project,
            invited_by=self.leader,
            invited_user=self.invitee,
            role=ProjectMembership.Role.MEMBER,
            status=ProjectInvitation.Status.PENDING,
        )
        self.client.force_login(self.leader)
        response = self.client.get(reverse('project_detail', args=[self.project.pk]))
        # Member count must only include active memberships (leader + member = 2)
        self.assertEqual(len(response.context['members']), 2)
        self.assertEqual(len(response.context['invitations']), 1)

    def test_leader_successfully_removes_member(self):
        self.client.force_login(self.leader)
        member_membership = ProjectMembership.objects.get(
            project=self.project,
            user=self.member,
        )
        # Create a task assigned to member
        task = Task.objects.create(
            project=self.project,
            title='Sample Task',
            description='Test description',
            assigned_to=self.member,
            creator=self.leader,
            priority=Task.Priority.MEDIUM,
            status=Task.Status.TODO,
        )

        response = self.client.post(
            reverse('project_detail', args=[self.project.pk]),
            {'action': 'remove_member', 'membership_id': member_membership.pk},
        )
        self.assertEqual(response.status_code, 302)
        # Target membership deleted
        self.assertFalse(
            ProjectMembership.objects.filter(pk=member_membership.pk).exists()
        )
        # User account intact
        self.assertTrue(User.objects.filter(pk=self.member.pk).exists())
        # Historical task intact
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())
        # Project intact
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())

    def test_ordinary_member_cannot_remove_member(self):
        another_member = User.objects.create_user(
            username='another_member',
            email='another@example.com',
            password='StrongPassword123!',
        )
        target_membership = ProjectMembership.objects.create(
            project=self.project,
            user=another_member,
            role=ProjectMembership.Role.MEMBER,
        )
        self.client.force_login(self.member)
        response = self.client.post(
            reverse('project_detail', args=[self.project.pk]),
            {'action': 'remove_member', 'membership_id': target_membership.pk},
        )
        # Ordinary member cannot execute leader actions (raises 404 in _locked_project_for_leader)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            ProjectMembership.objects.filter(pk=target_membership.pk).exists()
        )

    def test_unauthorized_user_cannot_remove_member(self):
        self.client.force_login(self.outsider)
        member_membership = ProjectMembership.objects.get(
            project=self.project,
            user=self.member,
        )
        response = self.client.post(
            reverse('project_detail', args=[self.project.pk]),
            {'action': 'remove_member', 'membership_id': member_membership.pk},
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            ProjectMembership.objects.filter(pk=member_membership.pk).exists()
        )

    def test_leader_cannot_remove_project_leader(self):
        co_leader = User.objects.create_user(
            username='co_leader',
            email='coleader@example.com',
            password='StrongPassword123!',
        )
        co_leader_membership = ProjectMembership.objects.create(
            project=self.project,
            user=co_leader,
            role=ProjectMembership.Role.LEADER,
        )
        self.client.force_login(self.leader)
        response = self.client.post(
            reverse('project_detail', args=[self.project.pk]),
            {'action': 'remove_member', 'membership_id': co_leader_membership.pk},
        )
        self.assertEqual(response.status_code, 302)
        # Must not be deleted
        self.assertTrue(
            ProjectMembership.objects.filter(pk=co_leader_membership.pk).exists()
        )

    def test_leader_cannot_remove_themselves(self):
        leader_membership = ProjectMembership.objects.get(
            project=self.project,
            user=self.leader,
        )
        self.client.force_login(self.leader)
        response = self.client.post(
            reverse('project_detail', args=[self.project.pk]),
            {'action': 'remove_member', 'membership_id': leader_membership.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ProjectMembership.objects.filter(pk=leader_membership.pk).exists()
        )

    def test_removed_member_loses_project_and_task_access(self):
        task = Task.objects.create(
            project=self.project,
            title='Project Task',
            description='Test task',
            assigned_to=self.member,
            creator=self.leader,
            priority=Task.Priority.MEDIUM,
            status=Task.Status.TODO,
        )
        member_membership = ProjectMembership.objects.get(
            project=self.project,
            user=self.member,
        )
        # Leader removes member
        self.client.force_login(self.leader)
        self.client.post(
            reverse('project_detail', args=[self.project.pk]),
            {'action': 'remove_member', 'membership_id': member_membership.pk},
        )

        # Removed member attempts to access project detail -> 404
        self.client.force_login(self.member)
        detail_resp = self.client.get(reverse('project_detail', args=[self.project.pk]))
        self.assertEqual(detail_resp.status_code, 404)

        # Removed member attempts to view task detail -> 404
        task_resp = self.client.get(reverse('task_detail', args=[task.pk]))
        self.assertEqual(task_resp.status_code, 404)

        # Removed member attempts to update task status -> 404
        update_resp = self.client.post(
            reverse('update_task_status', args=[task.pk]),
            {'status': Task.Status.COMPLETED},
        )
        self.assertEqual(update_resp.status_code, 404)

    def test_removed_member_excluded_from_task_assignment(self):
        from .forms import ProjectTaskForm

        member_membership = ProjectMembership.objects.get(
            project=self.project,
            user=self.member,
        )
        # Remove member
        self.client.force_login(self.leader)
        self.client.post(
            reverse('project_detail', args=[self.project.pk]),
            {'action': 'remove_member', 'membership_id': member_membership.pk},
        )

        # Check form assigned_to queryset
        form = ProjectTaskForm(project=self.project)
        assignable_users = list(form.fields['assigned_to'].queryset)
        self.assertNotIn(self.member, assignable_users)
        self.assertIn(self.leader, assignable_users)

    def test_other_members_remain_unaffected_when_one_is_removed(self):
        third_member = User.objects.create_user(
            username='third_member',
            email='third@example.com',
            password='StrongPassword123!',
        )
        third_membership = ProjectMembership.objects.create(
            project=self.project,
            user=third_member,
            role=ProjectMembership.Role.MEMBER,
        )
        member_membership = ProjectMembership.objects.get(
            project=self.project,
            user=self.member,
        )

        self.client.force_login(self.leader)
        self.client.post(
            reverse('project_detail', args=[self.project.pk]),
            {'action': 'remove_member', 'membership_id': member_membership.pk},
        )

        # Third member remains active
        self.assertTrue(
            ProjectMembership.objects.filter(pk=third_membership.pk).exists()
        )
        self.client.force_login(third_member)
        resp = self.client.get(reverse('project_detail', args=[self.project.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_leader_can_reinvite_removed_member(self):
        member_membership = ProjectMembership.objects.get(
            project=self.project,
            user=self.member,
        )
        self.client.force_login(self.leader)
        # Remove member
        self.client.post(
            reverse('project_detail', args=[self.project.pk]),
            {'action': 'remove_member', 'membership_id': member_membership.pk},
        )
        self.assertFalse(
            ProjectMembership.objects.filter(project=self.project, user=self.member).exists()
        )

        # Re-invite member
        invite_resp = self.client.post(
            reverse('project_detail', args=[self.project.pk]),
            {'action': 'invite_member', 'identifier': self.member.username, 'role': 'member'},
        )
        self.assertEqual(invite_resp.status_code, 302)
        invitation = ProjectInvitation.objects.get(
            project=self.project,
            invited_user=self.member,
            status=ProjectInvitation.Status.PENDING,
        )
        self.assertEqual(invitation.invited_by, self.leader)
