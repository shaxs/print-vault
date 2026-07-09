"""
Django-Q job orchestration for tracker thumbnail (re)generation.

Mirrors services/library_scanner's scan-job pattern: a TrackerThumbnailJob row
tracks progress for the tracker page's "N of M rendered" banner, and the heavy
rendering is split into time-budgeted chunks so no single Django-Q worker task
can exceed the cluster timeout, however many files the tracker has. (Rendering
the whole tracker in one task was the original bug — a large tracker blew the
300s worker timeout, got reincarnated, and never finished.)

Thin service functions here; importable dotted task wrappers live in
inventory/tasks.py (same convention as the library).
"""

import logging
import time

from django.db.models import F
from django.utils import timezone
from django_q.tasks import async_task

logger = logging.getLogger(__name__)

# Files per enqueued chunk. Small because each file is a full mesh load + render
# (heavier than the library's hash). The time budget below is the real safety
# net; this just bounds how many tasks are enqueued up front.
CHUNK_SIZE = 10

# Wall-clock budget per chunk task. Comfortably under Q_CLUSTER['timeout'] (300s)
# with headroom for one more (load + render, or a link download) file after the
# check trips, so a task returns and re-enqueues the rest instead of timing out.
CHUNK_TIME_BUDGET_SECONDS = 150

# A job stuck in pending/running past this is treated as dead (worker killed
# mid-run) and displaced by a new request — mirrors the library's scan guard.
STALE_JOB_AGE_HOURS = 12


def _job_slot_available(tracker):
    """Per-tracker concurrency guard with stale-job displacement."""
    from inventory.models import TrackerThumbnailJob

    existing = TrackerThumbnailJob.objects.filter(
        tracker=tracker, status__in=['pending', 'running']
    ).first()
    if existing is None:
        return True
    age = timezone.now() - existing.created_at
    if age.total_seconds() < STALE_JOB_AGE_HOURS * 3600:
        return False
    _fail_job(existing, f"Displaced as stale after {STALE_JOB_AGE_HOURS}h by a new request")
    return True


def start_tracker_thumbnail_regeneration(tracker, include_linked=False):
    """Create a TrackerThumbnailJob and enqueue its orchestrator task.
    Returns None if a job for this tracker is already pending/running."""
    from inventory.models import TrackerThumbnailJob

    if not _job_slot_available(tracker):
        return None
    job = TrackerThumbnailJob.objects.create(tracker=tracker, include_linked=include_linked)
    async_task('inventory.tasks.run_tracker_thumbnail_regeneration_task', job.pk)
    return job


def _eligible_file_ids(tracker, include_linked):
    """STL/3MF files in the tracker that should get an auto-thumbnail, skipping
    any file with a manually-uploaded image (never overwrite a manual upload)."""
    from inventory.services.stl_thumbnail_service import SUPPORTED_EXTENSIONS

    storage_types = ['local', 'link'] if include_linked else ['local']
    ids = []
    for tf in tracker.files.filter(storage_type__in=storage_types):
        if not tf.filename.lower().endswith(SUPPORTED_EXTENSIONS):
            continue
        if tf.images.filter(is_auto_generated=False).exists():
            continue
        ids.append(tf.pk)
    return ids


def run_regeneration(job_id):
    """Queue-up phase (counterpart of the library's run_regeneration): mark the
    job running, drop stale auto-images, then enqueue render chunks. Never
    raises; failures land on the job row."""
    from inventory.models import TrackerFileImage, TrackerThumbnailJob

    job = TrackerThumbnailJob.objects.select_related('tracker').filter(pk=job_id).first()
    if job is None:
        logger.info(f"TrackerThumbnailJob {job_id} no longer exists; skipping")
        return None
    if job.status != 'pending':
        logger.info(f"TrackerThumbnailJob {job_id} is {job.status}, not pending; skipping")
        return None

    job.status = 'running'
    job.started_at = timezone.now()
    job.save(update_fields=['status', 'started_at'])

    try:
        file_ids = _eligible_file_ids(job.tracker, job.include_linked)
        # Drop stale auto-generated images up front so generate_auto_thumbnail's
        # "already has an image" guard doesn't just no-op each file.
        TrackerFileImage.objects.filter(
            tracker_file_id__in=file_ids, is_auto_generated=True
        ).delete()

        job.files_queued = len(file_ids)
        job.save(update_fields=['files_queued'])

        if not file_ids:
            _finalize_job(job, success=True)
            return None

        for start in range(0, len(file_ids), CHUNK_SIZE):
            chunk = file_ids[start:start + CHUNK_SIZE]
            async_task('inventory.tasks.process_tracker_thumbnail_chunk_task', job.pk, chunk)
        return None
    except Exception as e:
        logger.exception(f"Tracker thumbnail job {job_id} failed during queue-up")
        _fail_job(job, str(e))
        return None


def process_chunk(job_id, file_ids):
    """Render a chunk of files. Time-budgeted: if the budget is exhausted with
    files left, re-enqueue the remainder as a fresh chunk task so no single
    worker task can exceed the cluster timeout. Per-file failures are logged and
    still counted as processed — one bad file must never wedge a job."""
    from inventory.models import TrackerFile, TrackerThumbnailJob
    from inventory.services.stl_thumbnail_service import generate_auto_thumbnail

    job = TrackerThumbnailJob.objects.filter(pk=job_id).first()
    if job is None or job.status != 'running':
        return None

    started = time.monotonic()
    processed = 0
    generated = 0
    for index, file_id in enumerate(file_ids):
        tracker_file = TrackerFile.objects.select_related('tracker').filter(pk=file_id).first()
        if tracker_file is not None:
            try:
                if generate_auto_thumbnail(tracker_file, allow_linked_download=job.include_linked):
                    generated += 1
            except Exception:
                logger.exception(f"Tracker thumbnail job {job_id}: file {file_id} failed")
        processed += 1

        remaining = file_ids[index + 1:]
        if remaining and time.monotonic() - started >= CHUNK_TIME_BUDGET_SECONDS:
            _bump_progress(job_id, processed, generated)
            async_task('inventory.tasks.process_tracker_thumbnail_chunk_task', job_id, remaining)
            return None

    _bump_progress(job_id, processed, generated)
    _maybe_finalize(job_id)
    return None


def _bump_progress(job_id, processed, generated):
    from inventory.models import TrackerThumbnailJob

    TrackerThumbnailJob.objects.filter(pk=job_id).update(
        files_processed=F('files_processed') + processed,
        files_generated=F('files_generated') + generated,
    )


def _maybe_finalize(job_id):
    from inventory.models import TrackerThumbnailJob

    job = TrackerThumbnailJob.objects.filter(pk=job_id).first()
    if job and job.status == 'running' and job.files_processed >= job.files_queued:
        _finalize_job(job, success=True)


def _finalize_job(job, success, error=''):
    job.status = 'success' if success else 'error'
    job.error = error
    job.finished_at = timezone.now()
    job.save(update_fields=['status', 'error', 'finished_at'])


def _fail_job(job, message):
    logger.error(f"Tracker thumbnail job {job.pk} failed: {message}")
    _finalize_job(job, success=False, error=message)
