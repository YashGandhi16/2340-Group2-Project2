from django import forms
from .models import CandidateProfile


class PrivacySettingsForm(forms.ModelForm):
    class Meta:
        model = CandidateProfile
        fields = [
            'show_headline',
            'show_skills',
            'show_summary',
            'show_location',
            'show_education',
            'show_work_experience',
            'show_linkedin',
            'show_github',
            'show_portfolio',
        ]

        labels = {
            'show_headline': 'Show my headline',
            'show_skills': 'Show my skills',
            'show_summary': 'Show my summary',
            'show_location': 'Show my location',
            'show_education': 'Show my education',
            'show_work_experience': 'Show my work experience',
            'show_linkedin': 'Show my LinkedIn',
            'show_github': 'Show my GitHub',
            'show_portfolio': 'Show my portfolio',
        }