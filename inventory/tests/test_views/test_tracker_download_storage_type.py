"""
Regression tests: TrackerViewSet._download_tracker_files_for_manual (used by
create_manual) and TrackerViewSet._download_new_files (used by add_files)
must reclassify a successfully-downloaded file's storage_type from the model
default ('link') to 'local'. Neither did before this fix -- confirmed by
inspection, every GitHub-URL download path left storage_type stuck at
'link' forever, even for files with a real local copy. The only path that
already did this correctly was the direct-upload endpoint (a different
code path entirely).

This is exactly why auto-thumbnail generation appeared to silently fail for
"Download and Store Locally" trackers: generate_auto_thumbnail's own guard
correctly treats storage_type='link' files as needing explicit permission to
fetch remotely, and these files were never actually reclassified as local,
so they were treated as ungenerated links forever.

Mirrors the mocking convention in
test_serializers/test_download_logic.py (mock StorageManager +
FileDownloadService, call the private download method directly).
"""
from unittest.mock import patch

import pytest

from inventory.tests.factories import TrackerFactory, TrackerFileFactory
from inventory.views import TrackerViewSet


@pytest.mark.django_db
class TestDownloadTrackerFilesForManualStorageType:
    @patch('inventory.views.StorageManager')
    @patch('inventory.views.FileDownloadService')
    def test_successful_download_sets_storage_type_local(self, mock_download_service_class, mock_storage_manager_class):
        tracker = TrackerFactory(storage_type='local')
        tracker_file = TrackerFileFactory(
            tracker=tracker, filename='part.stl', file_size=1000, directory_path='test'
        )

        mock_storage = mock_storage_manager_class.return_value
        mock_storage.check_available_space.return_value = {'sufficient': True}
        mock_storage.get_tracker_storage_path.return_value = '/media/trackers/1'
        mock_storage.get_category_path.return_value = '/media/trackers/1/files/test'
        mock_storage.sanitize_filename.side_effect = lambda x: x

        mock_download = mock_download_service_class.return_value
        mock_download.download_files_batch.return_value = {
            'successful': [{
                'tracker_file_id': tracker_file.id,
                'checksum': 'abc123',
                'bytes_downloaded': 1000,
                'duration': 1.0,
            }],
            'failed': [],
            'duration': 1.0,
        }

        viewset = TrackerViewSet()
        viewset._download_tracker_files_for_manual(tracker, [tracker_file])

        tracker_file.refresh_from_db()
        assert tracker_file.storage_type == 'local'
        assert tracker_file.download_status == 'completed'

    @patch('inventory.views.StorageManager')
    @patch('inventory.views.FileDownloadService')
    def test_failed_download_leaves_storage_type_as_link(self, mock_download_service_class, mock_storage_manager_class):
        tracker = TrackerFactory(storage_type='local')
        tracker_file = TrackerFileFactory(
            tracker=tracker, filename='part.stl', file_size=1000, directory_path='test'
        )

        mock_storage = mock_storage_manager_class.return_value
        mock_storage.check_available_space.return_value = {'sufficient': True}
        mock_storage.get_tracker_storage_path.return_value = '/media/trackers/1'
        mock_storage.get_category_path.return_value = '/media/trackers/1/files/test'
        mock_storage.sanitize_filename.side_effect = lambda x: x

        mock_download = mock_download_service_class.return_value
        mock_download.download_files_batch.return_value = {
            'successful': [],
            'failed': [{'tracker_file_id': tracker_file.id, 'error': 'Network timeout'}],
            'duration': 1.0,
        }

        viewset = TrackerViewSet()
        viewset._download_tracker_files_for_manual(tracker, [tracker_file])

        tracker_file.refresh_from_db()
        assert tracker_file.storage_type == 'link'
        assert tracker_file.download_status == 'failed'


@pytest.mark.django_db
class TestDownloadNewFilesStorageType:
    @patch('inventory.views.StorageManager')
    @patch('inventory.views.FileDownloadService')
    def test_successful_download_sets_storage_type_local(self, mock_download_service_class, mock_storage_manager_class):
        tracker = TrackerFactory(storage_type='local')
        tracker_file = TrackerFileFactory(
            tracker=tracker, filename='part.stl', file_size=1000, directory_path='test'
        )

        mock_storage = mock_storage_manager_class.return_value
        mock_storage.check_available_space.return_value = {'sufficient': True}
        mock_storage.get_tracker_storage_path.return_value = '/media/trackers/1'
        mock_storage.get_category_path.return_value = '/media/trackers/1/files/test'
        mock_storage.sanitize_filename.side_effect = lambda x: x

        mock_download = mock_download_service_class.return_value
        mock_download.download_files_batch.return_value = {
            'successful': [{
                'tracker_file_id': tracker_file.id,
                'checksum': 'abc123',
                'bytes_downloaded': 1000,
                'duration': 1.0,
            }],
            'failed': [],
            'duration': 1.0,
        }

        viewset = TrackerViewSet()
        viewset._download_new_files(tracker, [tracker_file])

        tracker_file.refresh_from_db()
        assert tracker_file.storage_type == 'local'
        assert tracker_file.download_status == 'completed'
