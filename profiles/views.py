from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.views import job_seeker_required

from .forms import CandidateProfileForm
from .models import CandidateProfile


# Profile sections shown in the completeness checklist, in the order recruiters read them.
PROFILE_CHECKLIST = (
	('headline', 'Headline'),
	('location', 'Location'),
	('skills', 'Skills'),
	('summary', 'Summary'),
	('work_experience', 'Work experience'),
	('education', 'Education'),
	('linkedin_url', 'LinkedIn'),
	('github_url', 'GitHub'),
	('portfolio_url', 'Portfolio'),
)


@job_seeker_required
def profile(request):
	candidate_profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
	form = CandidateProfileForm(request.POST or None, instance=candidate_profile)

	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, 'Your profile has been saved.')
		return redirect('profile')

	checklist = [
		(label, bool(getattr(candidate_profile, field)))
		for field, label in PROFILE_CHECKLIST
	]
	done = sum(1 for _, filled in checklist if filled)
	return render(
		request,
		'profiles/profile_form.html',
		{
			'form': form,
			'candidate_profile': candidate_profile,
			'checklist': checklist,
			'completeness': round(done * 100 / len(checklist)),
		},
	)
