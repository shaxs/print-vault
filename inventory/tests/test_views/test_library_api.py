"""
Tests for the STL/3MF Library API endpoints:

- /api/library/roots/ (CRUD + multi-root path-overlap validation + rescan/delete)
- /api/library/folders/ (tree skeleton, contents, scoped rescan)
- /api/library/files/ (detail + streamed download with path validation)
- /api/library/scans/ (job status polling)
"""
from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from inventory.models import LibraryFile, LibraryRoot, LibraryScan
from inventory.services import library_scanner
from inventory.tests.factories import (
    LibraryFileFactory,
    LibraryFolderFactory,
    LibraryRootFactory,
    LibraryScanFactory,
)


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
class TestLibraryRootAPI:
    def test_create_root(self, client):
        resp = client.post(
            '/api/library/roots/', {'name': 'NAS', 'path': '/mnt/nas/stls'}, format='json'
        )
        assert resp.status_code == 201
        assert resp.data['enabled'] is True  # model default applies

    def test_second_enabled_root_with_distinct_path_allowed(self, client):
        """Multi-root: a second enabled root on a non-overlapping path is fine
        (replaces the retired v1 single-enabled-root cap)."""
        LibraryRootFactory(path='/mnt/nas')

        resp = client.post(
            '/api/library/roots/', {'name': 'Other', 'path': '/mnt/other'}, format='json'
        )
        assert resp.status_code == 201

    def test_duplicate_path_rejected(self, client):
        """No two roots may index the same tree (normalized comparison, so a
        trailing slash doesn't sneak a duplicate through)."""
        LibraryRootFactory(path='/mnt/nas')

        resp = client.post(
            '/api/library/roots/', {'name': 'Dup', 'path': '/mnt/nas/'}, format='json'
        )
        assert resp.status_code == 400
        assert 'path' in resp.data

    def test_nested_path_rejected(self, client):
        """A new enabled root inside an existing enabled root would double-index."""
        LibraryRootFactory(path='/mnt/nas')

        resp = client.post(
            '/api/library/roots/', {'name': 'Sub', 'path': '/mnt/nas/sub'}, format='json'
        )
        assert resp.status_code == 400

    def test_containing_path_rejected(self, client):
        """A new enabled root that contains an existing enabled root, too."""
        LibraryRootFactory(path='/mnt/nas/sub')

        resp = client.post(
            '/api/library/roots/', {'name': 'Parent', 'path': '/mnt/nas'}, format='json'
        )
        assert resp.status_code == 400

    def test_nested_path_allowed_when_new_root_disabled(self, client):
        """The overlap rule only guards enabled roots (disabled roots aren't
        scanned, so they can't double-index); a distinct-but-nested disabled
        root is allowed."""
        LibraryRootFactory(path='/mnt/nas')

        resp = client.post(
            '/api/library/roots/',
            {'name': 'Sub', 'path': '/mnt/nas/sub', 'enabled': False},
            format='json',
        )
        assert resp.status_code == 201

    def test_enabling_second_root_allowed(self, client):
        """Enabling a second root on a distinct path now succeeds."""
        LibraryRootFactory(path='/mnt/nas')
        second = LibraryRootFactory(path='/mnt/other', enabled=False)

        resp = client.patch(
            f'/api/library/roots/{second.id}/', {'enabled': True}, format='json'
        )
        assert resp.status_code == 200


@pytest.mark.django_db
class TestLibraryRootRescan:
    def test_rescan_root_success(self, client):
        root = LibraryRootFactory()

        with mock.patch.object(library_scanner, 'async_task'):
            resp = client.post(f'/api/library/roots/{root.id}/rescan/')

        assert resp.status_code == 202
        assert 'id' in resp.data
        assert resp.data['status'] == 'pending'

    def test_rescan_root_running_conflict(self, client):
        root = LibraryRootFactory()
        LibraryScanFactory(root=root, status='running')

        resp = client.post(f'/api/library/roots/{root.id}/rescan/')
        assert resp.status_code == 409

    def test_rescan_root_disabled(self, client):
        root = LibraryRootFactory(enabled=False)

        resp = client.post(f'/api/library/roots/{root.id}/rescan/')
        assert resp.status_code == 400


