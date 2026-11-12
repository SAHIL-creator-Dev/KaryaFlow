# Generated manually for KaryaFlow Project Member Invitation and Acceptance System

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectInvitation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('leader', 'Leader'), ('member', 'Member')], default='member', help_text='Proposed role for the user upon acceptance.', max_length=15)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled'), ('expired', 'Expired')], default='pending', help_text='Current lifecycle state of the invitation.', max_length=15)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Timestamp when the invitation was dispatched.')),
                ('responded_at', models.DateTimeField(blank=True, help_text='Timestamp when the invitee accepted or rejected the invitation.', null=True)),
                ('expires_at', models.DateTimeField(blank=True, help_text='Optional expiration timestamp for the invitation.', null=True)),
                ('invited_by', models.ForeignKey(help_text='Project leader who issued the invitation.', on_delete=django.db.models.deletion.CASCADE, related_name='sent_project_invitations', to=settings.AUTH_USER_MODEL)),
                ('invited_user', models.ForeignKey(help_text='Registered KaryaFlow user invited to the project.', on_delete=django.db.models.deletion.CASCADE, related_name='received_project_invitations', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(help_text='Project the user is invited to join.', on_delete=django.db.models.deletion.CASCADE, related_name='invitations', to='projects.project')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='projectinvitation',
            index=models.Index(fields=['status'], name='projects_pr_status_67f2ec_idx'),
        ),
        migrations.AddIndex(
            model_name='projectinvitation',
            index=models.Index(fields=['created_at'], name='projects_pr_created_d2fa8e_idx'),
        ),
        migrations.AddIndex(
            model_name='projectinvitation',
            index=models.Index(fields=['project', 'status'], name='projects_pr_project_6fa1b1_idx'),
        ),
        migrations.AddIndex(
            model_name='projectinvitation',
            index=models.Index(fields=['invited_user', 'status'], name='projects_pr_invited_31d87e_idx'),
        ),
        migrations.AddConstraint(
            model_name='projectinvitation',
            constraint=models.UniqueConstraint(condition=models.Q(('status', 'pending')), fields=('project', 'invited_user'), name='unique_pending_project_invitation'),
        ),
    ]
