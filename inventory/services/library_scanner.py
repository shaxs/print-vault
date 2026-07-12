"""
STL/3MF Library scanner — the walk/diff engine.

Two entry points, both invoked from Django-Q tasks (inventory/library_tasks.py):

    run_scan(scan_id)
        Walks the scan's scope (full root, or a folder subtree for scoped
        rescans), mirrors directories as LibraryFolder rows, stat-compares
        files, bumps last_seen_at on everything encountered, soft-deletes
        whatever the walk didn't see, and enqueues chunked processing tasks
        for new/changed files. Deliberately does NO hashing or rendering —
        Django-Q kills tasks at Q_CLUSTER['timeout'] (300s), so the walk must
        stay cheap (stat + DB writes only) no matter how big the share is.

    process_file_chunk(scan_id, file_ids)
        The expensive per-file work (SHA-256 hash, thumbnail render, bounding
        box, 3MF metadata), CHUNK_SIZE files per task so each task stays well
        inside the timeout. Move detection lives here, not in the walk,
        because it needs the hash: a new path whose hash matches a
        soft-deleted row is the same file moved, so the old row keeps its
        identity (and its already-rendered thumbnail) instead of being
        replaced by the walk-created placeholder row.

Scan lifecycle: the walk finishes before processing does, so the LibraryScan
row stays 'running' until the last chunk task notices files_processed has
caught up with files_queued and finalizes it.
"""

import hashlib
import logging
import os
import time
from datetime import datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from django_q.tasks import async_task

from inventory.services.library_thumbnail_service import generate_library_file_assets
from inventory.services.stl_thumbnail_service import MAX_RENDER_FILE_SIZE_BYTES
from inventory.services.threemf_metadata_parser import parse_threemf_metadata

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {'stl', '3mf'}

# Files per processing task. Each file costs a full read (hash) plus a render.
# CHUNK_SIZE bounds two things: how many tasks are enqueued up front, and — the
# reason it's small — the PEAK memory a worker reaches inside a single task.
# Rendering loads whole meshes into numpy arrays (up to MAX_RENDER_FILE_SIZE_BYTES
# = 100 MB of geometry), and Q_CLUSTER's max_rss guard only recycles a bloated
# worker BETWEEN tasks — it can't reclaim mid-chunk. So a fat chunk can peak far
# past max_rss before the check ever fires: 20 renders/task thrash-locked a
# 6 GB LXC on the first index of a ~7k-file share (July 2026). 5 keeps the
# in-task peak ~4x lower so max_rss can actually do its job. CHUNK_TIME_BUDGET
# below is the separate timeout guard (re-enqueues unfinished work).
CHUNK_SIZE = 5

# Wall-clock budget per chunk task, with headroom under the 300s worker timeout
# for one more (network read + render) file after the check trips.
CHUNK_TIME_BUDGET_SECONDS = 150

# Live-RSS ceiling for the per-file memory bail in process_file_chunk. Mirrors
# Q_CLUSTER['max_rss'] (KB -> bytes) so the bail and Django-Q's own recycle use
# the same number: when a worker crosses it mid-chunk we stop taking on new
# renders, hand the remainder to a fresh task, and return so max_rss recycles
# the bloated process (the only way to give memory back to the OS — CPython
# won't). This bounds live peak independent of CHUNK_SIZE and mesh size, which
# is what keeps a small box (Pi/LXC) from OOMing on a first index. Whichever
# limit fires first — this one or the time budget — hands off the same way.
WORKER_RSS_LIMIT_BYTES = settings.Q_CLUSTER.get('max_rss', 600 * 1024) * 1024

try:
    _PAGE_SIZE_BYTES = os.sysconf('SC_PAGE_SIZE')
except (AttributeError, ValueError, OSError):
    _PAGE_SIZE_BYTES = 4096  # non-Linux dev; the RSS bail no-ops there anyway


