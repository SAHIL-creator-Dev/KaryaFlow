from django.contrib import admin

from .models import Project, ProjectInvitation, ProjectMembership


class ProjectMembershipInline(admin.TabularInline):
    model = ProjectMembership
    extra = 0
    fields = ('user', 'role', 'joined_at')
    readonly_fields = ('joined_at',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'creator__username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ProjectMembershipInline]


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'role', 'joined_at')
    list_filter = ('role', 'joined_at')
    search_fields = ('project__name', 'user__username', 'user__email')
    readonly_fields = ('joined_at',)


@admin.register(ProjectInvitation)
class ProjectInvitationAdmin(admin.ModelAdmin):
    list_display = ('project', 'invited_user', 'invited_by', 'role', 'status', 'created_at', 'responded_at')
    list_filter = ('status', 'role', 'created_at')
    search_fields = ('project__name', 'invited_user__username', 'invited_user__email', 'invited_by__username')
    readonly_fields = ('created_at', 'responded_at')
