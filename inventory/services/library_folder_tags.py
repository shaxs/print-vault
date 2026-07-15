"""
Folder-level tag cascade for the STL/3MF Library.

Design (see chat_docs/planning/LIBRARY_FOLDER_TAG_CASCADE_PLAN.md):

Two separate rules:

1. File resolution is trivial — a file's tags are exactly the tags on its
   IMMEDIATE parent folder, materialized as real ``LibraryFile.tags`` rows so
   the existing browse/search/filter machinery is unchanged. Nothing walks the
   tree at file level.

2. Cascade is folder-to-folder COPY-DOWN — setting/removing a tag on a folder
   propagates that change DOWNWARD into every descendant folder's own tag set
   (recursively, downward-only, never up to a parent), and each affected folder
   re-stamps its files.

Subtree membership uses the indexed ``relative_path`` prefix (``path + '/'``),
so a folder named ``10 inch`` never leaks into ``10 inch rack``. All propagation
is done with bulk through-model writes (two queries, independent of subtree
size) rather than per-row saves.
"""
from collections import defaultdict

from inventory.models import LibraryFile, LibraryFolder, Tag

# Auto-created M2M through models; used for bulk add/remove.
_FOLDER_TAGS = LibraryFolder.tags.through   # fields: libraryfolder_id, tag_id
_FILE_TAGS = LibraryFile.tags.through       # fields: libraryfile_id, tag_id

# Cap on in-memory through-rows before a flush. The additions list is a
# Cartesian product (rows x tags), and stamp_new_files runs once per WHOLE
# SCAN in the walk phase — which the module docstring requires to "stay
# cheap" because Django-Q kills the walk task at the 300s timeout. A first
# scan of a large, heavily-tagged library could otherwise build one unbounded
# list and blow that budget in a single bulk_create call. Matches
# library_scanner.BULK_BATCH_SIZE's convention.
_BATCH_SIZE = 500


def _subtree_prefix(folder):
    """The ``relative_path`` prefix matching everything strictly BELOW *folder*.
    Empty string for a root folder (``relative_path == ''``), meaning "the whole
    root" — callers handle that by not applying a prefix filter."""
    return f"{folder.relative_path}/" if folder.relative_path else ''


def descendant_folders(folder, include_self=False):
    """Folders under *folder* (same root). The root folder (empty relative_path)
    owns the whole root's folder set."""
    qs = LibraryFolder.objects.filter(root_id=folder.root_id)
    prefix = _subtree_prefix(folder)
    if prefix:
        from django.db.models import Q
        cond = Q(relative_path__startswith=prefix)
        if include_self:
            cond |= Q(pk=folder.pk)
        qs = qs.filter(cond)
    elif not include_self:
        qs = qs.exclude(pk=folder.pk)
    return qs


def descendant_files(folder):
    """All files under *folder* (its own direct files plus every subfolder's),
    same root, via the indexed relative_path prefix."""
    qs = LibraryFile.objects.filter(root_id=folder.root_id)
    prefix = _subtree_prefix(folder)
    if prefix:
        qs = qs.filter(relative_path__startswith=prefix)
    return qs


def _bulk_apply(through, left_field, left_ids, added_ids, removed_ids):
    """Add/remove a set of tag ids across many left-side rows in bulk.

    The removal is always a single DELETE regardless of size. The addition
    side is a Cartesian product (rows x tags) — built and inserted in
    _BATCH_SIZE-row chunks rather than one unbounded list, so a large subtree
    cascade can't hold the whole result set in memory at once."""
    left_ids = list(left_ids)
    if not left_ids:
        return 0
    if removed_ids:
        through.objects.filter(
            **{f'{left_field}_id__in': left_ids, 'tag_id__in': list(removed_ids)}
        ).delete()
    if added_ids:
        added_ids = list(added_ids)
        chunk = []
        for lid in left_ids:
            for tid in added_ids:
                chunk.append(through(**{f'{left_field}_id': lid, 'tag_id': tid}))
                if len(chunk) >= _BATCH_SIZE:
                    through.objects.bulk_create(chunk, ignore_conflicts=True)
                    chunk = []
        if chunk:
            through.objects.bulk_create(chunk, ignore_conflicts=True)
    return len(left_ids)


