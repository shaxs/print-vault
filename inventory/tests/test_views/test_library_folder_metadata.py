"""API tests for folder tags/notes metadata + folder search hits."""
import pytest
from rest_framework.test import APIClient

from inventory.models import Tag
from inventory.tests.factories import (
    LibraryRootFactory,
    LibraryFolderFactory,
    LibraryFileFactory,
)


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def tree(db):
    """root / A(rel 'A') / A1(rel 'A/1'), a file under each."""
    root = LibraryRootFactory(path='/mnt/meta')
    A = LibraryFolderFactory(root=root, relative_path='A', name='A')
    A1 = LibraryFolderFactory(root=root, relative_path='A/1', name='1')
    fA = LibraryFileFactory(folder=A, root=root, relative_path='A/a.stl', filename='a.stl')
    fA1 = LibraryFileFactory(folder=A1, root=root, relative_path='A/1/b.stl', filename='b.stl')
    return {'root': root, 'A': A, 'A1': A1, 'fA': fA, 'fA1': fA1}


@pytest.mark.django_db
class TestFolderMetadataEndpoint:
    def test_get_returns_tags_and_notes(self, client, tree):
        rack = Tag.objects.create(name='rack', slug='rack')
        tree['A'].tags.add(rack)
        tree['A'].notes = 'master folder'
        tree['A'].save()

        resp = client.get(f"/api/library/folders/{tree['A'].id}/metadata/")

        assert resp.status_code == 200
        assert resp.data['notes'] == 'master folder'
        assert [t['slug'] for t in resp.data['tags']] == ['rack']

    def test_put_sets_tags_notes_and_cascades(self, client, tree):
        rack = Tag.objects.create(name='rack', slug='rack')

        resp = client.put(
            f"/api/library/folders/{tree['A'].id}/metadata/",
            {'tag_ids': [rack.id], 'notes': 'ten inch rack'},
            format='json',
        )

        assert resp.status_code == 200
        assert resp.data['affected_files'] == 2      # both files in the subtree
        assert resp.data['affected_folders'] == 1    # subfolder A/1
        # Persisted + cascaded.
        assert 'rack' in tree['A1'].tags.values_list('slug', flat=True)
        assert 'rack' in tree['fA1'].tags.values_list('slug', flat=True)
        tree['A'].refresh_from_db()
        assert tree['A'].notes == 'ten inch rack'

    def test_put_removal_strips_descendants(self, client, tree):
        rack = Tag.objects.create(name='rack', slug='rack')
        client.put(
            f"/api/library/folders/{tree['A'].id}/metadata/",
            {'tag_ids': [rack.id], 'notes': ''}, format='json',
        )
        # Now remove it.
        client.put(
            f"/api/library/folders/{tree['A'].id}/metadata/",
            {'tag_ids': [], 'notes': ''}, format='json',
        )
        assert 'rack' not in tree['fA1'].tags.values_list('slug', flat=True)
        assert 'rack' not in tree['A1'].tags.values_list('slug', flat=True)

    def test_resync_restores_removed_subfolder_tag(self, client, tree):
        rack = Tag.objects.create(name='rack', slug='rack')
        client.put(
            f"/api/library/folders/{tree['A'].id}/metadata/",
            {'tag_ids': [rack.id], 'notes': ''}, format='json',
        )
        tree['A1'].tags.remove(rack)
        tree['fA1'].tags.remove(rack)

        resp = client.post(f"/api/library/folders/{tree['A'].id}/resync/")

        assert resp.status_code == 200
        assert 'rack' in tree['A1'].tags.values_list('slug', flat=True)
        assert 'rack' in tree['fA1'].tags.values_list('slug', flat=True)


@pytest.mark.django_db
class TestFolderSearchHits:
    def test_search_returns_folder_hit_on_name(self, client, tree):
        LibraryFolderFactory(
            root=tree['root'], relative_path='A/10 inch rack', name='10 inch rack',
        )
        data = client.get('/api/library/search/', {'q': '10 inch rack'}).json()

        assert any(f['name'] == '10 inch rack' for f in data['folders'])

    def test_search_returns_folder_hit_on_notes(self, client, tree):
        tree['A'].notes = 'all the 10-inch rack designs'
        tree['A'].save()

        data = client.get('/api/library/search/', {'q': '10-inch rack'}).json()

        assert any(f['id'] == tree['A'].id for f in data['folders'])

    def test_folder_hits_only_on_first_page(self, client, tree):
        # Folder A matches on notes; three files match on filename so a small
        # page_size yields a real second page.
        tree['A'].notes = 'rackmount'
        tree['A'].save()
        for i in range(3):
            LibraryFileFactory(
                folder=tree['A'], root=tree['root'],
                relative_path=f'A/rackmount_{i}.stl', filename=f'rackmount_{i}.stl',
            )

        params = {'q': 'rackmount', 'page_size': '2'}
        page1 = client.get('/api/library/search/', params).json()
        page2 = client.get('/api/library/search/', {**params, 'page': '2'}).json()

        assert len(page1['folders']) >= 1
        assert page2['folders'] == []  # present but empty on later pages

    def test_tag_browse_returns_no_folder_hits(self, client, tree):
        """A pure tag/favorite browse (no text q) has no folder text to match."""
        toys = Tag.objects.create(name='toys', slug='toys')
        tree['fA'].tags.add(toys)

        data = client.get('/api/library/search/', {'tags': 'toys'}).json()

        assert data['folders'] == []
