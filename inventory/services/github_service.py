"""
GitHub Repository Crawler Service

This service handles crawling GitHub repositories to extract printable 3D files.
Uses GitHub's Git Trees API for efficient single-request crawling.
Implements caching to minimize API calls and improve performance.
"""

import re
import requests
from django.core.cache import cache
from django.conf import settings
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from urllib.parse import unquote, quote


# Configuration
PRINTABLE_EXTENSIONS = ['.3mf', '.stl', '.oltp', '.stp', '.step', '.svg', '.amf', '.obj']
FILE_SIZE_WARN_BYTES = 10 * 1024 * 1024  # 10 MB
FILE_SIZE_BLOCK_BYTES = 100 * 1024 * 1024  # 100 MB
CACHE_TIMEOUT = 3600  # 1 hour in seconds

# GitHub API configuration
GITHUB_API_BASE = 'https://api.github.com'
GITHUB_RAW_BASE = 'https://raw.githubusercontent.com'


class GitHubCrawlerError(Exception):
    """Base exception for GitHub crawler errors"""
    pass


class InvalidURLError(GitHubCrawlerError):
    """Raised when URL is not a valid GitHub URL"""
    pass


class RepositoryNotFoundError(GitHubCrawlerError):
    """Raised when repository doesn't exist or is private"""
    pass


class RateLimitError(GitHubCrawlerError):
    """Raised when GitHub API rate limit is exceeded"""
    pass


class NetworkError(GitHubCrawlerError):
    """Raised when network request fails"""
    pass


class EmptyResultError(GitHubCrawlerError):
    """Raised when no printable files are found"""
    pass


def parse_github_url(url: str) -> Dict[str, str]:
    """
    Parse a GitHub URL and extract owner, repo, branch, and path.
    
    Supported formats:
    - https://github.com/{owner}/{repo}
    - https://github.com/{owner}/{repo}/tree/{branch}/{path}
    
    Args:
        url: GitHub URL string
        
    Returns:
        Dict with keys: owner, repo, branch (or None), path (or empty string)
        
    Raises:
        InvalidURLError: If URL is not a valid GitHub repository URL
    """
    # Remove trailing slashes
    url = url.rstrip('/')
    
    # Pattern for repo root: https://github.com/{owner}/{repo}
    pattern_root = r'^https?://github\.com/([^/]+)/([^/]+)/?$'
    
    # Pattern for specific path: https://github.com/{owner}/{repo}/tree/{branch}/{path}
    pattern_tree = r'^https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)(?:/(.+))?$'
    
    # Pattern for blob (single file) - we'll reject this
    pattern_blob = r'^https?://github\.com/([^/]+)/([^/]+)/blob/'
    
    # Check if it's a single file URL (blob)
    if re.match(pattern_blob, url):
        raise InvalidURLError(
            "Please provide a link to a directory, not a single file. "
            "Replace '/blob/' with '/tree/' in your URL."
        )
    
    # Try matching tree pattern (with path)
    match = re.match(pattern_tree, url)
    if match:
        owner, repo, branch, path = match.groups()
        # URL-decode the path to handle spaces and special characters
        decoded_path = unquote(path) if path else ''
        return {
            'owner': owner,
            'repo': repo,
            'branch': branch,
            'path': decoded_path
        }
    
    # Try matching root pattern (no specific path)
    match = re.match(pattern_root, url)
    if match:
        owner, repo = match.groups()
        return {
            'owner': owner,
            'repo': repo,
            'branch': None,  # Will use default branch
            'path': ''
        }
    
    # URL doesn't match any valid pattern
    raise InvalidURLError(
        "Not a valid GitHub repository URL. "
        "Expected format: https://github.com/{owner}/{repo} or "
        "https://github.com/{owner}/{repo}/tree/{branch}/{path}"
    )


def get_cache_key(owner: str, repo: str, branch: str, path: str) -> str:
    """
    Generate a normalized cache key for a GitHub tree request.
    
    Args:
        owner: Repository owner
        repo: Repository name
        branch: Branch name
        path: Directory path within repo
        
    Returns:
        Cache key string
    """
    # Normalize to lowercase and remove leading/trailing slashes from path
    owner = owner.lower()
    repo = repo.lower()
    branch = branch.lower()
    path = path.strip('/').lower() if path else ''
    
    return f'github_tree:{owner}:{repo}:{branch}:{path}'


