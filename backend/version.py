"""
Print Vault Version Information
"""
import subprocess
import os
import sys
from django.utils import timezone
import django

# Semantic version - update this manually on releases
VERSION = "1.0.0-beta.2"

def get_git_commit():
    """Get the short git commit hash."""
    try:
        # Try to get git commit hash
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"

def get_git_branch():
    """Get the current git branch."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"

def get_version():
    """Get the version string."""
    return VERSION

def get_migration_status():
    """
    Get migration status for troubleshooting.
    
    Returns:
        dict: Migration information including:
            - applied_count: Number of applied migrations
            - unapplied_count: Number of pending migrations
            - latest_migration: Most recent migration name
            - all_applied: List of all applied migrations
    """
    from django.db.migrations.executor import MigrationExecutor
    from django.db import connections, DEFAULT_DB_ALIAS
    
    try:
        connection = connections[DEFAULT_DB_ALIAS]
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        
        # Get applied migrations
        applied = executor.loader.applied_migrations
        applied_list = [f"{app}.{migration}" for app, migration in sorted(applied)]
        
        # Get unapplied migrations
        plan = executor.migration_plan(targets)
        unapplied_count = len(plan)
        
        # Get latest migration (most recent applied)
        latest_migration = applied_list[-1] if applied_list else "none"
        
        return {
            'applied_count': len(applied_list),
            'unapplied_count': unapplied_count,
            'latest_migration': latest_migration,
            'all_applied': applied_list
        }
    except Exception as e:
        return {
            'error': f"Failed to get migration status: {str(e)}",
            'applied_count': 0,
            'unapplied_count': 0,
            'latest_migration': 'unknown',
            'all_applied': []
        }

def get_latest_github_release():
    """
    Fetch latest release from GitHub API.
    
    Returns:
        dict: Latest release information or error
    """
    import requests
    from django.core.cache import cache
    
    # Check cache first (avoid GitHub API rate limits)
    cached = cache.get('github_latest_release')
    if cached:
        return cached
    
    try:
        # GitHub API endpoint for latest release
        url = 'https://api.github.com/repos/shaxs/print-vault/releases/latest'
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            result = {
                'version': data.get('tag_name', '').lstrip('v'),  # Remove 'v' prefix
                'name': data.get('name', ''),
                'published_at': data.get('published_at', ''),
                'html_url': data.get('html_url', ''),
                'body': data.get('body', ''),  # Release notes
                'error': None
            }
            # Cache for 1 hour (3600 seconds)
            cache.set('github_latest_release', result, 3600)
            return result
        else:
            return {
                'error': f'GitHub API returned status {response.status_code}',
                'version': None
            }
    except requests.Timeout:
        return {
            'error': 'GitHub API request timed out',
            'version': None
        }
    except Exception as e:
        return {
            'error': f'Failed to fetch latest release: {str(e)}',
            'version': None
        }

def compare_versions(current, latest):
    """
    Compare semantic versions including prerelease identifiers.
    
    Examples:
    - 1.0.0-beta.2 vs 1.0.0-beta.3 → outdated
    - 1.0.0-beta.3 vs 1.0.0 → outdated (stable is newer than beta)
    - 1.0.0 vs 1.1.0 → outdated
    
    Returns:
        str: 'outdated' if current < latest, 'up-to-date' if equal, 'newer' if current > latest
    """
    try:
        def parse_version(v):
            """
            Parse version into comparable tuple.
            Returns: (major, minor, patch, is_prerelease, prerelease_type, prerelease_num)
            
            Examples:
            - "1.0.0" → (1, 0, 0, False, "", 0)
            - "1.0.0-beta.2" → (1, 0, 0, True, "beta", 2)
            - "1.0.0-rc.1" → (1, 0, 0, True, "rc", 1)
            """
            # Split version and prerelease
            if '-' in v:
                base, prerelease = v.split('-', 1)
                is_prerelease = True
                
                # Parse prerelease (e.g., "beta.2" → type="beta", num=2)
                if '.' in prerelease:
                    pre_type, pre_num = prerelease.rsplit('.', 1)
                    try:
                        pre_num = int(pre_num)
                    except ValueError:
                        pre_num = 0
                else:
                    pre_type = prerelease
                    pre_num = 0
            else:
                base = v
                is_prerelease = False
                pre_type = ""
                pre_num = 0
            
            # Parse base version
            parts = base.split('.')
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            
            return (major, minor, patch, is_prerelease, pre_type, pre_num)
        
        current_parsed = parse_version(current)
        latest_parsed = parse_version(latest)
        
        # Compare base versions first (major, minor, patch)
        if current_parsed[:3] < latest_parsed[:3]:
            return 'outdated'
        elif current_parsed[:3] > latest_parsed[:3]:
            return 'newer'
        else:
            # Same base version - check prerelease
            current_is_pre = current_parsed[3]
            latest_is_pre = latest_parsed[3]
            
            if current_is_pre and not latest_is_pre:
                # Current is beta, latest is stable → outdated
                return 'outdated'
            elif not current_is_pre and latest_is_pre:
                # Current is stable, latest is beta → newer
                return 'newer'
            elif current_is_pre and latest_is_pre:
                # Both are prereleases - compare type and number
                current_pre_type = current_parsed[4]
                latest_pre_type = latest_parsed[4]
                current_pre_num = current_parsed[5]
                latest_pre_num = latest_parsed[5]
                
                # Priority: alpha < beta < rc
                pre_priority = {'alpha': 1, 'beta': 2, 'rc': 3}
                current_priority = pre_priority.get(current_pre_type, 2)
                latest_priority = pre_priority.get(latest_pre_type, 2)
                
                if current_priority < latest_priority:
                    return 'outdated'
                elif current_priority > latest_priority:
                    return 'newer'
                else:
                    # Same prerelease type - compare numbers
                    if current_pre_num < latest_pre_num:
                        return 'outdated'
                    elif current_pre_num > latest_pre_num:
                        return 'newer'
                    else:
                        return 'up-to-date'
            else:
                # Both stable and equal
                return 'up-to-date'
    except Exception as e:
        print(f"Version comparison error: {e}")
        return 'unknown'

def get_full_version_info():
    """
    Get complete version information for troubleshooting.
    
    Returns:
        dict: Version information including:
            - version: Semantic version (e.g., "1.0.0-beta.2")
            - commit: Git commit hash
            - branch: Git branch name
            - python_version: Python version string
            - django_version: Django version string
            - build_time: Current timestamp
            - migrations: Migration status information
    """
    return {
        'version': VERSION,
        'commit': get_git_commit(),
        'branch': get_git_branch(),
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'django_version': django.get_version(),
        'build_time': timezone.now().isoformat(),
        'migrations': get_migration_status()
    }
