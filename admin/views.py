from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Profile, Role
from accounts.views import administrator_required
from jobs.forms import JobPostingForm
from jobs.models import Job

User = get_user_model()


@administrator_required
def dashboard(request):
    users = User.objects.select_related('profile').order_by('username')

    role_filter = request.GET.get('role', '')
    if role_filter in Role.values:
        users = users.filter(profile__role=role_filter)
    else:
        role_filter = ''

    query = request.GET.get('q', '').strip()
    if query:
        users = users.filter(Q(username__icontains=query) | Q(email__icontains=query))

    counts = Profile.objects.aggregate(
        total=Count('pk'),
        **{value: Count('pk', filter=Q(role=value)) for value in Role.values},
    )
    role_counts = [(value, label, counts[value]) for value, label in Role.choices]

    return render(
        request,
        'admin_dashboard/dashboard.html',
        {
            'users': users,
            'roles': Role.choices,
            'role_counts': role_counts,
            'total_users': counts['total'],
            'role_filter': role_filter,
            'query': query,
        },
    )


@administrator_required
@require_POST
def update_user(request, user_id):
    target = get_object_or_404(User.objects.select_related('profile'), pk=user_id)
    new_role = request.POST.get('role')
    set_active = request.POST.get('is_active')

    if target == request.user and new_role != Role.ADMIN:
        messages.error(request, 'You cannot remove your own Administrator role.')
        return redirect('admin_dashboard:dashboard')

    if target == request.user and set_active == '0':
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('admin_dashboard:dashboard')

    if new_role in Role.values:
        target.profile.role = new_role
        target.profile.save()
        target.refresh_from_db()

    if set_active in ('0', '1'):
        target.is_active = set_active == '1'
        target.save(update_fields=['is_active'])

    messages.success(request, f'Updated {target.username}: {target.profile.get_role_display()}.')
    return redirect('admin_dashboard:dashboard')


JOB_STATUS_FILTERS = [
    ('open', 'Open'),
    ('closed', 'Closed'),
    ('hidden', 'Hidden'),
]


@administrator_required
def job_list(request):
    jobs = (
        Job.objects.select_related('posted_by')
        .annotate(application_count=Count('applications'))
        .order_by('-posted_at')
    )

    status = request.GET.get('status', '')
    today = timezone.localdate()
    if status == 'open':
        jobs = jobs.visible().open()
    elif status == 'closed':
        jobs = jobs.visible().filter(closing_date__lt=today)
    elif status == 'hidden':
        jobs = jobs.filter(is_hidden=True)
    else:
        status = ''

    query = request.GET.get('q', '').strip()
    if query:
        jobs = jobs.filter(
            Q(title__icontains=query)
            | Q(company__icontains=query)
            | Q(posted_by__username__icontains=query)
        )

    return render(
        request,
        'admin_dashboard/job_list.html',
        {
            'jobs': jobs,
            'status': status,
            'status_filters': JOB_STATUS_FILTERS,
            'query': query,
        },
    )


@administrator_required
def edit_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    form = JobPostingForm(request.POST or None, instance=job)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Updated {job.title} at {job.company}.')
        return redirect('admin_dashboard:job_list')

    return render(request, 'admin_dashboard/job_form.html', {'form': form, 'job': job})


@administrator_required
@require_POST
def moderate_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    action = request.POST.get('action')

    if action == 'hide':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'Give a reason so the recruiter knows why it was hidden.')
            return redirect('admin_dashboard:job_list')
        job.is_hidden = True
        job.moderation_note = reason
        job.save(update_fields=['is_hidden', 'moderation_note'])
        messages.success(request, f'Hid {job.title} at {job.company}.')
    elif action == 'restore':
        job.is_hidden = False
        job.moderation_note = ''
        job.save(update_fields=['is_hidden', 'moderation_note'])
        messages.success(request, f'Restored {job.title} at {job.company}.')
    else:
        messages.error(request, 'Unknown moderation action.')

    return redirect('admin_dashboard:job_list')


@administrator_required
def delete_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    if request.method == 'POST':
        label = str(job)
        job.delete()
        messages.success(request, f'Deleted {label} and its applications.')
        return redirect('admin_dashboard:job_list')

    return render(
        request,
        'admin_dashboard/job_confirm_delete.html',
        {'job': job, 'application_count': job.applications.count()},
    )
