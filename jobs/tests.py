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
