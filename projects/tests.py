from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from tasks.models import Task

from .models import Project, ProjectMembership


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

    def test_leader_can_add_member_by_username_or_email(self):
        invited_leader = User.objects.create_user(
            username='invited-leader',
            email='invited-leader@example.com',
            password='StrongPassword123!',
        )
        response = self.post_project_detail(
            'invite_member',
            identifier='outsider',
            role=ProjectMembership.Role.MEMBER,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            ProjectMembership.objects.get(project=self.project, user=self.outsider).role,
            ProjectMembership.Role.MEMBER,
        )

        response = self.post_project_detail(
            'invite_member',
            identifier='invited-leader@example.com',
            role=ProjectMembership.Role.LEADER,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            ProjectMembership.objects.get(project=self.project, user=invited_leader).role,
            ProjectMembership.Role.LEADER,
        )

    def test_member_cannot_add_another_member(self):
        self.client.force_login(self.member)

        response = self.post_project_detail(
            'invite_member',
            identifier='outsider',
            role=ProjectMembership.Role.MEMBER,
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            ProjectMembership.objects.filter(project=self.project, user=self.outsider).exists()
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
            ProjectMembership.objects.filter(project=self.project, user=self.outsider).exists()
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
