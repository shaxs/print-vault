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

from inventory.models import LibraryFile, LibraryRoot, LibraryScan, Tag
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

    def test_patch_notes_updates_field(self, client):
        """PATCH sets user notes and echoes them back."""
        file_row = LibraryFileFactory(filename='exhaust.stl', relative_path='exhaust.stl')

        resp = client.patch(
            f'/api/library/files/{file_row.id}/',
            {'notes': 'Uses a 140mm fan'},
            format='json',
        )

        assert resp.status_code == 200
        assert resp.data['notes'] == 'Uses a 140mm fan'
        file_row.refresh_from_db()
        assert file_row.notes == 'Uses a 140mm fan'

    def test_patch_ignores_non_notes_fields(self, client):
        """Only `notes` is writable — a PATCH can't overwrite scanner-owned
        fields like filename."""
        file_row = LibraryFileFactory(filename='original.stl', relative_path='original.stl')

        resp = client.patch(
            f'/api/library/files/{file_row.id}/',
            {'notes': 'a note', 'filename': 'hacked.stl', 'status': 'deleted'},
            format='json',
        )

        assert resp.status_code == 200
        file_row.refresh_from_db()
        assert file_row.notes == 'a note'
        assert file_row.filename == 'original.stl'  # untouched
        assert file_row.status == 'active'  # untouched

    def test_patch_tag_ids_assigns_tags(self, client):
        """PATCH tag_ids sets the M2M and the response returns nested tags."""
        file_row = LibraryFileFactory(filename='part.stl', relative_path='part.stl')
        toys = Tag.objects.create(name='toys', slug='toys')
        gridfinity = Tag.objects.create(name='gridfinity', slug='gridfinity')

        resp = client.patch(
            f'/api/library/files/{file_row.id}/',
            {'tag_ids': [toys.id, gridfinity.id]},
            format='json',
        )

        assert resp.status_code == 200
        assert {t['slug'] for t in resp.data['tags']} == {'toys', 'gridfinity'}
        assert set(file_row.tags.values_list('slug', flat=True)) == {'toys', 'gridfinity'}

    def test_patch_toggles_favorite(self, client):
        """PATCH is_favorite flags/unflags a file."""
        file_row = LibraryFileFactory(filename='part.stl', relative_path='part.stl')
        assert file_row.is_favorite is False

        resp = client.patch(
            f'/api/library/files/{file_row.id}/', {'is_favorite': True}, format='json',
        )
        assert resp.status_code == 200
        assert resp.data['is_favorite'] is True
        file_row.refresh_from_db()
        assert file_row.is_favorite is True

        resp = client.patch(
            f'/api/library/files/{file_row.id}/', {'is_favorite': False}, format='json',
        )
        file_row.refresh_from_db()
        assert file_row.is_favorite is False

    def test_patch_tag_ids_replaces_existing(self, client):
        """Sending a new tag_ids set replaces the old assignment."""
        file_row = LibraryFileFactory(filename='part.stl', relative_path='part.stl')
        a = Tag.objects.create(name='a', slug='a')
        b = Tag.objects.create(name='b', slug='b')
        file_row.tags.add(a)

        resp = client.patch(
            f'/api/library/files/{file_row.id}/', {'tag_ids': [b.id]}, format='json',
        )

        assert resp.status_code == 200
        assert set(file_row.tags.values_list('slug', flat=True)) == {'b'}

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

    def test_search_results_include_notes(self, client):
        """Search results carry the notes field so the results table can show a
        preview column."""
        LibraryFileFactory(
            filename='vent.stl', relative_path='vent.stl', notes='Fits a 140mm fan',
        )

        data = client.get('/api/library/search/', {'q': 'vent'}).json()

        assert data['results'][0]['notes'] == 'Fits a 140mm fan'

    def test_search_default_matches_notes(self, client):
        """A term only in a file's notes (not its name/path) still matches when
        no fields param is given — the default scope spans name + notes."""
        LibraryFileFactory(
            filename='exhaust_shroud.stl', relative_path='exhaust_shroud.stl',
            notes='Fits a 140mm fan for cooling',
        )

        data = client.get('/api/library/search/', {'q': 'fan'}).json()

        assert data['count'] == 1
        assert data['results'][0]['filename'] == 'exhaust_shroud.stl'

    def test_search_fields_notes_only(self, client):
        """fields=notes matches notes but not a same-named file whose only
        occurrence is in its filename."""
        folder = LibraryFolderFactory()
        LibraryFileFactory(
            folder=folder, filename='bracket.stl', relative_path='bracket.stl',
            notes='needs a 140mm fan',
        )
        LibraryFileFactory(
            folder=folder, filename='fan_duct.stl', relative_path='fan_duct.stl',
            notes='',
        )

        data = client.get('/api/library/search/', {'q': 'fan', 'fields': 'notes'}).json()

        assert data['count'] == 1
        assert data['results'][0]['filename'] == 'bracket.stl'

    def test_search_fields_name_only_ignores_notes(self, client):
        """fields=name matches filename/path but not notes."""
        LibraryFileFactory(
            filename='bracket.stl', relative_path='bracket.stl',
            notes='needs a 140mm fan',
        )

        data = client.get('/api/library/search/', {'q': 'fan', 'fields': 'name'}).json()

        assert data['count'] == 0

    def test_search_unknown_fields_falls_back_to_all(self, client):
        """An unrecognized fields value searches everything rather than
        returning nothing."""
        LibraryFileFactory(
            filename='bracket.stl', relative_path='bracket.stl',
            notes='needs a 140mm fan',
        )

        data = client.get('/api/library/search/', {'q': 'fan', 'fields': 'bogus'}).json()

        assert data['count'] == 1

    def test_search_default_matches_tags(self, client):
        """A term matching only a file's tag (not name/notes) still matches by
        default (all scopes include tags)."""
        f = LibraryFileFactory(filename='bracket.stl', relative_path='bracket.stl')
        f.tags.add(Tag.objects.create(name='gridfinity', slug='gridfinity'))

        data = client.get('/api/library/search/', {'q': 'gridfinity'}).json()

        assert data['count'] == 1
        assert data['results'][0]['filename'] == 'bracket.stl'

    def test_search_fields_tags_only(self, client):
        """fields=tags matches on tags, not on a same-worded filename."""
        folder = LibraryFolderFactory()
        tagged = LibraryFileFactory(folder=folder, filename='bracket.stl', relative_path='bracket.stl')
        tagged.tags.add(Tag.objects.create(name='toys', slug='toys'))
        LibraryFileFactory(folder=folder, filename='toys.stl', relative_path='toys.stl')

        data = client.get('/api/library/search/', {'q': 'toys', 'fields': 'tags'}).json()

        assert data['count'] == 1
        assert data['results'][0]['filename'] == 'bracket.stl'

    def test_browse_by_tags_default_is_intersection(self, client):
        """tags= with no tag_mode = AND: only files carrying EVERY selected tag."""
        folder = LibraryFolderFactory()
        toys = Tag.objects.create(name='toys', slug='toys')
        tools = Tag.objects.create(name='tools', slug='tools')
        both = LibraryFileFactory(folder=folder, filename='both.stl', relative_path='both.stl')
        both.tags.add(toys, tools)
        only_toys = LibraryFileFactory(folder=folder, filename='toys_only.stl', relative_path='toys_only.stl')
        only_toys.tags.add(toys)

        data = client.get('/api/library/search/', {'tags': 'toys,tools'}).json()

        assert data['count'] == 1
        assert data['results'][0]['filename'] == 'both.stl'

    def test_browse_by_tags_any_mode_is_union(self, client):
        """tag_mode=any = OR: files carrying at least one selected tag."""
        folder = LibraryFolderFactory()
        toys = Tag.objects.create(name='toys', slug='toys')
        tools = Tag.objects.create(name='tools', slug='tools')
        a = LibraryFileFactory(folder=folder, filename='a.stl', relative_path='a.stl')
        a.tags.add(toys)
        b = LibraryFileFactory(folder=folder, filename='b.stl', relative_path='b.stl')
        b.tags.add(tools)
        LibraryFileFactory(folder=folder, filename='c.stl', relative_path='c.stl')  # untagged

        data = client.get('/api/library/search/', {'tags': 'toys,tools', 'tag_mode': 'any'}).json()

        assert data['count'] == 2
        assert {r['filename'] for r in data['results']} == {'a.stl', 'b.stl'}

    def test_browse_by_tags_no_duplicate_rows(self, client):
        """A file carrying all requested tags appears once (distinct)."""
        f = LibraryFileFactory(filename='a.stl', relative_path='a.stl')
        f.tags.add(Tag.objects.create(name='toys', slug='toys'))
        f.tags.add(Tag.objects.create(name='tools', slug='tools'))

        data = client.get('/api/library/search/', {'tags': 'toys,tools'}).json()

        assert data['count'] == 1

    def test_search_results_include_tags(self, client):
        """Search results carry nested tags for the badge display."""
        f = LibraryFileFactory(filename='part.stl', relative_path='part.stl')
        f.tags.add(Tag.objects.create(name='toys', slug='toys'))

        data = client.get('/api/library/search/', {'q': 'part'}).json()

        assert [t['slug'] for t in data['results'][0]['tags']] == ['toys']

    def test_favorites_browse_without_query(self, client):
        """favorites=true browses favorited files with no text query."""
        folder = LibraryFolderFactory()
        LibraryFileFactory(folder=folder, filename='fav.stl', relative_path='fav.stl', is_favorite=True)
        LibraryFileFactory(folder=folder, filename='plain.stl', relative_path='plain.stl', is_favorite=False)

        data = client.get('/api/library/search/', {'favorites': 'true'}).json()

        assert data['count'] == 1
        assert data['results'][0]['filename'] == 'fav.stl'
        assert data['results'][0]['is_favorite'] is True

    def test_favorites_combines_with_query(self, client):
        """favorites=true narrows a text search to favorited hits."""
        folder = LibraryFolderFactory()
        LibraryFileFactory(folder=folder, filename='gear_a.stl', relative_path='gear_a.stl', is_favorite=True)
        LibraryFileFactory(folder=folder, filename='gear_b.stl', relative_path='gear_b.stl', is_favorite=False)

        data = client.get('/api/library/search/', {'q': 'gear', 'favorites': 'true'}).json()

        assert data['count'] == 1
        assert data['results'][0]['filename'] == 'gear_a.stl'


