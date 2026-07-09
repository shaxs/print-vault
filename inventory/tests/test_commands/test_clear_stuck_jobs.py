"""
Tests for the clear_stuck_jobs management command.
"""
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone
from django_q.models import OrmQ

from inventory.models import LibraryScan, TrackerThumbnailJob
from inventory.tests.factories import LibraryRootFactory, TrackerFactory


def _queue_a_task():
    # Minimal Django-Q ORM-broker queue row (contents don't matter here).
    return OrmQ.objects.create(key='printvault', payload=b'x', lock=timezone.now())


@pytest.mark.django_db
class TestClearStuckJobs:
    def test_fails_stuck_rows_and_purges_queue(self):
        root = LibraryRootFactory()
        scan = LibraryScan.objects.create(root=root, status='running')
        job = TrackerThumbnailJob.objects.create(tracker=TrackerFactory(), status='pending')
        _queue_a_task()

        call_command('clear_stuck_jobs', stdout=StringIO())

        scan.refresh_from_db()
        job.refresh_from_db()
        assert scan.status == 'error'
        assert job.status == 'error'
        assert OrmQ.objects.count() == 0

    def test_dry_run_changes_nothing(self):
        root = LibraryRootFactory()
        scan = LibraryScan.objects.create(root=root, status='running')
        _queue_a_task()

        call_command('clear_stuck_jobs', '--dry-run', stdout=StringIO())

        scan.refresh_from_db()
        assert scan.status == 'running'
        assert OrmQ.objects.count() == 1

    def test_queue_only_leaves_rows(self):
        root = LibraryRootFactory()
        scan = LibraryScan.objects.create(root=root, status='running')
        _queue_a_task()

        call_command('clear_stuck_jobs', '--queue-only', stdout=StringIO())

        scan.refresh_from_db()
        assert scan.status == 'running'  # untouched
        assert OrmQ.objects.count() == 0  # queue purged

    def test_jobs_only_leaves_queue(self):
        root = LibraryRootFactory()
        scan = LibraryScan.objects.create(root=root, status='running')
        _queue_a_task()

        call_command('clear_stuck_jobs', '--jobs-only', stdout=StringIO())

        scan.refresh_from_db()
        assert scan.status == 'error'  # failed
        assert OrmQ.objects.count() == 1  # queue untouched

    def test_completed_rows_are_not_touched(self):
        root = LibraryRootFactory()
        done = LibraryScan.objects.create(root=root, status='success')

        call_command('clear_stuck_jobs', stdout=StringIO())

        done.refresh_from_db()
        assert done.status == 'success'
