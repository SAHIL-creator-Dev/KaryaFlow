from django.urls import path

from . import views


urlpatterns = [
    path('', views.my_tasks_view, name='my_tasks'),
    path('<int:pk>/', views.task_detail_view, name='task_detail'),
    path('<int:pk>/edit/', views.task_edit_view, name='edit_task'),
    path('<int:pk>/delete/', views.task_delete_view, name='delete_task'),
    path('<int:pk>/status/', views.update_task_status, name='update_task_status'),
]