@pytest.mark.django_db
class TestTagsAPI:
    """/api/tags/ — shared tag CRUD with idempotent create."""

    def test_create_tag(self, client):
        resp = client.post('/api/tags/', {'name': 'Gridfinity'}, format='json')

        assert resp.status_code == 201
        assert resp.data['name'] == 'Gridfinity'
        assert resp.data['slug'] == 'gridfinity'

    def test_create_is_idempotent_on_slug(self, client):
        """Re-creating a name that normalizes to an existing slug returns the
        existing tag with 200 instead of erroring or duplicating."""
        first = client.post('/api/tags/', {'name': 'gridfinity'}, format='json')
        assert first.status_code == 201

        again = client.post('/api/tags/', {'name': 'Gridfinity'}, format='json')

        assert again.status_code == 200
        assert again.data['id'] == first.data['id']
        assert Tag.objects.filter(slug='gridfinity').count() == 1

    def test_create_blank_rejected(self, client):
        resp = client.post('/api/tags/', {'name': '   '}, format='json')
        assert resp.status_code == 400

    def test_list_filters_by_q(self, client):
        Tag.objects.create(name='toys', slug='toys')
        Tag.objects.create(name='tools', slug='tools')
        Tag.objects.create(name='gridfinity', slug='gridfinity')

        data = client.get('/api/tags/', {'q': 'too'}).json()

        names = {t['name'] for t in data}
        assert names == {'tools'}

    def test_list_reports_usage_count(self, client):
        """Each listed tag carries a live usage_count (files carrying it)."""
        popular = Tag.objects.create(name='popular', slug='popular')
        LibraryFileFactory(filename='a.stl', relative_path='a.stl').tags.add(popular)
        LibraryFileFactory(filename='b.stl', relative_path='b.stl').tags.add(popular)
        Tag.objects.create(name='unused', slug='unused')

        by_name = {t['name']: t for t in client.get('/api/tags/').json()}

        assert by_name['popular']['usage_count'] == 2
        assert by_name['unused']['usage_count'] == 0

    def test_list_ordered_most_used_first(self, client):
        """The list is ordered by usage_count desc (popular tags surface first)."""
        one = Tag.objects.create(name='one_use', slug='one-use')
        three = Tag.objects.create(name='three_use', slug='three-use')
        LibraryFileFactory(filename='x.stl', relative_path='x.stl').tags.add(one)
        for i in range(3):
            LibraryFileFactory(filename=f't{i}.stl', relative_path=f't{i}.stl').tags.add(three)

        names = [t['name'] for t in client.get('/api/tags/').json()]

        assert names.index('three_use') < names.index('one_use')

    def test_in_use_filter_hides_orphan_tags(self, client):
        """?in_use=true returns only tags applied to at least one file."""
        used = Tag.objects.create(name='used', slug='used')
        LibraryFileFactory(filename='u.stl', relative_path='u.stl').tags.add(used)
        Tag.objects.create(name='orphan', slug='orphan')  # never applied

        names = {t['name'] for t in client.get('/api/tags/', {'in_use': 'true'}).json()}

        assert names == {'used'}


