from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from tasks.models import Task

from .models import Project, ProjectMembership


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ('name', 'description', 'status')


class InviteMemberForm(forms.Form):
    identifier = forms.CharField(max_length=254)
    role = forms.ChoiceField(
        choices=ProjectMembership.Role.choices,
        initial=ProjectMembership.Role.MEMBER,
    )

    def clean_identifier(self):
        identifier = self.cleaned_data['identifier'].strip()
        users = get_user_model().objects.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        )
        if not users.exists():
            raise forms.ValidationError('No KaryaFlow account matches that username or email.')
        if users.count() > 1:
            raise forms.ValidationError('That email matches multiple accounts. Use a username instead.')
        return users.get()

    def clean_role(self):
        role = self.cleaned_data['role']
        if role not in ProjectMembership.Role.values:
            raise forms.ValidationError('Choose a valid project role.')
        return role


class ProjectTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = (
            'title',
            'description',
            'priority',
            'deadline',
            'assigned_to',
            'status',
        )
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.fields['assigned_to'].queryset = get_user_model().objects.filter(
            project_memberships__project=project,
        ).order_by('first_name', 'last_name', 'username').distinct()

    def save(self, commit=True):
        task = super().save(commit=False)
        task.project = self.project
        if commit:
            task.save()
        return task
