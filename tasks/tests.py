from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from projects.models import Project, ProjectMembership

from .models import Task


class TaskStatusUpdateTests(TestCase):
    def setUp(self):
        self.leader = User.objects.create_user(
            username='leader',
            password='StrongPassword123!',
        )
        self.assignee = User.objects.create_user(
            username='assignee',
            password='StrongPassword123!',
        )
        self.member = User.objects.create_user(
            username='member',
            password='StrongPassword123!',
        )
        self.outsider = User.objects.create_user(
            username='outsider',
            password='StrongPassword123!',
        )
        self.project = Project.objects.create(name='Status project', creator=self.leader)
        for user, role in (
            (self.leader, ProjectMembership.Role.LEADER),
            (self.assignee, ProjectMembership.Role.MEMBER),
            (self.member, ProjectMembership.Role.MEMBER),
        ):
            ProjectMembership.objects.create(
                project=self.project,
                user=user,
                role=role,
            )
        self.task = Task.objects.create(
            project=self.project,
            assigned_to=self.assignee,
            title='Implement task status',
            status=Task.Status.TODO,
        )
        self.status_url = reverse('update_task_status', args=[self.task.pk])

    def test_assignee_can_move_task_between_all_statuses(self):
        self.client.force_login(self.assignee)

        for status in Task.Status.values:
            response = self.client.post(self.status_url, {
                'status': status,
                'next': reverse('my_tasks'),
            })
            self.assertRedirects(response, reverse('my_tasks'))
            self.task.refresh_from_db()
            self.assertEqual(self.task.status, status)

    def test_project_leader_can_update_any_project_task(self):
        self.client.force_login(self.leader)

        response = self.client.post(self.status_url, {
            'status': Task.Status.COMPLETED,
            'next': reverse('dashboard'),
        })

        self.assertRedirects(response, reverse('dashboard'))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.COMPLETED)

    def test_member_cannot_update_task_assigned_to_another_user(self):
        self.client.force_login(self.member)

        response = self.client.post(self.status_url, {
            'status': Task.Status.COMPLETED,
        })

        self.assertEqual(response.status_code, 404)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.TODO)

    def test_nonmember_cannot_update_task(self):
        self.client.force_login(self.outsider)

        response = self.client.post(self.status_url, {
            'status': Task.Status.COMPLETED,
        })

        self.assertEqual(response.status_code, 404)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.TODO)

    def test_invalid_status_is_rejected(self):
        self.client.force_login(self.assignee)

        response = self.client.post(self.status_url, {
            'status': 'blocked',
            'next': reverse('my_tasks'),
        })

        self.assertRedirects(response, reverse('my_tasks'))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.TODO)

    def test_status_update_requires_post_and_authentication(self):
        self.client.force_login(self.assignee)
        get_response = self.client.get(self.status_url)
        self.assertEqual(get_response.status_code, 405)

        self.client.logout()
        post_response = self.client.post(self.status_url, {
            'status': Task.Status.COMPLETED,
        })
        self.assertEqual(post_response.status_code, 302)
        self.assertIn(reverse('login'), post_response.url)

    def test_redirect_rejects_external_next_url(self):
        self.client.force_login(self.assignee)

        response = self.client.post(self.status_url, {
            'status': Task.Status.COMPLETED,
            'next': 'https://example.com/',
        })

        self.assertRedirects(response, reverse('project_detail', args=[self.project.pk]))

    def test_my_tasks_page_uses_real_task_data_and_zero_safe_counts(self):
        self.client.force_login(self.assignee)
        response = self.client.get(reverse('my_tasks'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats'], {
            'total_assigned': 1,
            'pending_count': 1,
            'in_progress_count': 0,
            'completed_count': 0,
        })
        self.assertContains(response, 'Implement task status')
        self.assertContains(response, 'Status project')
        self.assertNotContains(response, 'Export brand logo variants')
