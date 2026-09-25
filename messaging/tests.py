"""Tests for in-platform messaging between recruiters and candidates.

StartConversationTests   - who can start a conversation, and with whom
ConversationThreadTests  - viewing and replying to a thread, privacy between users
UnreadTrackingTests      - unread counts and marking messages as read
EntryPointTests          - "Message" links on recruiter pages
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role

from .models import Conversation, Message

User = get_user_model()


def make_user(username, role=Role.JOB_SEEKER, **extra):
    user = User.objects.create_user(username=username, password='pass12345', **extra)
    if role != Role.JOB_SEEKER:
        user.profile.role = role
        user.profile.save()
    return user


class StartConversationTests(TestCase):
    """Recruiters opening a new conversation with a candidate."""

    def setUp(self):
        self.recruiter = make_user('rec', Role.RECRUITER)
        self.candidate = make_user('cand', email='cand@private.example.com')
        self.url = reverse('messaging:start_conversation', args=[self.candidate.pk])

    def test_recruiter_sends_first_message(self):
        """A recruiter's first message creates a conversation and lands on the thread."""
        self.client.login(username='rec', password='pass12345')
        response = self.client.post(self.url, {'body': 'Hi! Interested in a Python role?'})
        conversation = Conversation.objects.get()
        self.assertRedirects(
            response, reverse('messaging:conversation_detail', args=[conversation.pk])
        )
        self.assertEqual(conversation.recruiter, self.recruiter)
        self.assertEqual(conversation.candidate, self.candidate)
        self.assertEqual(conversation.messages.get().body, 'Hi! Interested in a Python role?')

    def test_existing_conversation_is_reused(self):
        """Messaging the same candidate again reopens the existing thread instead of making a new one."""
        conversation = Conversation.objects.create(recruiter=self.recruiter, candidate=self.candidate)
        self.client.login(username='rec', password='pass12345')
        response = self.client.get(self.url)
        self.assertRedirects(
            response, reverse('messaging:conversation_detail', args=[conversation.pk])
        )
        self.assertEqual(Conversation.objects.count(), 1)

    def test_empty_message_rejected(self):
        """Edge case: a blank or whitespace-only first message is rejected."""
        self.client.login(username='rec', password='pass12345')
        response = self.client.post(self.url, {'body': '   '})
        self.assertContains(response, 'Message cannot be empty.')
        self.assertFalse(Conversation.objects.exists())

    def test_job_seeker_cannot_start_conversation(self):
        """Job Seekers cannot open new conversations; they can only reply."""
        other = make_user('other')
        self.client.login(username='cand', password='pass12345')
        url = reverse('messaging:start_conversation', args=[other.pk])
        self.assertRedirects(self.client.post(url, {'body': 'Hi'}), reverse('home'))
        self.assertFalse(Conversation.objects.exists())

    def test_cannot_message_non_candidates(self):
        """Edge case: recruiters cannot start threads with other recruiters or admins (404)."""
        other_recruiter = make_user('rec2', Role.RECRUITER)
        admin = User.objects.create_superuser(username='boss', password='pass12345')
        self.client.login(username='rec', password='pass12345')
        for target in (other_recruiter, admin, self.recruiter):
            url = reverse('messaging:start_conversation', args=[target.pk])
            self.assertEqual(self.client.post(url, {'body': 'Hi'}).status_code, 404)
        self.assertFalse(Conversation.objects.exists())

    def test_cannot_message_inactive_candidate(self):
        """Edge case: a deactivated candidate account cannot be messaged (404)."""
        self.candidate.is_active = False
        self.candidate.save()
        self.client.login(username='rec', password='pass12345')
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_anonymous_redirected_to_login(self):
        """A logged-out visitor is sent to the login page."""
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")


