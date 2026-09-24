from django.urls import path

from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login-redirect/', views.login_redirect, name='login_redirect'),
]
