import logging

from django.apps import AppConfig
from django.db.models.signals import post_migrate

logger = logging.getLogger(__name__)


def _register_library_schedules(sender, **kwargs):
    """Ensure the global Library django-Q schedules (the stalled-scan reaper)
    exist. Runs on post_migrate so a fresh deploy registers them without any
    per-root save. Guarded: a failure here (e.g. django_q tables not yet
    migrated) must never break `migrate`."""
    try:
        from inventory.library_tasks import ensure_global_library_schedules
        ensure_global_library_schedules()
    except Exception:
        logger.exception("Could not register global library schedules")


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'

    def ready(self):
        post_migrate.connect(_register_library_schedules, sender=self)
