"""
Tests for the library scanner walk/diff engine, run against real temporary
directory trees (per the feature plan: not just mocks).

async_task is patched to execute processing chunks eagerly in-process, so a
"scan" here runs walk + sweep + per-file processing synchronously.
"""
import os
import shutil
import tempfile
from unittest import mock

import io

import trimesh
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from inventory.models import LibraryFile, LibraryFolder, LibraryRoot, LibraryScan
from inventory.services import library_scanner
from inventory.services.library_scanner import (
    MAX_RENDER_FILE_SIZE_BYTES,
    process_file_chunk,
    run_scan,
)
from inventory.tests.factories import LibraryFolderFactory, LibraryRootFactory


def _tiny_png_bytes():
    buf = io.BytesIO()
    Image.new('RGBA', (4, 4), (10, 20, 30, 255)).save(buf, 'PNG')
    return buf.getvalue()

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='pv_test_media_')


def _eager_async_task(task_path, scan_id, chunk, *extra):
    """Stand-in for django_q.tasks.async_task: run the chunk immediately.
    `extra` carries force_render for regeneration jobs."""
    assert task_path == 'inventory.library_tasks.process_library_file_chunk'
    process_file_chunk(scan_id, chunk, *extra)


def write_stl(path, extents=(10, 10, 10)):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    trimesh.creation.box(extents=extents).export(str(path))
    return path


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class LibraryScannerTestBase(TestCase):
    """Shared fixture: a real on-disk tree under a temp dir.

    Layout:
        <root>/
            top.stl
            widgets/
                gear.stl
                cover.3mf
            empty_leaf/parts_holder/    (no files — must still be navigable)
    """

    def setUp(self):
        self.share_dir = tempfile.mkdtemp(prefix='pv_test_share_')
        self.addCleanup(shutil.rmtree, self.share_dir, ignore_errors=True)

        write_stl(os.path.join(self.share_dir, 'top.stl'), extents=(5, 5, 5))
        write_stl(os.path.join(self.share_dir, 'widgets', 'gear.stl'), extents=(10, 20, 30))
        cover = os.path.join(self.share_dir, 'widgets', 'cover.3mf')
        os.makedirs(os.path.dirname(cover), exist_ok=True)
        trimesh.creation.box(extents=(8, 8, 8)).export(cover)
        os.makedirs(os.path.join(self.share_dir, 'empty_leaf', 'parts_holder'))

        self.root = LibraryRootFactory(path=self.share_dir)

    def scan(self, folder=None):
        """Create + run a scan with eager chunk processing; return the scan."""
        scan = LibraryScan.objects.create(root=self.root, folder=folder)
        with mock.patch.object(library_scanner, 'async_task', side_effect=_eager_async_task):
            run_scan(scan.pk)
        scan.refresh_from_db()
        return scan

    def file_row(self, relative_path):
        return LibraryFile.objects.get(root=self.root, relative_path=relative_path)

    def folder_row(self, relative_path):
        return LibraryFolder.objects.get(root=self.root, relative_path=relative_path)


