"""
Tests for the library Django-Q wiring: per-root Schedule sync (driven by
LibraryRoot save/delete signals), the start_scan concurrency guard, and the
scheduled-rescan entry point.
"""
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from django_q.models import Schedule

from inventory.library_tasks import scheduled_root_rescan
from inventory.models import LibraryScan
from inventory.services import library_scanner
from inventory.services.library_scanner import start_scan
from inventory.tests.factories import LibraryRootFactory


class RootScheduleSyncTest(TestCase):
    """Schedule rows stay in step with LibraryRoot settings via signals."""

    def test_saving_root_with_interval_creates_schedule(self):
        """A root with a rescan interval gets one Schedule row."""
        root = LibraryRootFactory(rescan_interval_hours=6)

        schedule = Schedule.objects.get(name=f"library-root-rescan-{root.pk}")
        self.assertEqual(schedule.minutes, 360)
        self.assertEqual(schedule.func, 'inventory.library_tasks.scheduled_root_rescan')
        self.assertEqual(schedule.args, str(root.pk))

    def test_changing_interval_updates_schedule_in_place(self):
        """Changing the interval updates the existing Schedule, no duplicates."""
        root = LibraryRootFactory(rescan_interval_hours=6)

        root.rescan_interval_hours = 12
        root.save()

        schedules = Schedule.objects.filter(name=f"library-root-rescan-{root.pk}")
        self.assertEqual(schedules.count(), 1)
        self.assertEqual(schedules.get().minutes, 720)

    def test_clearing_interval_removes_schedule(self):
        """Interval NULL means manual-only — the Schedule goes away."""
        root = LibraryRootFactory(rescan_interval_hours=6)

        root.rescan_interval_hours = None
        root.save()

        self.assertFalse(Schedule.objects.filter(name=f"library-root-rescan-{root.pk}").exists())

    def test_disabling_root_removes_schedule(self):
        """A disabled root must not keep rescanning."""
        root = LibraryRootFactory(rescan_interval_hours=6)

        root.enabled = False
        root.save()

        self.assertFalse(Schedule.objects.filter(name=f"library-root-rescan-{root.pk}").exists())

    def test_deleting_root_removes_schedule(self):
        """Deleting a root cleans up its Schedule row."""
        root = LibraryRootFactory(rescan_interval_hours=6)
        root_pk = root.pk

        root.delete()

        self.assertFalse(Schedule.objects.filter(name=f"library-root-rescan-{root_pk}").exists())

    def test_root_without_interval_has_no_schedule(self):
        """No interval configured → no Schedule row created."""
        root = LibraryRootFactory()

        self.assertFalse(Schedule.objects.filter(name=f"library-root-rescan-{root.pk}").exists())


class StartScanTest(TestCase):
    """start_scan creates + enqueues, and refuses concurrent scans per root."""

    def test_start_scan_creates_and_enqueues(self):
        root = LibraryRootFactory()

        with mock.patch.object(library_scanner, 'async_task') as mock_async:
            scan = start_scan(root)

        self.assertIsNotNone(scan)
        self.assertEqual(scan.status, 'pending')
        self.assertEqual(scan.kind, 'scan')
        mock_async.assert_called_once_with('inventory.library_tasks.run_library_scan', scan.pk)

    def test_start_scan_refused_while_scan_in_progress(self):
        """A second scan request while one is running is rejected."""
        root = LibraryRootFactory()
        LibraryScan.objects.create(root=root, status='running')

        with mock.patch.object(library_scanner, 'async_task') as mock_async:
            result = start_scan(root)

        self.assertIsNone(result)
        mock_async.assert_not_called()
        self.assertEqual(LibraryScan.objects.count(), 1)

    def test_start_scan_displaces_stale_scan(self):
        """A dead scan (>12h old, never finalized) is failed and displaced."""
        root = LibraryRootFactory()
        stale = LibraryScan.objects.create(root=root, status='running')
        LibraryScan.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - timedelta(hours=13)
        )

        with mock.patch.object(library_scanner, 'async_task'):
            new_scan = start_scan(root)

        self.assertIsNotNone(new_scan)
        stale.refresh_from_db()
        self.assertEqual(stale.status, 'error')


class ScheduledRescanTest(TestCase):
    """scheduled_root_rescan honors enabled/missing-root guards."""

    def test_scheduled_rescan_disabled_root_skipped(self):
        root = LibraryRootFactory(enabled=False)

        with mock.patch.object(library_scanner, 'async_task'):
            result = scheduled_root_rescan(root.pk)

        self.assertIsNone(result)
        self.assertEqual(LibraryScan.objects.count(), 0)

    def test_scheduled_rescan_missing_root_skipped(self):
        with mock.patch.object(library_scanner, 'async_task'):
            self.assertIsNone(scheduled_root_rescan(999999))

    def test_scheduled_rescan_creates_scan(self):
        root = LibraryRootFactory()

        with mock.patch.object(library_scanner, 'async_task'):
            result = scheduled_root_rescan(root.pk)

        self.assertEqual(result, LibraryScan.objects.get().pk)
