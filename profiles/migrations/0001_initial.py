import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CandidateProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('headline', models.CharField(blank=True, max_length=200)),
                ('skills', models.TextField(blank=True, help_text='Comma-separated or free-form skills.')),
                ('summary', models.TextField(blank=True, help_text='Experience and background.')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='candidate_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
