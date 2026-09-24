from django.urls import path

from . import views

urlpatterns = [
    path('manage-users/', views.manage_users, name='manage_users'),
]