def _worker_rss_bytes():
    """Resident set size of this worker process, in bytes. Linux-only (reads
    /proc/self/statm); returns 0 anywhere that's unavailable (dev on
    Windows/macOS, or a read error) so the RSS bail simply no-ops."""
    try:
        with open('/proc/self/statm') as fh:
            resident_pages = int(fh.read().split()[1])
    except (OSError, ValueError, IndexError):
        return 0
    return resident_pages * _PAGE_SIZE_BYTES


# Batch size for bulk last_seen_at bumps during the walk.
BULK_BATCH_SIZE = 500

# Directory names never worth indexing (NAS housekeeping, trash, VCS).
SKIPPED_DIR_NAMES = {'@eaDir', '#recycle', '$RECYCLE.BIN', 'System Volume Information'}


# A scan stuck in pending/running longer than this is considered dead (worker
# killed mid-scan without a chance to record an error) and can be displaced by
# a new scan request.
STALE_SCAN_AGE_HOURS = 12

# How long a scan in its PROCESSING phase may sit with an empty task queue before
# reap_stalled_scans finalizes it. Guards against a chunk worker dying (OOM /
# container restart) mid-scan, which leaves files_processed short of
# files_queued forever — the "stuck at 99%" the UI would otherwise show.
SCAN_STALL_SECONDS = 600

# Task funcs that can still advance a library scan. Only these postpone
# reaping: the reaper itself is ALSO a queued task while it executes (django-q's
# ORM broker keeps the row until the monitor acks it after completion), so a
# naive "whole queue empty" gate can never pass from inside the reaper — it
# blocked on its own queue row and never reaped anything (July 2026). Unrelated
# tasks (tracker thumbnails, etc.) don't advance scans, so they don't postpone
# reaping either.
_SCAN_ADVANCING_TASK_FUNCS = frozenset({
    'inventory.library_tasks.run_library_scan',
    'inventory.library_tasks.run_thumbnail_regeneration',
    'inventory.library_tasks.process_library_file_chunk',
    'inventory.library_tasks.scheduled_root_rescan',
})


def _scan_work_is_queued():
    """True if any queued/running Django-Q task could still advance a library
    scan. Decodes each queued payload; undecodable rows are treated as
    non-library (a permanently corrupt row must not disable the reaper)."""
    from django_q.models import OrmQ

    for queued in OrmQ.objects.all():
        try:
            if queued.func() in _SCAN_ADVANCING_TASK_FUNCS:
                return True
        except Exception:  # pragma: no cover - defensive
            continue
    return False


def reap_stalled_scans():
    """Finalize library scans that can no longer make progress.

    When a chunk task's worker dies (OOM-killed, container restart) its files
    never increment files_processed, so a scan sits at status='running' forever
    just short of files_queued. This periodic sweep finalizes such scans so the
    UI stops showing "Scanning… 99%" and a fresh scan can start.

    Only PROCESSING-phase scans (files_queued > 0) are reaped, and only when no
    scan-advancing task remains queued (see _SCAN_ADVANCING_TASK_FUNCS — the
    reaper's own queue row and unrelated tasks don't count) and they've been
    running past SCAN_STALL_SECONDS. Walk-phase scans (files_queued == 0, walk
    task still in flight) are deliberately left to the 12 h stale displacement,
    so a slow first walk is never cut short. Returns the count reaped.
    """
    from inventory.models import LibraryScan

    if _scan_work_is_queued():
        return 0

    cutoff = timezone.now() - timedelta(seconds=SCAN_STALL_SECONDS)
    stalled = LibraryScan.objects.filter(
        status='running', files_queued__gt=0, started_at__lt=cutoff,
    )
    reaped = 0
    for scan in stalled:
        gap = max(scan.files_queued - scan.files_processed, 0)
        note = (
            f"Finalized with {gap} file(s) unprocessed after a worker "
            f"interruption; the next scan will pick them up" if gap else ''
        )
        if gap:
            logger.warning(f"Reaping stalled library scan {scan.pk}: {note}")
        _finalize_scan(scan, success=True, error=note)
        reaped += 1
    return reaped


