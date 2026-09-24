from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.views import job_seeker_required

from .forms import CandidateProfileForm
from .models import CandidateProfile


@job_seeker_required
def profile(request):
	candidate_profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
	form = CandidateProfileForm(request.POST or None, instance=candidate_profile)

	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, 'Your profile has been saved.')
		return redirect('profile')

	return render(request, 'profiles/profile_form.html', {'form': form})
