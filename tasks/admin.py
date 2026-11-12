from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'project',
        'assigned_to',
        'priority',
        'status',
        'start_date',
        'deadline',
        'created_at',
    )
    list_filter = ('status', 'priority', 'project', 'deadline', 'created_at')
    search_fields = (
        'title',
        'description',
        'project__name',
        'assigned_to__username',
        'assigned_to__email',
    )
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('project', 'assigned_to', 'creator')
