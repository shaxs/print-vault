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
    from inventory.models import Tracker

    try:
        tracker = Tracker.objects.get(pk=tracker_id)
    except Tracker.DoesNotExist:
        logger.info(
            f"Tracker {tracker_id} no longer exists; skipping thumbnail regeneration"
        )
        return None

    return regenerate_tracker_thumbnails(tracker, include_linked=include_linked)
