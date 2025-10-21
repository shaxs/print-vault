"""
Management command to fix tracker files that were downloaded but not linked in database.
This happens when user clicks Save before download completes.

Usage:
    python manage.py fix_tracker_files <tracker_id>
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from inventory.models import Tracker, TrackerFile
from inventory.services.storage_manager import StorageManager
import os


class Command(BaseCommand):
    help = 'Fix tracker files by linking downloaded files to database records'

    def add_arguments(self, parser):
        parser.add_argument('tracker_id', type=int, help='ID of the tracker to fix')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes'
        )

    def handle(self, *args, **options):
        tracker_id = options['tracker_id']
        dry_run = options.get('dry_run', False)

        try:
            tracker = Tracker.objects.get(id=tracker_id)
        except Tracker.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Tracker {tracker_id} not found'))
            return

        self.stdout.write(self.style.SUCCESS(f'Fixing tracker: {tracker.name}'))
        
        # Get all files with URLs but no local_file
        broken_files = TrackerFile.objects.filter(
            tracker=tracker,
            github_url__isnull=False,
        ).exclude(github_url='').filter(local_file='')

        if not broken_files.exists():
            self.stdout.write(self.style.SUCCESS('No broken files found. All files are properly linked.'))
            return

        self.stdout.write(f'Found {broken_files.count()} files with missing local_file references')

        storage_manager = StorageManager()
        fixed_count = 0
        missing_count = 0

        for tracker_file in broken_files:
            # Build expected file path
            category = tracker_file.directory_path or 'uncategorized'
            safe_category = storage_manager.sanitize_filename(category)
            safe_filename = storage_manager.sanitize_filename(tracker_file.filename)
            
            # Expected relative path (relative to MEDIA_ROOT)
            relative_path = f"trackers/{tracker.id}/files/{safe_category}/{safe_filename}"
            
            # Full absolute path
            full_path = os.path.join(settings.MEDIA_ROOT, relative_path)

            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path)
                
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'[DRY RUN] Would fix: {tracker_file.filename} -> {relative_path} ({file_size} bytes)'
                        )
                    )
                else:
                    # Update the database record
                    tracker_file.local_file = relative_path
                    tracker_file.actual_file_size = file_size
                    tracker_file.download_status = 'completed'
                    tracker_file.download_error = ''
                    tracker_file.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Fixed: {tracker_file.filename} -> {relative_path} ({file_size} bytes)'
                        )
                    )
                
                fixed_count += 1
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ File not found on disk: {tracker_file.filename} (expected at {full_path})'
                    )
                )
                missing_count += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN] No changes were made'))
            self.stdout.write(f'Would fix: {fixed_count} files')
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully fixed: {fixed_count} files'))
        
        if missing_count > 0:
            self.stdout.write(self.style.ERROR(f'Missing on disk: {missing_count} files'))
        
        self.stdout.write('')
        self.stdout.write('To verify, check the tracker detail page or run:')
        self.stdout.write(f'  python manage.py fix_tracker_files {tracker_id} --dry-run')
