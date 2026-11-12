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
            'in_review_count': 0,
            'completed_count': 0,
        })
        self.assertContains(response, 'Implement task status')
        self.assertContains(response, 'Status project')
        self.assertNotContains(response, 'Export brand logo variants')


class TaskManagementPhase4Tests(TestCase):
    def setUp(self):
        self.leader = User.objects.create_user(username='leader', password='StrongPassword123!')
        self.member1 = User.objects.create_user(username='member1', password='StrongPassword123!')
        self.member2 = User.objects.create_user(username='member2', password='StrongPassword123!')
        self.outsider = User.objects.create_user(username='outsider', password='StrongPassword123!')

        self.project = Project.objects.create(name='Phase 4 Project', creator=self.leader)
        ProjectMembership.objects.create(project=self.project, user=self.leader, role=ProjectMembership.Role.LEADER)
        ProjectMembership.objects.create(project=self.project, user=self.member1, role=ProjectMembership.Role.MEMBER)
        ProjectMembership.objects.create(project=self.project, user=self.member2, role=ProjectMembership.Role.MEMBER)

        self.task = Task.objects.create(
            project=self.project,
            assigned_to=self.member1,
            creator=self.leader,
            title='Core API Development',
            description='Build RESTful views and models.',
            priority=Task.Priority.HIGH,
            status=Task.Status.TODO,
            start_date='2026-11-01',
            deadline='2026-11-10',
        )

    def test_date_validation_rejects_deadline_before_start_date(self):
        self.task.start_date = '2026-11-15'
        self.task.deadline = '2026-11-10'
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.task.full_clean()

    def test_task_detail_accessible_by_member_and_leader_denied_to_outsider(self):
        # Leader
        self.client.force_login(self.leader)
        response = self.client.get(reverse('task_detail', args=[self.task.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_leader'])

        # Member
        self.client.force_login(self.member2)
        response = self.client.get(reverse('task_detail', args=[self.task.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_leader'])

        # Outsider
        self.client.force_login(self.outsider)
        response = self.client.get(reverse('task_detail', args=[self.task.pk]))
        self.assertEqual(response.status_code, 404)

    def test_leader_can_edit_and_reassign_task(self):
        self.client.force_login(self.leader)
        response = self.client.post(reverse('edit_task', args=[self.task.pk]), {
            'title': 'Updated Core API',
            'description': 'Updated scope.',
            'priority': Task.Priority.URGENT,
            'status': Task.Status.IN_REVIEW,
            'start_date': '2026-11-02',
            'deadline': '2026-11-12',
            'assigned_to': str(self.member2.pk),
        })
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Updated Core API')
        self.assertEqual(self.task.priority, Task.Priority.URGENT)
        self.assertEqual(self.task.status, Task.Status.IN_REVIEW)
        self.assertEqual(self.task.assigned_to, self.member2)

    def test_member_and_outsider_cannot_edit_task(self):
        # Member
        self.client.force_login(self.member1)
        response = self.client.post(reverse('edit_task', args=[self.task.pk]), {
            'title': 'Hacked Title',
            'priority': Task.Priority.LOW,
            'status': Task.Status.TODO,
            'assigned_to': str(self.member1.pk),
        })
        self.assertEqual(response.status_code, 404)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Core API Development')

        # Outsider
        self.client.force_login(self.outsider)
        response = self.client.post(reverse('edit_task', args=[self.task.pk]), {
            'title': 'Outsider Hacked',
            'assigned_to': str(self.member1.pk),
        })
        self.assertEqual(response.status_code, 404)

    def test_reassignment_rejects_non_project_member(self):
        self.client.force_login(self.leader)
        response = self.client.post(reverse('edit_task', args=[self.task.pk]), {
            'title': 'Core API Development',
            'priority': Task.Priority.HIGH,
            'status': Task.Status.TODO,
            'assigned_to': str(self.outsider.pk),
        })
        self.assertEqual(response.status_code, 200)  # Form error
        self.task.refresh_from_db()
        self.assertEqual(self.task.assigned_to, self.member1)

    def test_leader_can_delete_task_member_cannot(self):
        # Member cannot delete
        self.client.force_login(self.member1)
        response = self.client.post(reverse('delete_task', args=[self.task.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

        # Leader can delete
        self.client.force_login(self.leader)
        response = self.client.post(reverse('delete_task', args=[self.task.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())

    def test_project_detail_edit_and_delete_actions(self):
        self.client.force_login(self.leader)
        # Edit task via project detail post
        response = self.client.post(reverse('project_detail', args=[self.project.pk]), {
            'action': 'edit_task',
            'task_id': str(self.task.pk),
            'title': 'Detail Action Edit',
            'priority': Task.Priority.URGENT,
            'status': Task.Status.IN_REVIEW,
            'assigned_to': str(self.member1.pk),
        })
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Detail Action Edit')
        self.assertEqual(self.task.priority, Task.Priority.URGENT)
        self.assertEqual(self.task.status, Task.Status.IN_REVIEW)

        # Delete task via project detail post
        response = self.client.post(reverse('project_detail', args=[self.project.pk]), {
            'action': 'delete_task',
            'task_id': str(self.task.pk),
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())

    def test_my_tasks_server_side_filtering(self):
        self.client.force_login(self.member1)
        # Add another task
        Task.objects.create(
            project=self.project,
            assigned_to=self.member1,
            title='Documentation Guide',
            priority=Task.Priority.LOW,
            status=Task.Status.COMPLETED,
        )

        # Filter by status
        response = self.client.get(reverse('my_tasks'), {'status': 'completed'})
        self.assertEqual(len(response.context['tasks']), 1)
        self.assertEqual(response.context['tasks'][0].title, 'Documentation Guide')

        # Filter by search
        response = self.client.get(reverse('my_tasks'), {'q': 'Core'})
        self.assertEqual(len(response.context['tasks']), 1)
        self.assertEqual(response.context['tasks'][0].title, 'Core API Development')

        # Filter by priority
        response = self.client.get(reverse('my_tasks'), {'priority': 'high'})
        self.assertEqual(len(response.context['tasks']), 1)
        self.assertEqual(response.context['tasks'][0].title, 'Core API Development')

