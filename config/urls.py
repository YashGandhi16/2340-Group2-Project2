from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path(
        'accounts/login/',
        auth_views.LoginView.as_view(template_name='accounts/login.html'),
        name='login',
    ),
    path(
        'accounts/logout/',
        auth_views.LogoutView.as_view(next_page='home'),
        name='logout',
    ),
    path('accounts/', include('accounts.urls')),
    path('profile/', include('profiles.urls')),
    path('jobs/', include('jobs.urls')),
    path('dashboard/', include('admin.urls')),
]
