from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Task(models.Model):
    """
    Represents an actionable unit of work belonging to a specific Project,
    assigned to a team member within that project.
    """

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    class Status(models.TextChoices):
        TODO = 'pending', 'To Do'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'

    title = models.CharField(
        max_length=200,
        help_text="Short, descriptive headline of the task."
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed instructions or acceptance criteria for the task."
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='tasks',
        help_text="The project this task belongs to."
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='assigned_tasks',
        help_text="Project member responsible for executing this task."
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tasks',
        help_text="User who authored/created the task."
    )
    priority = models.CharField(
        max_length=15,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text="Urgency or importance of the task."
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
        help_text="Current execution status of the task."
    )
    deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Target date for completion."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the task was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the task was last modified."
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['deadline']),
            models.Index(fields=['project', 'status']),
            models.Index(fields=['assigned_to', 'status']),
        ]

    def clean(self):
        """
        Model-level validation enforcing that the assigned user must be
        an active member of the project.
        """
        super().clean()
        if self.project_id and self.assigned_to_id:
            # Check membership in the target project
            from projects.models import ProjectMembership
            is_member = ProjectMembership.objects.filter(
                project_id=self.project_id,
                user_id=self.assigned_to_id
            ).exists()
            if not is_member:
                raise ValidationError({
                    'assigned_to': (
                        f"The assigned user '{self.assigned_to}' is not a member of "
                        f"the project '{self.project.name}'."
                    )
                })

    def save(self, *args, **kwargs):
        # Always run model validation before saving
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.project.name}) - {self.get_status_display()}"
