from django.contrib import admin

from .models import Job, JobApplication


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'closing_date', 'posted_by', 'posted_at')
    list_filter = ('closing_date',)
    search_fields = ('title', 'company', 'location')


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('job', 'applicant', 'applied_at')
    search_fields = ('job__title', 'applicant__username', 'note')
