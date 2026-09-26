from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from .models import CandidateProfile

class CandidateProfileViewTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(username='jobseeker', password='test-password')
		self.client.login(username='jobseeker', password='test-password')
		
	def save_profile(self):
		response = self.client.post(
			reverse('profile'),
			{'headline': 'Python developer',
			 'skills': 'Python, Django',
             'education' : 'Computer Science degree',
             'work_experience' : 'Built web applications.',
             'linkedin_url' : 'https://www.linkedin.come/in/jobseeker',
             'portfolio_url' : 'https://www.jobseeker.example.com',
            }
        )
		self.assertRedirects(response, reverse('profile'))
		profile = CandidateProfile.objects.get(user=self.user)
		self.assertEqual(profile.headline, 'Python developer')
		self.assertEqual(profile.skills, 'Python, Django')
		self.assertEqual(profile.education, 'Computer Science degree')
		self.assertEqual(profile.work_experience, 'Built web applications.')
		self.assertEqual(profile.github_url, 'https://github.com/jobseeker')
	def test_profile_saves_location_and_summary(self):
		"""Location and summary are editable, since recruiters search on both."""
		response = self.client.post(
			reverse('profile'),
			{'headline': 'Analyst', 'location': 'Remote', 'summary': 'Five years of SQL.'},
		)
		self.assertRedirects(response, reverse('profile'))
		profile = CandidateProfile.objects.get(user=self.user)
		self.assertEqual((profile.location, profile.summary), ('Remote', 'Five years of SQL.'))
