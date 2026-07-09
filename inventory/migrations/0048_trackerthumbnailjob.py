# Hand-written (makemigrations is user-run in this repo; verify with
# `python manage.py makemigrations --check --dry-run`).
# Backs the tracker-page thumbnail-regeneration progress banner and the
# per-tracker concurrency guard, mirroring LibraryScan for the library.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0047_libraryfile_thumbnail_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrackerThumbnailJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tracker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='thumbnail_jobs', to='inventory.tracker')),
                ('include_linked', models.BooleanField(default=False, help_text="Also (re)render storage_type='link' files for this run")),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('success', 'Success'), ('error', 'Error')], default='pending', max_length=16)),
                ('error', models.TextField(blank=True)),
                ('files_queued', models.PositiveIntegerField(default=0, help_text='Eligible files needing a render (excludes manual-image and non-STL/3MF files)')),
                ('files_processed', models.PositiveIntegerField(default=0)),
                ('files_generated', models.PositiveIntegerField(default=0, help_text='Of the processed files, how many produced a thumbnail')),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Tracker Thumbnail Job',
                'verbose_name_plural': 'Tracker Thumbnail Jobs',
                'ordering': ['-created_at'],
            },
        ),
    ]
