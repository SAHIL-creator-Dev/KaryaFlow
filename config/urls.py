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
from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('login/', TemplateView.as_view(template_name='accounts/login.html'), name='login'),
    path('register/', TemplateView.as_view(template_name='accounts/register.html'), name='register'),
    path('dashboard/', TemplateView.as_view(template_name='dashboard/dashboard.html', extra_context={'preview_mode': True}), name='dashboard'),
    path('projects/', TemplateView.as_view(template_name='projects/my_projects.html', extra_context={'preview_mode': True, 'can_create_project': True}), name='my_projects'),
    path('projects/<int:pk>/', TemplateView.as_view(template_name='projects/project_detail.html', extra_context={'preview_mode': True, 'is_leader': True}), name='project_detail'),
    path('tasks/', TemplateView.as_view(template_name='tasks/my_tasks.html', extra_context={'preview_mode': True}), name='my_tasks'),
    path('profile/', TemplateView.as_view(template_name='accounts/profile.html', extra_context={'preview_mode': True}), name='profile'),

    # -------------------------------------------------------------------------
    # Backend Developer Note:
    # When accounts, projects, and tasks backend views are ready:
    # - Replace login & register with accounts.views.login_view & register_view.
    # - Replace dashboard with projects.views.dashboard_view.
    # - Replace projects/ with projects.views.my_projects_view.
    # - Replace projects/<int:pk>/ with projects.views.project_detail_view.
    # - Replace tasks/ with tasks.views.my_tasks_view.
    # - Replace profile/ with accounts.views.profile_view.
    # (Refer to FRONTEND_BACKEND_INTEGRATION.md for context variable specifications)
    # -------------------------------------------------------------------------
]
