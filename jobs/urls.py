from django.urls import path

from . import views

urlpatterns = [
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