def apply_folder_metadata(folder, tag_ids, notes):
    """Save a folder's notes + tags and cascade the tag DELTA down its subtree.

    - The folder's own tag set becomes exactly *tag_ids* (authoritative for
      itself).
    - Only the delta (added / removed vs. the folder's previous tags) is applied
      to descendant folders and to every file in the subtree — so a subfolder's
      own extra tags, and tags a user put on a file by hand, are preserved
      (except the accepted v1 edge case: a removed tag that also happens to be a
      manual tag is stripped, since there is no per-row provenance).

    Returns ``{'affected_folders', 'affected_files'}`` counts.
    """
    new_ids = set(tag_ids)
    old_ids = set(folder.tags.values_list('id', flat=True))
    added = new_ids - old_ids
    removed = old_ids - new_ids

    folder.notes = notes or ''
    folder.save(update_fields=['notes'])
    folder.tags.set(new_ids)

    if not (added or removed):
        return {'affected_folders': 0, 'affected_files': 0}

    sub_folder_ids = list(descendant_folders(folder).values_list('id', flat=True))
    affected_folders = _bulk_apply(_FOLDER_TAGS, 'libraryfolder', sub_folder_ids, added, removed)

    file_ids = list(descendant_files(folder).values_list('id', flat=True))
    affected_files = _bulk_apply(_FILE_TAGS, 'libraryfile', file_ids, added, removed)

    return {'affected_folders': affected_folders, 'affected_files': affected_files}


def resync_folder(folder):
    """Forceful push-down: re-assert this folder's CURRENT tags onto every
    descendant folder and file (add-only — never strips a subfolder's own
    tags). Used by the "Re-apply to all files below" button to recover from
    drift, overriding a deliberate subfolder-only removal."""
    tag_ids = list(folder.tags.values_list('id', flat=True))
    sub_folder_ids = list(descendant_folders(folder).values_list('id', flat=True))
    affected_folders = _bulk_apply(_FOLDER_TAGS, 'libraryfolder', sub_folder_ids, tag_ids, [])
    file_ids = list(descendant_files(folder).values_list('id', flat=True))
    affected_files = _bulk_apply(_FILE_TAGS, 'libraryfile', file_ids, tag_ids, [])
    return {'affected_folders': affected_folders, 'affected_files': affected_files}


def stamp_new_files(new_files_by_folder):
    """Apply each folder's current tags to files freshly created by a scan.

    *new_files_by_folder* maps ``folder_pk -> [file_pk, ...]`` (only brand-new
    file rows — existing/updated files keep whatever tags they already had).
    One query fetches every relevant folder's tags; one bulk_create stamps them.
    Folders with no tags are skipped, so an untagged library costs nothing.
    """
    if not new_files_by_folder:
        return 0

    tag_map = defaultdict(list)
    for folder_id, tag_id in _FOLDER_TAGS.objects.filter(
        libraryfolder_id__in=list(new_files_by_folder)
    ).values_list('libraryfolder_id', 'tag_id'):
        tag_map[folder_id].append(tag_id)

    if not tag_map:
        return 0

    total = 0
    chunk = []
    for folder_id, file_ids in new_files_by_folder.items():
        for tag_id in tag_map.get(folder_id, ()):
            for file_id in file_ids:
                chunk.append(_FILE_TAGS(libraryfile_id=file_id, tag_id=tag_id))
                total += 1
                if len(chunk) >= _BATCH_SIZE:
                    _FILE_TAGS.objects.bulk_create(chunk, ignore_conflicts=True)
                    chunk = []
    if chunk:
        _FILE_TAGS.objects.bulk_create(chunk, ignore_conflicts=True)
    return total
