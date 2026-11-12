from django.db import models
from django.conf import settings


class Project(models.Model):
    """
    Represents a workspace or collaborative project in KaryaFlow.
    """

    class Status(models.TextChoices):
        PLANNING = 'planning', 'Planning'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        ON_HOLD = 'on_hold', 'On Hold'

    name = models.CharField(
        max_length=150,
        help_text="Name of the project."
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the project objectives and scope."
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_projects',
        help_text="User who originally initialized the project."
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
        help_text="Current operational status of the project."
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ProjectMembership',
        related_name='projects',
        help_text="Users who are part of this project with an assigned role."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the project was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the project details were last updated."
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.name


class ProjectMembership(models.Model):
    """
    Intermediate model associating a User with a Project, holding their project-specific role.
    This enables a user to be a Leader in Project A and a Member in Project B.
    """

    class Role(models.TextChoices):
        LEADER = 'leader', 'Leader'
        MEMBER = 'member', 'Member'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_memberships',
        help_text="User participating in the project."
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='memberships',
        help_text="Project the user is associated with."
    )
    role = models.CharField(
        max_length=15,
        choices=Role.choices,
        default=Role.MEMBER,
        help_text="Project-specific role determining permissions."
    )
    joined_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the user joined the project."
    )

    class Meta:
        ordering = ['-joined_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'project'],
                name='unique_user_project_membership'
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.project.name} ({self.get_role_display()})"


class ProjectInvitation(models.Model):
    """
    Represents an invitation sent by a project leader to a registered KaryaFlow user.
    Membership is only granted once the invited user accepts the invitation.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'
        EXPIRED = 'expired', 'Expired'

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='invitations',
        help_text="Project the user is invited to join."
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_project_invitations',
        help_text="Project leader who issued the invitation."
    )
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_project_invitations',
        help_text="Registered KaryaFlow user invited to the project."
    )
    role = models.CharField(
        max_length=15,
        choices=ProjectMembership.Role.choices,
        default=ProjectMembership.Role.MEMBER,
        help_text="Proposed role for the user upon acceptance."
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Current lifecycle state of the invitation."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the invitation was dispatched."
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the invitee accepted or rejected the invitation."
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiration timestamp for the invitation."
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['project', 'status']),
            models.Index(fields=['invited_user', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'invited_user'],
                condition=models.Q(status='pending'),
                name='unique_pending_project_invitation',
            ),
        ]

    def __str__(self):
        return f"Invite for {self.invited_user} to {self.project.name} ({self.get_status_display()})"
