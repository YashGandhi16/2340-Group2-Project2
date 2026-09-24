"""Tests for account creation and logout.

LogoutTests  - the home page log out button
SignUpTests  - public signup form: success and validation errors
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Role


class LogoutTests(TestCase):
    """Logging out from the home page."""

    def test_home_logout_button_logs_user_out(self):
        """Home page shows a POST log out form, and submitting it ends the session."""
        get_user_model().objects.create_user(username='u', password='pass12345')
        self.client.login(username='u', password='pass12345')
        home = self.client.get(reverse('home'))
        self.assertContains(home, f'action="{reverse("logout")}"')

        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)


class SignUpTests(TestCase):
    """Creating an account through /accounts/signup/."""

    def signup(self, **overrides):
        data = {
            'username': 'newbie',
            'email': 'newbie@example.com',
            'password1': 'S3cure-pass-123',
            'password2': 'S3cure-pass-123',
        }
        data.update(overrides)
        return self.client.post(reverse('signup'), data)

    def test_signup_creates_job_seeker_and_logs_in(self):
        """Valid signup creates a Job Seeker (not superuser) and logs them in."""
        response = self.signup()
        self.assertRedirects(response, reverse('login_redirect'), target_status_code=302)
        user = get_user_model().objects.get(username='newbie')
        self.assertEqual(user.email, 'newbie@example.com')
        self.assertEqual(user.profile.role, Role.JOB_SEEKER)
        self.assertFalse(user.is_superuser)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_mismatched_passwords_rejected(self):
        """Edge case: the two password fields differ, so no account is created."""
        response = self.signup(password2='different-pass-456')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username='newbie').exists())

    def test_duplicate_email_rejected(self):
        """Edge case: an email already in use (any capitalization) is rejected."""
        get_user_model().objects.create_user(username='old', email='newbie@example.com', password='x')
        response = self.signup(email='NEWBIE@example.com')
        self.assertContains(response, 'An account with this email already exists.')
        self.assertFalse(get_user_model().objects.filter(username='newbie').exists())

    def test_logged_in_user_redirected_away(self):
        """Edge case: a logged-in user opening signup is redirected instead."""
        get_user_model().objects.create_user(username='u', password='pass12345')
        self.client.login(username='u', password='pass12345')
        response = self.client.get(reverse('signup'))
        self.assertRedirects(response, reverse('login_redirect'), target_status_code=302)
