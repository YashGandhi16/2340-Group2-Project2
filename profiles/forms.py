from django import forms
from .models import CandidateProfile
class CandidateProfileForm(forms.ModelForm):
	class Meta:
		model = CandidateProfile
		fields = ('headline', 'skills', 'education', 'work_experience', 'linkedin_url', 'github_url', 'portfolio_url')
		widgets = {'skills': forms.Textarea(attrs={'rows': 3}), 'education': forms.Textarea(attrs={'rows': 4}), 'work_experience': forms.Textarea(attrs={'rows': 5}),}
from django import forms

from .models import CandidateProfile


class CandidateProfileForm(forms.ModelForm):
	class Meta:
		model = CandidateProfile
		fields = (
			'headline',
			'skills',
			'education',
			'work_experience',
			'linkedin_url',
			'github_url',
			'portfolio_url',
		)
		widgets = {
			'skills': forms.Textarea(attrs={'rows': 3}),
			'education': forms.Textarea(attrs={'rows': 4}),
			'work_experience': forms.Textarea(attrs={'rows': 5}),
		}
