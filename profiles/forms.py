from django import forms

from .models import CandidateProfile


class CandidateProfileForm(forms.ModelForm):
	class Meta:
		model = CandidateProfile
		fields = (
			'headline',
			'location',
			'skills',
			'summary',
			'education',
			'work_experience',
			'linkedin_url',
			'github_url',
			'portfolio_url',
		)
		widgets = {
			'location': forms.TextInput(attrs={'placeholder': 'e.g. Atlanta, GA or Remote'}),
			'skills': forms.Textarea(attrs={'rows': 3}),
			'summary': forms.Textarea(attrs={'rows': 4}),
			'education': forms.Textarea(attrs={'rows': 4}),
			'work_experience': forms.Textarea(attrs={'rows': 5}),
		}
