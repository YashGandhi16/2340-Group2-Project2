from django.conf import settings
from django.db import models
from django.db.models import Q


class Conversation(models.Model):
    """A private thread between one recruiter and one candidate."""

    recruiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recruiter_conversations',
    )
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='candidate_conversations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recruiter', 'candidate'],
                name='unique_conversation_per_pair',
            ),
        ]
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.recruiter.username} ↔ {self.candidate.username}'

    @classmethod
    def for_user(cls, user):
        return cls.objects.filter(Q(recruiter=user) | Q(candidate=user))

    def has_participant(self, user):
        return user.pk in (self.recruiter_id, self.candidate_id)

    def other_participant(self, user):
        return self.candidate if user.pk == self.recruiter_id else self.recruiter


class MessageQuerySet(models.QuerySet):
    def unread_for(self, user):
        """Messages sent to `user` that they haven't opened yet."""
        return self.filter(
            Q(conversation__recruiter=user) | Q(conversation__candidate=user),
            read_at__isnull=True,
        ).exclude(sender=user)


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
    )
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    objects = MessageQuerySet.as_manager()

    class Meta:
        ordering = ['sent_at']

    def __str__(self):
        return f'{self.sender.username}: {self.body[:40]}'
