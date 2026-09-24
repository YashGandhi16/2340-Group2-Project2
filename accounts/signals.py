from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile, Role


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        role = Role.ADMIN if instance.is_superuser else Role.JOB_SEEKER
        Profile.objects.create(user=instance, role=role)
    else:
        Profile.objects.get_or_create(
            user=instance,
            defaults={
                'role': Role.ADMIN if instance.is_superuser else Role.JOB_SEEKER,
            },
        )
