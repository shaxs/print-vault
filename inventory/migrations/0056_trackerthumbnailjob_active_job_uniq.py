from django.db import migrations, models


def resolve_duplicate_active_jobs(apps, schema_editor):
    """Before enforcing one active job per tracker, finalize any pre-existing
    duplicates so the constraint can be added cleanly. Keep the newest
    pending/running job per tracker; mark older ones as errored."""
    TrackerThumbnailJob = apps.get_model('inventory', 'TrackerThumbnailJob')
    seen_trackers = set()
    for job in (
        TrackerThumbnailJob.objects.filter(status__in=['pending', 'running'])
        .order_by('tracker_id', '-created_at')
    ):
        if job.tracker_id in seen_trackers:
            job.status = 'error'
            job.error = (
                (job.error + ' ' if job.error else '')
                + '(auto-resolved duplicate active job when adding the '
                'per-tracker uniqueness constraint)'
            )
            job.save(update_fields=['status', 'error'])
        else:
            seen_trackers.add(job.tracker_id)


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0055_libraryscan_active_scan_uniq'),
    ]

    operations = [
        migrations.RunPython(resolve_duplicate_active_jobs, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='trackerthumbnailjob',
            constraint=models.UniqueConstraint(
                condition=models.Q(status__in=['pending', 'running']),
                fields=['tracker'],
                name='uniq_active_tracker_thumbnail_job_per_tracker',
            ),
        ),
    ]
