from django import forms

from .models import Message


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['body']
        labels = {'body': 'Message'}
        widgets = {'body': forms.Textarea(attrs={'rows': 4, 'cols': 60})}
        # Django strips whitespace first, so a whitespace-only message also hits this.
        error_messages = {'body': {'required': 'Message cannot be empty.'}}
