"""
File Download Service for Print Vault Trackers

Handles downloading files from various sources:
- GitHub (raw.githubusercontent.com)
- Thingiverse
- Printables
- Generic URLs

Features:
- Streaming downloads (no memory overflow)
- Retry logic with exponential backoff
- Progress callbacks
- Checksum verification
- Timeout handling
"""

import os
import time
import hashlib
import requests
from urllib.parse import urlparse, quote
from django.conf import settings


class DownloadTimeoutError(Exception):
    """Raised when download times out after all retries."""
    pass


class DownloadError(Exception):
    """Raised when download fails for any reason."""
    pass


class FileTooLargeError(Exception):
    """Raised when file exceeds size limits."""
    pass


class FileDownloadService:
    """Handles file downloads from various sources."""
    
    def __init__(self):
        """Initialize download service with settings."""
        tracker_storage = getattr(settings, 'TRACKER_STORAGE', {})
        
        self.timeout = tracker_storage.get('DOWNLOAD_TIMEOUT', 600)  # 10 minutes
        self.max_retries = tracker_storage.get('MAX_RETRIES', 3)
        self.retry_delay = tracker_storage.get('RETRY_DELAY', 2)
        self.chunk_size = tracker_storage.get('CHUNK_SIZE', 8192)
        self.max_file_size = tracker_storage.get('MAX_FILE_SIZE', 5 * 1024 * 1024 * 1024)  # 5 GB
        self.verify_checksums = tracker_storage.get('VERIFY_CHECKSUMS', False)
        
        # Allowed domains for security
        self.allowed_domains = getattr(settings, 'ALLOWED_DOWNLOAD_DOMAINS', [
            'github.com',
            'raw.githubusercontent.com',
            'thingiverse.com',
            'thingiverse-production-new.s3.amazonaws.com',
            'printables.com',
            'media.printables.com',
        ])
    
    def validate_url(self, url):
        """
        Validate that URL is from an allowed domain.
        
        Args:
            url (str): URL to validate
            
        Raises:
            ValueError: If URL domain is not allowed
        """
        parsed = urlparse(url)
        
        if not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")
        
        if parsed.netloc not in self.allowed_domains:
            raise ValueError(
                f"Downloads from {parsed.netloc} are not allowed. "
                f"Allowed domains: {', '.join(self.allowed_domains)}"
            )
    
    def download_file(self, url, destination, timeout=None, progress_callback=None):
        """
        Download a single file from URL to destination.
        
        Args:
            url (str): Source URL
            destination (str): Destination file path
            timeout (int, optional): Timeout in seconds
            progress_callback (callable, optional): Function(downloaded, total, percentage)
            
        Returns:
            dict: {
                'success': bool,
                'bytes_downloaded': int,
                'duration': float,
                'checksum': str (if verification enabled)
            }
            
        Raises:
            DownloadError: If download fails
            FileTooLargeError: If file exceeds size limit
        """
        # Validate URL
        self.validate_url(url)
        
        # Use instance timeout if not specified
        timeout = timeout or self.timeout
        
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        start_time = time.time()
        
        try:
            # Don't re-encode URLs - they should already be properly encoded
            # Just use the URL as-is to avoid double-encoding issues
            # Make request with streaming
            response = requests.get(
                url,
                stream=True,
                timeout=timeout,
                headers={'User-Agent': 'PrintVault/1.0'}
            )
            response.raise_for_status()
            
            # Check file size
            total_size = int(response.headers.get('content-length', 0))
            if total_size > self.max_file_size:
                raise FileTooLargeError(
                    f"File size ({self._format_bytes(total_size)}) "
                    f"exceeds maximum ({self._format_bytes(self.max_file_size)})"
                )
            
            # Download file
            downloaded = 0
            checksum = hashlib.sha256() if self.verify_checksums else None
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if checksum:
                            checksum.update(chunk)
                        
                        # Call progress callback if provided
                        if progress_callback and total_size > 0:
                            percentage = (downloaded / total_size) * 100
                            progress_callback(downloaded, total_size, percentage)
            
            duration = time.time() - start_time
            
            # Verify file size
            actual_size = os.path.getsize(destination)
            if total_size > 0 and abs(actual_size - total_size) > 1024:  # Allow 1KB difference
                if actual_size < total_size * 0.95:  # Less than 95% of expected
                    os.remove(destination)
                    raise DownloadError(
                        f"Incomplete download. "
                        f"Downloaded {self._format_bytes(actual_size)}, "
                        f"expected {self._format_bytes(total_size)}"
                    )
            
            result = {
                'success': True,
                'bytes_downloaded': actual_size,
                'duration': duration,
                'speed_mbps': (actual_size / duration / 1024 / 1024) if duration > 0 else 0
            }
            
            if checksum:
                result['checksum'] = checksum.hexdigest()
            
            return result
            
        except requests.Timeout as e:
            raise DownloadTimeoutError(f"Download timed out after {timeout}s") from e
        except requests.HTTPError as e:
            raise DownloadError(f"HTTP error {e.response.status_code}: {str(e)}") from e
        except requests.RequestException as e:
            raise DownloadError(f"Download failed: {str(e)}") from e
        except OSError as e:
            # Disk full or permission issues
            if os.path.exists(destination):
                os.remove(destination)  # Cleanup partial file
            raise DownloadError(f"File write error: {str(e)}") from e
    
    def download_with_retry(self, url, destination, max_retries=None, progress_callback=None):
        """
        Download file with automatic retry on failure.
        
        Args:
            url (str): Source URL
            destination (str): Destination path
            max_retries (int, optional): Max retry attempts
            progress_callback (callable, optional): Progress callback
            
        Returns:
            dict: Download result
            
        Raises:
            DownloadError: If all retries fail
        """
        max_retries = max_retries or self.max_retries
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Increase timeout for each retry
                timeout = self.timeout * (attempt + 1)
                
                result = self.download_file(
                    url,
                    destination,
                    timeout=timeout,
                    progress_callback=progress_callback
                )
                
                # Success!
                result['attempts'] = attempt + 1
                return result
                
            except (DownloadTimeoutError, DownloadError) as e:
                last_error = e
                
                # Don't retry on certain errors
                if isinstance(e, DownloadError) and '404' in str(e):
                    raise  # File not found, no point retrying
                
                if isinstance(e, FileTooLargeError):
                    raise  # Too large, no point retrying
                
                # Cleanup partial file
                if os.path.exists(destination):
                    try:
                        os.remove(destination)
                    except OSError:
                        pass
                
                # If not last attempt, wait before retry (exponential backoff)
                if attempt < max_retries - 1:
                    delay = self.retry_delay ** attempt
                    time.sleep(delay)
        
        # All retries failed
        raise DownloadError(
            f"Download failed after {max_retries} attempts. "
            f"Last error: {str(last_error)}"
        ) from last_error
    
    def download_files_batch(self, file_list, progress_callback=None):
        """
        Download multiple files.
        
        Args:
            file_list (list): List of dicts with 'url', 'destination', 'name', 'tracker_file_id' (optional)
            progress_callback (callable, optional): Function(current_file, total_files, file_progress)
            
        Returns:
            dict: {
                'successful': list of dicts,
                'failed': list of dicts with error info,
                'total_bytes': int,
                'duration': float
            }
        """
        results = {
            'successful': [],
            'failed': [],
            'total_bytes': 0,
            'duration': 0
        }
        
        start_time = time.time()
        
        for index, file_info in enumerate(file_list):
            url = file_info['url']
            destination = file_info['destination']
            name = file_info.get('name', os.path.basename(destination))
            tracker_file_id = file_info.get('tracker_file_id')
            
            # Create per-file progress callback
            def file_progress(downloaded, total, percentage):
                if progress_callback:
                    progress_callback(
                        current_file=index + 1,
                        total_files=len(file_list),
                        file_name=name,
                        file_downloaded=downloaded,
                        file_total=total,
                        file_percentage=percentage
                    )
            
            try:
                # Convert GitHub blob URLs to raw URLs if needed
                download_url = url
                if 'github.com' in url and 'raw.githubusercontent.com' not in url:
                    # Convert: https://github.com/user/repo/blob/main/file.stl
                    # To: https://raw.githubusercontent.com/user/repo/main/file.stl
                    download_url = url.replace('github.com', 'raw.githubusercontent.com')
                    download_url = download_url.replace('/blob/', '/')
                
                result = self.download_with_retry(
                    download_url,
                    destination,
                    progress_callback=file_progress
                )
                
                # Compute checksum of downloaded file
                checksum = ''
                try:
                    if os.path.exists(destination):
                        checksum = self.compute_checksum(destination)
                except Exception:
                    pass  # Checksum is optional
                
                success_result = {
                    'name': name,
                    'url': url,
                    'destination': destination,
                    'bytes_downloaded': result['bytes_downloaded'],
                    'duration': result['duration'],
                    'attempts': result.get('attempts', 1),
                    'checksum': checksum
                }
                
                # Include tracker_file_id if provided
                if tracker_file_id is not None:
                    success_result['tracker_file_id'] = tracker_file_id
                
                results['successful'].append(success_result)
                results['total_bytes'] += result['bytes_downloaded']
                
            except Exception as e:
                fail_result = {
                    'name': name,
                    'url': url,
                    'destination': destination,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
                
                # Include tracker_file_id if provided
                if tracker_file_id is not None:
                    fail_result['tracker_file_id'] = tracker_file_id
                
                results['failed'].append(fail_result)
        
        results['duration'] = time.time() - start_time
        
        return results
    
    def verify_file(self, file_path, expected_size=None, expected_checksum=None):
        """
        Verify downloaded file integrity.
        
        Args:
            file_path (str): Path to file
            expected_size (int, optional): Expected file size
            expected_checksum (str, optional): Expected SHA256 checksum
            
        Returns:
            dict: Verification result
            
        Raises:
            ValueError: If verification fails
        """
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
        
        actual_size = os.path.getsize(file_path)
        result = {
            'valid': True,
            'actual_size': actual_size
        }
        
        # Check size
        if expected_size is not None:
            size_match = abs(actual_size - expected_size) <= 1024  # Allow 1KB difference
            result['size_match'] = size_match
            result['expected_size'] = expected_size
            
            if not size_match:
                result['valid'] = False
                raise ValueError(
                    f"Size mismatch. "
                    f"Expected: {self._format_bytes(expected_size)}, "
                    f"Actual: {self._format_bytes(actual_size)}"
                )
        
        # Check checksum
        if expected_checksum is not None:
            actual_checksum = self.compute_checksum(file_path)
            checksum_match = actual_checksum == expected_checksum
            result['checksum_match'] = checksum_match
            result['expected_checksum'] = expected_checksum
            result['actual_checksum'] = actual_checksum
            
            if not checksum_match:
                result['valid'] = False
                raise ValueError(
                    f"Checksum mismatch. "
                    f"Expected: {expected_checksum}, "
                    f"Actual: {actual_checksum}"
                )
        
        return result
    
    @staticmethod
    def compute_checksum(file_path):
        """
        Compute SHA256 checksum of a file.
        
        Args:
            file_path (str): Path to file
            
        Returns:
            str: Hex checksum
        """
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def get_file_from_github(self, github_url, destination, progress_callback=None):
        """
        Download file from GitHub, converting to raw URL if needed.
        
        Args:
            github_url (str): GitHub file URL
            destination (str): Destination path
            progress_callback (callable, optional): Progress callback
            
        Returns:
            dict: Download result
        """
        # Convert GitHub URL to raw URL if needed
        raw_url = github_url
        
        if 'github.com' in github_url and 'raw.githubusercontent.com' not in github_url:
            # Convert: https://github.com/user/repo/blob/main/file.stl
            # To: https://raw.githubusercontent.com/user/repo/main/file.stl
            raw_url = github_url.replace('github.com', 'raw.githubusercontent.com')
            raw_url = raw_url.replace('/blob/', '/')
        
        return self.download_with_retry(raw_url, destination, progress_callback=progress_callback)
    
    @staticmethod
    def _format_bytes(bytes_value):
        """Format bytes to human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
