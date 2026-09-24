from django.apps import AppConfig


class AdminDashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin'
    # django.contrib.admin already owns the "admin" label, so this app needs its own.
    label = 'admin_dashboard'
    verbose_name = 'Admin Dashboard'
