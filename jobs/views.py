from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Role
from accounts.views import job_seeker_required

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


def job_detail(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    profile = getattr(request.user, 'profile', None)
    is_job_seeker = (
        request.user.is_authenticated
        and profile is not None
        and profile.role == Role.JOB_SEEKER
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
            'already_applied': already_applied,
        },
    )
