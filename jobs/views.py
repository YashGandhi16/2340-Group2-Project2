from django.contrib import messages
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Role
from accounts.views import job_seeker_required, recruiter_or_admin_required, recruiter_required
from profiles.models import CandidateProfile

from .forms import JobPostingForm
from .models import ApplicationStatus, Job, JobApplication


def job_list(request):
    jobs = Job.objects.visible().open()

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


def _status_breakdown(applications):
    """[{value, label, count, pct}] for each hiring stage, in pipeline order."""
    counts = dict(
        applications.order_by().values_list('status').annotate(n=Count('pk'))
    )
    total = sum(counts.values())
    return [
        {
            'value': value,
            'label': label,
            'count': counts.get(value, 0),
            'pct': round(counts.get(value, 0) * 100 / total) if total else 0,
        }
        for value, label in ApplicationStatus.choices
    ]


@recruiter_required
def recruiter_dashboard(request):
    postings = (
        Job.objects.filter(posted_by=request.user)
        .annotate(application_count=Count('applications'))
        .order_by('-posted_at')
    )
    applications = JobApplication.objects.filter(job__posted_by=request.user)
    status_breakdown = _status_breakdown(applications)
    stage_counts = {row['value']: row['count'] for row in status_breakdown}
    return render(
        request,
        'jobs/recruiter_dashboard.html',
        {
            'postings': postings,
            'status_breakdown': status_breakdown,
            'total_applicants': sum(stage_counts.values()),
            'new_applicants': stage_counts[ApplicationStatus.APPLIED],
            'interviewing': stage_counts[ApplicationStatus.INTERVIEW],
            'open_posting_count': sum(1 for job in postings if job.accepts_applications),
            'recent_applications': applications.select_related(
                'job', 'applicant', 'applicant__candidate_profile'
            ).order_by('-applied_at')[:5],
        },
    )



@recruiter_required
def candidate_search(request):
    candidates = CandidateProfile.objects.select_related('user').all()
    skills = request.GET.get('skills', '').strip()
    location = request.GET.get('location', '').strip()
    projects = request.GET.get('projects', '').strip()

    if skills:
        candidates = candidates.filter(skills__icontains=skills)
    if location:
        candidates = candidates.filter(location__icontains=location)
    if projects:
        candidates = candidates.filter(
            Q(work_experience__icontains=projects)
            | Q(summary__icontains=projects)
        )

    return render(
        request,
        'jobs/candidate_search.html',
        {
            'candidates': candidates,
            'skills': skills,
            'location': location,
            'projects': projects,
        },
    )


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

    if not job.accepts_applications:
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
        status=ApplicationStatus.APPLIED,
    )

    messages.success(request, f'Application sent for {job.title}.')
    return redirect('my_applications')


@job_seeker_required
def my_applications(request):
    """Job Seeker view: track each application through hiring stages."""
    applications = (
        JobApplication.objects.filter(applicant=request.user)
        .select_related('job')
        .order_by('-applied_at')
    )
    # Position of each application's stage, so the stepper can mark earlier stages done.
    for app in applications:
        app.stage_index = ApplicationStatus.values.index(app.status)
    return render(
        request,
        'jobs/my_applications.html',
        {
            'applications': applications,
            'status_pipeline': ApplicationStatus.choices,
            'status_breakdown': _status_breakdown(applications),
        },
    )


def _visible_jobs(user):
    """Admins see every posting's applications; recruiters only their own postings'."""
    return Job.objects.all() if user.is_superuser else Job.objects.filter(posted_by=user)


@recruiter_or_admin_required
def application_list(request):
    visible_jobs = _visible_jobs(request.user)
    applications = JobApplication.objects.filter(job__in=visible_jobs).select_related(
        'job',
        'job__posted_by',
        'applicant',
        'applicant__candidate_profile',
    ).order_by('-applied_at')

    job = None
    job_id = request.GET.get('job')
    if job_id and job_id.isdigit():
        job = get_object_or_404(visible_jobs, pk=job_id)
        applications = applications.filter(job=job)

    return render(
        request,
        'jobs/application_list.html',
        {'applications': applications, 'job': job},
    )