class InitialScanTest(LibraryScannerTestBase):
    def test_initial_scan_mirrors_tree_and_processes_files(self):
        """First scan creates folder rows (including empty dirs), file rows
        with hash/thumbnail/bounding box, and finishes successfully."""
        scan = self.scan()

        self.assertEqual(scan.status, 'success')
        self.assertEqual(scan.files_seen, 3)
        self.assertEqual(scan.files_queued, 3)
        self.assertEqual(scan.files_processed, 3)

        # Folder tree mirrored, root row anchored at relative_path ''
        root_folder = self.folder_row('')
        self.assertIsNone(root_folder.parent)
        widgets = self.folder_row('widgets')
        self.assertEqual(widgets.parent, root_folder)
        # Empty directories still get rows — core navigation decision
        holder = self.folder_row('empty_leaf/parts_holder')
        self.assertEqual(holder.parent, self.folder_row('empty_leaf'))

        gear = self.file_row('widgets/gear.stl')
        self.assertEqual(gear.extension, 'stl')
        self.assertEqual(gear.status, 'active')
        self.assertEqual(len(gear.sha256_hash), 64)
        self.assertTrue(gear.thumbnail)
        self.assertEqual(gear.thumbnail_status, 'rendered')
        self.assertAlmostEqual(gear.bounding_box_x, 10.0, places=3)
        self.assertAlmostEqual(gear.bounding_box_y, 20.0, places=3)
        self.assertAlmostEqual(gear.bounding_box_z, 30.0, places=3)

        self.root.refresh_from_db()
        self.assertEqual(self.root.last_scan_status, 'success')
        self.assertIsNotNone(self.root.last_scanned_at)

    def test_long_source_filename_still_thumbnails(self):
        """A file whose name would overflow the thumbnail ImageField's
        max_length must still render + persist (regression: thumbnail names
        were derived from the long, non-unique source STL name and failed with
        SuspiciousFileOperation, wedging the file on every rescan). The stored
        name is keyed on the row pk instead."""
        long_stem = 'STH-36_and_BTT_EBB36_orbiter_2.0_mounting_plate_strain_relief_EBB_PUG_mount_' + 'x' * 60
        write_stl(os.path.join(self.share_dir, f'{long_stem}.stl'), extents=(6, 6, 6))

        scan = self.scan()

        self.assertEqual(scan.status, 'success')
        row = self.file_row(f'{long_stem}.stl')
        self.assertTrue(row.thumbnail)
        self.assertEqual(len(row.sha256_hash), 64)
        self.assertIn(f'{row.pk}_thumb', os.path.basename(row.thumbnail.name))
        self.assertLessEqual(len(row.thumbnail.name), 100)

    def test_non_model_files_ignored(self):
        """Only .stl/.3mf are indexed."""
        with open(os.path.join(self.share_dir, 'readme.txt'), 'w') as fh:
            fh.write('not a model')

        scan = self.scan()

        self.assertEqual(scan.files_seen, 3)
        self.assertFalse(
            LibraryFile.objects.filter(root=self.root, filename='readme.txt').exists()
        )


class RescanTest(LibraryScannerTestBase):
    def test_unchanged_files_not_reprocessed(self):
        """A rescan with nothing changed queues zero files (stat-first skip)."""
        self.scan()
        gear_before = self.file_row('widgets/gear.stl')

        rescan = self.scan()

        self.assertEqual(rescan.status, 'success')
        self.assertEqual(rescan.files_seen, 3)
        self.assertEqual(rescan.files_queued, 0)
        gear_after = self.file_row('widgets/gear.stl')
        self.assertEqual(gear_after.sha256_hash, gear_before.sha256_hash)
        self.assertEqual(gear_after.thumbnail.name, gear_before.thumbnail.name)
        self.assertGreater(gear_after.last_seen_at, gear_before.last_seen_at)

    def test_changed_file_is_reprocessed(self):
        """A stat mismatch (size/mtime) triggers re-hash and re-render."""
        self.scan()
        gear_before = self.file_row('widgets/gear.stl')
        gear_path = os.path.join(self.share_dir, 'widgets', 'gear.stl')
        write_stl(gear_path, extents=(1, 2, 3))
        st = os.stat(gear_path)
        os.utime(gear_path, (st.st_atime, st.st_mtime + 60))

        rescan = self.scan()

        self.assertEqual(rescan.files_queued, 1)
        gear_after = self.file_row('widgets/gear.stl')
        self.assertNotEqual(gear_after.sha256_hash, gear_before.sha256_hash)
        self.assertAlmostEqual(gear_after.bounding_box_z, 3.0, places=3)

    def test_touched_mtime_same_content_keeps_assets(self):
        """mtime bump with identical bytes re-hashes but keeps the render."""
        self.scan()
        gear_before = self.file_row('widgets/gear.stl')
        gear_path = os.path.join(self.share_dir, 'widgets', 'gear.stl')
        st = os.stat(gear_path)
        os.utime(gear_path, (st.st_atime, st.st_mtime + 60))

        rescan = self.scan()

        self.assertEqual(rescan.files_queued, 1)
        gear_after = self.file_row('widgets/gear.stl')
        self.assertEqual(gear_after.sha256_hash, gear_before.sha256_hash)
        self.assertEqual(gear_after.thumbnail.name, gear_before.thumbnail.name)