def _scan_slot_available(root):
    """Per-root concurrency guard shared by scans and thumbnail regeneration:
    one job at a time, with stale-job displacement (dead-worker recovery)."""
    from inventory.models import LibraryScan

    existing = LibraryScan.objects.filter(
        root=root, status__in=['pending', 'running']
    ).first()
    if existing is None:
        return True
    age = timezone.now() - existing.created_at
    if age.total_seconds() < STALE_SCAN_AGE_HOURS * 3600:
        return False
    _fail_scan(existing, f"Displaced as stale after {STALE_SCAN_AGE_HOURS}h by a new scan request")
    return True


def start_scan(root, folder=None):
    """
    Create a LibraryScan and enqueue its walk task.

    Returns None (nothing enqueued) if a job for this root is already
    pending/running and not stale.
    """
    from inventory.models import LibraryScan

    if not _scan_slot_available(root):
        return None
    scan = LibraryScan.objects.create(root=root, folder=folder, kind='scan')
    async_task('inventory.library_tasks.run_library_scan', scan.pk)
    return scan


def start_thumbnail_regeneration(root):
    """
    Create a job that re-renders every active file's thumbnail in the root's
    current thumbnail_color. No walk, no sweep — just forced per-file
    processing, reusing the LibraryScan row for progress/finalization so the
    existing polling endpoint works unchanged.
    """
    from inventory.models import LibraryScan

    if not _scan_slot_available(root):
        return None
    scan = LibraryScan.objects.create(root=root, kind='thumbnails')
    async_task('inventory.library_tasks.run_thumbnail_regeneration', scan.pk)
    return scan


def run_regeneration(scan_id):
    """Queue-up phase of a thumbnail regeneration job (the counterpart of
    run_scan's walk). Never raises; failures land on the scan row."""
    from inventory.models import LibraryFile, LibraryScan

    scan = LibraryScan.objects.select_related('root').filter(pk=scan_id).first()
    if scan is None:
        logger.info(f"LibraryScan {scan_id} no longer exists; skipping regeneration")
        return None
    if scan.status != 'pending':
        logger.info(f"LibraryScan {scan_id} is {scan.status}, not pending; skipping")
        return None

    root = scan.root
    scan.status = 'running'
    scan.started_at = timezone.now()
    scan.save(update_fields=['status', 'started_at'])
    root.last_scan_status = 'running'
    root.save(update_fields=['last_scan_status'])

    try:
        file_ids = list(
            LibraryFile.objects.filter(root=root, status='active').values_list('pk', flat=True)
        )
        scan.files_seen = len(file_ids)
        scan.files_queued = len(file_ids)
        scan.save(update_fields=['files_seen', 'files_queued'])

        if not file_ids:
            _finalize_scan(scan, success=True)
            return None

        for start in range(0, len(file_ids), CHUNK_SIZE):
            chunk = file_ids[start:start + CHUNK_SIZE]
            async_task(
                'inventory.library_tasks.process_library_file_chunk', scan.pk, chunk, True
            )
        return None
    except Exception as e:
        logger.exception(f"Thumbnail regeneration {scan_id} failed during queue-up")
        _fail_scan(scan, str(e))
        return None


def run_scan(scan_id):
    """Execute the walk phase of a LibraryScan. Never raises: all failures
    are recorded on the scan row (status='error') instead."""
    from inventory.models import LibraryScan

    scan = LibraryScan.objects.select_related('root', 'folder').filter(pk=scan_id).first()
    if scan is None:
        logger.info(f"LibraryScan {scan_id} no longer exists; skipping")
        return None
    if scan.status != 'pending':
        # Re-delivered task (e.g. Django-Q retry after a worker recycle) — the
        # scan already ran or is running; don't walk twice.
        logger.info(f"LibraryScan {scan_id} is {scan.status}, not pending; skipping")
        return None

    root = scan.root
    scan_time = timezone.now()
    scan.status = 'running'
    scan.started_at = scan_time
    scan.save(update_fields=['status', 'started_at'])
    root.last_scan_status = 'running'
    root.save(update_fields=['last_scan_status'])

    try:
        root_path = os.path.realpath(root.path)
        scope_rel = scan.folder.relative_path if scan.folder_id else ''
        start_path = os.path.join(root_path, *scope_rel.split('/')) if scope_rel else root_path
        if not os.path.isdir(start_path):
            _fail_scan(scan, f"Scan path does not exist or is not a directory: {start_path}")
            return None

        to_process = _walk(scan, root, root_path, start_path, scope_rel, scan_time)
        scan.files_deleted = _sweep_deletions(root, scope_rel, scan_time)

        scan.files_queued = len(to_process)
        scan.save(update_fields=[
            'files_seen', 'files_queued', 'files_new', 'files_updated', 'files_deleted',
        ])

        if not to_process:
            _finalize_scan(scan, success=True)
            return None

        for start in range(0, len(to_process), CHUNK_SIZE):
            chunk = to_process[start:start + CHUNK_SIZE]
            async_task('inventory.library_tasks.process_library_file_chunk', scan.pk, chunk)
        return None
    except Exception as e:
        logger.exception(f"Library scan {scan_id} failed during walk")
        _fail_scan(scan, str(e))
        return None


