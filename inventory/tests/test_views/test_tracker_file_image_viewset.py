"""
Tests for TrackerFile image attachment endpoints (PR #20).

Covers:
  - GET/POST /api/tracker-files/{id}/images/
  - PATCH/DELETE /api/tracker-file-images/{id}/
  - TrackerFileSerializer.thumbnail (first image by order, or null)
"""
import io
import pytest
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient
from inventory.models import TrackerFileImage
from inventory.tests.factories import TrackerFileFactory, TrackerFileImageFactory


@pytest.fixture
def api_client():
    return APIClient()


def _image_file(filename='preview.png', color=(0, 128, 255)):
    """Return a minimal real PNG as a file-like object for multipart upload."""
    buffer = io.BytesIO()
    Image.new('RGB', (4, 4), color=color).save(buffer, format='PNG')
    buffer.seek(0)
    buffer.name = filename
    return buffer


# ============================================================================
# LIST / UPLOAD — /api/tracker-files/{id}/images/
# ============================================================================

@pytest.mark.django_db
class TestTrackerFileImagesAction:
    """Test GET/POST /api/tracker-files/{id}/images/."""

    def test_list_images_empty(self, api_client):
        """Test listing images for a file with none returns an empty array."""
        tracker_file = TrackerFileFactory()
        url = f'/api/tracker-files/{tracker_file.pk}/images/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_list_images_returns_ordered(self, api_client):
        """Test listing images returns them ordered by `order`."""
        tracker_file = TrackerFileFactory()
        TrackerFileImageFactory(tracker_file=tracker_file, order=1, caption='Second')
        TrackerFileImageFactory(tracker_file=tracker_file, order=0, caption='First')
        url = f'/api/tracker-files/{tracker_file.pk}/images/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert [img['caption'] for img in response.data] == ['First', 'Second']

    def test_upload_image_success(self, api_client):
        """Test uploading an image creates a TrackerFileImage linked to the file."""
        tracker_file = TrackerFileFactory()
        url = f'/api/tracker-files/{tracker_file.pk}/images/'

        response = api_client.post(
            url,
            {'image': _image_file(), 'caption': 'Auto-generated preview'},
            format='multipart',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert tracker_file.images.count() == 1
        image = tracker_file.images.first()
        assert image.caption == 'Auto-generated preview'

    def test_upload_image_defaults_order_to_current_count(self, api_client):
        """Test order defaults to the current image count when not provided."""
        tracker_file = TrackerFileFactory()
        TrackerFileImageFactory(tracker_file=tracker_file, order=0)
        url = f'/api/tracker-files/{tracker_file.pk}/images/'

        response = api_client.post(url, {'image': _image_file()}, format='multipart')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['order'] == 1

    def test_upload_image_respects_explicit_order(self, api_client):
        """Test an explicitly provided order overrides the default."""
        tracker_file = TrackerFileFactory()
        url = f'/api/tracker-files/{tracker_file.pk}/images/'

        response = api_client.post(
            url, {'image': _image_file(), 'order': 5}, format='multipart',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['order'] == 5

    def test_upload_without_image_returns_400(self, api_client):
        """Test POSTing with no image file returns 400."""
        tracker_file = TrackerFileFactory()
        url = f'/api/tracker-files/{tracker_file.pk}/images/'

        response = api_client.post(url, {'caption': 'no file here'}, format='multipart')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_upload_to_nonexistent_file_returns_404(self, api_client, db):
        """Test uploading to a non-existent tracker file ID returns 404."""
        url = '/api/tracker-files/999999/images/'

        response = api_client.post(url, {'image': _image_file()}, format='multipart')

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# UPDATE / DELETE — /api/tracker-file-images/{id}/
# ============================================================================

@pytest.mark.django_db
class TestTrackerFileImageViewSet:
    """Test PATCH/DELETE /api/tracker-file-images/{id}/."""

    def test_update_caption(self, api_client):
        """Test updating an image's caption."""
        image = TrackerFileImageFactory(caption='Old caption')
        url = f'/api/tracker-file-images/{image.pk}/'

        response = api_client.patch(url, {'caption': 'New caption'}, format='json')

        assert response.status_code == status.HTTP_200_OK
        image.refresh_from_db()
        assert image.caption == 'New caption'

    def test_update_order(self, api_client):
        """Test updating an image's order (used for reordering)."""
        image = TrackerFileImageFactory(order=0)
        url = f'/api/tracker-file-images/{image.pk}/'

        response = api_client.patch(url, {'order': 3}, format='json')

        assert response.status_code == status.HTTP_200_OK
        image.refresh_from_db()
        assert image.order == 3

    def test_delete_image(self, api_client):
        """Test deleting an image."""
        image = TrackerFileImageFactory()
        image_id = image.pk
        url = f'/api/tracker-file-images/{image_id}/'

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not TrackerFileImage.objects.filter(pk=image_id).exists()

    def test_delete_one_image_leaves_others(self, api_client):
        """Test deleting one image doesn't affect its siblings."""
        tracker_file = TrackerFileFactory()
        keep = TrackerFileImageFactory(tracker_file=tracker_file, order=0)
        remove = TrackerFileImageFactory(tracker_file=tracker_file, order=1)

        response = api_client.delete(f'/api/tracker-file-images/{remove.pk}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert tracker_file.images.count() == 1
        assert tracker_file.images.first().pk == keep.pk


# ============================================================================
# THUMBNAIL FIELD — TrackerFileSerializer via /api/tracker-files/{id}/
# ============================================================================

@pytest.mark.django_db
class TestTrackerFileThumbnailField:
    """Test TrackerFileSerializer.thumbnail reflects the first image by order."""

    def test_thumbnail_is_null_with_no_images(self, api_client):
        """Test thumbnail is null when the file has no images."""
        tracker_file = TrackerFileFactory()
        url = f'/api/tracker-files/{tracker_file.pk}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['thumbnail'] is None

    def test_thumbnail_uses_first_image_by_order(self, api_client):
        """Test thumbnail reflects the lowest-`order` image, not upload order."""
        tracker_file = TrackerFileFactory()
        TrackerFileImageFactory(tracker_file=tracker_file, order=1)
        first = TrackerFileImageFactory(tracker_file=tracker_file, order=0)
        url = f'/api/tracker-files/{tracker_file.pk}/'

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['thumbnail'] is not None
        assert first.image.name.split('/')[-1] in response.data['thumbnail']
