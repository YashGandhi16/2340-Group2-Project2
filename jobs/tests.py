from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Role

from .models import Job, JobApplication

User = get_user_model()


class ApplyToJobTests(TestCase):
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
        self.client.login(username='seeker', password='pass12345')
        url = reverse('apply_to_job', args=[self.job.pk])
        response = self.client.post(url, {'note': 'I love Django and your mission.'})
        self.assertRedirects(response, reverse('job_detail', args=[self.job.pk]))
        application = JobApplication.objects.get(job=self.job, applicant=self.seeker)
        self.assertEqual(application.note, 'I love Django and your mission.')

    def test_apply_requires_non_empty_note(self):
        self.client.login(username='seeker', password='pass12345')
        url = reverse('apply_to_job', args=[self.job.pk])
        response = self.client.post(url, {'note': '   '})
        self.assertRedirects(response, reverse('job_detail', args=[self.job.pk]))
        self.assertFalse(JobApplication.objects.filter(job=self.job).exists())

    def test_cannot_apply_twice(self):
        self.client.login(username='seeker', password='pass12345')
        url = reverse('apply_to_job', args=[self.job.pk])
        self.client.post(url, {'note': 'First application.'})
        response = self.client.post(url, {'note': 'Second try.'})
        self.assertRedirects(response, reverse('job_detail', args=[self.job.pk]))
        self.assertEqual(JobApplication.objects.filter(job=self.job).count(), 1)

    def test_recruiter_cannot_apply(self):
        self.client.login(username='recruiter', password='pass12345')
        url = reverse('apply_to_job', args=[self.job.pk])
        response = self.client.post(url, {'note': 'I want this job.'})
        self.assertRedirects(response, reverse('home'))
        self.assertFalse(JobApplication.objects.exists())


class ReviewApplicationTests(TestCase):
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
        self.client.login(username='recruiter', password='pass12345')
        url = reverse('review_application', args=[self.application.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Django developer', content)
        self.assertIn('Excited about this role.', content)
        self.assertIn('Backend Engineer', content)

    def test_recruiter_can_list_applications(self):
        self.client.login(username='recruiter', password='pass12345')
        response = self.client.get(reverse('application_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'seeker')

    def test_job_seeker_cannot_review_applications(self):
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
        self.login_recruiter()
        response = self.client.get(reverse('review_application', args=[self.application.pk]))
        self.assertContains(response, 'iOS Developer')
        self.assertContains(
            response, reverse('review_application', args=[self.other_application.pk])
        )

    def test_candidate_with_blank_profile_still_reviewable(self):
        self.login_recruiter()
        response = self.client.get(reverse('review_application', args=[self.bare_application.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No profile details on file yet.')
        self.assertContains(response, 'Hello.')

    def test_application_list_filters_by_job(self):
        self.login_recruiter()
        response = self.client.get(reverse('application_list'), {'job': self.job.pk})
        self.assertEqual(
            set(response.context['applications']), {self.application, self.bare_application}
        )
        self.assertContains(response, 'Applicants for Backend Engineer')

    def test_application_list_unknown_job_404(self):
        self.login_recruiter()
        response = self.client.get(reverse('application_list'), {'job': 9999})
        self.assertEqual(response.status_code, 404)

    def test_job_detail_links_recruiter_to_applicants(self):
        self.login_recruiter()
        response = self.client.get(reverse('job_detail', args=[self.job.pk]))
        self.assertContains(response, 'Review applicants (2)')
        self.assertContains(response, f"{reverse('application_list')}?job={self.job.pk}")

    def test_job_seeker_does_not_see_applicant_link(self):
        self.client.login(username='seeker', password='pass12345')
        response = self.client.get(reverse('job_detail', args=[self.job.pk]))
        self.assertNotContains(response, 'Review applicants')

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse('review_application', args=[self.application.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_missing_application_returns_404(self):
        self.login_recruiter()
        response = self.client.get(reverse('review_application', args=[9999]))
        self.assertEqual(response.status_code, 404)