def _walk(scan, root, root_path, start_path, scope_rel, scan_time):
    """Mirror directories/files under start_path into DB rows.

    Returns the list of LibraryFile ids needing expensive processing
    (new files, stat-changed files, and never-hashed files).
    """
    from inventory.models import LibraryFile, LibraryFolder

    folder_cache = {}   # relative_path -> LibraryFolder (this walk's scope)
    seen_folder_ids = []
    seen_file_ids = []  # unchanged files: last_seen bump only
    to_process = []
    files_seen = 0
    new_count = 0       # walk-created rows (paths not previously indexed)
    updated_count = 0   # stat-changed rows reprocessed

    if scope_rel:
        # Scoped rescan: the scope folder row already exists (the UI navigated
        # to it); anchor the cache on it so children link to the right parent.
        folder_cache[scope_rel] = scan.folder

    def on_walk_error(error):
        logger.warning(f"Library scan {scan.pk}: unreadable directory skipped: {error}")

    for dirpath, dirnames, filenames in os.walk(start_path, onerror=on_walk_error):
        dirnames[:] = sorted(
            d for d in dirnames
            if not d.startswith('.') and d not in SKIPPED_DIR_NAMES
        )
        rel_dir = _normalize_relpath(os.path.relpath(dirpath, root_path))

        folder = folder_cache.get(rel_dir)
        if folder is None:
            parent = None
            if rel_dir:
                parent_rel = rel_dir.rsplit('/', 1)[0] if '/' in rel_dir else ''
                parent = folder_cache.get(parent_rel)
                if parent is None and parent_rel != rel_dir:
                    # Only reachable for the walk's top directory (os.walk is
                    # top-down, so descendants always find a cached parent).
                    parent = _get_or_create_ancestry(root, parent_rel, folder_cache)
            folder, _ = LibraryFolder.objects.update_or_create(
                root=root,
                relative_path=rel_dir,
                defaults={
                    'name': os.path.basename(dirpath) if rel_dir else root.name,
                    'parent': parent,
                    'status': 'active',
                },
            )
            folder_cache[rel_dir] = folder
        seen_folder_ids.append(folder.pk)

        for filename in filenames:
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            file_path = os.path.join(dirpath, filename)
            try:
                st = os.stat(file_path)
            except OSError as e:
                logger.warning(f"Library scan {scan.pk}: could not stat {file_path}: {e}")
                continue

            files_seen += 1
            rel_file = f"{rel_dir}/{filename}" if rel_dir else filename
            mtime = _stat_datetime(st)

            existing = LibraryFile.objects.filter(root=root, relative_path=rel_file).first()
            if existing is None:
                created = LibraryFile.objects.create(
                    root=root,
                    folder=folder,
                    filename=filename,
                    relative_path=rel_file,
                    extension=ext,
                    size_bytes=st.st_size,
                    modified_time=mtime,
                    last_seen_at=scan_time,
                )
                to_process.append(created.pk)
                new_count += 1
                continue

            unchanged = (
                existing.size_bytes == st.st_size
                and existing.modified_time == mtime
                and existing.sha256_hash
            )
            if unchanged:
                # Covers plain unchanged files and soft-deleted rows whose file
                # reappeared identically — both just need active + last_seen.
                seen_file_ids.append(existing.pk)
            else:
                existing.folder = folder
                existing.size_bytes = st.st_size
                existing.modified_time = mtime
                existing.status = 'active'
                existing.last_seen_at = scan_time
                existing.save(update_fields=[
                    'folder', 'size_bytes', 'modified_time', 'status', 'last_seen_at',
                ])
                to_process.append(existing.pk)
                updated_count += 1

            if len(seen_file_ids) >= BULK_BATCH_SIZE:
                _bump_seen(LibraryFile, seen_file_ids, scan_time)
                seen_file_ids = []

        if len(seen_folder_ids) >= BULK_BATCH_SIZE:
            _bump_seen(LibraryFolder, seen_folder_ids, scan_time)
            seen_folder_ids = []

    _bump_seen(LibraryFile, seen_file_ids, scan_time)
    _bump_seen(LibraryFolder, seen_folder_ids, scan_time)
    scan.files_seen = files_seen
    scan.files_new = new_count
    scan.files_updated = updated_count
    return to_process


