from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from projects.models import Project, ProjectInvitation, ProjectMembership
from tasks.models import Task


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='member', password='StrongPassword123!')
        self.other_user = User.objects.create_user(username='other', password='StrongPassword123!')
        self.client.force_login(self.user)
        self.dashboard_url = reverse('dashboard')

    def create_project(self, name, user, role=ProjectMembership.Role.MEMBER):
        project = Project.objects.create(name=name, creator=user)
        ProjectMembership.objects.create(user=user, project=project, role=role)
        return project

    def create_task(self, project, assigned_to, title, status):
        return Task.objects.create(
            project=project,
            assigned_to=assigned_to,
            title=title,
            status=status,
        )

    def test_dashboard_shows_only_the_users_projects_and_assigned_tasks(self):
        leader_project = self.create_project(
            'Leader project',
            self.user,
            ProjectMembership.Role.LEADER,
        )
        self.create_project('Member project', self.user)
        other_project = self.create_project('Other project', self.other_user)
        ProjectMembership.objects.create(
            user=self.other_user,
            project=leader_project,
            role=ProjectMembership.Role.MEMBER,
        )

        self.create_task(leader_project, self.user, 'To do', Task.Status.TODO)
        self.create_task(leader_project, self.user, 'In progress', Task.Status.IN_PROGRESS)
        self.create_task(leader_project, self.user, 'Completed', Task.Status.COMPLETED)
        self.create_task(other_project, self.other_user, 'Assigned elsewhere', Task.Status.TODO)

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats'], {
            'total_projects': 2,
            'leader_projects': 1,
            'member_projects': 1,
            'active_tasks': 2,
            'completed_tasks': 1,
            'pending_tasks': 1,
        })
        self.assertEqual(
            {project['name'] for project in response.context['projects']},
            {'Leader project', 'Member project'},
        )
        leader_project_data = next(
            project for project in response.context['projects']
            if project['name'] == 'Leader project'
        )
        self.assertTrue(leader_project_data['is_leader'])
        self.assertEqual(leader_project_data['member_count'], 2)
        self.assertEqual(leader_project_data['progress'], 33)
        self.assertEqual(
            {task.title for task in response.context['tasks']},
            {'To do', 'In progress', 'Completed'},
        )
        self.assertContains(response, 'To Do')
        self.assertContains(response, 'In Progress')
        self.assertNotContains(response, 'Audit accessibility')

    def test_dashboard_renders_live_empty_states_and_zero_stats(self):
        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats'], {
            'total_projects': 0,
            'leader_projects': 0,
            'member_projects': 0,
            'active_tasks': 0,
            'completed_tasks': 0,
            'pending_tasks': 0,
        })
        self.assertContains(response, 'No projects yet')
        self.assertContains(response, 'All caught up!')
        self.assertNotContains(response, 'KaryaFlow Platform Hardening')

    def test_dashboard_detailed_stats_invitations_team_and_analytics(self):
        today = timezone.localdate()
        leader_project = self.create_project(
            'Active Alpha',
            self.user,
            ProjectMembership.Role.LEADER,
        )
        completed_project = Project.objects.create(
            name='Finished Beta',
            creator=self.other_user,
            status=Project.Status.COMPLETED,
        )
        ProjectMembership.objects.create(
            user=self.other_user,
            project=completed_project,
            role=ProjectMembership.Role.LEADER,
        )
        ProjectMembership.objects.create(
            user=self.user,
            project=completed_project,
            role=ProjectMembership.Role.MEMBER,
        )
        ProjectMembership.objects.create(
            user=self.other_user,
            project=leader_project,
            role=ProjectMembership.Role.MEMBER,
        )

        # Create tasks across statuses and deadlines
        Task.objects.create(
            project=leader_project,
            assigned_to=self.user,
            title='Overdue task',
            status=Task.Status.TODO,
            priority=Task.Priority.HIGH,
            deadline=today - timedelta(days=2),
        )
        Task.objects.create(
            project=leader_project,
            assigned_to=self.user,
            title='Review task',
            status=Task.Status.IN_REVIEW,
            priority=Task.Priority.URGENT,
            deadline=today + timedelta(days=3),
        )
        Task.objects.create(
            project=completed_project,
            assigned_to=self.user,
            title='Done task',
            status=Task.Status.COMPLETED,
            priority=Task.Priority.LOW,
        )

        # Incoming invitation from another project
        external_project = self.create_project(
            'External Gamma',
            self.other_user,
            ProjectMembership.Role.LEADER,
        )
        incoming_inv = ProjectInvitation.objects.create(
            project=external_project,
            invited_by=self.other_user,
            invited_user=self.user,
            role=ProjectMembership.Role.MEMBER,
            status=ProjectInvitation.Status.PENDING,
        )

        # Outgoing invitation sent from user's leader_project
        invitee = User.objects.create_user(username='invitee', password='StrongPassword123!')
        outgoing_inv = ProjectInvitation.objects.create(
            project=leader_project,
            invited_by=self.user,
            invited_user=invitee,
            role=ProjectMembership.Role.MEMBER,
            status=ProjectInvitation.Status.PENDING,
        )

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        detailed = response.context['detailed_stats']
        self.assertEqual(detailed['total_projects'], 2)
        self.assertEqual(detailed['active_projects'], 1)
        self.assertEqual(detailed['completed_projects'], 1)
        self.assertEqual(detailed['total_tasks'], 3)
        self.assertEqual(detailed['pending_tasks'], 1)
        self.assertEqual(detailed['in_progress_tasks'], 0)
        self.assertEqual(detailed['in_review_tasks'], 1)
        self.assertEqual(detailed['completed_tasks'], 1)
        self.assertEqual(detailed['overdue_tasks'], 1)

        analytics = response.context['analytics']
        self.assertEqual(analytics['workspace_total_tasks'], 3)
        self.assertEqual(analytics['workspace_completed_tasks'], 1)
        self.assertEqual(analytics['workspace_remaining_tasks'], 2)
        self.assertEqual(analytics['workspace_overdue_tasks'], 1)

        self.assertEqual(
            [inv.pk for inv in response.context['incoming_invitations']],
            [incoming_inv.pk],
        )
        self.assertEqual(
            [inv.pk for inv in response.context['outgoing_invitations']],
            [outgoing_inv.pk],
        )
        self.assertEqual(len(response.context['team_members']), 1)
        self.assertEqual(response.context['team_members'][0]['name'], 'other')

        # Test dashboard task filtering by status and priority
        filtered_resp = self.client.get(
            self.dashboard_url,
            {'status': Task.Status.IN_REVIEW, 'priority': Task.Priority.URGENT},
        )
        self.assertEqual(filtered_resp.status_code, 200)
        self.assertEqual(
            [t.title for t in filtered_resp.context['tasks']],
            ['Review task'],
        )
