from django.urls import path

from . import views


urlpatterns = [
    path('', views.my_projects_view, name='my_projects'),
    path('<int:pk>/', views.project_detail_view, name='project_detail'),
]