def _get_or_create_ancestry(root, rel_path, folder_cache):
    """Ensure every folder row from the root down to rel_path exists,
    returning the rel_path folder. Used only to anchor a walk's top folder."""
    from inventory.models import LibraryFolder

    if rel_path in folder_cache:
        return folder_cache[rel_path]

    parent = None
    built = ''
    for segment in ([''] + (rel_path.split('/') if rel_path else [])):
        built = f"{built}/{segment}".strip('/') if segment else ''
        folder = folder_cache.get(built)
        if folder is None:
            folder, _ = LibraryFolder.objects.update_or_create(
                root=root,
                relative_path=built,
                defaults={
                    'name': segment if built else root.name,
                    'parent': parent,
                    'status': 'active',
                },
            )
            folder_cache[built] = folder
        parent = folder
    return parent


def _bump_seen(model, ids, scan_time):
    if ids:
        model.objects.filter(pk__in=ids).update(last_seen_at=scan_time, status='active')


def _sweep_deletions(root, scope_rel, scan_time):
    """Soft-delete every active row in scope the walk didn't touch.
    One bulk UPDATE per table — no per-row loop, no in-memory id sets.

    Returns the number of files soft-deleted (for the scan's result summary);
    folder sweeps aren't counted since the UI reports the file-level diff."""
    from inventory.models import LibraryFile, LibraryFolder

    stale = Q(last_seen_at__lt=scan_time) | Q(last_seen_at__isnull=True)
    folders = LibraryFolder.objects.filter(root=root, status='active')
    files = LibraryFile.objects.filter(root=root, status='active')
    if scope_rel:
        # Only the subtree below the scope folder — never sibling folders.
        prefix = f"{scope_rel}/"
        folders = folders.filter(relative_path__startswith=prefix)
        files = files.filter(relative_path__startswith=prefix)
    folders.filter(stale).update(status='deleted')
    return files.filter(stale).update(status='deleted')


