"""Tests for the admin dashboard and role state.

RoleStateTests         - how a user's role and Django's superuser flag stay in sync
DashboardAccessTests   - who can open the dashboard and what it shows
DashboardUpdateTests   - changing roles / active status from the dashboard
LoginRedirectTests     - where each role lands right after logging in
JobModerationTests     - admins listing, hiding/restoring, editing, and deleting job postings
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from jobs.models import Job, JobApplication

User = get_user_model()


class RoleStateTests(TestCase):
    """A user's role and the superuser/staff flags always agree."""

    def test_superuser_starts_as_admin(self):
        """createsuperuser gives the account the Administrator role."""
        admin = User.objects.create_superuser(username='boss', password='pass12345')
        self.assertEqual(admin.profile.role, Role.ADMIN)

    def test_new_user_starts_as_job_seeker(self):
        """A normal new account defaults to Job Seeker and is not a superuser."""
        user = User.objects.create_user(username='new', password='pass12345')
        self.assertEqual(user.profile.role, Role.JOB_SEEKER)
        self.assertFalse(user.is_superuser)

    def test_admin_role_grants_and_revokes_superuser(self):
        """Setting role to Admin makes the user a superuser; changing it away removes that."""
        user = User.objects.create_user(username='u', password='pass12345')
        user.profile.role = Role.ADMIN
        user.profile.save()
        user.refresh_from_db()
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

        user.profile.role = Role.RECRUITER
        user.profile.save()
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)

    def test_clearing_superuser_flag_demotes_role(self):
        """Unticking superuser elsewhere (e.g. Django admin site) drops the Admin role."""
        admin = User.objects.create_superuser(username='boss', password='pass12345')
        admin.is_superuser = False
        admin.save()
        admin.profile.refresh_from_db()
        self.assertEqual(admin.profile.role, Role.JOB_SEEKER)


class DashboardAccessTests(TestCase):
    """Only superusers can view the dashboard."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username='boss', password='pass12345')
        self.recruiter = User.objects.create_user(username='rec', password='pass12345')
        self.recruiter.profile.role = Role.RECRUITER
        self.recruiter.profile.save()
        self.seeker = User.objects.create_user(username='seeker', password='pass12345')
        self.url = reverse('admin_dashboard:dashboard')

    def test_anonymous_redirected_to_login(self):
        """A logged-out visitor is sent to the login page."""
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_non_admin_roles_blocked(self):
        """Recruiters and Job Seekers are bounced back to the home page."""
        for username in ('rec', 'seeker'):
            self.client.login(username=username, password='pass12345')
            self.assertRedirects(self.client.get(self.url), reverse('home'))

    def test_admin_sees_all_accounts_and_roles(self):
        """Admin sees every account and correct per-role counts."""
        self.client.login(username='boss', password='pass12345')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['users']), 3)
        counts = {value: count for value, _, count in response.context['role_counts']}
        self.assertEqual(counts, {Role.JOB_SEEKER: 1, Role.RECRUITER: 1, Role.ADMIN: 1})

    def test_filter_by_role(self):
        """The ?role= filter shows only users with that role."""
        self.client.login(username='boss', password='pass12345')
        response = self.client.get(self.url, {'role': Role.RECRUITER})
        self.assertEqual([u.username for u in response.context['users']], ['rec'])


class DashboardUpdateTests(TestCase):
    """Admins changing other users from the dashboard."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username='boss', password='pass12345')
        self.seeker = User.objects.create_user(username='seeker', password='pass12345')
        self.client.login(username='boss', password='pass12345')

    def post(self, user, **data):
        return self.client.post(reverse('admin_dashboard:update_user', args=[user.pk]), data)

    def test_admin_changes_role(self):
        """Admin can switch a Job Seeker to Recruiter."""
        self.post(self.seeker, role=Role.RECRUITER, is_active='1')
        self.seeker.refresh_from_db()
        self.assertEqual(self.seeker.profile.role, Role.RECRUITER)

    def test_promote_to_admin_grants_dashboard(self):
        """Promoting a user to Admin lets that user open the dashboard."""
        self.post(self.seeker, role=Role.ADMIN, is_active='1')
        self.seeker.refresh_from_db()
        self.assertTrue(self.seeker.is_superuser)
        other = Client()
        other.login(username='seeker', password='pass12345')
        self.assertEqual(other.get(reverse('admin_dashboard:dashboard')).status_code, 200)

    def test_deactivate_user(self):
        """Admin can mark an account inactive."""
        self.post(self.seeker, role=Role.JOB_SEEKER, is_active='0')
        self.seeker.refresh_from_db()
        self.assertFalse(self.seeker.is_active)

    def test_cannot_demote_or_deactivate_self(self):
        """Edge case: an admin cannot remove their own Admin role or deactivate themselves."""
        self.post(self.admin, role=Role.JOB_SEEKER, is_active='1')
        self.post(self.admin, role=Role.ADMIN, is_active='0')
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.profile.role, Role.ADMIN)
        self.assertTrue(self.admin.is_active)

    def test_get_not_allowed(self):
        """Edge case: the update URL rejects GET requests (405); changes must be POSTed."""
        response = self.client.get(reverse('admin_dashboard:update_user', args=[self.seeker.pk]))
        self.assertEqual(response.status_code, 405)


