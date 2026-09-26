from django.db.models import Count, Q
from django.shortcuts import render

from jobs.models import ApplicationStatus, Job, JobApplication


def home(request):
    open_jobs = Job.objects.visible().open()
    context = {
        'recent_jobs': open_jobs[:6],
        'open_job_count': open_jobs.count(),
        'company_count': open_jobs.values('company').distinct().count(),
    }

    profile = getattr(request.user, 'profile', None)
    if request.user.is_authenticated and profile is not None and profile.is_job_seeker:
        applications = JobApplication.objects.filter(applicant=request.user)
        counts = applications.aggregate(
            total=Count('pk'),
            active=Count('pk', filter=~Q(status__in=[ApplicationStatus.CLOSED])),
            interviews=Count('pk', filter=Q(status=ApplicationStatus.INTERVIEW)),
            offers=Count('pk', filter=Q(status=ApplicationStatus.OFFER)),
        )
        context.update(
            {
                'application_counts': counts,
                'recent_applications': applications.select_related('job')[:4],
            }
        )

    return render(request, 'home.html', context)
