"""
Tests for the thumbnail-invalidation signals in inventory/models.py:
queue_auto_thumbnail_generation, clear_stale_auto_thumbnail_on_color_change
(per-file color/material changes), and detect_manual_color_change /
requeue_thumbnails_on_manual_color_change (tracker-level manual-hex
primary_color/accent_color changes, which never touch a TrackerFile row so
the per-file signals can't see them).

Mocks django_q.tasks.async_task so these run without a live Django-Q
cluster -- they only verify the signals' own pre-filters decide correctly
whether to enqueue/clear. Whether the queued task itself succeeds is covered
by test_services/test_stl_thumbnail_service.py.
"""
from unittest import mock

import pytest

from inventory.tests.factories import (
    TrackerFactory,
    TrackerFileFactory,
    TrackerFileImageFactory,
    MaterialFactory,
)


@pytest.mark.django_db
class TestQueueAutoThumbnailGenerationSignal:
    def test_enqueues_for_new_local_stl_file(self):
        with mock.patch('django_q.tasks.async_task') as mock_async_task:
            tracker_file = TrackerFileFactory(storage_type='local', filename='part.stl')

        mock_async_task.assert_called_once_with(
            'inventory.tasks.generate_auto_thumbnail_task', tracker_file.id
        )

    def test_enqueues_for_new_3mf_file(self):
        with mock.patch('django_q.tasks.async_task') as mock_async_task:
            TrackerFileFactory(storage_type='local', filename='part.3mf')

        mock_async_task.assert_called_once()

    def test_does_not_enqueue_for_other_extensions(self):
        with mock.patch('django_q.tasks.async_task') as mock_async_task:
            TrackerFileFactory(storage_type='local', filename='readme.txt')

        mock_async_task.assert_not_called()

    def test_does_not_enqueue_when_image_already_exists(self):
        tracker_file = TrackerFileFactory(storage_type='local', filename='part.stl')
        TrackerFileImageFactory(tracker_file=tracker_file)

        with mock.patch('django_q.tasks.async_task') as mock_async_task:
            tracker_file.save()  # re-save to trigger post_save again

        mock_async_task.assert_not_called()

    def test_does_not_enqueue_for_link_storage_when_tracker_setting_off(self):
        tracker = TrackerFactory(generate_thumbnails_for_linked_files=False)

        with mock.patch('django_q.tasks.async_task') as mock_async_task:
            TrackerFileFactory(tracker=tracker, storage_type='link', filename='part.stl')

        mock_async_task.assert_not_called()

    def test_enqueues_for_link_storage_when_tracker_setting_on(self):
        tracker = TrackerFactory(generate_thumbnails_for_linked_files=True)

        with mock.patch('django_q.tasks.async_task') as mock_async_task:
            tracker_file = TrackerFileFactory(tracker=tracker, storage_type='link', filename='part.stl')

        mock_async_task.assert_called_once_with(
            'inventory.tasks.generate_auto_thumbnail_task', tracker_file.id
        )

    def test_reevaluates_on_link_to_local_transition(self):
        """A file created as 'link' and later switched to 'local' (existing
        download flow) should become eligible on that save too."""
        tracker = TrackerFactory(generate_thumbnails_for_linked_files=False)
        tracker_file = TrackerFileFactory(tracker=tracker, storage_type='link', filename='part.stl')

        tracker_file.storage_type = 'local'
        with mock.patch('django_q.tasks.async_task') as mock_async_task:
            tracker_file.save()

        mock_async_task.assert_called_once_with(
            'inventory.tasks.generate_auto_thumbnail_task', tracker_file.id
        )


