from django.conf import settings
from django.db import models


class CandidateProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='candidate_profile',
    )
    headline = models.CharField(max_length=200, blank=True)
    skills = models.TextField(blank=True, help_text='Comma-separated or free-form skills.')
    summary = models.TextField(blank=True, help_text='Experience and background.')
    location = models.CharField(max_length=200, blank=True)
    education = models.TextField(blank=True)
    work_experience = models.TextField(blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)

    #privacy settings
    show_headline = models.BooleanField(default=True)
    show_skills = models.BooleanField(default=True)
    show_summary = models.BooleanField(default=True)
    show_location = models.BooleanField(default=True)
    show_education = models.BooleanField(default=True)
    show_work_experience = models.BooleanField(default=True)
    show_linkedin = models.BooleanField(default=True)
    show_github = models.BooleanField(default=True)
    show_portfolio = models.BooleanField(default=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile for {self.user.username}'

    @property
    def skill_list(self):
        return [s.strip() for s in self.skills.split(',') if s.strip()]

    @property
    def links(self):
        return [
            (label, url)
            for label, url in (
                ('LinkedIn', self.linkedin_url),
                ('GitHub', self.github_url),
                ('Portfolio', self.portfolio_url),
            )
            if url
        ]

    @property
    def is_empty(self):
        return not any(
            (
                self.headline,
                self.skills,
                self.summary,
                self.location,
                self.education,
                self.work_experience,
                self.linkedin_url,
                self.github_url,
                self.portfolio_url,
            )
        )