class ConversationThreadTests(TestCase):
    """Reading and replying inside a conversation."""

    def setUp(self):
        self.recruiter = make_user('rec', Role.RECRUITER, email='rec@private.example.com')
        self.candidate = make_user('cand', email='cand@private.example.com')
        self.conversation = Conversation.objects.create(
            recruiter=self.recruiter, candidate=self.candidate
        )
        Message.objects.create(
            conversation=self.conversation, sender=self.recruiter, body='Are you available Friday?'
        )
        self.url = reverse('messaging:conversation_detail', args=[self.conversation.pk])

    def test_candidate_sees_and_replies(self):
        """The candidate can read the recruiter's message and reply in the same thread."""
        self.client.login(username='cand', password='pass12345')
        self.assertContains(self.client.get(self.url), 'Are you available Friday?')
        self.client.post(self.url, {'body': 'Yes, Friday works.'})
        last = self.conversation.messages.last()
        self.assertEqual((last.sender, last.body), (self.candidate, 'Yes, Friday works.'))

    def test_recruiter_sees_reply(self):
        """The recruiter sees the candidate's reply in the thread."""
        Message.objects.create(conversation=self.conversation, sender=self.candidate, body='Yes!')
        self.client.login(username='rec', password='pass12345')
        self.assertContains(self.client.get(self.url), 'Yes!')

    def test_email_addresses_never_shown(self):
        """Neither side's email address appears in the thread or the inbox."""
        for username in ('rec', 'cand'):
            self.client.login(username=username, password='pass12345')
            for url in (self.url, reverse('messaging:inbox')):
                response = self.client.get(url)
                self.assertNotContains(response, 'private.example.com')

    def test_outsiders_cannot_view_or_post(self):
        """Edge case: another recruiter or candidate gets 404 on someone else's conversation."""
        make_user('rec2', Role.RECRUITER)
        make_user('cand2')
        for username in ('rec2', 'cand2'):
            self.client.login(username=username, password='pass12345')
            self.assertEqual(self.client.get(self.url).status_code, 404)
            self.assertEqual(self.client.post(self.url, {'body': 'sneaky'}).status_code, 404)
        self.assertFalse(Message.objects.filter(body='sneaky').exists())

    def test_empty_reply_rejected(self):
        """Edge case: a blank reply is not sent."""
        self.client.login(username='cand', password='pass12345')
        response = self.client.post(self.url, {'body': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.conversation.messages.count(), 1)

    def test_missing_conversation_404(self):
        """Edge case: a conversation id that does not exist returns 404."""
        self.client.login(username='rec', password='pass12345')
        url = reverse('messaging:conversation_detail', args=[9999])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_inbox_lists_only_own_conversations(self):
        """Each user's inbox shows only conversations they are part of."""
        rec2 = make_user('rec2', Role.RECRUITER)
        cand2 = make_user('cand2')
        Conversation.objects.create(recruiter=rec2, candidate=cand2)
        self.client.login(username='cand', password='pass12345')
        threads = self.client.get(reverse('messaging:inbox')).context['threads']
        self.assertEqual([t['conversation'] for t in threads], [self.conversation])


class UnreadTrackingTests(TestCase):
    """Unread message counts and read receipts."""

    def setUp(self):
        self.recruiter = make_user('rec', Role.RECRUITER)
        self.candidate = make_user('cand')
        self.conversation = Conversation.objects.create(
            recruiter=self.recruiter, candidate=self.candidate
        )
        for body in ('Hello', 'Following up'):
            Message.objects.create(conversation=self.conversation, sender=self.recruiter, body=body)

    def test_unread_count_shown_to_recipient_only(self):
        """The candidate sees 2 new messages; the recruiter who sent them sees none."""
        self.client.login(username='cand', password='pass12345')
        self.assertContains(self.client.get(reverse('home')), 'Messages (2 new)')
        self.client.login(username='rec', password='pass12345')
        self.assertNotContains(self.client.get(reverse('home')), 'new)')

    def test_opening_thread_marks_messages_read(self):
        """Opening the conversation clears the recipient's unread count."""
        self.client.login(username='cand', password='pass12345')
        self.client.get(reverse('messaging:conversation_detail', args=[self.conversation.pk]))
        self.assertFalse(Message.objects.unread_for(self.candidate).exists())
        self.assertNotContains(self.client.get(reverse('home')), 'new)')

    def test_sender_viewing_does_not_mark_read(self):
        """Edge case: the sender reopening the thread does not mark their own messages as read."""
        self.client.login(username='rec', password='pass12345')
        self.client.get(reverse('messaging:conversation_detail', args=[self.conversation.pk]))
        self.assertEqual(Message.objects.unread_for(self.candidate).count(), 2)


class EntryPointTests(TestCase):
    """Where recruiters find the "Message" button."""

    def setUp(self):
        self.recruiter = make_user('rec', Role.RECRUITER)
        self.candidate = make_user('cand')
        self.client.login(username='rec', password='pass12345')

    def test_candidate_search_has_message_link_for_job_seekers_only(self):
        """Search results link to messaging Job Seekers, but not recruiters who also appear."""
        response = self.client.get(reverse('candidate_search'))
        self.assertContains(
            response, reverse('messaging:start_conversation', args=[self.candidate.pk])
        )
        self.assertNotContains(
            response, reverse('messaging:start_conversation', args=[self.recruiter.pk])
        )

    def test_recruiter_dashboard_links_to_inbox(self):
        """The recruiter dashboard links to the Messages inbox."""
        self.assertContains(self.client.get(reverse('recruiter_dashboard')), reverse('messaging:inbox'))
