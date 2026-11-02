from django.urls import path

from . import views


urlpatterns = [
    path('', views.my_tasks_view, name='my_tasks'),
    path('<int:pk>/status/', views.update_task_status, name='update_task_status'),
]
