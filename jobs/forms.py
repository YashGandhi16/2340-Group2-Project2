from django import forms
from django.utils import timezone

from .models import Job


class JobPostingForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['company', 'title', 'location', 'description', 'requirements', 'closing_date']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 6, 'cols': 60}),
            'requirements': forms.Textarea(
                attrs={
                    'rows': 4,
                    'cols': 60,
                    'placeholder': 'e.g. 2+ years of Python, B.S. in CS, US work authorization',
                }
            ),
            'closing_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Every posting field is mandatory, even though older rows may have blanks.
        for field in self.fields.values():
            field.required = True

    def clean_closing_date(self):
        closing_date = self.cleaned_data['closing_date']
        changed = 'closing_date' in self.changed_data
        if changed and closing_date < timezone.localdate():
            raise forms.ValidationError('Closing date cannot be in the past.')
        return closing_date
