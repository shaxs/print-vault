"""
Tests for the TrackerFileImage model.

Covers ordering, defaults, cascade delete behavior, and the related_name
lookup used by TrackerFileSerializer's thumbnail field.
"""
import pytest
from inventory.models import TrackerFileImage
from inventory.tests.factories import TrackerFileFactory, TrackerFileImageFactory


@pytest.mark.django_db
class TestTrackerFileImageModel:
    """Test TrackerFileImage model behavior."""

    def test_create_image_with_defaults(self):
        """Test creating an image attaches to its tracker file."""
        image = TrackerFileImageFactory()

        assert image.pk is not None
        # order is factory.Sequence-driven (shared counter across the whole
        # test run), not the model's own default=0 -- just assert it's a
        # sane int rather than depending on absolute sequence position.
        assert isinstance(image.order, int)
        assert image.tracker_file is not None
        assert image.is_auto_generated is False

    def test_is_auto_generated_can_be_set(self):
        """Test is_auto_generated flags an image as machine-generated vs. manual."""
        image = TrackerFileImageFactory(is_auto_generated=True)

        assert image.is_auto_generated is True

    def test_related_name_images(self):
        """Test tracker_file.images returns attached images via related_name."""
        tracker_file = TrackerFileFactory()
        TrackerFileImageFactory(tracker_file=tracker_file, order=0)
        TrackerFileImageFactory(tracker_file=tracker_file, order=1)

        assert tracker_file.images.count() == 2

    def test_default_ordering_by_order_then_created_at(self):
        """Test images are returned in `order` order, not creation order."""
        tracker_file = TrackerFileFactory()
        second = TrackerFileImageFactory(tracker_file=tracker_file, order=1)
        first = TrackerFileImageFactory(tracker_file=tracker_file, order=0)

        ordered = list(tracker_file.images.all())
        assert ordered == [first, second]

    def test_str_includes_filename_and_caption(self):
        """Test __str__ includes the parent filename and caption."""
        tracker_file = TrackerFileFactory(filename='part.stl')
        image = TrackerFileImageFactory(tracker_file=tracker_file, caption='Front view')

        assert str(image) == 'part.stl - Front view'

    def test_str_without_caption(self):
        """Test __str__ falls back to 'No caption' when caption is blank."""
        tracker_file = TrackerFileFactory(filename='part.stl')
        image = TrackerFileImageFactory(tracker_file=tracker_file, caption='')

        assert str(image) == 'part.stl - No caption'

    def test_cascade_delete_when_tracker_file_deleted(self):
        """Test deleting the parent TrackerFile deletes its images too."""
        tracker_file = TrackerFileFactory()
        image = TrackerFileImageFactory(tracker_file=tracker_file)
        image_id = image.pk

        tracker_file.delete()

        assert not TrackerFileImage.objects.filter(pk=image_id).exists()
