"""
Django-Q task entry points for inventory.

Thin wrappers around service functions: async_task() needs stable,
importable, serializable dotted paths — pass IDs, not live model instances.
"""

import logging

from inventory.services.stl_thumbnail_service import (
    generate_auto_thumbnail,
    regenerate_tracker_thumbnails,
)

logger = logging.getLogger(__name__)


def generate_auto_thumbnail_task(tracker_file_id):
    from inventory.models import TrackerFile

    try:
        tracker_file = TrackerFile.objects.select_related('tracker').get(pk=tracker_file_id)
    except TrackerFile.DoesNotExist:
        logger.info(
            f"TrackerFile {tracker_file_id} no longer exists; skipping thumbnail generation"
        )
        return None

    return generate_auto_thumbnail(tracker_file)


def regenerate_tracker_thumbnails_task(tracker_id, include_linked=False):
    """Legacy synchronous whole-tracker regeneration (one task renders every
    file). Superseded for the API by the chunked TrackerThumbnailJob queue
    below, which can't blow the worker timeout on large trackers; retained as a
    stable entry point for ad-hoc/backward-compatible use."""
    from inventory.models import Tracker

    try:
        tracker = Tracker.objects.get(pk=tracker_id)
    except Tracker.DoesNotExist:
        logger.info(
            f"Tracker {tracker_id} no longer exists; skipping thumbnail regeneration"
        )
        return None

    return regenerate_tracker_thumbnails(tracker, include_linked=include_linked)


def run_tracker_thumbnail_regeneration_task(job_id):
    """Queue-up phase of a TrackerThumbnailJob (enqueued by
    start_tracker_thumbnail_regeneration)."""
    from inventory.services.tracker_thumbnail_jobs import run_regeneration

    return run_regeneration(job_id)


def process_tracker_thumbnail_chunk_task(job_id, file_ids):
    """Time-budgeted per-file render phase, enqueued in chunks by
    run_tracker_thumbnail_regeneration_task."""
    from inventory.services.tracker_thumbnail_jobs import process_chunk

    return process_chunk(job_id, file_ids)
