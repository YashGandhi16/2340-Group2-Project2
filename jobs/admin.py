from django.contrib import admin

from .models import Job, JobApplication


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'posted_at')
    search_fields = ('title', 'company')


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('job', 'applicant', 'applied_at')
    search_fields = ('job__title', 'applicant__username', 'note')
