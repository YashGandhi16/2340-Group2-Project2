from django.urls import path

from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('users/<int:user_id>/', views.update_user, name='update_user'),
]
