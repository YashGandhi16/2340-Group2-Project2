from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Profile, Role
from accounts.views import administrator_required

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