@pytest.mark.django_db
class TestLibraryRootDelete:
    def test_delete_blocked_while_scanning(self, client):
        """A cascading root delete must not race an in-flight walk task."""
        root = LibraryRootFactory()
        LibraryScanFactory(root=root, status='running')

        resp = client.delete(f'/api/library/roots/{root.id}/')

        assert resp.status_code == 409
        assert LibraryRoot.objects.filter(pk=root.id).exists()

    def test_delete_allowed_when_idle(self, client):
        root = LibraryRootFactory()
        LibraryScanFactory(root=root, status='success')  # finished job doesn't block

        resp = client.delete(f'/api/library/roots/{root.id}/')

        assert resp.status_code == 204
        assert not LibraryRoot.objects.filter(pk=root.id).exists()

    def test_delete_removes_rescan_schedule(self, client):
        """The per-root periodic-rescan Schedule is cleaned up on delete."""
        from django_q.models import Schedule

        root = LibraryRootFactory(rescan_interval_hours=6)
        name = f'library-root-rescan-{root.id}'
        assert Schedule.objects.filter(name=name).exists()

        resp = client.delete(f'/api/library/roots/{root.id}/')

        assert resp.status_code == 204
        assert not Schedule.objects.filter(name=name).exists()


@pytest.mark.django_db
class TestFolderTree:
    def test_folder_tree_skeleton_and_deleted_exclusion(self, client):
        root = LibraryRootFactory()
        LibraryFolderFactory(root=root)
        deleted_folder = LibraryFolderFactory(root=root, status='deleted')

        resp = client.get('/api/library/folders/tree/', {'root': root.id})

        assert resp.status_code == 200
        for item in resp.data:
            # `root` lets the multi-root frontend attribute each folder;
            # `file_count` drives the client-side "hide empty folders" toggle.
            assert set(item.keys()) == {'id', 'name', 'parent_id', 'status', 'root', 'file_count'}
            assert item['root'] == root.id
        assert deleted_folder.id not in [item['id'] for item in resp.data]

    def test_folder_tree_file_count_counts_active_files_only(self, client):
        root = LibraryRootFactory()
        folder = LibraryFolderFactory(root=root)
        empty = LibraryFolderFactory(root=root)
        LibraryFileFactory(folder=folder, filename='a.stl', relative_path='a.stl')
        LibraryFileFactory(folder=folder, filename='b.3mf', relative_path='b.3mf')
        LibraryFileFactory(
            folder=folder, filename='gone.stl', relative_path='gone.stl', status='deleted'
        )

        resp = client.get('/api/library/folders/tree/', {'root': root.id})

        counts = {item['id']: item['file_count'] for item in resp.data}
        assert counts[folder.id] == 2  # two active files, the deleted one excluded
        assert counts[empty.id] == 0


@pytest.mark.django_db
class TestFolderContents:
    def test_folder_contents_structure(self, client):
        folder = LibraryFolderFactory()

        resp = client.get(f'/api/library/folders/{folder.id}/contents/')

        assert resp.status_code == 200
        assert 'folder' in resp.data
        assert 'subfolders' in resp.data
        assert set(resp.data['files'].keys()) == {'count', 'next', 'previous', 'results'}

    def test_deleted_files_excluded_by_default(self, client):
        folder = LibraryFolderFactory()
        LibraryFileFactory(folder=folder, filename='keep.stl', relative_path='keep.stl')
        LibraryFileFactory(
            folder=folder, filename='ghost.stl', relative_path='ghost.stl', status='deleted'
        )

        resp = client.get(f'/api/library/folders/{folder.id}/contents/')

        filenames = [f['filename'] for f in resp.data['files']['results']]
        assert 'ghost.stl' not in filenames
        assert 'keep.stl' in filenames

    def test_include_deleted_toggle(self, client):
        folder = LibraryFolderFactory()
        LibraryFileFactory(
            folder=folder, filename='ghost.stl', relative_path='ghost.stl', status='deleted'
        )

        resp = client.get(
            f'/api/library/folders/{folder.id}/contents/', {'include_deleted': 'true'}
        )

        filenames = [f['filename'] for f in resp.data['files']['results']]
        assert 'ghost.stl' in filenames

    def test_ordering(self, client):
        folder = LibraryFolderFactory()
        LibraryFileFactory(folder=folder, filename='b.stl', relative_path='b.stl', size_bytes=10)
        LibraryFileFactory(folder=folder, filename='a.stl', relative_path='a.stl', size_bytes=99)

        resp = client.get(f'/api/library/folders/{folder.id}/contents/')
        assert resp.data['files']['results'][0]['filename'] == 'a.stl'

        resp = client.get(
            f'/api/library/folders/{folder.id}/contents/', {'ordering': '-size_bytes'}
        )
        assert resp.data['files']['results'][0]['filename'] == 'a.stl'  # 99 > 10

        resp = client.get(
            f'/api/library/folders/{folder.id}/contents/', {'ordering': 'size_bytes'}
        )
        assert resp.data['files']['results'][0]['filename'] == 'b.stl'

    def test_pagination(self, client):
        folder = LibraryFolderFactory()
        for i in range(3):
            LibraryFileFactory(
                folder=folder, filename=f'file{i}.stl', relative_path=f'file{i}.stl'
            )

        resp = client.get(f'/api/library/folders/{folder.id}/contents/', {'page_size': 2})

        assert len(resp.data['files']['results']) == 2
        assert resp.data['files']['count'] == 3
        assert resp.data['files']['next'] is not None


