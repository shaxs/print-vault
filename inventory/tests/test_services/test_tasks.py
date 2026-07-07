"""
Tests for inventory/tasks.py — the Django-Q entry points.

These call the task functions directly (as Django-Q's worker would),
verifying the DoesNotExist handling and delegation to the service layer.
"""
from unittest import mock

import pytest

from inventory import tasks
from inventory.tests.factories import TrackerFactory, TrackerFileFactory


@pytest.mark.django_db
class TestGenerateAutoThumbnailTask:
    def test_delegates_to_service_for_existing_file(self):
        tracker_file = TrackerFileFactory(storage_type='local', filename='part.stl')

        with mock.patch('inventory.tasks.generate_auto_thumbnail') as mock_generate:
            tasks.generate_auto_thumbnail_task(tracker_file.id)

        mock_generate.assert_called_once_with(tracker_file)

    def test_noop_when_tracker_file_deleted_before_task_runs(self):
        # No exception should be raised for a since-deleted file.
        tasks.generate_auto_thumbnail_task(999999)


@pytest.mark.django_db
class TestRegenerateTrackerThumbnailsTask:
    def test_delegates_to_service_for_existing_tracker(self):
        tracker = TrackerFactory()

        with mock.patch('inventory.tasks.regenerate_tracker_thumbnails') as mock_regen:
            tasks.regenerate_tracker_thumbnails_task(tracker.id, include_linked=True)

        mock_regen.assert_called_once_with(tracker, include_linked=True)

    def test_noop_when_tracker_deleted_before_task_runs(self):
        tasks.regenerate_tracker_thumbnails_task(999999)