class DeletionSweepTest(LibraryScannerTestBase):
    def test_removed_file_soft_deleted(self):
        """A file missing from the walk flips to status='deleted', not gone."""
        self.scan()
        os.remove(os.path.join(self.share_dir, 'top.stl'))

        self.scan()

        top = self.file_row('top.stl')
        self.assertEqual(top.status, 'deleted')

    def test_removed_folder_soft_deleted(self):
        """A removed directory soft-deletes its folder row and file rows."""
        self.scan()
        shutil.rmtree(os.path.join(self.share_dir, 'widgets'))

        self.scan()

        self.assertEqual(self.folder_row('widgets').status, 'deleted')
        self.assertEqual(self.file_row('widgets/gear.stl').status, 'deleted')

    def test_restored_file_resurrected_without_reprocessing(self):
        """A soft-deleted file reappearing with identical stat comes back
        active without a re-render (hash retained across soft-delete)."""
        self.scan()
        gear_path = os.path.join(self.share_dir, 'widgets', 'gear.stl')
        backup = gear_path + '.bak'
        os.rename(gear_path, backup)
        # rename keeps mtime, but it's now an unindexed extension → swept
        self.scan()
        self.assertEqual(self.file_row('widgets/gear.stl').status, 'deleted')

        os.rename(backup, gear_path)
        rescan = self.scan()

        self.assertEqual(rescan.files_queued, 0)
        self.assertEqual(self.file_row('widgets/gear.stl').status, 'active')


class MoveDetectionTest(LibraryScannerTestBase):
    def test_moved_file_keeps_row_identity_and_assets(self):
        """Moving a file transfers the existing row to the new path (same pk,
        same thumbnail) instead of delete+recreate."""
        self.scan()
        gear_before = self.file_row('widgets/gear.stl')
        old_thumb = gear_before.thumbnail.name
        src = os.path.join(self.share_dir, 'widgets', 'gear.stl')
        dst = os.path.join(self.share_dir, 'moved_gear.stl')
        shutil.move(src, dst)

        self.scan()

        moved = self.file_row('moved_gear.stl')
        self.assertEqual(moved.pk, gear_before.pk)
        self.assertEqual(moved.status, 'active')
        self.assertEqual(moved.filename, 'moved_gear.stl')
        self.assertEqual(moved.thumbnail.name, old_thumb)
        self.assertFalse(
            LibraryFile.objects.filter(root=self.root, relative_path='widgets/gear.stl').exists()
        )

    def test_duplicate_content_copies_assets_without_rerender(self):
        """A copied file (same hash, original still active) reuses the twin's
        assets instead of rendering again."""
        self.scan()
        src = os.path.join(self.share_dir, 'widgets', 'gear.stl')
        shutil.copy2(src, os.path.join(self.share_dir, 'gear_copy.stl'))

        with mock.patch.object(
            library_scanner, 'generate_library_file_assets',
            side_effect=AssertionError("duplicate content must not re-render"),
        ):
            self.scan()

        copy_row = self.file_row('gear_copy.stl')
        original = self.file_row('widgets/gear.stl')
        self.assertEqual(copy_row.sha256_hash, original.sha256_hash)
        self.assertTrue(copy_row.thumbnail)
        self.assertNotEqual(copy_row.thumbnail.name, original.thumbnail.name)
        self.assertEqual(copy_row.bounding_box_x, original.bounding_box_x)
        self.assertEqual(original.status, 'active')


class ScopedRescanTest(LibraryScannerTestBase):
    def test_scoped_rescan_only_sweeps_its_subtree(self):
        """Rescanning one folder must not touch sibling folders' rows."""
        write_stl(os.path.join(self.share_dir, 'other', 'brace.stl'))
        self.scan()
        # Delete one file in each of two sibling folders on disk
        os.remove(os.path.join(self.share_dir, 'widgets', 'gear.stl'))
        os.remove(os.path.join(self.share_dir, 'other', 'brace.stl'))

        widgets = self.folder_row('widgets')
        scoped = self.scan(folder=widgets)

        self.assertEqual(scoped.status, 'success')
        # In-scope deletion swept…
        self.assertEqual(self.file_row('widgets/gear.stl').status, 'deleted')
        # …but the sibling folder's deletion is untouched until its own scan
        self.assertEqual(self.file_row('other/brace.stl').status, 'active')
        self.assertEqual(self.file_row('top.stl').status, 'active')

    def test_scoped_rescan_picks_up_new_file_in_scope(self):
        self.scan()
        write_stl(os.path.join(self.share_dir, 'widgets', 'new_part.stl'))

        scoped = self.scan(folder=self.folder_row('widgets'))

        self.assertEqual(scoped.files_queued, 1)
        self.assertEqual(self.file_row('widgets/new_part.stl').status, 'active')