@pytest.mark.django_db
class TestFolderRescan:
    def test_scoped_rescan_records_folder(self, client):
        folder = LibraryFolderFactory()

        with mock.patch.object(library_scanner, 'async_task'):
            resp = client.post(f'/api/library/folders/{folder.id}/rescan/')

        assert resp.status_code == 202
        assert LibraryScan.objects.filter(folder_id=folder.id).exists()


@pytest.mark.django_db
class TestFileDetailAndDownload:
    def test_file_detail(self, client):
        file_row = LibraryFileFactory(filename='test.stl', relative_path='test.stl')

        resp = client.get(f'/api/library/files/{file_row.id}/')

        assert resp.status_code == 200
        assert 'relative_path' in resp.data
        assert 'embedded_metadata' in resp.data
        assert 'sha256_hash' in resp.data

    def test_file_download_streams_share_bytes(self, client, tmp_path):
        root = LibraryRootFactory(path=str(tmp_path))
        folder = LibraryFolderFactory(root=root, relative_path='')
        (tmp_path / 'part.stl').write_bytes(b'solid test')
        file_row = LibraryFileFactory(
            root=root, folder=folder, filename='part.stl', relative_path='part.stl'
        )

        resp = client.get(f'/api/library/files/{file_row.id}/download/')

        assert resp.status_code == 200
        assert b''.join(resp.streaming_content) == b'solid test'

    def test_file_download_missing_on_disk_404(self, client, tmp_path):
        root = LibraryRootFactory(path=str(tmp_path))
        folder = LibraryFolderFactory(root=root, relative_path='')
        file_row = LibraryFileFactory(
            root=root, folder=folder, filename='ghost.stl', relative_path='ghost.stl'
        )

        resp = client.get(f'/api/library/files/{file_row.id}/download/')
        assert resp.status_code == 404

    def test_file_download_traversal_rejected(self, client, tmp_path):
        root = LibraryRootFactory(path=str(tmp_path))
        folder = LibraryFolderFactory(root=root, relative_path='')
        file_row = LibraryFileFactory(
            root=root, folder=folder,
            filename='passwd.stl', relative_path='../../etc/passwd',
        )

        resp = client.get(f'/api/library/files/{file_row.id}/download/')
        assert resp.status_code == 404


@pytest.mark.django_db
class TestScanStatus:
    def test_scan_progress_running(self, client):
        scan = LibraryScanFactory(status='running', files_queued=10, files_processed=5)

        resp = client.get(f'/api/library/scans/{scan.id}/')

        assert resp.status_code == 200
        assert resp.data['progress_percent'] == 50

    def test_scan_progress_success(self, client):
        scan = LibraryScanFactory(status='success', files_queued=10, files_processed=10)

        resp = client.get(f'/api/library/scans/{scan.id}/')

        assert resp.status_code == 200
        assert resp.data['progress_percent'] == 100

    def test_active_filter_returns_only_running_and_pending(self, client):
        """?active=true powers banner re-attachment after a page refresh — it
        must return in-flight jobs (pending/running) and drop finished ones."""
        root = LibraryRootFactory()
        running = LibraryScanFactory(root=root, status='running')
        pending = LibraryScanFactory(root=root, status='pending')
        LibraryScanFactory(root=root, status='success')
        LibraryScanFactory(root=root, status='error')

        resp = client.get('/api/library/scans/?active=true')

        assert resp.status_code == 200
        returned_ids = {row['id'] for row in resp.data}
        assert returned_ids == {running.id, pending.id}

    def test_scan_serializer_exposes_root_name_and_kind(self, client):
        """The banner renders job label + owning root without extra requests."""
        root = LibraryRootFactory(name='NAS Prints')
        scan = LibraryScanFactory(root=root, status='running', kind='thumbnails')

        resp = client.get(f'/api/library/scans/{scan.id}/')

        assert resp.status_code == 200
        assert resp.data['root_name'] == 'NAS Prints'
        assert resp.data['kind'] == 'thumbnails'

    def test_scan_serializer_exposes_result_counts(self, client):
        """The scan payload carries the per-scan new/updated/removed breakdown."""
        scan = LibraryScanFactory(
            status='success', files_new=5, files_updated=2, files_deleted=1
        )

        resp = client.get(f'/api/library/scans/{scan.id}/')

        assert resp.data['files_new'] == 5
        assert resp.data['files_updated'] == 2
        assert resp.data['files_deleted'] == 1


