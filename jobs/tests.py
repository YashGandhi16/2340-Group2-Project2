"""Tests for job postings, search, and applications.

ApplyToJobTests               - Job Seekers applying to a job with a note
ReviewApplicationTests        - recruiters viewing applications (basic access)
ReviewApplicationDetailsTests - recruiters reviewing full candidate details (SCRUM-20)
RecruiterPostingTests         - recruiter dashboard, creating/editing postings, closing dates, search
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role

from .models import Job, JobApplication

User = get_user_model()


class ApplyToJobTests(TestCase):
    """Job Seekers applying to a posting."""

    def setUp(self):
        self.client = Client()
        self.job = Job.objects.create(
            title='Backend Engineer',
            company='Acme Corp',
            description='Build APIs.',
        )
        self.seeker = User.objects.create_user(username='seeker', password='pass12345')
        self.seeker.profile.role = Role.JOB_SEEKER
        self.seeker.profile.save()
        self.recruiter = User.objects.create_user(username='recruiter', password='pass12345')
        self.recruiter.profile.role = Role.RECRUITER
        self.recruiter.profile.save()

    def test_job_seeker_can_apply_with_note(self):
        """A Job Seeker applies with a tailored note and it is saved."""
        self.client.login(username='seeker', password='pass12345')
        url = reverse('apply_to_job', args=[self.job.pk])
        response = self.client.post(url, {'note': 'I love Django and your mission.'})
        self.assertRedirects(response, reverse('job_detail', args=[self.job.pk]))
        application = JobApplication.objects.get(job=self.job, applicant=self.seeker)
        self.assertEqual(application.note, 'I love Django and your mission.')

    def test_apply_requires_non_empty_note(self):
        """Edge case: a blank/whitespace-only note is rejected."""
        self.client.login(username='seeker', password='pass12345')
        url = reverse('apply_to_job', args=[self.job.pk])
        response = self.client.post(url, {'note': '   '})
        self.assertRedirects(response, reverse('job_detail', args=[self.job.pk]))
        self.assertFalse(JobApplication.objects.filter(job=self.job).exists())

    def test_cannot_apply_twice(self):
        """Edge case: applying to the same job a second time is blocked."""
        self.client.login(username='seeker', password='pass12345')
        url = reverse('apply_to_job', args=[self.job.pk])
        self.client.post(url, {'note': 'First application.'})
        response = self.client.post(url, {'note': 'Second try.'})
        self.assertRedirects(response, reverse('job_detail', args=[self.job.pk]))
        self.assertEqual(JobApplication.objects.filter(job=self.job).count(), 1)

    def test_recruiter_cannot_apply(self):
        """Recruiters are not allowed to apply to jobs."""
        self.client.login(username='recruiter', password='pass12345')
        url = reverse('apply_to_job', args=[self.job.pk])
        response = self.client.post(url, {'note': 'I want this job.'})
        self.assertRedirects(response, reverse('home'))
        self.assertFalse(JobApplication.objects.exists())


class ReviewApplicationTests(TestCase):
    """Recruiters viewing applications."""

    def setUp(self):
        self.client = Client()
        self.job = Job.objects.create(
            title='Backend Engineer',
            company='Acme Corp',
            description='Build APIs.',
        )
        self.seeker = User.objects.create_user(
            username='seeker',
            email='seeker@example.com',
            password='pass12345',
        )
        self.seeker.profile.role = Role.JOB_SEEKER
        self.seeker.profile.save()
        self.seeker.candidate_profile.headline = 'Django developer'
        self.seeker.candidate_profile.skills = 'Python, Django'
        self.seeker.candidate_profile.summary = 'Two years of backend work.'
        self.seeker.candidate_profile.save()

        self.recruiter = User.objects.create_user(username='recruiter', password='pass12345')
        self.recruiter.profile.role = Role.RECRUITER
        self.recruiter.profile.save()

        self.application = JobApplication.objects.create(
            job=self.job,
            applicant=self.seeker,
            note='Excited about this role.',
        )

    def test_recruiter_can_review_application_in_one_place(self):
        """Review page shows the candidate profile, note, and job together."""
        self.client.login(username='recruiter', password='pass12345')
        url = reverse('review_application', args=[self.application.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Django developer', content)
        self.assertIn('Excited about this role.', content)
        self.assertIn('Backend Engineer', content)

    def test_recruiter_can_list_applications(self):
        """Recruiter sees applications on the application list."""
        self.client.login(username='recruiter', password='pass12345')
        response = self.client.get(reverse('application_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'seeker')

    def test_job_seeker_cannot_review_applications(self):
        """Job Seekers cannot open the application review page."""
        self.client.login(username='seeker', password='pass12345')
        response = self.client.get(reverse('review_application', args=[self.application.pk]))
        self.assertRedirects(response, reverse('home'))


class ReviewApplicationDetailsTests(TestCase):
    """SCRUM-20: recruiter sees full profile and application details in one place."""

    def setUp(self):
        self.client = Client()
        self.job = Job.objects.create(title='Backend Engineer', company='Acme', description='APIs.')
        self.other_job = Job.objects.create(title='iOS Developer', company='Globex', description='Swift.')

        self.seeker = User.objects.create_user(
            username='seeker', password='pass12345', email='seeker@example.com',
            first_name='Sam', last_name='Seeker',
        )
        cp = self.seeker.candidate_profile
        cp.headline = 'Full-stack developer'
        cp.location = 'Atlanta, GA'
        cp.skills = 'Python, Django, SQL'
        cp.education = 'B.S. Computer Science'
        cp.work_experience = 'Intern at Initech'
        cp.github_url = 'https://github.com/sam'
        cp.save()

        self.application = JobApplication.objects.create(
            job=self.job, applicant=self.seeker, note='I love building APIs.',
        )
        self.other_application = JobApplication.objects.create(
            job=self.other_job, applicant=self.seeker, note='Swift fan.',
        )

        self.newbie = User.objects.create_user(username='newbie', password='pass12345')
        self.bare_application = JobApplication.objects.create(
            job=self.job, applicant=self.newbie, note='Hello.',
        )

        self.recruiter = User.objects.create_user(username='recruiter', password='pass12345')
        self.recruiter.profile.role = Role.RECRUITER
        self.recruiter.profile.save()

    def login_recruiter(self):
        self.client.login(username='recruiter', password='pass12345')

    def test_review_page_shows_full_profile_and_application(self):
        """Review page shows every profile field (name, email, skills, education, links...)."""
        self.login_recruiter()
        response = self.client.get(reverse('review_application', args=[self.application.pk]))
        self.assertEqual(response.status_code, 200)
        for text in (
            'Sam Seeker', 'seeker@example.com', 'I love building APIs.',
            'Full-stack developer', 'Atlanta, GA', '<li>Django</li>',
            'B.S. Computer Science', 'Intern at Initech', 'https://github.com/sam',
        ):
            self.assertContains(response, text)

    def test_review_page_lists_candidates_other_applications(self):
        """Review page links to the candidate's applications to other jobs."""
        self.login_recruiter()
        response = self.client.get(reverse('review_application', args=[self.application.pk]))
        self.assertContains(response, 'iOS Developer')
        self.assertContains(
            response, reverse('review_application', args=[self.other_application.pk])
        )

    def test_candidate_with_blank_profile_still_reviewable(self):
        """Edge case: a candidate with an empty profile can still be reviewed."""
        self.login_recruiter()
        response = self.client.get(reverse('review_application', args=[self.bare_application.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No profile details on file yet.')
        self.assertContains(response, 'Hello.')

    def test_application_list_filters_by_job(self):
        """The ?job= filter shows only applicants for that job."""
        self.login_recruiter()
        response = self.client.get(reverse('application_list'), {'job': self.job.pk})
        self.assertEqual(
            set(response.context['applications']), {self.application, self.bare_application}
        )
        self.assertContains(response, 'Applicants for Backend Engineer')

    def test_application_list_unknown_job_404(self):
        """Edge case: filtering by a job id that does not exist returns 404."""
        self.login_recruiter()
        response = self.client.get(reverse('application_list'), {'job': 9999})
        self.assertEqual(response.status_code, 404)

    def test_job_detail_links_recruiter_to_applicants(self):
        """Recruiters see a "Review applicants (N)" link on the job page."""
        self.login_recruiter()
        response = self.client.get(reverse('job_detail', args=[self.job.pk]))
        self.assertContains(response, 'Review applicants (2)')
        self.assertContains(response, f"{reverse('application_list')}?job={self.job.pk}")

    def test_job_seeker_does_not_see_applicant_link(self):
        """Job Seekers do not see the applicants link."""
        self.client.login(username='seeker', password='pass12345')
        response = self.client.get(reverse('job_detail', args=[self.job.pk]))
        self.assertNotContains(response, 'Review applicants')

    def test_anonymous_redirected_to_login(self):
        """Edge case: a logged-out visitor opening a review page is sent to login."""
        response = self.client.get(reverse('review_application', args=[self.application.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_missing_application_returns_404(self):
        """Edge case: reviewing an application id that does not exist returns 404."""
        self.login_recruiter()
        response = self.client.get(reverse('review_application', args=[9999]))
        self.assertEqual(response.status_code, 404)


class RecruiterPostingTests(TestCase):
    """Recruiter dashboard, creating/editing postings, and the job search page."""

    def setUp(self):
        self.recruiter = User.objects.create_user(username='recruiter', password='pass12345')
        self.recruiter.profile.role = Role.RECRUITER
        self.recruiter.profile.save()
        self.other_recruiter = User.objects.create_user(username='other', password='pass12345')
        self.other_recruiter.profile.role = Role.RECRUITER
        self.other_recruiter.profile.save()
        self.seeker = User.objects.create_user(username='seeker', password='pass12345')
        self.tomorrow = timezone.localdate() + timedelta(days=1)

    def posting_data(self, **overrides):
        data = {
            'company': 'Acme Corp',
            'title': 'Data Analyst',
            'location': 'Atlanta, GA',
            'description': 'Analyze sales data.',
            'requirements': 'SQL and Excel.',
            'closing_date': (timezone.localdate() + timedelta(days=30)).isoformat(),
        }
        data.update(overrides)
        return data

    def test_recruiter_dashboard_lists_only_own_postings(self):
        """The dashboard shows only this recruiter's postings, not other recruiters'."""
        Job.objects.create(title='Mine', company='A', description='d', posted_by=self.recruiter)
        Job.objects.create(title='Theirs', company='B', description='d', posted_by=self.other_recruiter)
        self.client.login(username='recruiter', password='pass12345')
        response = self.client.get(reverse('recruiter_dashboard'))
        self.assertEqual([j.title for j in response.context['postings']], ['Mine'])

    def test_non_recruiters_blocked_from_posting(self):
        """Job Seekers cannot open the dashboard or submit a posting."""
        self.client.login(username='seeker', password='pass12345')
        for url in (reverse('recruiter_dashboard'), reverse('create_job')):
            self.assertRedirects(self.client.get(url), reverse('home'))
        self.client.post(reverse('create_job'), self.posting_data())
        self.assertFalse(Job.objects.exists())

    def test_recruiter_creates_posting_visible_to_job_seekers(self):
        """A new posting is saved with all fields and shows on the search and detail pages."""
        self.client.login(username='recruiter', password='pass12345')
        response = self.client.post(reverse('create_job'), self.posting_data())
        self.assertRedirects(response, reverse('recruiter_dashboard'))
        job = Job.objects.get()
        self.assertEqual(job.posted_by, self.recruiter)
        self.assertEqual(job.location, 'Atlanta, GA')
        self.assertEqual(job.requirements, 'SQL and Excel.')

        self.client.login(username='seeker', password='pass12345')
        self.assertContains(self.client.get(reverse('job_list')), 'Data Analyst')
        detail = self.client.get(reverse('job_detail', args=[job.pk]))
        for text in ('Acme Corp', 'Atlanta, GA', 'Analyze sales data.', 'SQL and Excel.', 'Applicant criteria'):
            self.assertContains(detail, text)

    def test_all_fields_required(self):
        """Edge case: leaving any one of the six posting fields blank is rejected."""
        self.client.login(username='recruiter', password='pass12345')
        for field in ('company', 'title', 'location', 'description', 'requirements', 'closing_date'):
            response = self.client.post(reverse('create_job'), self.posting_data(**{field: ''}))
            self.assertEqual(response.status_code, 200, field)
        self.assertFalse(Job.objects.exists())

    def test_closing_date_in_past_rejected(self):
        """Edge case: a closing date before today is rejected."""
        self.client.login(username='recruiter', password='pass12345')
        yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
        response = self.client.post(reverse('create_job'), self.posting_data(closing_date=yesterday))
        self.assertContains(response, 'Closing date cannot be in the past.')
        self.assertFalse(Job.objects.exists())

    def test_recruiter_edits_own_posting_only(self):
        """A recruiter can edit their own posting but gets 404 on another recruiter's."""
        job = Job.objects.create(
            title='Old', company='A', description='d', posted_by=self.recruiter,
            closing_date=self.tomorrow,
        )
        self.client.login(username='recruiter', password='pass12345')
        self.client.post(reverse('edit_job', args=[job.pk]), self.posting_data(title='New'))
        job.refresh_from_db()
        self.assertEqual(job.title, 'New')

        self.client.login(username='other', password='pass12345')
        response = self.client.post(reverse('edit_job', args=[job.pk]), self.posting_data(title='Hijack'))
        self.assertEqual(response.status_code, 404)
        job.refresh_from_db()
        self.assertEqual(job.title, 'New')

    def test_closed_postings_hidden_and_not_applicable(self):
        """Postings past their closing date are hidden from search and cannot be applied to."""
        closed = Job.objects.create(
            title='Closed role', company='A', description='d',
            closing_date=timezone.localdate() - timedelta(days=1),
        )
        Job.objects.create(title='Open role', company='B', description='d', closing_date=self.tomorrow)
        self.client.login(username='seeker', password='pass12345')
        listing = self.client.get(reverse('job_list'))
        self.assertContains(listing, 'Open role')
        self.assertNotContains(listing, 'Closed role')

        self.client.post(reverse('apply_to_job', args=[closed.pk]), {'note': 'Please?'})
        self.assertFalse(JobApplication.objects.exists())

    def test_job_search_by_keyword_and_location(self):
        """Search matches by keyword and by location (case-insensitive)."""
        Job.objects.create(title='Python Dev', company='A', description='d', location='Atlanta, GA')
        Job.objects.create(title='Java Dev', company='B', description='d', location='Remote')
        response = self.client.get(reverse('job_list'), {'q': 'python'})
        self.assertEqual([j.title for j in response.context['jobs']], ['Python Dev'])
        response = self.client.get(reverse('job_list'), {'location': 'remote'})
        self.assertEqual([j.title for j in response.context['jobs']], ['Java Dev'])


class CandidateSearchTests(TestCase):
    def setUp(self):
        self.recruiter = User.objects.create_user(username='recruiter', password='pass12345')
        self.recruiter.profile.role = Role.RECRUITER
        self.recruiter.profile.save()
        self.seeker = User.objects.create_user(username='matching-seeker', password='pass12345')
        matching_profile = self.seeker.candidate_profile
        matching_profile.skills = 'Python, Django'
        matching_profile.location = 'Atlanta, GA'
        matching_profile.work_experience = 'Built a Django recruiting project.'
        matching_profile.save()
        self.other_seeker = User.objects.create_user(username='other-seeker', password='pass12345')
        other_profile = self.other_seeker.candidate_profile
        other_profile.skills = 'Java'
        other_profile.location = 'Remote'
        other_profile.work_experience = 'Built an Android project.'
        other_profile.save()

    def test_recruiter_can_filter_candidates(self):
        self.client.login(username='recruiter', password='pass12345')
        response = self.client.get(
            reverse('candidate_search'),
            {'skills': 'django', 'location': 'atlanta', 'projects': 'recruiting'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'matching-seeker')
        self.assertNotContains(response, 'other-seeker')

    def test_job_seeker_cannot_search_candidates(self):
        self.client.login(username='matching-seeker', password='pass12345')
        response = self.client.get(reverse('candidate_search'))
        self.assertRedirects(response, reverse('home'))
