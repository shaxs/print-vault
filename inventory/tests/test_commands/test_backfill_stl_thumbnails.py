"""
Tests for the backfill_stl_thumbnails management command.
"""
from io import StringIO

import pytest
import trimesh
from django.core.files.base import ContentFile
from django.core.management import call_command

from inventory.tests.factories import (
    TrackerFactory,
    TrackerFileFactory,
    TrackerFileImageFactory,
)


def _stl_bytes():
    box = trimesh.creation.box(extents=(10, 10, 10))
    return box.export(file_type='stl')


@pytest.mark.django_db
class TestBackfillStlThumbnailsCommand:
    def test_dry_run_makes_no_changes(self):
        tracker_file = TrackerFileFactory(storage_type='local', filename='part.stl')
        tracker_file.local_file.save('part.stl', ContentFile(_stl_bytes()), save=True)

        out = StringIO()
        call_command('backfill_stl_thumbnails', '--dry-run', stdout=out)

        assert tracker_file.images.count() == 0
        assert 'DRY RUN' in out.getvalue()

    def test_generates_for_eligible_files(self):
        tracker_file = TrackerFileFactory(storage_type='local', filename='part.stl')
        tracker_file.local_file.save('part.stl', ContentFile(_stl_bytes()), save=True)

        out = StringIO()
        call_command('backfill_stl_thumbnails', stdout=out)

        assert tracker_file.images.count() == 1
        assert tracker_file.images.get().is_auto_generated is True

    def test_skips_files_that_already_have_an_image(self):
        tracker_file = TrackerFileFactory(storage_type='local', filename='part.stl')
        tracker_file.local_file.save('part.stl', ContentFile(_stl_bytes()), save=True)
        TrackerFileImageFactory(tracker_file=tracker_file)

        out = StringIO()
        call_command('backfill_stl_thumbnails', stdout=out)

        assert tracker_file.images.count() == 1  # unchanged

    def test_filters_by_tracker_id(self):
        tracker_a = TrackerFactory()
        tracker_b = TrackerFactory()
        file_a = TrackerFileFactory(tracker=tracker_a, storage_type='local', filename='a.stl')
        file_a.local_file.save('a.stl', ContentFile(_stl_bytes()), save=True)
        file_b = TrackerFileFactory(tracker=tracker_b, storage_type='local', filename='b.stl')
        file_b.local_file.save('b.stl', ContentFile(_stl_bytes()), save=True)

        out = StringIO()
        call_command('backfill_stl_thumbnails', '--tracker-id', str(tracker_a.pk), stdout=out)

        assert file_a.images.count() == 1
        assert file_b.images.count() == 0

    def test_unknown_tracker_id_reports_error(self):
        out = StringIO()
        call_command('backfill_stl_thumbnails', '--tracker-id', '999999', stdout=out)

        assert 'not found' in out.getvalue()

    def test_respects_limit(self):
        tracker = TrackerFactory()
        for i in range(3):
            tf = TrackerFileFactory(tracker=tracker, storage_type='local', filename=f'part_{i}.stl')
            tf.local_file.save(f'part_{i}.stl', ContentFile(_stl_bytes()), save=True)

        out = StringIO()
        call_command('backfill_stl_thumbnails', '--limit', '1', stdout=out)

        generated_count = sum(1 for tf in tracker.files.all() if tf.images.exists())
        assert generated_count == 1