@pytest.mark.django_db
class TestNewFilesSince:
    """GET /api/library/new-files/ — files first indexed by each root's most
    recent successful scan (created_at >= that scan's start). A root needs at
    least two successful scans (a baseline) to contribute."""

    def _scan(self, root, started_at):
        return LibraryScanFactory(
            root=root, kind='scan', status='success', started_at=started_at,
            finished_at=started_at + timedelta(minutes=1),
        )

    def _baseline(self, root, started_at):
        """An earlier successful scan so the root clears the >=2-scan bar; its
        time is older than the boundary scan, so it doesn't affect results."""
        return self._scan(root, started_at - timedelta(hours=3))

    def test_lists_files_created_since_last_scan(self, client):
        root = LibraryRootFactory(path='/mnt/nas')
        folder = LibraryFolderFactory(root=root)
        boundary = timezone.now() - timedelta(hours=1)
        self._baseline(root, boundary)
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

    def test_requires_two_scans_baseline(self, client):
        """A root with only ONE successful scan has no baseline, so nothing is
        "new" yet — every file was first indexed in that single pass."""
        root = LibraryRootFactory()
        folder = LibraryFolderFactory(root=root)
        self._scan(root, timezone.now() - timedelta(hours=1))  # only one scan
        LibraryFileFactory(folder=folder, filename='fresh.stl', relative_path='fresh.stl')

        assert client.get('/api/library/new-files/').json()['count'] == 0

    def test_excludes_deleted_files(self, client):
        root = LibraryRootFactory()
        folder = LibraryFolderFactory(root=root)
        self._baseline(root, timezone.now() - timedelta(hours=1))
        self._scan(root, timezone.now() - timedelta(hours=1))
        LibraryFileFactory(folder=folder, status='deleted')

        assert client.get('/api/library/new-files/').json()['count'] == 0

    def test_extension_filter(self, client):
        root = LibraryRootFactory()
        folder = LibraryFolderFactory(root=root)
        self._baseline(root, timezone.now() - timedelta(hours=1))
        self._scan(root, timezone.now() - timedelta(hours=1))
        LibraryFileFactory(folder=folder, filename='a.stl', relative_path='a.stl', extension='stl')
        LibraryFileFactory(folder=folder, filename='a.3mf', relative_path='a.3mf', extension='3mf')

        data = client.get('/api/library/new-files/', {'extension': '3mf'}).json()

        assert data['count'] == 1
        assert data['results'][0]['extension'] == '3mf'

    def test_spans_enabled_roots_excludes_disabled(self, client):
        enabled = LibraryRootFactory(path='/mnt/on')
        disabled = LibraryRootFactory(path='/mnt/off', enabled=False)
        self._baseline(enabled, timezone.now() - timedelta(hours=1))
        self._scan(enabled, timezone.now() - timedelta(hours=1))
        self._baseline(disabled, timezone.now() - timedelta(hours=1))
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