def get_default_branch(owner: str, repo: str) -> str:
    """
    Get the default branch for a GitHub repository.
    
    Args:
        owner: Repository owner
        repo: Repository name
        
    Returns:
        Default branch name (e.g., 'main' or 'master')
        
    Raises:
        RepositoryNotFoundError: If repo doesn't exist or is private
        RateLimitError: If GitHub API rate limit exceeded
        NetworkError: If request fails
    """
    url = f'{GITHUB_API_BASE}/repos/{owner}/{repo}'
    
    try:
        response = requests.get(url, timeout=10)
        
        # Check rate limit
        if response.status_code == 403:
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', '0')
            if rate_limit_remaining == '0':
                reset_time = response.headers.get('X-RateLimit-Reset', 'unknown')
                raise RateLimitError(
                    f"GitHub API rate limit exceeded. Resets at: {reset_time}. "
                    "Consider adding a GitHub token in settings."
                )
        
        # Check if repo exists
        if response.status_code == 404:
            raise RepositoryNotFoundError(
                f"Repository '{owner}/{repo}' not found. "
                "Check the URL or verify you have access to this repository."
            )
        
        response.raise_for_status()
        data = response.json()
        return data['default_branch']
        
    except requests.exceptions.Timeout:
        raise NetworkError("Request to GitHub timed out. Please try again.")
    except requests.exceptions.ConnectionError:
        raise NetworkError("Failed to connect to GitHub. Check your internet connection.")
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"GitHub API request failed: {str(e)}")


def fetch_tree(owner: str, repo: str, branch: str) -> List[Dict]:
    """
    Fetch the complete file tree from a GitHub repository using Git Trees API.
    
    This makes a single API call to get all files recursively.
    
    Args:
        owner: Repository owner
        repo: Repository name
        branch: Branch name
        
    Returns:
        List of file objects with 'path', 'size', 'type', etc.
        
    Raises:
        RepositoryNotFoundError: If repo or branch doesn't exist
        RateLimitError: If GitHub API rate limit exceeded
        NetworkError: If request fails
    """
    # First, get the branch SHA
    url = f'{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1'
    
    try:
        response = requests.get(url, timeout=30)
        
        # Check rate limit
        if response.status_code == 403:
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', '0')
            if rate_limit_remaining == '0':
                reset_time = response.headers.get('X-RateLimit-Reset', 'unknown')
                raise RateLimitError(
                    f"GitHub API rate limit exceeded. Resets at: {reset_time}. "
                    "Consider adding a GitHub token in settings."
                )
        
        # Check if branch/repo exists
        if response.status_code == 404:
            raise RepositoryNotFoundError(
                f"Branch '{branch}' not found in repository '{owner}/{repo}'. "
                "Verify the branch name and repository access."
            )
        
        response.raise_for_status()
        data = response.json()
        
        # Return only blob (file) entries, not trees (directories)
        return [item for item in data.get('tree', []) if item['type'] == 'blob']
        
    except requests.exceptions.Timeout:
        raise NetworkError("Request to GitHub timed out. The repository may be very large. Please try again.")
    except requests.exceptions.ConnectionError:
        raise NetworkError("Failed to connect to GitHub. Check your internet connection.")
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"GitHub API request failed: {str(e)}")


