from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Role
from accounts.views import recruiter_required

from .forms import MessageForm
from .models import Conversation, Message

User = get_user_model()


def _send(conversation, sender, body):
    Message.objects.create(conversation=conversation, sender=sender, body=body)
    # Bump updated_at so the thread moves to the top of both inboxes.
    conversation.save(update_fields=['updated_at'])


@login_required
def inbox(request):
    conversations = (
        Conversation.for_user(request.user)
        .select_related('recruiter', 'candidate')
        .annotate(
            unread_count=Count(
                'messages',
                filter=Q(messages__read_at__isnull=True) & ~Q(messages__sender=request.user),
            )
        )
    )
    threads = [
        {
            'conversation': c,
            'other': c.other_participant(request.user),
            'last_message': c.messages.order_by('-sent_at').first(),
            'unread_count': c.unread_count,
        }
        for c in conversations
    ]
    return render(request, 'messaging/inbox.html', {'threads': threads})


@recruiter_required
def start_conversation(request, candidate_id):
    candidate = get_object_or_404(
        User.objects.select_related('profile'),
        pk=candidate_id,
        is_active=True,
        profile__role=Role.JOB_SEEKER,
    )

    # One thread per recruiter/candidate pair: reuse it if it already exists.
    existing = Conversation.objects.filter(recruiter=request.user, candidate=candidate).first()
    if existing:
        return redirect('messaging:conversation_detail', conversation_id=existing.pk)

    form = MessageForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        conversation = Conversation.objects.create(recruiter=request.user, candidate=candidate)
        _send(conversation, request.user, form.cleaned_data['body'])
        messages.success(request, f'Message sent to {candidate.username}.')
        return redirect('messaging:conversation_detail', conversation_id=conversation.pk)

    return render(
        request,
        'messaging/start_conversation.html',
        {'form': form, 'candidate': candidate},
    )


@login_required
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(
        Conversation.objects.select_related('recruiter', 'candidate'),
        pk=conversation_id,
    )
    if not conversation.has_participant(request.user):
        raise Http404

    form = MessageForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        _send(conversation, request.user, form.cleaned_data['body'])
        return redirect('messaging:conversation_detail', conversation_id=conversation.pk)

    conversation.messages.filter(read_at__isnull=True).exclude(sender=request.user).update(
        read_at=timezone.now()
    )

    return render(
        request,
        'messaging/conversation_detail.html',
        {
            'conversation': conversation,
            'other': conversation.other_participant(request.user),
            'thread': conversation.messages.select_related('sender'),
            'form': form,
        },
    )