class ScanGuardsTest(LibraryScannerTestBase):
    def test_missing_root_path_fails_scan(self):
        """A root pointing at a nonexistent directory errors cleanly."""
        bad_root = LibraryRootFactory(path=os.path.join(self.share_dir, 'nope'))
        scan = LibraryScan.objects.create(root=bad_root)

        run_scan(scan.pk)
        scan.refresh_from_db()

        self.assertEqual(scan.status, 'error')
        self.assertIn('nope', scan.error)
        bad_root.refresh_from_db()
        self.assertEqual(bad_root.last_scan_status, 'error')

    def test_non_pending_scan_not_rerun(self):
        """Task redelivery on an already-running scan is a no-op."""
        scan = LibraryScan.objects.create(root=self.root, status='running')

        run_scan(scan.pk)
        scan.refresh_from_db()

        self.assertEqual(scan.status, 'running')
        self.assertEqual(scan.files_seen, 0)

    def test_path_escape_marks_file_deleted(self):
        """A row whose relative_path escapes the root is refused and
        soft-deleted, never opened."""
        self.scan()
        evil_target = write_stl(os.path.join(os.path.dirname(self.share_dir), 'evil.stl'))
        self.addCleanup(os.remove, evil_target)
        root_folder = self.folder_row('')
        evil = LibraryFile.objects.create(
            root=self.root,
            folder=root_folder,
            filename='evil.stl',
            relative_path='../evil.stl',
            extension='stl',
            size_bytes=1,
            modified_time=self.file_row('top.stl').modified_time,
        )

        process_file_chunk(
            LibraryScan.objects.create(root=self.root, status='running').pk,
            [evil.pk],
        )

        evil.refresh_from_db()
        self.assertEqual(evil.status, 'deleted')
        self.assertIsNone(evil.sha256_hash)


class ThumbnailRegenerationTest(LibraryScannerTestBase):
    def test_regeneration_rerenders_all_in_new_color(self):
        """Changing thumbnail_color + regenerating re-renders every active
        file (content hashes untouched) in the new color."""
        self.scan()
        gear_before = self.file_row('widgets/gear.stl')
        self.root.thumbnail_color = '#ff0000'
        self.root.save()

        regen = LibraryScan.objects.create(root=self.root)
        with mock.patch.object(library_scanner, 'async_task', side_effect=_eager_async_task):
            library_scanner.run_regeneration(regen.pk)
        regen.refresh_from_db()

        self.assertEqual(regen.status, 'success')
        self.assertEqual(regen.files_queued, 3)
        self.assertEqual(regen.files_processed, 3)

        gear_after = self.file_row('widgets/gear.stl')
        self.assertEqual(gear_after.sha256_hash, gear_before.sha256_hash)
        self.assertTrue(gear_after.thumbnail)
        from PIL import Image
        with gear_after.thumbnail.open('rb') as fh:
            img = Image.open(fh).convert('RGBA')
            center = img.getpixel((128, 128))
        self.assertEqual(center[3], 255)
        self.assertGreater(center[0], 80)   # red channel dominates
        self.assertLess(center[1], 50)
        self.assertLess(center[2], 50)

    def test_regeneration_refused_while_scan_running(self):
        """The shared per-root slot also blocks regeneration during a scan."""
        LibraryScan.objects.create(root=self.root, status='running')

        with mock.patch.object(library_scanner, 'async_task') as mock_async:
            result = library_scanner.start_thumbnail_regeneration(self.root)

        self.assertIsNone(result)
        mock_async.assert_not_called()

    def test_regeneration_tags_scan_kind_thumbnails(self):
        """A regeneration job is discriminated as kind='thumbnails' so a
        re-attached progress banner can label it correctly."""
        with mock.patch.object(library_scanner, 'async_task') as mock_async:
            scan = library_scanner.start_thumbnail_regeneration(self.root)

        self.assertIsNotNone(scan)
        self.assertEqual(scan.kind, 'thumbnails')
        mock_async.assert_called_once_with(
            'inventory.library_tasks.run_thumbnail_regeneration', scan.pk
        )