@recruiter_or_admin_required
def review_application(request, application_id):
    application = get_object_or_404(
        JobApplication.objects.select_related(
            'job',
            'applicant',
            'applicant__candidate_profile',
        ),
        pk=application_id,
        job__in=_visible_jobs(request.user),
    )
    # Admins can view any application, but only the posting's recruiter moves it through hiring.
    can_update_status = application.job.posted_by_id == request.user.pk

    if request.method == 'POST' and not can_update_status:
        messages.error(request, "Only the posting's recruiter can change the application status.")
        return redirect('review_application', application_id=application.pk)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ApplicationStatus.values:
            application.status = new_status
            application.save(update_fields=['status', 'status_updated_at'])
            messages.success(
                request,
                f'Status updated to {application.get_status_display()}.',
            )
            return redirect('review_application', application_id=application.pk)
        messages.error(request, 'Invalid application status.')

    candidate = application.applicant
    candidate_profile = getattr(candidate, 'candidate_profile', None)
    other_applications = (
        candidate.job_applications.filter(job__in=_visible_jobs(request.user))
        .exclude(pk=application.pk)
        .select_related('job')
    )
    return render(
        request,
        'jobs/review_application.html',
        {
            'application': application,
            'candidate': candidate,
            'candidate_profile': candidate_profile,
            'other_applications': other_applications,
            'statuses': ApplicationStatus.choices,
            'can_update_status': can_update_status,
        },
    )


@recruiter_required
def hiring_pipeline(request):
    """Kanban board of applicants for jobs this recruiter posted."""
    owned_jobs = Job.objects.filter(posted_by=request.user).order_by('-posted_at')
    applications = (
        JobApplication.objects.filter(job__posted_by=request.user)
        .select_related('job', 'applicant', 'applicant__candidate_profile')
        .order_by('-applied_at')
    )

    selected_job = None
    job_id = request.GET.get('job', '').strip()
    if job_id.isdigit():
        selected_job = get_object_or_404(Job, pk=job_id, posted_by=request.user)
        applications = applications.filter(job=selected_job)

    columns = []
    for value, label in ApplicationStatus.choices:
        columns.append(
            {
                'value': value,
                'label': label,
                'applications': [app for app in applications if app.status == value],
            }
        )

    return render(
        request,
        'jobs/pipeline.html',
        {
            'columns': columns,
            'owned_jobs': owned_jobs,
            'selected_job': selected_job,
            'status_values': ApplicationStatus.values,
        },
    )


@recruiter_required
@require_POST
def update_pipeline_status(request, application_id):
    """JSON endpoint used by Kanban drag-and-drop."""
    application = get_object_or_404(
        JobApplication.objects.select_related('job'),
        pk=application_id,
        job__posted_by=request.user,
    )
    new_status = request.POST.get('status')
    if new_status not in ApplicationStatus.values:
        return JsonResponse({'ok': False, 'error': 'Invalid status.'}, status=400)

    application.status = new_status
    application.save(update_fields=['status', 'status_updated_at'])
    return JsonResponse(
        {
            'ok': True,
            'application_id': application.pk,
            'status': application.status,
            'status_label': application.get_status_display(),
        }
    )


def job_detail(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    # Hidden postings are only visible to admins and the recruiter who posted them.
    if job.is_hidden and not (request.user.is_superuser or job.posted_by_id == request.user.pk):
        raise Http404
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
    is_owner = is_recruiter and job.posted_by_id == request.user.pk
    can_review_applicants = is_owner or request.user.is_superuser
    already_applied = False
    application_status = None
    if request.user.is_authenticated:
        existing = JobApplication.objects.filter(
            job=job,
            applicant=request.user,
        ).first()
        if existing:
            already_applied = True
            application_status = existing.get_status_display()

    return render(
        request,
        'jobs/job_detail.html',
        {
            'job': job,
            'is_job_seeker': is_job_seeker,
            'is_recruiter': is_recruiter,
            'application_count': job.applications.count() if can_review_applicants else None,
            'is_owner': is_owner,
            'can_review_applicants': can_review_applicants,
            'already_applied': already_applied,
            'application_status': application_status,
        },
    )
