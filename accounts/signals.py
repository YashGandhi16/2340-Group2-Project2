from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile, Role


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    default_role = Role.ADMIN if instance.is_superuser else Role.JOB_SEEKER
    if created:
        Profile.objects.create(user=instance, role=default_role)
        return

    profile, _ = Profile.objects.get_or_create(user=instance, defaults={'role': default_role})

    # Keep the role in step when the superuser flag is changed elsewhere
    # (e.g. `createsuperuser` or Django's built-in admin site).
    if instance.is_superuser and profile.role != Role.ADMIN:
        profile.role = Role.ADMIN
        profile.save()
    elif not instance.is_superuser and profile.role == Role.ADMIN:
        profile.role = Role.JOB_SEEKER
        profile.save()
