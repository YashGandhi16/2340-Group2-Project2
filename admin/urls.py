from django.urls import path

from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('users/<int:user_id>/', views.update_user, name='update_user'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<int:job_id>/edit/', views.edit_job, name='edit_job'),
    path('jobs/<int:job_id>/moderate/', views.moderate_job, name='moderate_job'),
    path('jobs/<int:job_id>/delete/', views.delete_job, name='delete_job'),
]