def process_file_chunk(scan_id, file_ids, force_render=False):
    """Hash + move-detect + render + parse a chunk of files, then finalize
    the scan if this chunk was the last one. Per-file failures are logged and
    counted as processed — one corrupt file must never wedge a scan.

    force_render=True (thumbnail regeneration) skips the same-content
    shortcuts and always re-renders in the root's current thumbnail_color."""
    from inventory.models import LibraryScan

    scan = LibraryScan.objects.select_related('root').filter(pk=scan_id).first()
    if scan is None:
        return None

    started = time.monotonic()
    processed = 0
    for index, file_id in enumerate(file_ids):
        try:
            _process_one_file(scan.root, file_id, force_render=force_render)
        except Exception:
            logger.exception(f"Library scan {scan_id}: processing file {file_id} failed")
        processed += 1

        # Hand the rest of the chunk to a fresh task when either guard trips:
        #   - time budget: don't risk exceeding the worker timeout;
        #   - memory: a worker over the RSS ceiling must stop rendering NOW so
        #     Django-Q's max_rss recycles it and returns memory to the OS,
        #     rather than keep growing across the rest of the chunk. This is the
        #     mid-chunk companion to max_rss (which only fires between tasks) and
        #     is what keeps a single fat task from OOMing a small box.
        remaining = file_ids[index + 1:]
        if remaining:
            over_time = time.monotonic() - started >= CHUNK_TIME_BUDGET_SECONDS
            over_memory = _worker_rss_bytes() >= WORKER_RSS_LIMIT_BYTES
            if over_time or over_memory:
                if over_memory:
                    logger.info(
                        f"Library scan {scan_id}: worker RSS over "
                        f"{WORKER_RSS_LIMIT_BYTES // (1024 * 1024)} MB after "
                        f"{processed} file(s); handing {len(remaining)} to a "
                        f"fresh task so the worker can recycle"
                    )
                LibraryScan.objects.filter(pk=scan_id).update(
                    files_processed=F('files_processed') + processed
                )
                async_task(
                    'inventory.library_tasks.process_library_file_chunk',
                    scan_id, remaining, force_render,
                )
                return None

    LibraryScan.objects.filter(pk=scan_id).update(files_processed=F('files_processed') + processed)
    scan.refresh_from_db()
    if scan.status == 'running' and scan.files_processed >= scan.files_queued:
        _finalize_scan(scan, success=True)
    return None


def _process_one_file(root, file_id, force_render=False):
    from inventory.models import LibraryFile

    lib_file = LibraryFile.objects.filter(pk=file_id).first()
    if lib_file is None or lib_file.status != 'active':
        return

    file_path = resolve_within_root(root, lib_file.relative_path)
    if file_path is None or not os.path.isfile(file_path):
        # Vanished (or escaped the root via symlink trickery) between walk and
        # processing — treat as deleted; the next scan settles the truth.
        lib_file.status = 'deleted'
        lib_file.save(update_fields=['status'])
        return

    file_hash = _hash_file(file_path)

    if force_render:
        # Thumbnail regeneration: same bytes, new color. The move/duplicate
        # shortcuts below would copy a twin's OLD-color thumbnail, so skip
        # straight to a fresh render.
        _render_and_save(root, lib_file, file_path, file_hash)
        return

    if file_hash == lib_file.sha256_hash and lib_file.thumbnail:
        return  # touched mtime, same content — stat fields already updated by the walk

    twins = LibraryFile.objects.filter(root=root, sha256_hash=file_hash).exclude(pk=lib_file.pk)

    move_source = twins.filter(status='deleted').first()
    if move_source is not None:
        # Same content, old row soft-deleted: this is a move/rename. Keep the
        # old row's identity (v2 tags/notes will hang off it) and its rendered
        # assets; drop the placeholder row the walk created for the new path.
        with transaction.atomic():
            new_location = {
                'folder': lib_file.folder,
                'filename': lib_file.filename,
                'relative_path': lib_file.relative_path,
                'extension': lib_file.extension,
                'size_bytes': lib_file.size_bytes,
                'modified_time': lib_file.modified_time,
                'last_seen_at': lib_file.last_seen_at,
                'status': 'active',
            }
            # The placeholder has no thumbnail yet, so its post_delete cleanup
            # is a no-op; delete first to free the unique (root, relative_path).
            lib_file.delete()
            for field, value in new_location.items():
                setattr(move_source, field, value)
            move_source.save()
        return

    duplicate = twins.filter(status='active').exclude(thumbnail='').exclude(thumbnail__isnull=True).first()
    if duplicate is not None and duplicate.thumbnail:
        # Same bytes already rendered elsewhere — copy assets, skip the render.
        _replace_thumbnail(lib_file, duplicate.thumbnail.read())
        lib_file.sha256_hash = file_hash
        lib_file.bounding_box_x = duplicate.bounding_box_x
        lib_file.bounding_box_y = duplicate.bounding_box_y
        lib_file.bounding_box_z = duplicate.bounding_box_z
        lib_file.embedded_metadata = duplicate.embedded_metadata
        lib_file.thumbnail_status = 'rendered'
        lib_file.save()
        return

    _render_and_save(root, lib_file, file_path, file_hash)


