from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class JobQuerySet(models.QuerySet):
    def open(self):
        """Postings that are still accepting applications (closing date today or later)."""
        today = timezone.localdate()
        return self.filter(Q(closing_date__gte=today) | Q(closing_date__isnull=True))


class Job(models.Model):
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='job_postings',
    )
    title = models.CharField('position', max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200, default='')
    description = models.TextField('job description')
    requirements = models.TextField('applicant criteria', default='')
    # Nullable only so postings created before this field existed stay valid;
    # the posting form always requires it.
    closing_date = models.DateField(null=True)
    posted_at = models.DateTimeField(auto_now_add=True)

    objects = JobQuerySet.as_manager()

    class Meta:
        ordering = ['-posted_at']

    def __str__(self):
        return f'{self.title} at {self.company}'

    @property
    def is_open(self):
        return self.closing_date is None or self.closing_date >= timezone.localdate()


class ApplicationStatus(models.TextChoices):
    APPLIED = 'APPLIED', 'Applied'
    REVIEW = 'REVIEW', 'Review'
    INTERVIEW = 'INTERVIEW', 'Interview'
    OFFER = 'OFFER', 'Offer'
    CLOSED = 'CLOSED', 'Closed'


class JobApplication(models.Model):
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='applications',
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_applications',
    )
    note = models.TextField(help_text='Personalized message for the recruiter.')
    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.APPLIED,
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    status_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['job', 'applicant'],
                name='unique_application_per_job',
            ),
        ]
        ordering = ['-applied_at']

    def __str__(self):
        return f'{self.applicant.username} → {self.job} ({self.get_status_display()})'

    @property
    def status_pipeline(self):
        """Ordered stages for seeker tracking UI (current stage highlighted in templates)."""
        return list(ApplicationStatus.choices)
