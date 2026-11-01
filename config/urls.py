"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),

    # Accounts application routes (login, register, logout, profile, change_password)
    path('', include('accounts.urls')),

    # Protected Core Application Workspace Routes
    path(
        'dashboard/', 
        login_required(TemplateView.as_view(template_name='dashboard/dashboard.html', extra_context={'preview_mode': True})), 
        name='dashboard'
    ),
    path(
        'projects/', 
        login_required(TemplateView.as_view(template_name='projects/my_projects.html', extra_context={'preview_mode': True, 'can_create_project': True})), 
        name='my_projects'
    ),
    path(
        'projects/<int:pk>/', 
        login_required(TemplateView.as_view(template_name='projects/project_detail.html', extra_context={'preview_mode': True, 'is_leader': True})), 
        name='project_detail'
    ),
    path(
        'tasks/', 
        login_required(TemplateView.as_view(template_name='tasks/my_tasks.html', extra_context={'preview_mode': True})), 
        name='my_tasks'
    ),
]

# Serve media files in local development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