@pytest.mark.django_db
class TestClearStaleAutoThumbnailOnColorChangeSignal:
    def test_color_change_deletes_existing_auto_image(self):
        tracker_file = TrackerFileFactory(storage_type='local', filename='part.stl', color='Primary')
        image = TrackerFileImageFactory(tracker_file=tracker_file, is_auto_generated=True)

        tracker_file.color = 'Accent'
        with mock.patch('django_q.tasks.async_task'):
            tracker_file.save()

        assert not tracker_file.images.filter(pk=image.pk).exists()

    def test_color_change_requeues_generation(self):
        """End-to-end with the other signal: deleting the stale image in
        pre_save means post_save's "already has an image" guard no longer
        blocks re-generation."""
        tracker_file = TrackerFileFactory(storage_type='local', filename='part.stl', color='Primary')
        TrackerFileImageFactory(tracker_file=tracker_file, is_auto_generated=True)

        tracker_file.color = 'Accent'
        with mock.patch('django_q.tasks.async_task') as mock_async_task:
            tracker_file.save()

        mock_async_task.assert_called_once_with(
            'inventory.tasks.generate_auto_thumbnail_task', tracker_file.id
        )

    def test_material_ids_change_deletes_existing_auto_image(self):
        tracker_file = TrackerFileFactory(
            storage_type='local', filename='part.stl', color='Other', material_ids=[1]
        )
        image = TrackerFileImageFactory(tracker_file=tracker_file, is_auto_generated=True)

        tracker_file.material_ids = [2]
        with mock.patch('django_q.tasks.async_task'):
            tracker_file.save()

        assert not tracker_file.images.filter(pk=image.pk).exists()

    def test_unrelated_field_change_does_not_delete_image(self):
        tracker_file = TrackerFileFactory(storage_type='local', filename='part.stl', color='Primary')
        image = TrackerFileImageFactory(tracker_file=tracker_file, is_auto_generated=True)

        tracker_file.quantity = 5
        with mock.patch('django_q.tasks.async_task'):
            tracker_file.save()

        assert tracker_file.images.filter(pk=image.pk).exists()

    def test_never_touches_a_manually_uploaded_image(self):
        tracker_file = TrackerFileFactory(storage_type='local', filename='part.stl', color='Primary')
        manual_image = TrackerFileImageFactory(tracker_file=tracker_file, is_auto_generated=False)

        tracker_file.color = 'Accent'
        with mock.patch('django_q.tasks.async_task') as mock_async_task:
            tracker_file.save()

        assert tracker_file.images.filter(pk=manual_image.pk).exists()
        # A manual image still means "has an image" -> post_save must not requeue.
        mock_async_task.assert_not_called()

    def test_new_file_creation_does_not_error(self):
        # No prior DB row to compare against -- must be a no-op, not a crash.
        with mock.patch('django_q.tasks.async_task'):
            tracker_file = TrackerFileFactory(storage_type='local', filename='part.stl')

        assert tracker_file.pk is not None


