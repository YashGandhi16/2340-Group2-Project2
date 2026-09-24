from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Role
from accounts.views import job_seeker_required, recruiter_required

from .forms import JobPostingForm
from .models import Job, JobApplication


def job_list(request):
    jobs = Job.objects.open()

    query = request.GET.get('q', '').strip()
    if query:
        jobs = jobs.filter(
            Q(title__icontains=query)
            | Q(company__icontains=query)
            | Q(description__icontains=query)
            | Q(requirements__icontains=query)
        )

    location = request.GET.get('location', '').strip()
    if location:
        jobs = jobs.filter(location__icontains=location)

    return render(
        request,
        'jobs/job_list.html',
        {'jobs': jobs, 'query': query, 'location': location},
    )


@recruiter_required
def recruiter_dashboard(request):
    postings = (
        Job.objects.filter(posted_by=request.user)
        .annotate(application_count=Count('applications'))
        .order_by('-posted_at')
    )
    return render(request, 'jobs/recruiter_dashboard.html', {'postings': postings})


@recruiter_required
def create_job(request):
    form = JobPostingForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        job = form.save(commit=False)
        job.posted_by = request.user
        job.save()
        messages.success(request, f'Posted {job.title} at {job.company}.')
        return redirect('recruiter_dashboard')

    return render(request, 'jobs/job_form.html', {'form': form, 'job': None})


@recruiter_required
def edit_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id, posted_by=request.user)
    form = JobPostingForm(request.POST or None, instance=job)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Updated {job.title} at {job.company}.')
        return redirect('recruiter_dashboard')

    return render(request, 'jobs/job_form.html', {'form': form, 'job': job})


@job_seeker_required
def apply_to_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)

    if request.method != 'POST':
        return redirect('job_detail', job_id=job.pk)

    if not job.is_open:
        messages.error(request, 'This posting is closed and no longer accepts applications.')
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
            'is_owner': is_recruiter and job.posted_by_id == request.user.pk,
            'already_applied': already_applied,
        },
    )
