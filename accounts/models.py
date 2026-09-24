from django.conf import settings
from django.db import models


class Role(models.TextChoices):
    JOB_SEEKER = 'JOB_SEEKER', 'Job Seeker'
    RECRUITER = 'RECRUITER', 'Recruiter'
    ADMIN = 'ADMIN', 'Administrator'


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.JOB_SEEKER,
    )

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # The Administrator role and Django's superuser/staff flags are kept in sync,
        # so promoting a user to Admin grants dashboard access and demoting revokes it.
        is_admin = self.role == Role.ADMIN
        user = self.user
        if user.is_superuser != is_admin or user.is_staff != is_admin:
            user.is_superuser = is_admin
            user.is_staff = is_admin
            user.save(update_fields=['is_superuser', 'is_staff'])

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def is_recruiter(self):
        return self.role == Role.RECRUITER

    @property
    def is_job_seeker(self):
        return self.role == Role.JOB_SEEKER