class ScanResultCountsTest(LibraryScannerTestBase):
    """The per-scan result breakdown (files_new / files_updated / files_deleted)
    that backs the settings screen's 'what the last scan found' summary."""

    def test_initial_scan_counts_all_files_new(self):
        scan = self.scan()

        self.assertEqual(scan.files_new, 3)
        self.assertEqual(scan.files_updated, 0)
        self.assertEqual(scan.files_deleted, 0)

    def test_unchanged_rescan_counts_zero(self):
        self.scan()

        rescan = self.scan()

        self.assertEqual(rescan.files_new, 0)
        self.assertEqual(rescan.files_updated, 0)
        self.assertEqual(rescan.files_deleted, 0)

    def test_added_file_counts_as_new(self):
        self.scan()
        write_stl(os.path.join(self.share_dir, 'widgets', 'new_part.stl'))

        rescan = self.scan()

        self.assertEqual(rescan.files_new, 1)
        self.assertEqual(rescan.files_updated, 0)
        self.assertEqual(rescan.files_deleted, 0)

    def test_changed_file_counts_as_updated(self):
        self.scan()
        gear_path = os.path.join(self.share_dir, 'widgets', 'gear.stl')
        write_stl(gear_path, extents=(1, 2, 3))
        st = os.stat(gear_path)
        os.utime(gear_path, (st.st_atime, st.st_mtime + 60))

        rescan = self.scan()

        self.assertEqual(rescan.files_new, 0)
        self.assertEqual(rescan.files_updated, 1)
        self.assertEqual(rescan.files_deleted, 0)

    def test_removed_file_counts_as_deleted(self):
        self.scan()
        os.remove(os.path.join(self.share_dir, 'top.stl'))

        rescan = self.scan()

        self.assertEqual(rescan.files_new, 0)
        self.assertEqual(rescan.files_updated, 0)
        self.assertEqual(rescan.files_deleted, 1)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ThumbnailStatusTest(TestCase):
    """_render_and_save records WHY a file does/doesn't get a preview so the UI
    can explain a blank thumbnail (too large vs unrenderable vs rendered)."""

    def setUp(self):
        self.root = LibraryRootFactory(path='/tmp/lib')
        self.folder = LibraryFolderFactory(root=self.root, relative_path='')

    def _make_file(self, size_bytes):
        return LibraryFile.objects.create(
            root=self.root, folder=self.folder, filename='m.stl',
            relative_path=f'm{size_bytes}.stl', extension='stl',
            size_bytes=size_bytes, modified_time=timezone.now(),
        )

    def test_successful_render_marked_rendered(self):
        f = self._make_file(1000)
        assets = {'png_bytes': _tiny_png_bytes(), 'bounding_box': (1.0, 2.0, 3.0)}
        with mock.patch.object(library_scanner, 'generate_library_file_assets', return_value=assets):
            library_scanner._render_and_save(self.root, f, '/x/m.stl', 'a' * 64)
        f.refresh_from_db()
        self.assertEqual(f.thumbnail_status, 'rendered')
        self.assertTrue(f.thumbnail)

    def test_unreadable_mesh_marked_unrenderable(self):
        f = self._make_file(1000)  # under the cap, but render returns None
        with mock.patch.object(library_scanner, 'generate_library_file_assets', return_value=None):
            library_scanner._render_and_save(self.root, f, '/x/m.stl', 'a' * 64)
        f.refresh_from_db()
        self.assertEqual(f.thumbnail_status, 'unrenderable')
        self.assertFalse(f.thumbnail)

    def test_oversized_file_marked_too_large(self):
        f = self._make_file(MAX_RENDER_FILE_SIZE_BYTES + 1)
        with mock.patch.object(library_scanner, 'generate_library_file_assets', return_value=None):
            library_scanner._render_and_save(self.root, f, '/x/m.stl', 'a' * 64)
        f.refresh_from_db()
        self.assertEqual(f.thumbnail_status, 'too_large')