@pytest.mark.django_db
class TestThumbnailColorSetting:
    def test_patch_thumbnail_color(self, client):
        root = LibraryRootFactory()

        resp = client.patch(
            f'/api/library/roots/{root.id}/', {'thumbnail_color': '#FF8800'}, format='json'
        )

        assert resp.status_code == 200
        assert resp.data['thumbnail_color'] == '#ff8800'  # normalized lowercase

    def test_invalid_color_rejected(self, client):
        root = LibraryRootFactory()

        resp = client.patch(
            f'/api/library/roots/{root.id}/', {'thumbnail_color': 'red'}, format='json'
        )

        assert resp.status_code == 400

    def test_regenerate_thumbnails_accepted(self, client):
        root = LibraryRootFactory()

        with mock.patch.object(library_scanner, 'async_task'):
            resp = client.post(f'/api/library/roots/{root.id}/regenerate-thumbnails/')

        assert resp.status_code == 202
        assert resp.data['status'] == 'pending'

    def test_regenerate_conflict_while_scan_running(self, client):
        root = LibraryRootFactory()
        LibraryScanFactory(root=root, status='running')

        resp = client.post(f'/api/library/roots/{root.id}/regenerate-thumbnails/')
        assert resp.status_code == 409


@pytest.mark.django_db
class TestExtensionFilter:
    def test_filter_by_extension(self, client):
        folder = LibraryFolderFactory()
        LibraryFileFactory(folder=folder, filename='a.stl', relative_path='a.stl', extension='stl')
        LibraryFileFactory(folder=folder, filename='b.3mf', relative_path='b.3mf', extension='3mf')

        resp = client.get(f'/api/library/folders/{folder.id}/contents/', {'extension': '3mf'})
        filenames = [f['filename'] for f in resp.data['files']['results']]
        assert filenames == ['b.3mf']

        resp = client.get(f'/api/library/folders/{folder.id}/contents/', {'extension': 'stl'})
        filenames = [f['filename'] for f in resp.data['files']['results']]
        assert filenames == ['a.stl']

        resp = client.get(f'/api/library/folders/{folder.id}/contents/')
        assert resp.data['files']['count'] == 2

    def test_unknown_extension_value_ignored(self, client):
        folder = LibraryFolderFactory()
        LibraryFileFactory(folder=folder, filename='a.stl', relative_path='a.stl', extension='stl')

        resp = client.get(f'/api/library/folders/{folder.id}/contents/', {'extension': 'exe'})
        assert resp.data['files']['count'] == 1


# Phase 3 endpoints: search, permanent delete, purge
from inventory.models import LibraryFile, LibraryFolder  # noqa: E402


@pytest.mark.django_db
class TestPreviewSummary:
    def test_summary_counts_by_status_across_enabled_roots(self, client):
        folder = LibraryFolderFactory()
        LibraryFileFactory(folder=folder, relative_path='a.stl', thumbnail_status='rendered')
        LibraryFileFactory(folder=folder, relative_path='b.stl', thumbnail_status='rendered')
        LibraryFileFactory(folder=folder, relative_path='c.stl', thumbnail_status='too_large')
        LibraryFileFactory(folder=folder, relative_path='d.3mf', extension='3mf',
                           thumbnail_status='unrenderable')

        resp = client.get('/api/library/preview-summary/')

        assert resp.status_code == 200
        assert resp.data['total'] == 4
        assert resp.data['rendered'] == 2
        assert resp.data['too_large'] == 1
        assert resp.data['unrenderable'] == 1
        assert resp.data['without_preview'] == 2

    def test_summary_excludes_disabled_roots(self, client):
        disabled = LibraryRootFactory(path='/mnt/off', enabled=False)
        folder = LibraryFolderFactory(root=disabled)
        LibraryFileFactory(folder=folder, relative_path='x.stl', thumbnail_status='unrenderable')

        resp = client.get('/api/library/preview-summary/')
        assert resp.data['total'] == 0


