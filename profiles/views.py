from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import PrivacySettingsForm
from .models import CandidateProfile


@login_required
def privacy_settings(request):
    profile, created = CandidateProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == 'POST':
        form = PrivacySettingsForm(request.POST, instance=profile)

        if form.is_valid():
            form.save()
            messages.success(request, 'Your privacy settings have been saved.')
            return redirect('privacy_settings')
    else:
        form = PrivacySettingsForm(instance=profile)

    return render(
        request,
        'profiles/privacy_settings.html',
        {'form': form},
    )