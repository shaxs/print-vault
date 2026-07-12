"""Unit tests for the folder tag cascade service.

Covers the copy-down model: a folder's tags cascade DOWN into every descendant
folder and file, downward-only (never up), delta-based add/remove, forceful
re-sync, and scan-time stamping of new files. See
chat_docs/planning/LIBRARY_FOLDER_TAG_CASCADE_PLAN.md.
"""
import pytest

from inventory.models import LibraryFile, LibraryFolder, Tag
from inventory.services.library_folder_tags import (
    apply_folder_metadata,
    resync_folder,
    stamp_new_files,
)
from inventory.tests.factories import (
    LibraryRootFactory,
    LibraryFolderFactory,
    LibraryFileFactory,
)


@pytest.fixture
def tree(db):
    """A / {1 / {B, C}, 2}, one file per folder, all in one root.

    Returns a dict of folders + files + root for readable assertions.
    """
    root = LibraryRootFactory(path='/mnt/tree')

    def folder(rel):
        name = rel.rsplit('/', 1)[-1]
        return LibraryFolderFactory(root=root, relative_path=rel, name=name)

    A = folder('A')
    A1 = folder('A/1')
    B = folder('A/1/B')
    C = folder('A/1/C')
    A2 = folder('A/2')

    def file(folder_obj, rel):
        return LibraryFileFactory(
            folder=folder_obj, root=root, relative_path=rel,
            filename=rel.rsplit('/', 1)[-1],
        )

    return {
        'root': root,
        'A': A, 'A1': A1, 'B': B, 'C': C, 'A2': A2,
        'fA': file(A, 'A/root.stl'),
        'fB': file(B, 'A/1/B/hotswap.stl'),
        'fC': file(C, 'A/1/C/pdu.stl'),
        'fA2': file(A2, 'A/2/tray.stl'),
    }


def slugs(obj):
    return set(obj.tags.values_list('slug', flat=True))


@pytest.mark.django_db
def test_apply_cascades_down_to_every_descendant(tree):
    rack = Tag.objects.create(name='rack', slug='rack')

    result = apply_folder_metadata(tree['A'], [rack.id], '')

    # Every descendant folder and file carries the tag.
    for key in ('A', 'A1', 'B', 'C', 'A2'):
        assert 'rack' in slugs(tree[key]), key
    for key in ('fA', 'fB', 'fC', 'fA2'):
        assert 'rack' in slugs(tree[key]), key
    # Counts: 4 descendant folders (not A itself) + 4 files.
    assert result['affected_folders'] == 4
    assert result['affected_files'] == 4


@pytest.mark.django_db
def test_cascade_is_downward_only(tree):
    """Tagging a mid-level folder never bubbles up to its parents/siblings."""
    extra = Tag.objects.create(name='extra', slug='extra')

    apply_folder_metadata(tree['A1'], [extra.id], '')

    # Down into 1's subtree...
    assert 'extra' in slugs(tree['B'])
    assert 'extra' in slugs(tree['C'])
    assert 'extra' in slugs(tree['fB'])
    # ...but NOT up to A, nor across to sibling 2.
    assert 'extra' not in slugs(tree['A'])
    assert 'extra' not in slugs(tree['A2'])
    assert 'extra' not in slugs(tree['fA2'])


@pytest.mark.django_db
def test_removal_strips_descendants_but_keeps_their_own_tags(tree):
    rack = Tag.objects.create(name='rack', slug='rack')
    hdd = Tag.objects.create(name='hdd', slug='hdd')
    tree['B'].tags.add(hdd)
    tree['fB'].tags.add(hdd)

    apply_folder_metadata(tree['A'], [rack.id], '')      # rack everywhere
    apply_folder_metadata(tree['A'], [], '')             # remove rack from A

    # rack gone from the whole subtree, hdd (B's own) preserved.
    assert 'rack' not in slugs(tree['B'])
    assert 'rack' not in slugs(tree['fB'])
    assert 'hdd' in slugs(tree['B'])
    assert 'hdd' in slugs(tree['fB'])


@pytest.mark.django_db
def test_prefix_isolation_no_sibling_name_leak(tree):
    """'A/1' must not cascade into a name-prefixed sibling 'A/10'."""
    a10 = LibraryFolderFactory(root=tree['root'], relative_path='A/10', name='10')
    f10 = LibraryFileFactory(
        folder=a10, root=tree['root'], relative_path='A/10/x.stl', filename='x.stl',
    )
    extra = Tag.objects.create(name='extra', slug='extra')

    apply_folder_metadata(tree['A1'], [extra.id], '')

    assert 'extra' not in slugs(a10)
    assert 'extra' not in slugs(f10)


@pytest.mark.django_db
def test_notes_do_not_cascade(tree):
    apply_folder_metadata(tree['A'], [], 'ten inch rack master folder')

    tree['A'].refresh_from_db()
    tree['B'].refresh_from_db()
    assert tree['A'].notes == 'ten inch rack master folder'
    assert tree['B'].notes == ''  # never cascades to subfolders


@pytest.mark.django_db
def test_resync_restores_a_removed_subfolder_tag(tree):
    rack = Tag.objects.create(name='rack', slug='rack')
    apply_folder_metadata(tree['A'], [rack.id], '')

    # Simulate drift: someone stripped rack from folder C and its file.
    tree['C'].tags.remove(rack)
    tree['fC'].tags.remove(rack)
    assert 'rack' not in slugs(tree['C'])

    resync_folder(tree['A'])

    assert 'rack' in slugs(tree['C'])
    assert 'rack' in slugs(tree['fC'])


@pytest.mark.django_db
def test_stamp_new_files_applies_folder_tags(tree):
    hdd = Tag.objects.create(name='hdd', slug='hdd')
    tree['B'].tags.add(hdd)
    new_file = LibraryFileFactory(
        folder=tree['B'], root=tree['root'],
        relative_path='A/1/B/new.stl', filename='new.stl',
    )
    assert slugs(new_file) == set()

    stamped = stamp_new_files({tree['B'].pk: [new_file.pk]})

    assert stamped == 1
    assert 'hdd' in slugs(new_file)


@pytest.mark.django_db
def test_stamp_new_files_skips_untagged_folder(tree):
    new_file = LibraryFileFactory(
        folder=tree['C'], root=tree['root'],
        relative_path='A/1/C/new.stl', filename='new.stl',
    )
    stamped = stamp_new_files({tree['C'].pk: [new_file.pk]})
    assert stamped == 0
    assert slugs(new_file) == set()