class ReapStalledScansTest(TestCase):
    """reap_stalled_scans finalizes scans stuck 'running' after a chunk worker
    died. OrmQ is naturally empty in the test DB, so the queue-empty gate is
    satisfied without mocking except where a non-empty queue is under test."""

    def _stalled_scan(self, **kwargs):
        from datetime import timedelta
        from inventory.tests.factories import LibraryScanFactory
        defaults = dict(
            status='running', files_queued=100, files_processed=97,
            started_at=timezone.now() - timedelta(seconds=3600),
        )
        defaults.update(kwargs)
        return LibraryScanFactory(root=LibraryRootFactory(), **defaults)

    def test_reaps_stalled_processing_scan(self):
        scan = self._stalled_scan()
        reaped = library_scanner.reap_stalled_scans()
        scan.refresh_from_db()
        self.assertEqual(reaped, 1)
        self.assertEqual(scan.status, 'success')
        self.assertIn('unprocessed', scan.error)
        self.assertEqual(scan.root.last_scan_status, 'success')

    def test_does_not_reap_walk_phase_scan(self):
        # files_queued == 0: the walk hasn't finished enqueuing; never cut short.
        scan = self._stalled_scan(files_queued=0, files_processed=0)
        self.assertEqual(library_scanner.reap_stalled_scans(), 0)
        scan.refresh_from_db()
        self.assertEqual(scan.status, 'running')

    def test_does_not_reap_recent_scan(self):
        scan = self._stalled_scan(started_at=timezone.now())
        self.assertEqual(library_scanner.reap_stalled_scans(), 0)
        scan.refresh_from_db()
        self.assertEqual(scan.status, 'running')

    @staticmethod
    def _queued_task(func_path):
        row = mock.Mock()
        row.func.return_value = func_path
        return row

    def test_does_not_reap_when_scan_work_is_queued(self):
        scan = self._stalled_scan()
        with mock.patch('django_q.models.OrmQ.objects') as q:
            q.all.return_value = [
                self._queued_task('inventory.library_tasks.process_library_file_chunk'),
            ]
            self.assertEqual(library_scanner.reap_stalled_scans(), 0)
        scan.refresh_from_db()
        self.assertEqual(scan.status, 'running')

    def test_reaps_despite_own_queue_row_and_unrelated_tasks(self):
        """The reaper is itself a queued task while executing (the ORM broker
        keeps the row until post-completion ack), so its own row — and any
        non-library task — must NOT postpone reaping, or nothing ever reaps."""
        scan = self._stalled_scan()
        with mock.patch('django_q.models.OrmQ.objects') as q:
            q.all.return_value = [
                self._queued_task('inventory.library_tasks.reap_stalled_library_scans'),
                self._queued_task('inventory.tasks.some_unrelated_task'),
            ]
            self.assertEqual(library_scanner.reap_stalled_scans(), 1)
        scan.refresh_from_db()
        self.assertEqual(scan.status, 'success')


class FolderTagStampOnScanTest(LibraryScannerTestBase):
    """New files discovered under a tagged folder inherit that folder's tags on
    a rescan; pre-existing files are not retro-stamped (only new rows inherit)."""

    def test_new_file_inherits_folder_tags_on_rescan(self):
        from inventory.models import Tag

        self.scan()  # initial index: creates widgets/ + gear.stl, cover.3mf
        widgets = self.folder_row('widgets')
        rack = Tag.objects.create(name='rack', slug='rack')
        widgets.tags.add(rack)

        write_stl(os.path.join(self.share_dir, 'widgets', 'newpart.stl'), extents=(4, 4, 4))
        self.scan()

        new_row = self.file_row('widgets/newpart.stl')
        self.assertIn('rack', new_row.tags.values_list('slug', flat=True))
        # Files that already existed before the folder was tagged stay untouched.
        gear = self.file_row('widgets/gear.stl')
        self.assertNotIn('rack', gear.tags.values_list('slug', flat=True))


class ActiveScanUniquenessTest(TestCase):
    """The DB-level per-root concurrency guard (partial unique constraint):
    at most one pending/running LibraryScan per root."""

    def test_second_active_scan_for_root_is_rejected(self):
        from django.db import IntegrityError, transaction

        root = LibraryRootFactory()
        LibraryScan.objects.create(root=root, status='running')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LibraryScan.objects.create(root=root, status='pending')

    def test_finished_scans_do_not_occupy_the_slot(self):
        root = LibraryRootFactory()
        LibraryScan.objects.create(root=root, status='success')
        LibraryScan.objects.create(root=root, status='error')
        # A fresh pending scan is allowed once the prior ones are finalized.
        LibraryScan.objects.create(root=root, status='pending')

    def test_different_roots_are_independent(self):
        LibraryScan.objects.create(root=LibraryRootFactory(), status='running')
        LibraryScan.objects.create(root=LibraryRootFactory(), status='running')
