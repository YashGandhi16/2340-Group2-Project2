from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Role
from accounts.views import job_seeker_required, recruiter_required

from .models import Job, JobApplication


def job_list(request):
    jobs = Job.objects.all()
    return render(request, 'jobs/job_list.html', {'jobs': jobs})


@job_seeker_required
def apply_to_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)

    if request.method != 'POST':
        return redirect('job_detail', job_id=job.pk)

    note = (request.POST.get('note') or '').strip()
    if not note:
        messages.error(request, 'Add a short tailored note before applying.')
        return redirect('job_detail', job_id=job.pk)

    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        messages.info(request, 'You have already applied to this job.')
        return redirect('job_detail', job_id=job.pk)

    JobApplication.objects.create(
        job=job,
        applicant=request.user,
        note=note,
    )

    messages.success(request, f'Application sent for {job.title}.')
    return redirect('job_detail', job_id=job.pk)


@recruiter_required
def application_list(request):
    applications = JobApplication.objects.select_related(
        'job',
        'applicant',
        'applicant__candidate_profile',
    ).order_by('-applied_at')

    job = None
    job_id = request.GET.get('job')
    if job_id and job_id.isdigit():
        job = get_object_or_404(Job, pk=job_id)
        applications = applications.filter(job=job)

    return render(
        request,
        'jobs/application_list.html',
        {'applications': applications, 'job': job},
    )


@recruiter_required
def review_application(request, application_id):
    application = get_object_or_404(
        JobApplication.objects.select_related(
            'job',
            'applicant',
            'applicant__candidate_profile',
        ),
        pk=application_id,
    )
    candidate = application.applicant
    candidate_profile = getattr(candidate, 'candidate_profile', None)
    other_applications = (
        candidate.job_applications.exclude(pk=application.pk).select_related('job')
    )
    return render(
        request,
        'jobs/review_application.html',
        {
            'application': application,
            'candidate': candidate,
            'candidate_profile': candidate_profile,
            'other_applications': other_applications,
        },
    )


def job_detail(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    profile = getattr(request.user, 'profile', None)
    is_job_seeker = (
        request.user.is_authenticated
        and profile is not None
        and profile.role == Role.JOB_SEEKER
    )
    is_recruiter = (
        request.user.is_authenticated
        and profile is not None
        and profile.role == Role.RECRUITER
    )
    already_applied = False
    if request.user.is_authenticated:
        already_applied = JobApplication.objects.filter(
            job=job,
            applicant=request.user,
        ).exists()

    return render(
        request,
        'jobs/job_detail.html',
        {
            'job': job,
            'is_job_seeker': is_job_seeker,
            'is_recruiter': is_recruiter,
            'application_count': job.applications.count() if is_recruiter else None,
            'already_applied': already_applied,
        },
    )
