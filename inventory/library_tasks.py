"""
Django-Q task entry points + Schedule wiring for the STL/3MF Library.

Same convention as inventory/tasks.py: thin wrappers around service functions,
stable importable dotted paths, IDs (never live instances) as arguments.
"""

import logging

from inventory.services.library_scanner import (
    process_file_chunk,
    run_regeneration,
    run_scan,
    start_scan,
)

logger = logging.getLogger(__name__)

SCHEDULE_NAME_PREFIX = 'library-root-rescan-'


def run_library_scan(scan_id):
    """Walk phase of a scan (enqueued by start_scan)."""
    return run_scan(scan_id)


def run_thumbnail_regeneration(scan_id):
    """Queue-up phase of a thumbnail regeneration job (enqueued by
    start_thumbnail_regeneration)."""
    return run_regeneration(scan_id)


def process_library_file_chunk(scan_id, file_ids, force_render=False):
    """Expensive per-file phase (enqueued in chunks by run_scan and
    run_regeneration)."""
    return process_file_chunk(scan_id, file_ids, force_render=force_render)


def scheduled_root_rescan(root_id):
    """Periodic rescan entry point, driven by a django_q Schedule per root."""
    from inventory.models import LibraryRoot

    root = LibraryRoot.objects.filter(pk=root_id).first()
    if root is None:
        logger.info(f"LibraryRoot {root_id} no longer exists; skipping scheduled rescan")
        return None
    if not root.enabled:
        logger.info(f"LibraryRoot {root_id} is disabled; skipping scheduled rescan")
        return None

    scan = start_scan(root)
    if scan is None:
        logger.info(f"LibraryRoot {root_id}: scan already in progress; scheduled rescan skipped")
    return scan.pk if scan else None


def sync_root_schedule(root):
    """
    Keep the root's periodic-rescan Schedule row in step with its settings:
    one Schedule per root, updated in place when the interval changes,
    removed when rescans are disabled (interval NULL) or the root is disabled.
    """
    from django_q.models import Schedule

    name = f"{SCHEDULE_NAME_PREFIX}{root.pk}"
    if root.enabled and root.rescan_interval_hours:
        Schedule.objects.update_or_create(
            name=name,
            defaults={
                'func': 'inventory.library_tasks.scheduled_root_rescan',
                'args': str(root.pk),
                'schedule_type': Schedule.MINUTES,
                'minutes': root.rescan_interval_hours * 60,
                'repeats': -1,
            },
        )
    else:
        Schedule.objects.filter(name=name).delete()


def delete_root_schedule(root_pk):
    """Remove the Schedule row for a deleted root."""
    from django_q.models import Schedule

    Schedule.objects.filter(name=f"{SCHEDULE_NAME_PREFIX}{root_pk}").delete()
