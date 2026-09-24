from django.urls import path

from . import views

urlpatterns = [
    path('recruiter/', views.recruiter_dashboard, name='recruiter_dashboard'),
    path('new/', views.create_job, name='create_job'),
    path('<int:job_id>/edit/', views.edit_job, name='edit_job'),
    path('applications/', views.application_list, name='application_list'),
    path(
        'applications/<int:application_id>/',
        views.review_application,
        name='review_application',
    ),
    path('', views.job_list, name='job_list'),
    path('<int:job_id>/', views.job_detail, name='job_detail'),
    path('<int:job_id>/apply/', views.apply_to_job, name='apply_to_job'),
]