def filter_printable_files(files: List[Dict], base_path: str = '') -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Filter files to only include printable 3D files, separated by size.
    
    Args:
        files: List of file objects from GitHub tree
        base_path: Optional base path to filter by (only include files under this path)
        
    Returns:
        Tuple of (normal_files, large_files, blocked_files)
        - normal_files: Files < 10 MB
        - large_files: Files 10-100 MB (warning)
        - blocked_files: Files > 100 MB (blocked)
    """
    normal_files = []
    large_files = []
    blocked_files = []
    
    for file in files:
        path = file['path']
        
        # If base_path is specified, only include files under that path
        if base_path and not path.startswith(base_path.strip('/')):
            continue
        
        # Check file extension
        file_ext = '.' + path.lower().split('.')[-1] if '.' in path else ''
        if file_ext not in PRINTABLE_EXTENSIONS:
            continue
        
        size = file.get('size', 0)
        
        # Categorize by size
        if size >= FILE_SIZE_BLOCK_BYTES:
            blocked_files.append(file)
        elif size >= FILE_SIZE_WARN_BYTES:
            large_files.append(file)
        else:
            normal_files.append(file)
    
    return normal_files, large_files, blocked_files


def build_file_tree(files: List[Dict], owner: str, repo: str, branch: str, base_path: str = '') -> Dict:
    """
    Build a hierarchical file tree structure grouped by directory.
    
    Args:
        files: List of file objects (already filtered for printable files)
        owner: Repository owner
        repo: Repository name
        branch: Branch name
        base_path: Base path to strip from file paths
        
    Returns:
        Dict with directory_path as keys and list of file info as values
    """
    tree = defaultdict(list)
    
    for file in files:
        full_path = file['path']
        
        # Remove base_path prefix if it exists
        if base_path:
            base_path_clean = base_path.strip('/')
            if full_path.startswith(base_path_clean):
                relative_path = full_path[len(base_path_clean):].lstrip('/')
            else:
                relative_path = full_path
        else:
            relative_path = full_path
        
        # Split into directory and filename
        parts = relative_path.split('/')
        if len(parts) == 1:
            # File is in root
            directory_path = ''
            filename = parts[0]
        else:
            # File is in a subdirectory
            directory_path = '/'.join(parts[:-1])
            filename = parts[-1]
        
        # Build raw GitHub URL for the file
        # Note: Store URL with spaces/special chars unencoded - the download service will encode when fetching
        github_url = f'{GITHUB_RAW_BASE}/{owner}/{repo}/{branch}/{full_path}'
        
        # Calculate file size in MB for display
        size_bytes = file.get('size', 0)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        
        # Determine file status
        is_large = size_bytes >= FILE_SIZE_WARN_BYTES
        is_blocked = size_bytes >= FILE_SIZE_BLOCK_BYTES
        
        file_info = {
            'filename': filename,
            'github_url': github_url,
            'file_size': size_bytes,
            'file_size_mb': size_mb,
            'sha': file.get('sha', ''),  # GitHub file hash for verification
            'is_large': is_large,
            'is_blocked': is_blocked,
        }
        
        tree[directory_path].append(file_info)
    
    # Convert defaultdict to regular dict and sort
    return {k: sorted(v, key=lambda x: x['filename']) for k, v in sorted(tree.items())}


def crawl_github_repository(github_url: str, force_refresh: bool = False) -> Dict:
    """
    Main function to crawl a GitHub repository and return printable files.
    
    This function:
    1. Parses the GitHub URL
    2. Checks cache (unless force_refresh=True)
    3. Fetches repository tree from GitHub API
    4. Filters for printable files
    5. Categorizes by size
    6. Builds hierarchical structure
    7. Caches result
    
    Args:
        github_url: GitHub repository or directory URL
        force_refresh: If True, bypass cache and fetch fresh data
        
    Returns:
        Dict containing:
        - success: bool
        - repo_info: dict with owner, repo, branch, path
        - file_tree: hierarchical structure of files
        - stats: file counts and sizes
        - warnings: list of warning messages
        - cached: bool indicating if result was from cache
        - cache_timestamp: when data was cached
        
    Raises:
        GitHubCrawlerError: For various error conditions
    """
    # Parse URL
    parsed = parse_github_url(github_url)
    owner = parsed['owner']
    repo = parsed['repo']
    branch = parsed['branch']
    path = parsed['path']
    
    # Get default branch if not specified
    if not branch:
        branch = get_default_branch(owner, repo)
    
    # Check cache (unless force refresh)
    cache_key = get_cache_key(owner, repo, branch, path)
    
    if not force_refresh:
        cached_data = cache.get(cache_key)
        if cached_data:
            cached_data['cached'] = True
            return cached_data
    
    # Fetch tree from GitHub
    all_files = fetch_tree(owner, repo, branch)
    
    # Filter for printable files
    normal_files, large_files, blocked_files = filter_printable_files(all_files, path)
    
    # Combine all printable files for tree building
    all_printable = normal_files + large_files + blocked_files
    
    # Check if any files were found
    if not all_printable:
        raise EmptyResultError(
            f"No printable files found in '{owner}/{repo}' at path '{path or 'root'}'. "
            f"Looking for files with extensions: {', '.join(PRINTABLE_EXTENSIONS)}"
        )
    
    # Build file tree structure
    file_tree_dict = build_file_tree(all_printable, owner, repo, branch, path)
    
    # Convert to list format for response
    file_tree = [
        {
            'directory_path': dir_path,
            'files': files
        }
        for dir_path, files in file_tree_dict.items()
    ]
    
    # Calculate statistics
    total_files = len(all_printable)
    total_size = sum(f.get('size', 0) for f in all_printable)
    total_size_mb = round(total_size / (1024 * 1024), 2)
    
    # Count file types
    file_types = defaultdict(int)
    for file in all_printable:
        ext = '.' + file['path'].lower().split('.')[-1] if '.' in file['path'] else ''
        if ext:
            file_types[ext] += 1
    
    # Build warnings list
    warnings = []
    if large_files:
        warnings.append(f"{len(large_files)} files are larger than 10 MB")
    if blocked_files:
        blocked_names = [f['path'].split('/')[-1] for f in blocked_files[:3]]
        if len(blocked_files) > 3:
            blocked_names.append(f"and {len(blocked_files) - 3} more")
        warnings.append(
            f"{len(blocked_files)} files blocked (>100 MB): {', '.join(blocked_names)}"
        )
    
    # Build response
    result = {
        'success': True,
        'repo_info': {
            'owner': owner,
            'repo': repo,
            'branch': branch,
            'path': path
        },
        'file_tree': file_tree,
        'stats': {
            'total_files': total_files,
            'normal_files': len(normal_files),
            'large_files': len(large_files),
            'blocked_files': len(blocked_files),
            'total_size': total_size,
            'total_size_mb': total_size_mb,
            'file_types': dict(file_types)
        },
        'warnings': warnings,
        'cached': False,
        'cache_timestamp': None
    }
    
    # Cache the result
    cache.set(cache_key, result, CACHE_TIMEOUT)
    
    return result