@pytest.mark.django_db
class TestLibrarySearch:
    def test_search_matches_filename(self, client):
        """Substring match against filename."""
        folder = LibraryFolderFactory()
        LibraryFileFactory(folder=folder, filename='dragon_head.stl', relative_path='dragon_head.stl')
        LibraryFileFactory(folder=folder, filename='benchy.stl', relative_path='benchy.stl')

        resp = client.get('/api/library/search/', {'q': 'dragon'})

        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 1
        assert data['results'][0]['filename'] == 'dragon_head.stl'

    def test_search_matches_folder_path(self, client):
        """Substring match against the folder path portion of relative_path."""
        LibraryFileFactory(relative_path='widgets/gear.stl', filename='gear.stl')

        resp = client.get('/api/library/search/', {'q': 'widgets'})

        data = resp.json()
        assert data['count'] == 1
        assert data['results'][0]['relative_path'] == 'widgets/gear.stl'

    def test_search_spans_all_enabled_roots_by_default(self, client):
        """With no root param, search spans every enabled root and each hit is
        attributed to its owning root via root/root_name."""
        root_a = LibraryRootFactory(name='NAS', path='/mnt/nas')
        root_b = LibraryRootFactory(name='SSD', path='/mnt/ssd')
        folder_a = LibraryFolderFactory(root=root_a)
        folder_b = LibraryFolderFactory(root=root_b)
        LibraryFileFactory(folder=folder_a, filename='gadget_a.stl', relative_path='gadget_a.stl')
        LibraryFileFactory(folder=folder_b, filename='gadget_b.stl', relative_path='gadget_b.stl')

        resp = client.get('/api/library/search/', {'q': 'gadget'})

        data = resp.json()
        assert data['count'] == 2
        names = {r['root_name'] for r in data['results']}
        assert names == {'NAS', 'SSD'}

    def test_search_excludes_disabled_roots_when_unscoped(self, client):
        """A disabled root's files stay out of an all-roots (unscoped) search."""
        disabled = LibraryRootFactory(path='/mnt/off', enabled=False)
        folder = LibraryFolderFactory(root=disabled)
        LibraryFileFactory(folder=folder, filename='hidden_gizmo.stl', relative_path='hidden_gizmo.stl')

        resp = client.get('/api/library/search/', {'q': 'gizmo'})
        assert resp.json()['count'] == 0

        # Explicit root scope still reaches it.
        resp = client.get('/api/library/search/', {'q': 'gizmo', 'root': disabled.id})
        assert resp.json()['count'] == 1

    def test_search_excludes_deleted_by_default(self, client):
        """Soft-deleted files are hidden unless include_deleted=true."""
        LibraryFileFactory(filename='test.stl', status='deleted')

        resp = client.get('/api/library/search/', {'q': 'test'})
        assert resp.json()['count'] == 0

        resp = client.get('/api/library/search/', {'q': 'test', 'include_deleted': 'true'})
        assert resp.json()['count'] == 1

    def test_search_empty_query_returns_nothing(self, client):
        """Missing/empty q returns an empty result set, not everything."""
        LibraryFileFactory(filename='test.stl')

        data = client.get('/api/library/search/').json()

        assert data['count'] == 0
        assert data['results'] == []

    def test_search_extension_filter(self, client):
        """extension= narrows search hits by file type."""
        folder = LibraryFolderFactory()
        LibraryFileFactory(folder=folder, filename='test.stl', relative_path='test.stl', extension='stl')
        LibraryFileFactory(folder=folder, filename='test.3mf', relative_path='test.3mf', extension='3mf')

        data = client.get('/api/library/search/', {'q': 'test', 'extension': '3mf'}).json()

        assert data['count'] == 1
        assert data['results'][0]['filename'] == 'test.3mf'


