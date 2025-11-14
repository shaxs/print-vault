"""
Test suite for TrackerCreateSerializer download logic.

Tests the complex _download_tracker_files method with StorageManager
and FileDownloadService integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from django.utils import timezone

from inventory.tests.factories import TrackerFactory, TrackerFileFactory


@pytest.mark.django_db
class TestTrackerCreateDownloadLogic:
    """Tests for TrackerCreateSerializer._download_tracker_files method."""
    
    @patch('inventory.serializers.StorageManager')
    @patch('inventory.serializers.FileDownloadService')
    def test_successful_download_all_files(self, mock_download_service_class, mock_storage_manager_class):
        """Test successful download of all files."""
        from inventory.serializers import TrackerCreateSerializer
        
        # Setup tracker and files
        tracker = TrackerFactory(id=1)
        file1 = TrackerFileFactory(
            tracker=tracker,
            filename='part1.stl',
            github_url='https://github.com/user/repo/blob/main/part1.stl',
            file_size=1000,
            directory_path='test'
        )
        file2 = TrackerFileFactory(
            tracker=tracker,
            filename='part2.stl',
            github_url='https://github.com/user/repo/blob/main/part2.stl',
            file_size=2000,
            directory_path='test'
        )
        tracker_files = [file1, file2]
        
        # Mock StorageManager
        mock_storage = mock_storage_manager_class.return_value
        mock_storage.check_available_space.return_value = {'sufficient': True}
        mock_storage.get_tracker_storage_path.return_value = '/media/trackers/1'
        mock_storage.get_category_path.return_value = '/media/trackers/1/files/test'
        mock_storage.sanitize_filename.side_effect = lambda x: x  # Return unchanged
        
        # Mock FileDownloadService
        mock_download = mock_download_service_class.return_value
        mock_download.download_files_batch.return_value = {
            'successful': [
                {
                    'tracker_file_id': file1.id,
                    'checksum': 'abc123',
                    'bytes_downloaded': 1000,
                    'duration': 1.5
                },
                {
                    'tracker_file_id': file2.id,
                    'checksum': 'def456',
                    'bytes_downloaded': 2000,
                    'duration': 2.0
                }
            ],
            'failed': [],
            'duration': 3.5
        }
        
        # Execute download
        serializer = TrackerCreateSerializer()
        results = serializer._download_tracker_files(tracker, tracker_files)
        
        # Verify results
        assert len(results['successful']) == 2
        assert len(results['failed']) == 0
        assert results['total_bytes'] == 3000
        
        # Verify file updates
        file1.refresh_from_db()
        file2.refresh_from_db()
        assert file1.download_status == 'completed'
        assert file1.file_checksum == 'abc123'
        assert file1.actual_file_size == 1000
        assert file2.download_status == 'completed'
        assert file2.file_checksum == 'def456'
        
        # Verify tracker updates
        tracker.refresh_from_db()
        assert tracker.storage_path == '/media/trackers/1'
        assert tracker.total_storage_used == 3000
        assert tracker.files_downloaded is True
    
    @patch('inventory.serializers.StorageManager')
    @patch('inventory.serializers.FileDownloadService')
    def test_partial_download_failure(self, mock_download_service_class, mock_storage_manager_class):
        """Test partial failure - some files succeed, some fail."""
        from inventory.serializers import TrackerCreateSerializer
        
        tracker = TrackerFactory(id=2)
        file1 = TrackerFileFactory(tracker=tracker, filename='success.stl', file_size=1000)
        file2 = TrackerFileFactory(tracker=tracker, filename='failure.stl', file_size=2000)
        tracker_files = [file1, file2]
        
        # Mock successful space check and path creation
        mock_storage = mock_storage_manager_class.return_value
        mock_storage.check_available_space.return_value = {'sufficient': True}
        mock_storage.get_tracker_storage_path.return_value = '/media/trackers/2'
        mock_storage.get_category_path.return_value = '/media/trackers/2/files/uncategorized'
        mock_storage.sanitize_filename.side_effect = lambda x: x
        
        # Mock mixed download results
        mock_download = mock_download_service_class.return_value
        mock_download.download_files_batch.return_value = {
            'successful': [
                {
                    'tracker_file_id': file1.id,
                    'checksum': 'abc123',
                    'bytes_downloaded': 1000,
                    'duration': 1.0
                }
            ],
            'failed': [
                {
                    'tracker_file_id': file2.id,
                    'error': 'Network timeout'
                }
            ],
            'duration': 5.0
        }
        
        serializer = TrackerCreateSerializer()
        results = serializer._download_tracker_files(tracker, tracker_files)
        
        # Verify results
        assert len(results['successful']) == 1
        assert len(results['failed']) == 1
        assert results['total_bytes'] == 1000
        assert results['failed'][0]['error'] == 'Network timeout'
        
        # Verify file statuses
        file1.refresh_from_db()
        file2.refresh_from_db()
        assert file1.download_status == 'completed'
        assert file2.download_status == 'failed'
        assert file2.download_error == 'Network timeout'
        
        # Tracker should show partial completion
        tracker.refresh_from_db()
        assert tracker.files_downloaded is False  # Not all succeeded
    
    @patch('inventory.serializers.StorageManager')
    def test_insufficient_disk_space_before_download(self, mock_storage_manager_class):
        """Test insufficient disk space caught before download starts."""
        from inventory.serializers import TrackerCreateSerializer
        
        tracker = TrackerFactory(id=3)
        file1 = TrackerFileFactory(tracker=tracker, filename='large.stl', file_size=10000000000)
        tracker_files = [file1]
        
        # Mock insufficient space
        mock_storage = mock_storage_manager_class.return_value
        mock_storage.check_available_space.return_value = {
            'sufficient': False,
            'available_formatted': '1.5 GB'
        }
        mock_storage._format_bytes.return_value = '9.31 GB'
        
        serializer = TrackerCreateSerializer()
        results = serializer._download_tracker_files(tracker, tracker_files)
        
        # Verify failure
        assert len(results['successful']) == 0
        assert len(results['failed']) == 1
        assert 'Insufficient disk space' in results['failed'][0]['error']
        assert results['error'] == 'Insufficient disk space'
        
        # Verify file marked as failed
        file1.refresh_from_db()
        assert file1.download_status == 'failed'
        assert 'Insufficient disk space' in file1.download_error
    
    @patch('inventory.serializers.StorageManager')
    def test_insufficient_storage_error_exception(self, mock_storage_manager_class):
        """Test InsufficientStorageError exception handling."""
        from inventory.serializers import TrackerCreateSerializer
        from inventory.services.storage_manager import InsufficientStorageError
        
        tracker = TrackerFactory(id=4)
        file1 = TrackerFileFactory(tracker=tracker, filename='file.stl', file_size=1000)
        tracker_files = [file1]
        
        # Mock exception
        mock_storage = mock_storage_manager_class.return_value
        mock_storage.check_available_space.side_effect = InsufficientStorageError('Not enough space')
        
        serializer = TrackerCreateSerializer()
        results = serializer._download_tracker_files(tracker, tracker_files)
        
        # Verify exception handled
        assert len(results['failed']) == 1
        assert 'Not enough space' in results['failed'][0]['error']
        
        file1.refresh_from_db()
        assert file1.download_status == 'failed'
    
    @patch('inventory.serializers.StorageManager')
    def test_storage_permission_error_exception(self, mock_storage_manager_class):
        """Test StoragePermissionError exception handling."""
        from inventory.serializers import TrackerCreateSerializer
        from inventory.services.storage_manager import StoragePermissionError
        
        tracker = TrackerFactory(id=5)
        file1 = TrackerFileFactory(tracker=tracker, filename='file.stl', file_size=1000)
        tracker_files = [file1]
        
        # Mock permission error
        mock_storage = mock_storage_manager_class.return_value
        mock_storage.check_available_space.side_effect = StoragePermissionError('Permission denied')
        
        serializer = TrackerCreateSerializer()
        results = serializer._download_tracker_files(tracker, tracker_files)
        
        # Verify permission error handled
        assert len(results['failed']) == 1
        assert 'Storage permission error' in results['failed'][0]['error']
        
        file1.refresh_from_db()
        assert file1.download_status == 'failed'
    
    @patch('inventory.serializers.StorageManager')
    def test_storage_path_creation_failure(self, mock_storage_manager_class):
        """Test failure when creating tracker storage path."""
        from inventory.serializers import TrackerCreateSerializer
        
        tracker = TrackerFactory(id=6)
        file1 = TrackerFileFactory(tracker=tracker, filename='file.stl', file_size=1000)
        tracker_files = [file1]
        
        # Mock space check success but path creation failure
        mock_storage = mock_storage_manager_class.return_value
        mock_storage.check_available_space.return_value = {'sufficient': True}
        mock_storage.get_tracker_storage_path.side_effect = Exception('Cannot create directory')
        
        serializer = TrackerCreateSerializer()
        results = serializer._download_tracker_files(tracker, tracker_files)
        
        # Verify path creation failure handled
        assert len(results['failed']) == 1
        assert 'Failed to create storage path' in results['failed'][0]['error']
        
        file1.refresh_from_db()
        assert file1.download_status == 'failed'
    
    @patch('inventory.serializers.StorageManager')
    @patch('inventory.serializers.FileDownloadService')
    def test_empty_file_list(self, mock_download_service_class, mock_storage_manager_class):
        """Test download with empty file list."""
        from inventory.serializers import TrackerCreateSerializer
        
        tracker = TrackerFactory(id=7)
        tracker_files = []
        
        serializer = TrackerCreateSerializer()
        results = serializer._download_tracker_files(tracker, tracker_files)
        
        # With no files, should return empty results quickly
        # Exact behavior depends on implementation - adjust as needed
        assert len(results['successful']) == 0
        assert len(results['failed']) == 0
    
    @patch('inventory.serializers.StorageManager')
    @patch('inventory.serializers.FileDownloadService')
    def test_file_path_sanitization(self, mock_download_service_class, mock_storage_manager_class):
        """Test that filenames are properly sanitized."""
        from inventory.serializers import TrackerCreateSerializer
        
        tracker = TrackerFactory(id=8)
        file1 = TrackerFileFactory(
            tracker=tracker,
            filename='bad/file\\name.stl',  # Unsafe filename
            file_size=1000,
            directory_path='test/../hack'  # Unsafe path
        )
        tracker_files = [file1]
        
        # Mock sanitization
        mock_storage = mock_storage_manager_class.return_value
        mock_storage.check_available_space.return_value = {'sufficient': True}
        mock_storage.get_tracker_storage_path.return_value = '/media/trackers/8'
        mock_storage.get_category_path.return_value = '/media/trackers/8/files/safe'
        mock_storage.sanitize_filename.side_effect = lambda x: x.replace('/', '_').replace('\\', '_').replace('..', '')
        
        # Mock successful download
        mock_download = mock_download_service_class.return_value
        mock_download.download_files_batch.return_value = {
            'successful': [{
                'tracker_file_id': file1.id,
                'checksum': 'abc',
                'bytes_downloaded': 1000,
                'duration': 1.0
            }],
            'failed': [],
            'duration': 1.0
        }
        
        serializer = TrackerCreateSerializer()
        results = serializer._download_tracker_files(tracker, tracker_files)
        
        # Verify sanitization was called
        assert mock_storage.sanitize_filename.call_count >= 2  # Called for filename and category
        assert len(results['successful']) == 1
