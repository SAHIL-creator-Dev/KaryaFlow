from django.urls import path

from . import views


urlpatterns = [
    path('', views.my_projects_view, name='my_projects'),
    path('invitations/', views.my_invitations_view, name='my_invitations'),
    path('invitations/<int:invitation_id>/accept/', views.accept_invitation_view, name='accept_invitation'),
    path('invitations/<int:invitation_id>/reject/', views.reject_invitation_view, name='reject_invitation'),
    path('invitations/<int:invitation_id>/cancel/', views.cancel_invitation_view, name='cancel_invitation'),
    path('<int:pk>/', views.project_detail_view, name='project_detail'),
]