@pytest.mark.django_db
class TestNewFilesSince:
    """GET /api/library/new-files/ — files first indexed by each root's most
    recent successful scan (created_at >= that scan's start)."""

    def _scan(self, root, started_at):
        return LibraryScanFactory(
            root=root, kind='scan', status='success', started_at=started_at,
            finished_at=started_at + timedelta(minutes=1),
        )

    def test_lists_files_created_since_last_scan(self, client):
        root = LibraryRootFactory(path='/mnt/nas')
        folder = LibraryFolderFactory(root=root)
        boundary = timezone.now() - timedelta(hours=1)
        self._scan(root, boundary)

        # "new": created after the scan started (factory sets created_at=now).
        LibraryFileFactory(folder=folder, filename='fresh.stl', relative_path='fresh.stl')
        # "old": created well before the boundary (auto_now_add only fires on
        # insert, so a follow-up .update() can backdate created_at).
        old = LibraryFileFactory(folder=folder, filename='old.stl', relative_path='old.stl')
        LibraryFile.objects.filter(pk=old.pk).update(created_at=boundary - timedelta(hours=2))

        data = client.get('/api/library/new-files/').json()

        assert data['count'] == 1
        assert data['results'][0]['filename'] == 'fresh.stl'

    def test_empty_when_no_scan_yet(self, client):
        folder = LibraryFolderFactory()
        LibraryFileFactory(folder=folder)

        data = client.get('/api/library/new-files/').json()

        assert data['count'] == 0
        assert data['results'] == []

    def test_excludes_deleted_files(self, client):
        root = LibraryRootFactory()
        folder = LibraryFolderFactory(root=root)
        self._scan(root, timezone.now() - timedelta(hours=1))
        LibraryFileFactory(folder=folder, status='deleted')

        assert client.get('/api/library/new-files/').json()['count'] == 0

    def test_extension_filter(self, client):
        root = LibraryRootFactory()
        folder = LibraryFolderFactory(root=root)
        self._scan(root, timezone.now() - timedelta(hours=1))
        LibraryFileFactory(folder=folder, filename='a.stl', relative_path='a.stl', extension='stl')
        LibraryFileFactory(folder=folder, filename='a.3mf', relative_path='a.3mf', extension='3mf')

        data = client.get('/api/library/new-files/', {'extension': '3mf'}).json()

        assert data['count'] == 1
        assert data['results'][0]['extension'] == '3mf'

    def test_spans_enabled_roots_excludes_disabled(self, client):
        enabled = LibraryRootFactory(path='/mnt/on')
        disabled = LibraryRootFactory(path='/mnt/off', enabled=False)
        self._scan(enabled, timezone.now() - timedelta(hours=1))
        self._scan(disabled, timezone.now() - timedelta(hours=1))
        LibraryFileFactory(
            folder=LibraryFolderFactory(root=enabled), filename='on.stl', relative_path='on.stl'
        )
        LibraryFileFactory(
            folder=LibraryFolderFactory(root=disabled), filename='off.stl', relative_path='off.stl'
        )

        data = client.get('/api/library/new-files/').json()

        assert data['count'] == 1
        assert data['results'][0]['filename'] == 'on.stl'

    def test_measures_against_most_recent_scan(self, client):
        """Only the latest scan defines 'since last scan': a file indexed
        between an older and a newer scan is not new relative to the newer one."""
        root = LibraryRootFactory()
        folder = LibraryFolderFactory(root=root)
        self._scan(root, timezone.now() - timedelta(hours=2))
        mid = LibraryFileFactory(folder=folder, filename='mid.stl', relative_path='mid.stl')
        LibraryFile.objects.filter(pk=mid.pk).update(created_at=timezone.now() - timedelta(hours=1))
        self._scan(root, timezone.now() - timedelta(minutes=1))

        assert client.get('/api/library/new-files/').json()['count'] == 0