def _render_and_save(root, lib_file, file_path, file_hash):
    """Fresh render + metadata parse for one file, in the root's configured
    thumbnail color."""
    assets = generate_library_file_assets(file_path, color_hex=root.thumbnail_color)
    metadata = parse_threemf_metadata(file_path) if lib_file.extension == '3mf' else {}

    lib_file.sha256_hash = file_hash
    lib_file.embedded_metadata = metadata
    if assets is not None:
        _replace_thumbnail(lib_file, assets['png_bytes'])
        lib_file.bounding_box_x, lib_file.bounding_box_y, lib_file.bounding_box_z = assets['bounding_box']
        lib_file.thumbnail_status = 'rendered'
    else:
        # No preview — clear stale assets from any previous version of the
        # file's content, and record WHY so the UI can explain the blank:
        # over the render size cap (by design) vs an unreadable/empty mesh.
        if lib_file.thumbnail:
            lib_file.thumbnail.delete(False)
            lib_file.thumbnail = None
        lib_file.bounding_box_x = lib_file.bounding_box_y = lib_file.bounding_box_z = None
        lib_file.thumbnail_status = (
            'too_large' if lib_file.size_bytes > MAX_RENDER_FILE_SIZE_BYTES else 'unrenderable'
        )
    lib_file.save()


def _replace_thumbnail(lib_file, png_bytes):
    """Swap in a new thumbnail, deleting the old image file from disk first
    (Django never removes replaced FieldFile content on its own).

    The stored file is named from the LibraryFile pk, NOT the source STL name.
    Share filenames are long and non-unique across folders, so deriving the
    thumbnail name from them overflowed the ImageField's max_length and forced
    Django to append collision-avoidance suffixes in the flat thumbnail dir —
    which grew until save() blew up with SuspiciousFileOperation and wedged
    those files (their hash never persisted, so every rescan re-queued them).
    A pk-based name is short and unique per row, sidestepping both problems.
    """
    if lib_file.thumbnail:
        lib_file.thumbnail.delete(False)
    lib_file.thumbnail = ContentFile(png_bytes, name=f"{lib_file.pk}_thumb.png")


def resolve_within_root(root, relative_path):
    """Join relative_path onto the root and refuse anything that escapes it.
    Defense-in-depth: walk-derived paths can't escape, but rows are also
    reachable through the API/DB, so re-validate before touching the disk."""
    root_path = os.path.realpath(root.path)
    candidate = os.path.realpath(os.path.join(root_path, *relative_path.split('/')))
    if candidate != root_path and not candidate.startswith(root_path + os.sep):
        logger.warning(
            f"Library path escape rejected for root {root.pk}: {relative_path!r}"
        )
        return None
    return candidate


def _hash_file(file_path):
    digest = hashlib.sha256()
    with open(file_path, 'rb') as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _stat_datetime(st):
    """File mtime as an aware UTC datetime (deterministic across scans, so
    stored-vs-fresh equality is a valid unchanged check)."""
    return datetime.fromtimestamp(st.st_mtime, tz=dt_timezone.utc)


def _normalize_relpath(rel):
    """os.path.relpath output -> stored form: forward slashes, '' for the root."""
    rel = rel.replace('\\', '/')
    return '' if rel == '.' else rel


def _finalize_scan(scan, success, error=''):
    from inventory.models import LibraryScan

    now = timezone.now()
    scan.status = 'success' if success else 'error'
    scan.error = error
    scan.finished_at = now
    scan.save(update_fields=['status', 'error', 'finished_at'])

    root = scan.root
    root.last_scanned_at = scan.started_at or now
    root.last_scan_status = scan.status
    root.last_scan_error = error
    root.save(update_fields=['last_scanned_at', 'last_scan_status', 'last_scan_error'])


def _fail_scan(scan, message):
    logger.error(f"Library scan {scan.pk} failed: {message}")
    _finalize_scan(scan, success=False, error=message)
