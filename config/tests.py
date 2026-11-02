from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from projects.models import Project, ProjectMembership
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
            'active_tasks': 0,
            'completed_tasks': 0,
            'pending_tasks': 0,
        })
        self.assertContains(response, 'No projects yet')
        self.assertContains(response, 'All caught up!')
        self.assertNotContains(response, 'KaryaFlow Platform Hardening')