@pytest.mark.django_db
class TestManualColorChangeSignal:
    def test_primary_color_change_clears_and_requeues_primary_files(self):
        tracker = TrackerFactory(primary_color='#111111')
        primary_file = TrackerFileFactory(tracker=tracker, storage_type='local', filename='a.stl', color='Primary')
        image = TrackerFileImageFactory(tracker_file=primary_file, is_auto_generated=True)

        tracker.primary_color = '#222222'
        with mock.patch('django_q.tasks.async_task') as mock_async_task:
            tracker.save()

        assert not primary_file.images.filter(pk=image.pk).exists()
        mock_async_task.assert_called_once_with(
            'inventory.tasks.generate_auto_thumbnail_task', primary_file.id
        )

    def test_accent_color_change_only_affects_accent_files(self):
        tracker = TrackerFactory(accent_color='#111111')
        primary_file = TrackerFileFactory(tracker=tracker, storage_type='local', filename='a.stl', color='Primary')
        accent_file = TrackerFileFactory(tracker=tracker, storage_type='local', filename='b.stl', color='Accent')
        primary_image = TrackerFileImageFactory(tracker_file=primary_file, is_auto_generated=True)
        accent_image = TrackerFileImageFactory(tracker_file=accent_file, is_auto_generated=True)

        tracker.accent_color = '#222222'
        with mock.patch('django_q.tasks.async_task') as mock_async_task:
            tracker.save()

        assert primary_file.images.filter(pk=primary_image.pk).exists()  # untouched
        assert not accent_file.images.filter(pk=accent_image.pk).exists()  # cleared
        mock_async_task.assert_called_once_with(
            'inventory.tasks.generate_auto_thumbnail_task', accent_file.id
        )

    def test_never_touches_a_manually_uploaded_image(self):
        tracker = TrackerFactory(primary_color='#111111')
        primary_file = TrackerFileFactory(tracker=tracker, storage_type='local', filename='a.stl', color='Primary')
        manual_image = TrackerFileImageFactory(tracker_file=primary_file, is_auto_generated=False)

        tracker.primary_color = '#222222'
        with mock.patch('django_q.tasks.async_task') as mock_async_task:
            tracker.save()

        assert primary_file.images.filter(pk=manual_image.pk).exists()
        mock_async_task.assert_not_called()

    def test_multicolor_and_other_files_are_not_affected(self):
        tracker = TrackerFactory(primary_color='#111111')
        other_file = TrackerFileFactory(tracker=tracker, storage_type='local', filename='a.stl', color='Other')
        image = TrackerFileImageFactory(tracker_file=other_file, is_auto_generated=True)

        tracker.primary_color = '#222222'
        with mock.patch('django_q.tasks.async_task') as mock_async_task:
            tracker.save()

        assert other_file.images.filter(pk=image.pk).exists()
        mock_async_task.assert_not_called()

    def test_material_blueprint_change_does_not_double_queue(self):
        """
        Switching primary_material is update_materials's job (its own
        per-file .save() loop already triggers the TrackerFile-level
        signal) -- this tracker-level signal must not also react to it,
        or the same files would get queued twice.
        """
        material = MaterialFactory(colors=['#abcdef'])
        tracker = TrackerFactory(primary_material=None)
        TrackerFileFactory(tracker=tracker, storage_type='local', filename='a.stl', color='Primary')

        tracker.primary_material = material
        with mock.patch('django_q.tasks.async_task') as mock_async_task:
            tracker.save()

        mock_async_task.assert_not_called()

    def test_unrelated_field_change_does_not_touch_images(self):
        tracker = TrackerFactory(primary_color='#111111')
        primary_file = TrackerFileFactory(tracker=tracker, storage_type='local', filename='a.stl', color='Primary')
        image = TrackerFileImageFactory(tracker_file=primary_file, is_auto_generated=True)

        tracker.name = 'Renamed'
        with mock.patch('django_q.tasks.async_task') as mock_async_task:
            tracker.save()

        assert primary_file.images.filter(pk=image.pk).exists()
        mock_async_task.assert_not_called()

    def test_new_tracker_creation_does_not_error(self):
        with mock.patch('django_q.tasks.async_task'):
            tracker = TrackerFactory()

        assert tracker.pk is not None

    def test_skips_requeue_for_linked_file_when_tracker_setting_off(self):
        """Stale thumbnail still gets cleared (it's wrong now), but
        regeneration is gated by generate_thumbnails_for_linked_files same
        as everywhere else."""
        tracker = TrackerFactory(primary_color='#111111', generate_thumbnails_for_linked_files=False)
        primary_file = TrackerFileFactory(tracker=tracker, storage_type='link', filename='a.stl', color='Primary')
        image = TrackerFileImageFactory(tracker_file=primary_file, is_auto_generated=True)

        tracker.primary_color = '#222222'
        with mock.patch('django_q.tasks.async_task') as mock_async_task:
            tracker.save()

        assert not primary_file.images.filter(pk=image.pk).exists()
        mock_async_task.assert_not_called()
