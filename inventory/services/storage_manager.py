"""
Storage Manager Service for Print Vault Trackers

Handles file storage operations including:
- Disk space checking
- Path management
- File cleanup
- Storage statistics
"""

import os
import shutil
import errno
from pathlib import Path
from django.conf import settings


class InsufficientStorageError(Exception):
    """Raised when there is not enough disk space available."""
    pass


class StoragePermissionError(Exception):
    """Raised when there are permission issues with storage directories."""
    pass


class StorageManager:
    """Manages file storage for tracker files."""
    
    def __init__(self):
        """Initialize storage manager with settings."""
        self.base_path = getattr(settings, 'TRACKER_STORAGE', {}).get(
            'BASE_PATH',
            os.path.join(settings.MEDIA_ROOT, 'trackers')
        )
        self.organize_by_category = getattr(settings, 'TRACKER_STORAGE', {}).get(
            'ORGANIZE_BY_CATEGORY',
            True
        )
        self.min_free_space = getattr(settings, 'TRACKER_STORAGE', {}).get(
            'MIN_FREE_SPACE',
            5 * 1024 * 1024 * 1024  # 5 GB default
        )
    
    def check_available_space(self, required_bytes):
        """
        Check if enough disk space is available.
        
        Args:
            required_bytes (int): Number of bytes needed
            
        Returns:
            dict: {
                'sufficient': bool,
                'available': int,
                'required': int,
                'after_download': int
            }
            
        Raises:
            InsufficientStorageError: If not enough space available
        """
        # Ensure base path exists
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path, exist_ok=True)
        
        # Get disk usage statistics
        stat = shutil.disk_usage(self.base_path)
        available = stat.free
        
        # Add buffer (10% extra space required)
        required_with_buffer = int(required_bytes * 1.1)
        
        # Check if we have enough space
        sufficient = available >= required_with_buffer
        
        result = {
            'sufficient': sufficient,
            'available': available,
            'required': required_bytes,
            'required_with_buffer': required_with_buffer,
            'after_download': available - required_with_buffer,
            'min_free_space': self.min_free_space,
        }
        
        # Also check against minimum free space setting
        if result['after_download'] < self.min_free_space:
            result['sufficient'] = False
            result['shortage'] = self.min_free_space - result['after_download']
        
        if not sufficient:
            raise InsufficientStorageError(
                f"Insufficient disk space. "
                f"Required: {self._format_bytes(required_with_buffer)}, "
                f"Available: {self._format_bytes(available)}"
            )
        
        return result
    
    def get_tracker_storage_path(self, tracker_id, create=True):
        """
        Get the storage path for a tracker.
        
        Args:
            tracker_id (int): Tracker ID
            create (bool): Whether to create the directory if it doesn't exist
            
        Returns:
            str: Absolute path to tracker's storage directory
            
        Raises:
            StoragePermissionError: If directory cannot be created
        """
        tracker_path = os.path.join(
            self.base_path,
            str(tracker_id),
            'files'
        )
        
        if create and not os.path.exists(tracker_path):
            try:
                os.makedirs(tracker_path, exist_ok=True)
            except PermissionError as e:
                raise StoragePermissionError(
                    f"No write permission for {tracker_path}. "
                    f"Check directory ownership and permissions."
                ) from e
            except OSError as e:
                raise StoragePermissionError(
                    f"Failed to create directory {tracker_path}: {str(e)}"
                ) from e
        
        return tracker_path
    
    def get_category_path(self, tracker_id, category, create=True):
        """
        Get the storage path for a specific category within a tracker.
        
        Args:
            tracker_id (int): Tracker ID
            category (str): Category name (e.g., "Body", "Mount")
            create (bool): Whether to create the directory
            
        Returns:
            str: Absolute path to category directory
        """
        if not self.organize_by_category or not category:
            return self.get_tracker_storage_path(tracker_id, create)
        
        # Sanitize category name for filesystem
        safe_category = self.sanitize_filename(category)
        category_path = os.path.join(
            self.get_tracker_storage_path(tracker_id, create),
            safe_category
        )
        
        if create and not os.path.exists(category_path):
            os.makedirs(category_path, exist_ok=True)
        
        return category_path
    
    def cleanup_tracker_files(self, tracker_id):
        """
        Delete all files for a tracker.
        
        Args:
            tracker_id (int): Tracker ID
            
        Returns:
            dict: {
                'success': bool,
                'deleted_bytes': int,
                'deleted_files': int,
                'error': str (if failed)
            }
        """
        tracker_path = os.path.join(self.base_path, str(tracker_id))
        
        if not os.path.exists(tracker_path):
            return {
                'success': True,
                'deleted_bytes': 0,
                'deleted_files': 0,
                'message': 'No files to delete'
            }
        
        try:
            # Calculate size before deletion
            total_size = 0
            file_count = 0
            
            for root, dirs, files in os.walk(tracker_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
                    file_count += 1
            
            # Delete the entire tracker directory
            shutil.rmtree(tracker_path)
            
            return {
                'success': True,
                'deleted_bytes': total_size,
                'deleted_files': file_count
            }
            
        except Exception as e:
            return {
                'success': False,
                'deleted_bytes': 0,
                'deleted_files': 0,
                'error': str(e)
            }
    
    def get_storage_stats(self, tracker_id=None):
        """
        Get storage statistics.
        
        Args:
            tracker_id (int, optional): Get stats for specific tracker, or all if None
            
        Returns:
            dict: Storage statistics
        """
        if tracker_id:
            # Stats for specific tracker
            tracker_path = os.path.join(self.base_path, str(tracker_id))
            
            if not os.path.exists(tracker_path):
                return {
                    'tracker_id': tracker_id,
                    'total_bytes': 0,
                    'file_count': 0,
                    'exists': False
                }
            
            total_size = 0
            file_count = 0
            
            for root, dirs, files in os.walk(tracker_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                        file_count += 1
                    except OSError:
                        pass  # Skip files we can't read
            
            return {
                'tracker_id': tracker_id,
                'total_bytes': total_size,
                'file_count': file_count,
                'exists': True,
                'formatted_size': self._format_bytes(total_size)
            }
        else:
            # Stats for all trackers
            disk_stat = shutil.disk_usage(self.base_path)
            
            return {
                'total_space': disk_stat.total,
                'used_space': disk_stat.used,
                'free_space': disk_stat.free,
                'formatted_total': self._format_bytes(disk_stat.total),
                'formatted_used': self._format_bytes(disk_stat.used),
                'formatted_free': self._format_bytes(disk_stat.free),
            }
    
    def check_write_permissions(self, path=None):
        """
        Check if we have write permissions to storage directory.
        
        Args:
            path (str, optional): Path to check, defaults to base_path
            
        Returns:
            bool: True if writable
            
        Raises:
            StoragePermissionError: If not writable
        """
        check_path = path or self.base_path
        
        # Ensure directory exists
        if not os.path.exists(check_path):
            os.makedirs(check_path, exist_ok=True)
        
        # Try to write a test file
        test_file = os.path.join(check_path, '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return True
        except PermissionError as e:
            raise StoragePermissionError(
                f"No write permission for {check_path}. "
                f"Check directory ownership and permissions."
            ) from e
        except OSError as e:
            raise StoragePermissionError(
                f"Cannot write to {check_path}: {str(e)}"
            ) from e
    
    def save_uploaded_file(self, uploaded_file, relative_path):
        """
        Save an uploaded file to storage.
        
        Args:
            uploaded_file: Django UploadedFile instance
            relative_path (str): Relative path from MEDIA_ROOT (e.g., 'trackers/1/files/bracket.stl')
            
        Returns:
            str: Relative path where file was saved
            
        Raises:
            InsufficientStorageError: If not enough disk space
            StoragePermissionError: If write permission denied
        """
        # Check if we have enough space
        self.check_available_space(uploaded_file.size)
        
        # Build full path
        full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        
        # Ensure directory exists
        directory = os.path.dirname(full_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        # Check write permissions
        self.check_write_permissions(directory)
        
        # Save file in chunks
        with open(full_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        # Return relative path for database storage
        return relative_path
    
    @staticmethod
    def sanitize_filename(filename, max_length=255):
        """
        Sanitize a filename for safe filesystem use.
        
        Args:
            filename (str): Original filename
            max_length (int): Maximum filename length
            
        Returns:
            str: Sanitized filename
        """
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        filename = filename.strip('. ')
        
        # Truncate if too long (preserve extension)
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            max_name_length = max_length - len(ext)
            filename = name[:max_name_length] + ext
        
        # Ensure not empty
        if not filename:
            filename = 'unnamed_file'
        
        return filename
    
    @staticmethod
    def _format_bytes(bytes_value):
        """
        Format bytes to human-readable string.
        
        Args:
            bytes_value (int): Number of bytes
            
        Returns:
            str: Formatted string (e.g., "1.23 GB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    
    def validate_path_length(self, path):
        """
        Validate that a path is not too long for the filesystem.
        
        Args:
            path (str): Path to validate
            
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If path is too long
        """
        # Windows has a 260 character limit (MAX_PATH)
        # Unix systems typically have a 4096 character limit
        max_path = 260 if os.name == 'nt' else 4096
        
        if len(path) > max_path:
            raise ValueError(
                f"Path length ({len(path)}) exceeds maximum ({max_path}). "
                f"Consider using shorter category names or filenames."
            )
        
        return True
