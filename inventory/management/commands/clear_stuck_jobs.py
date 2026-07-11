"""
Clear stuck background work: purge the Django-Q task queue and mark any
library scans / tracker thumbnail jobs left in pending/running as errored.

Use this when the qcluster has wedged (e.g. workers reincarnating on a task
that outlives the timeout) and you want a clean slate before restarting it.
Purging the queue removes the *backlog*; restart the qcluster afterwards so it
picks up current code and starts fresh.

Usage:
    python manage.py clear_stuck_jobs
    python manage.py clear_stuck_jobs --dry-run
    python manage.py clear_stuck_jobs --queue-only   # leave scan/job rows alone
    python manage.py clear_stuck_jobs --jobs-only     # leave the queue alone
"""

from django.core.management.base import BaseCommand

from inventory.models import LibraryScan, TrackerThumbnailJob

ACTIVE_STATUSES = ['pending', 'running']


class Command(BaseCommand):
    help = 'Purge the Django-Q queue and fail any stuck library/thumbnail jobs.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would be cleared without changing anything'
        )
        parser.add_argument(
            '--queue-only', action='store_true',
            help='Only purge the task queue; leave scan/job rows untouched'
        )
        parser.add_argument(
            '--jobs-only', action='store_true',
            help='Only fail stuck scan/job rows; leave the task queue untouched'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        queue_only = options['queue_only']
        jobs_only = options['jobs_only']

        if queue_only and jobs_only:
            self.stderr.write('--queue-only and --jobs-only are mutually exclusive.')
            return

        if not jobs_only:
            self._clear_queue(dry_run)
        if not queue_only:
            self._fail_stuck_rows(dry_run)

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN] Nothing was changed.'))
        else:
            self.stdout.write(self.style.SUCCESS(
                'Done. Restart the qcluster so it starts on a clean queue.'
            ))

    def _clear_queue(self, dry_run):
        # OrmQ is the Django-Q ORM broker's queued-task table (the default
        # broker for this project — see Q_CLUSTER in settings). Import lazily
        # so the command still loads if django_q isn't installed.
        from django_q.models import OrmQ

        count = OrmQ.objects.count()
        if dry_run:
            self.stdout.write(f'[DRY RUN] Would purge {count} queued task(s).')
        else:
            OrmQ.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'Purged {count} queued task(s).'))

    def _fail_stuck_rows(self, dry_run):
        scans = LibraryScan.objects.filter(status__in=ACTIVE_STATUSES)
        jobs = TrackerThumbnailJob.objects.filter(status__in=ACTIVE_STATUSES)
        scan_count = scans.count()
        job_count = jobs.count()

        if dry_run:
            self.stdout.write(
                f'[DRY RUN] Would fail {scan_count} stuck library scan(s) '
                f'and {job_count} stuck thumbnail job(s).'
            )
            return

        # Reset the roots of the scans we're failing, otherwise their
        # last_scan_status stays 'running' and the settings UI shows a stale
        # "SCANNING…" badge with no scan actually running.
        from inventory.models import LibraryRoot
        root_ids = list(scans.values_list('root_id', flat=True))

        scans.update(status='error', error='Cleared by clear_stuck_jobs')
        jobs.update(status='error', error='Cleared by clear_stuck_jobs')

        roots_reset = 0
        if root_ids:
            roots_reset = LibraryRoot.objects.filter(
                pk__in=root_ids, last_scan_status='running'
            ).update(last_scan_status='idle', last_scan_error='Cleared by clear_stuck_jobs')

        self.stdout.write(self.style.SUCCESS(
            f'Failed {scan_count} stuck library scan(s) and {job_count} stuck '
            f'thumbnail job(s); reset {roots_reset} stuck root badge(s).'
        ))