class LoginRedirectTests(TestCase):
    """Role-based landing page after login."""

    def login(self, username):
        return self.client.post(
            reverse('login'), {'username': username, 'password': 'pass12345'}, follow=True
        )

    def test_each_role_lands_on_its_page(self):
        """Admin -> dashboard, Recruiter -> recruiter dashboard, Job Seeker -> job list."""
        User.objects.create_superuser(username='boss', password='pass12345')
        rec = User.objects.create_user(username='rec', password='pass12345')
        rec.profile.role = Role.RECRUITER
        rec.profile.save()
        User.objects.create_user(username='seeker', password='pass12345')

        expected = {
            'boss': reverse('admin_dashboard:dashboard'),
            'rec': reverse('recruiter_dashboard'),
            'seeker': reverse('job_list'),
        }
        for username, url in expected.items():
            self.client.logout()
            response = self.login(username)
            self.assertEqual(response.redirect_chain[-1][0], url)


class JobModerationTests(TestCase):
    """Admins moderating, editing, and deleting any recruiter's job postings."""

    def setUp(self):
        self.admin = User.objects.create_superuser(username='boss', password='pass12345')
        self.recruiter = User.objects.create_user(username='rec', password='pass12345')
        self.recruiter.profile.role = Role.RECRUITER
        self.recruiter.profile.save()
        self.seeker = User.objects.create_user(username='seeker', password='pass12345')
        self.job = Job.objects.create(
            title='Data Analyst', company='Acme', location='Atlanta', description='Analyze.',
            requirements='SQL', closing_date=timezone.localdate() + timedelta(days=10),
            posted_by=self.recruiter,
        )
        self.application = JobApplication.objects.create(
            job=self.job, applicant=self.seeker, note='Hire me.'
        )
        self.client.login(username='boss', password='pass12345')

    def hide(self, reason='Spam posting'):
        return self.client.post(
            reverse('admin_dashboard:moderate_job', args=[self.job.pk]),
            {'action': 'hide', 'reason': reason},
        )

    def test_admin_sees_all_postings(self):
        """The moderation page lists postings from every recruiter."""
        other = User.objects.create_user(username='rec2', password='pass12345')
        other.profile.role = Role.RECRUITER
        other.profile.save()
        Job.objects.create(title='Other', company='B', description='d', posted_by=other)
        response = self.client.get(reverse('admin_dashboard:job_list'))
        self.assertEqual({j.title for j in response.context['jobs']}, {'Data Analyst', 'Other'})

    def test_non_admins_blocked(self):
        """Recruiters and Job Seekers cannot open any moderation page or action."""
        urls = [
            reverse('admin_dashboard:job_list'),
            reverse('admin_dashboard:edit_job', args=[self.job.pk]),
            reverse('admin_dashboard:delete_job', args=[self.job.pk]),
        ]
        for username in ('rec', 'seeker'):
            self.client.login(username=username, password='pass12345')
            for url in urls:
                self.assertRedirects(self.client.get(url), reverse('home'))
            self.hide()
            self.client.post(reverse('admin_dashboard:delete_job', args=[self.job.pk]))
        self.job.refresh_from_db()
        self.assertFalse(self.job.is_hidden)

    def test_hide_removes_from_search_and_blocks_applying(self):
        """A hidden posting disappears from job search, its page 404s, and new applications are blocked."""
        self.hide()
        self.job.refresh_from_db()
        self.assertTrue(self.job.is_hidden)
        self.assertEqual(self.job.moderation_note, 'Spam posting')

        newbie = User.objects.create_user(username='newbie', password='pass12345')
        self.client.login(username='newbie', password='pass12345')
        self.assertNotIn(self.job, self.client.get(reverse('job_list')).context['jobs'])
        self.assertEqual(self.client.get(reverse('job_detail', args=[self.job.pk])).status_code, 404)
        self.client.post(reverse('apply_to_job', args=[self.job.pk]), {'note': 'Please'})
        self.assertFalse(JobApplication.objects.filter(applicant=newbie).exists())

    def test_hide_keeps_existing_applications(self):
        """Hiding does not delete applications that were already submitted."""
        self.hide()
        self.assertTrue(JobApplication.objects.filter(pk=self.application.pk).exists())

    def test_recruiter_sees_hidden_reason(self):
        """The posting's recruiter still sees it, marked hidden with the admin's reason."""
        self.hide('Missing salary info')
        self.client.login(username='rec', password='pass12345')
        self.assertContains(self.client.get(reverse('recruiter_dashboard')), 'Missing salary info')
        self.assertContains(
            self.client.get(reverse('job_detail', args=[self.job.pk])), 'Hidden by an administrator'
        )

    def test_hide_requires_reason(self):
        """Edge case: hiding without a reason is rejected and the posting stays visible."""
        self.hide(reason='   ')
        self.job.refresh_from_db()
        self.assertFalse(self.job.is_hidden)

    def test_restore_makes_posting_visible_again(self):
        """Restoring a hidden posting puts it back in job search and clears the reason."""
        self.hide()
        self.client.post(
            reverse('admin_dashboard:moderate_job', args=[self.job.pk]), {'action': 'restore'}
        )
        self.job.refresh_from_db()
        self.assertFalse(self.job.is_hidden)
        self.assertEqual(self.job.moderation_note, '')
        self.assertContains(self.client.get(reverse('job_list')), 'Data Analyst')

    def test_moderate_rejects_get(self):
        """Edge case: the moderate URL only accepts POST (405 on GET)."""
        url = reverse('admin_dashboard:moderate_job', args=[self.job.pk])
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_filter_by_status(self):
        """The status filter separates open, closed, and hidden postings."""
        Job.objects.create(
            title='Old role', company='B', description='d',
            closing_date=timezone.localdate() - timedelta(days=1),
        )
        Job.objects.create(title='Removed role', company='C', description='d', is_hidden=True)
        url = reverse('admin_dashboard:job_list')
        titles = lambda status: [j.title for j in self.client.get(url, {'status': status}).context['jobs']]
        self.assertEqual(titles('open'), ['Data Analyst'])
        self.assertEqual(titles('closed'), ['Old role'])
        self.assertEqual(titles('hidden'), ['Removed role'])

    def test_admin_edits_any_posting(self):
        """An admin can edit another recruiter's posting; the recruiter stays the owner."""
        data = {
            'company': 'Acme', 'title': 'Senior Data Analyst', 'location': 'Remote',
            'description': 'Analyze.', 'requirements': 'SQL',
            'closing_date': self.job.closing_date.isoformat(),
        }
        response = self.client.post(reverse('admin_dashboard:edit_job', args=[self.job.pk]), data)
        self.assertRedirects(response, reverse('admin_dashboard:job_list'))
        self.job.refresh_from_db()
        self.assertEqual((self.job.title, self.job.location), ('Senior Data Analyst', 'Remote'))
        self.assertEqual(self.job.posted_by, self.recruiter)

    def test_admin_edit_validates_fields(self):
        """Edge case: admin edits follow the same rules (no blank fields)."""
        data = {'company': '', 'title': 'X', 'location': 'Y', 'description': 'Z',
                'requirements': 'R', 'closing_date': self.job.closing_date.isoformat()}
        response = self.client.post(reverse('admin_dashboard:edit_job', args=[self.job.pk]), data)
        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertEqual(self.job.company, 'Acme')

    def test_delete_needs_confirmation(self):
        """Opening delete shows a confirmation with the applications count; nothing is deleted yet."""
        response = self.client.get(reverse('admin_dashboard:delete_job', args=[self.job.pk]))
        self.assertContains(response, 'This also deletes 1 application')
        self.assertTrue(Job.objects.filter(pk=self.job.pk).exists())

    def test_confirmed_delete_removes_posting_and_applications(self):
        """Confirming delete removes the posting and its applications."""
        response = self.client.post(reverse('admin_dashboard:delete_job', args=[self.job.pk]))
        self.assertRedirects(response, reverse('admin_dashboard:job_list'))
        self.assertFalse(Job.objects.filter(pk=self.job.pk).exists())
        self.assertFalse(JobApplication.objects.filter(pk=self.application.pk).exists())

    def test_missing_posting_404(self):
        """Edge case: acting on a posting id that does not exist returns 404."""
        for name in ('edit_job', 'delete_job'):
            self.assertEqual(
                self.client.get(reverse(f'admin_dashboard:{name}', args=[9999])).status_code, 404
            )