@pytest.mark.django_db
class TestRootScanSummary:
    """LibraryRootSerializer's next_scan_at + last_scan (settings-screen extras)."""

    def test_last_scan_summary_exposed(self, client):
        root = LibraryRootFactory()
        LibraryScanFactory(
            root=root, kind='scan', status='success', finished_at=timezone.now(),
            files_seen=40, files_new=12, files_updated=3, files_deleted=1,
        )

        resp = client.get(f'/api/library/roots/{root.id}/')

        summary = resp.data['last_scan']
        assert summary['status'] == 'success'
        assert summary['files_new'] == 12
        assert summary['files_updated'] == 3
        assert summary['files_deleted'] == 1

    def test_last_scan_null_before_any_scan(self, client):
        root = LibraryRootFactory()

        resp = client.get(f'/api/library/roots/{root.id}/')

        assert resp.data['last_scan'] is None

    def test_last_scan_ignores_thumbnail_jobs(self, client):
        """A later thumbnail regeneration must not overwrite the shown scan
        summary — only kind='scan' jobs count as 'the last scan'."""
        root = LibraryRootFactory()
        LibraryScanFactory(
            root=root, kind='scan', status='success',
            finished_at=timezone.now() - timedelta(minutes=5), files_new=7,
        )
        LibraryScanFactory(
            root=root, kind='thumbnails', status='success', finished_at=timezone.now(),
        )

        resp = client.get(f'/api/library/roots/{root.id}/')

        assert resp.data['last_scan']['files_new'] == 7

    def test_next_scan_at_present_with_interval(self, client):
        """A root with a rescan interval has a periodic Schedule (created by the
        post_save signal); next_scan_at surfaces its next run time."""
        root = LibraryRootFactory(rescan_interval_hours=6)

        resp = client.get(f'/api/library/roots/{root.id}/')

        assert resp.data['next_scan_at'] is not None

    def test_next_scan_at_null_without_interval(self, client):
        root = LibraryRootFactory()  # manual-only, no interval

        resp = client.get(f'/api/library/roots/{root.id}/')

        assert resp.data['next_scan_at'] is None


@pytest.mark.django_db
class TestPermanentDelete:
    def test_delete_soft_deleted_file(self, client):
        file_row = LibraryFileFactory(status='deleted')

        resp = client.delete(f'/api/library/files/{file_row.id}/')

        assert resp.status_code == 204
        assert not LibraryFile.objects.filter(pk=file_row.pk).exists()

    def test_delete_active_file_refused(self, client):
        """No path from active straight to hard-deleted."""
        file_row = LibraryFileFactory(status='active')

        resp = client.delete(f'/api/library/files/{file_row.id}/')

        assert resp.status_code == 409
        assert LibraryFile.objects.filter(pk=file_row.pk).exists()

    def test_delete_soft_deleted_folder(self, client):
        folder = LibraryFolderFactory(status='deleted')

        resp = client.delete(f'/api/library/folders/{folder.id}/')

        assert resp.status_code == 204
        assert not LibraryFolder.objects.filter(pk=folder.pk).exists()

    def test_delete_active_folder_refused(self, client):
        folder = LibraryFolderFactory(status='active')

        resp = client.delete(f'/api/library/folders/{folder.id}/')
        assert resp.status_code == 409

    def test_delete_folder_with_active_descendant_refused(self, client):
        """A deleted folder row shielding active rows can't be purged."""
        folder = LibraryFolderFactory(status='deleted', relative_path='old')
        LibraryFileFactory(folder=folder, relative_path='old/sub.stl', status='active')

        resp = client.delete(f'/api/library/folders/{folder.id}/')
        assert resp.status_code == 409


@pytest.mark.django_db
class TestPurgeDeleted:
    def test_purge_removes_only_deleted(self, client):
        folder = LibraryFolderFactory()
        active_file = LibraryFileFactory(folder=folder, relative_path='active.stl', status='active')
        deleted_file = LibraryFileFactory(folder=folder, relative_path='deleted.stl', status='deleted')
        deleted_folder = LibraryFolderFactory(status='deleted')

        data = client.post('/api/library/purge-deleted/').json()

        assert data['files_purged'] == 1
        assert data['folders_purged'] == 1
        assert not LibraryFile.objects.filter(pk=deleted_file.pk).exists()
        assert LibraryFile.objects.filter(pk=active_file.pk).exists()
        assert not LibraryFolder.objects.filter(pk=deleted_folder.pk).exists()

    def test_purge_skips_folder_with_active_content(self, client):
        """A deleted folder with an active descendant survives the purge."""
        folder = LibraryFolderFactory(status='deleted', relative_path='keepme')
        LibraryFileFactory(folder=folder, relative_path='keepme/live.stl', status='active')

        data = client.post('/api/library/purge-deleted/').json()

        assert LibraryFolder.objects.filter(pk=folder.pk).exists()
        assert data['files_purged'] == 0
        assert data['folders_purged'] == 0
