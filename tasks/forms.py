from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import Task


class TaskForm(forms.ModelForm):
    """
    Form for creating and editing tasks within a project.
    Restricts assigned_to candidates strictly to existing project members.
    """
    class Meta:
        model = Task
        fields = (
            'title',
            'description',
            'priority',
            'status',
            'start_date',
            'deadline',
            'assigned_to',
        )
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'deadline': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.fields['assigned_to'].queryset = get_user_model().objects.filter(
            project_memberships__project=project,
        ).order_by('first_name', 'last_name', 'username').distinct()

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        deadline = cleaned_data.get('deadline')
        if start_date and deadline and deadline < start_date:
            self.add_error('deadline', "Deadline cannot be earlier than start date.")

        assigned_to = cleaned_data.get('assigned_to')
        if assigned_to and self.project:
            from projects.models import ProjectMembership
            if not ProjectMembership.objects.filter(project=self.project, user=assigned_to).exists():
                self.add_error('assigned_to', f"{assigned_to} is not a member of this project.")
        return cleaned_data

    def save(self, commit=True):
        task = super().save(commit=False)
        task.project = self.project
        if commit:
            task.save()
        return task


class TaskStatusUpdateForm(forms.Form):
    """
    Form for updating a task's status.
    """
    status = forms.ChoiceField(choices=Task.Status.choices)
    next = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_status(self):
        status = self.cleaned_data['status']
        if status not in Task.Status.values:
            raise ValidationError("Choose a valid task status.")
        return status
