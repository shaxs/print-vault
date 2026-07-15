# Hand-written (makemigrations is user-run in this repo; verify with
# `python manage.py makemigrations --check --dry-run`).
# Adds a job-kind discriminator to LibraryScan so a re-attached progress
# banner can tell a directory scan from a thumbnail regeneration.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0046_libraryroot_thumbnail_color'),
    ]

    operations = [
        migrations.AddField(
            model_name='libraryscan',
            name='kind',
            field=models.CharField(
                choices=[('scan', 'Scan'), ('thumbnails', 'Thumbnails')],
                default='scan',
                help_text='What this job does — a directory scan or a thumbnail regeneration; lets a re-attached progress banner label the job correctly',
                max_length=16,
            ),
        ),
    ]
