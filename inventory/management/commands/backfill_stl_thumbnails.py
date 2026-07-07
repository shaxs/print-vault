"""
Management command to backfill auto-generated thumbnails for existing
STL/3MF tracker files that don't have one yet (e.g. right after upgrading
to a Print Vault version that has this feature).

Runs synchronously (not via Django-Q) since this is a one-time admin
operation, typically run before the qcluster worker is even confirmed
running.

Usage:
    python manage.py backfill_stl_thumbnails
    python manage.py backfill_stl_thumbnails --tracker-id 30
    python manage.py backfill_stl_thumbnails --limit 50 --dry-run
    python manage.py backfill_stl_thumbnails --include-linked
"""

from django.core.management.base import BaseCommand

from inventory.models import Tracker, TrackerFile
from inventory.services.stl_thumbnail_service import (
    SUPPORTED_EXTENSIONS,
    generate_auto_thumbnail,
)


class Command(BaseCommand):
    help = 'Backfill auto-generated thumbnails for existing STL/3MF tracker files without one'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tracker-id', type=int,
            help='Only process files belonging to this tracker'
        )
        parser.add_argument(
            '--limit', type=int, default=0,
            help='Maximum number of files to process (0 = unlimited)'
        )
        parser.add_argument(
            '--include-linked', action='store_true',
            help="Also generate thumbnails for storage_type='link' files "
                 "(downloads each one temporarily; no local copy is kept)"
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be processed without generating anything'
        )

    def handle(self, *args, **options):
        tracker_id = options.get('tracker_id')
        limit = options.get('limit') or 0
        include_linked = options.get('include_linked', False)
        dry_run = options.get('dry_run', False)

        storage_types = ['local', 'link'] if include_linked else ['local']
        queryset = TrackerFile.objects.filter(
            storage_type__in=storage_types,
            images__isnull=True,
        ).select_related('tracker').distinct()

        if tracker_id:
            try:
                tracker = Tracker.objects.get(id=tracker_id)
            except Tracker.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Tracker {tracker_id} not found'))
                return
            queryset = queryset.filter(tracker=tracker)
            self.stdout.write(self.style.SUCCESS(f'Backfilling thumbnails for tracker: {tracker.name}'))
        else:
            self.stdout.write(self.style.SUCCESS('Backfilling thumbnails for all trackers'))

        candidates = [tf for tf in queryset if tf.filename.lower().endswith(SUPPORTED_EXTENSIONS)]

        if limit > 0:
            candidates = candidates[:limit]

        if not candidates:
            self.stdout.write(self.style.SUCCESS('No eligible files found. Nothing to do.'))
            return

        self.stdout.write(f'Found {len(candidates)} eligible file(s)')

        if dry_run:
            for tracker_file in candidates:
                self.stdout.write(
                    f'[DRY RUN] Would process: {tracker_file.tracker.name} / '
                    f'{tracker_file.filename} (storage_type={tracker_file.storage_type})'
                )
            self.stdout.write(self.style.WARNING(
                f'[DRY RUN] No changes were made ({len(candidates)} would be processed)'
            ))
            return

        generated = 0
        failed = 0

        for tracker_file in candidates:
            image = generate_auto_thumbnail(tracker_file, allow_linked_download=include_linked)
            if image:
                generated += 1
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Generated: {tracker_file.tracker.name} / {tracker_file.filename}'
                ))
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(
                    f'✗ Skipped/failed: {tracker_file.tracker.name} / {tracker_file.filename}'
                ))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'Generated: {generated}'))
        if failed:
            self.stdout.write(self.style.ERROR(f'Skipped/failed: {failed}'))
