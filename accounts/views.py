from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import SignUpForm
from .models import Role


def administrator_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, 'Administrator access required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)

    return _wrapped


def recruiter_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        if profile is None or profile.role != Role.RECRUITER:
            messages.error(request, 'Recruiter access required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)

    return _wrapped


def recruiter_or_admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        is_recruiter = profile is not None and profile.role == Role.RECRUITER
        if not (is_recruiter or request.user.is_superuser):
            messages.error(request, 'Recruiter or Administrator access required.')
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


@login_required
def login_redirect(request):
    """Send a freshly logged-in user to the landing page for their role."""
    profile = getattr(request.user, 'profile', None)
    if request.user.is_superuser:
        return redirect('admin_dashboard:dashboard')
    if profile is not None and profile.is_recruiter:
        return redirect('recruiter_dashboard')
    return redirect('job_list')


def signup(request):
    """Public registration. New accounts start as Job Seekers; admins assign other roles."""
    if request.user.is_authenticated:
        return redirect('login_redirect')

    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Welcome, {user.username}! Your account has been created.')
        return redirect('login_redirect')

    return render(request, 'accounts/signup.html', {'form': form})
