from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Role

User = get_user_model()


def administrator_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        if profile is None or not profile.is_admin:
            messages.error(request, 'Administrator access required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)

    return _wrapped


def job_seeker_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        if profile is None or profile.role != Role.JOB_SEEKER:
            messages.error(request, 'Job Seeker access required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)

    return _wrapped


@administrator_required
def manage_users(request):
    users = User.objects.select_related('profile').order_by('username')

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('role')
        set_active = request.POST.get('is_active')

        target = get_object_or_404(User.objects.select_related('profile'), pk=user_id)

        if target == request.user and new_role != Role.ADMIN:
            messages.error(request, 'You cannot remove your own Administrator role.')
            return redirect('manage_users')

        if target == request.user and set_active == '0':
            messages.error(request, 'You cannot deactivate your own account.')
            return redirect('manage_users')

        if new_role in Role.values:
            target.profile.role = new_role
            target.profile.save()

        if set_active in ('0', '1'):
            target.is_active = set_active == '1'
            target.save()

        messages.success(request, f'Updated {target.username}.')
        return redirect('manage_users')

    return render(
        request,
        'accounts/manage_users.html',
        {
            'users': users,
            'roles': Role.choices,
        },
    )
