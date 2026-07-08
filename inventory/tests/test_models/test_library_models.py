"""
Model tests for the STL/3MF Library feature: LibraryRoot, LibraryFolder,
LibraryFile, LibraryScan, and the thumbnail-cleanup signal.
"""
import time

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.test import TestCase

from inventory.models import LibraryFile, LibraryFolder, LibraryRoot, LibraryScan
from inventory.tests.factories import (
    LibraryFileFactory,
    LibraryFolderFactory,
    LibraryRootFactory,
    LibraryScanFactory,
)


class LibraryRootModelTest(TestCase):
    def test_create_with_defaults(self):
        """LibraryRoot initializes with expected defaults and str() shows name and path."""
        root = LibraryRoot.objects.create(name="Alpha Root", path="/mnt/alpha")

        self.assertTrue(root.enabled)
        self.assertEqual(root.last_scan_status, 'idle')
        self.assertIsNone(root.rescan_interval_hours)
        self.assertIn("Alpha Root", str(root))
        self.assertIn("/mnt/alpha", str(root))


class LibraryFolderModelTest(TestCase):
    def test_unique_together_root_relative_path(self):
        """Duplicate (root, relative_path) raises IntegrityError."""
        root = LibraryRootFactory()
        LibraryFolderFactory(root=root, relative_path="shared")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LibraryFolderFactory(root=root, relative_path="shared")

    def test_same_relative_path_allowed_on_different_roots(self):
        """The same relative_path is fine under two different roots."""
        LibraryFolderFactory(root=LibraryRootFactory(), relative_path="shared")
        LibraryFolderFactory(root=LibraryRootFactory(), relative_path="shared")

        self.assertEqual(LibraryFolder.objects.count(), 2)

    def test_parent_child_relationship(self):
        """Child folders link to their parent and appear in parent.children."""
        parent = LibraryFolderFactory()
        child = LibraryFolderFactory(root=parent.root, parent=parent)

        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.children.all())


class LibraryFileModelTest(TestCase):
    def test_unique_together_root_relative_path(self):
        """Duplicate (root, relative_path) raises IntegrityError."""
        folder = LibraryFolderFactory()
        LibraryFileFactory(folder=folder, relative_path="dup.stl")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LibraryFileFactory(folder=folder, relative_path="dup.stl")

    def test_duplicate_sha256_allowed_across_paths(self):
        """sha256_hash is deliberately not unique — real duplicate files share one."""
        folder = LibraryFolderFactory()
        hash_val = "a1" * 32
        LibraryFileFactory(folder=folder, relative_path="file1.stl", sha256_hash=hash_val)
        LibraryFileFactory(folder=folder, relative_path="file2.stl", sha256_hash=hash_val)

        self.assertEqual(LibraryFile.objects.filter(sha256_hash=hash_val).count(), 2)

    def test_defaults(self):
        """LibraryFile initializes with expected defaults."""
        file_obj = LibraryFileFactory()

        self.assertEqual(file_obj.status, 'active')
        self.assertEqual(file_obj.embedded_metadata, {})
        self.assertIsNone(file_obj.sha256_hash)


class LibraryCascadeTest(TestCase):
    def test_deleting_root_cascades(self):
        """Deleting a root cascades to its folders, files, and scans."""
        root = LibraryRootFactory()
        folder = LibraryFolderFactory(root=root)
        LibraryFileFactory(folder=folder)
        LibraryScanFactory(root=root, folder=folder)

        root.delete()

        self.assertEqual(LibraryFolder.objects.count(), 0)
        self.assertEqual(LibraryFile.objects.count(), 0)
        self.assertEqual(LibraryScan.objects.count(), 0)


class LibraryFileThumbnailCleanupTest(TestCase):
    def test_thumbnail_file_removed_on_delete(self):
        """Hard-deleting a LibraryFile removes its thumbnail from storage."""
        file_obj = LibraryFileFactory(
            thumbnail=ContentFile(b'fakepng', name='thumb.png')
        )
        thumbnail_path = file_obj.thumbnail.name
        self.assertTrue(default_storage.exists(thumbnail_path))

        file_obj.delete()

        self.assertFalse(default_storage.exists(thumbnail_path))


class LibraryScanModelTest(TestCase):
    def test_defaults(self):
        """LibraryScan initializes as pending with zeroed counters."""
        scan = LibraryScanFactory()

        self.assertEqual(scan.status, 'pending')
        self.assertEqual(scan.files_seen, 0)
        self.assertEqual(scan.files_queued, 0)
        self.assertEqual(scan.files_processed, 0)

    def test_ordering_newest_first(self):
        """Default ordering returns the most recent scan first."""
        root = LibraryRootFactory()
        LibraryScanFactory(root=root)
        time.sleep(0.01)  # ensure distinct auto_now_add timestamps
        newer = LibraryScanFactory(root=root)

        self.assertEqual(LibraryScan.objects.first(), newer)
