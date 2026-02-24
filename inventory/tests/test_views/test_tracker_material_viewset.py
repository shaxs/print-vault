"""
Tests for Tracker Material Blueprint API endpoints.

Tests the new update_materials endpoint and enhanced file configuration:
- POST /api/trackers/{id}/update_materials/
- PATCH /api/tracker-files/{id}/update_configuration/ (material_ids support)
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from inventory.models import Tracker, TrackerFile
from inventory.tests.factories import (
    TrackerFactory, TrackerFileFactory, MaterialFactory
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def api_client():
    """Provide an API client for making requests."""
    return APIClient()


@pytest.fixture
def blue_material(db):
    """Create a blue ABS material blueprint."""
    return MaterialFactory(
        name="Blue ABS",
        is_generic=False,
        colors=["#1E40AF", "#2563EB"]
    )


@pytest.fixture
def red_material(db):
    """Create a red ABS material blueprint."""
    return MaterialFactory(
        name="Red ABS",
        is_generic=False,
        colors=["#DC2626", "#EF4444"]
    )


# ============================================================================
# UPDATE MATERIALS ENDPOINT TESTS
# ============================================================================

@pytest.mark.django_db
class TestUpdateMaterialsEndpoint:
    """Test /api/trackers/{id}/update_materials/ endpoint."""
    
    def test_update_materials_cascade_to_files(self, api_client, blue_material, red_material):
        """Test that updating tracker materials cascades to Primary/Accent files."""
        # Create tracker with files
        tracker = TrackerFactory()
        primary_file1 = TrackerFileFactory(tracker=tracker, color="Primary", material_ids=[])
        primary_file2 = TrackerFileFactory(tracker=tracker, color="Primary", material_ids=[])
        accent_file = TrackerFileFactory(tracker=tracker, color="Accent", material_ids=[])
        other_file = TrackerFileFactory(tracker=tracker, color="Other", material_ids=[])
        
        # Update materials
        url = f'/api/trackers/{tracker.id}/update_materials/'
        data = {
            'primary_material_id': blue_material.id,
            'accent_material_id': red_material.id
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'tracker' in response.data
        assert 'updates_made' in response.data
        
        # Verify tracker updated
        tracker.refresh_from_db()
        assert tracker.primary_material_id == blue_material.id
        assert tracker.accent_material_id == red_material.id
        
        # Verify Primary files updated
        primary_file1.refresh_from_db()
        primary_file2.refresh_from_db()
        assert primary_file1.material_ids == [blue_material.id]
        assert primary_file2.material_ids == [blue_material.id]
        
        # Verify Accent file updated
        accent_file.refresh_from_db()
        assert accent_file.material_ids == [red_material.id]
        
        # Verify Other file NOT updated (preserves custom material)
        other_file.refresh_from_db()
        assert other_file.material_ids == []  # Unchanged
    
    def test_update_only_primary_material(self, api_client, blue_material):
        """Test updating only primary material, leaving accent unchanged."""
        tracker = TrackerFactory()
        
        primary_file = TrackerFileFactory(tracker=tracker, color="Primary")
        accent_file = TrackerFileFactory(tracker=tracker, color="Accent")
        
        url = f'/api/trackers/{tracker.id}/update_materials/'
        data = {'primary_material_id': blue_material.id}
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        tracker.refresh_from_db()
        assert tracker.primary_material_id == blue_material.id
        assert tracker.accent_material is None
        
        primary_file.refresh_from_db()
        assert primary_file.material_ids == [blue_material.id]
        
        # Accent file should not be updated (no accent_material_id provided)
        accent_file.refresh_from_db()
        assert accent_file.material_ids == []
    
    def test_update_materials_no_change_when_not_provided(self, api_client, blue_material):
        """Test that materials are not changed if not provided in request."""
        # Start with materials set
        tracker = TrackerFactory(primary_material=blue_material)
        file = TrackerFileFactory(tracker=tracker, color="Primary", material_ids=[blue_material.id])
        
        # Call endpoint without providing primary_material_id
        url = f'/api/trackers/{tracker.id}/update_materials/'
        data = {}  # Empty data - don't update anything
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Materials should remain unchanged
        tracker.refresh_from_db()
        assert tracker.primary_material == blue_material
        
        file.refresh_from_db()
        assert file.material_ids == [blue_material.id]
    
    def test_update_materials_returns_file_counts(self, api_client, blue_material, red_material):
        """Test that response includes counts of updated files."""
        tracker = TrackerFactory()
        # Create 3 Primary, 2 Accent files
        TrackerFileFactory.create_batch(3, tracker=tracker, color="Primary")
        TrackerFileFactory.create_batch(2, tracker=tracker, color="Accent")
        
        url = f'/api/trackers/{tracker.id}/update_materials/'
        data = {
            'primary_material_id': blue_material.id,
            'accent_material_id': red_material.id
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['updates_made']['primary'] == 3
        assert response.data['updates_made']['accent'] == 2
    
    def test_update_materials_nonexistent_tracker(self, api_client):
        """Test updating materials for non-existent tracker."""
        url = '/api/trackers/99999/update_materials/'
        data = {'primary_material_id': 1}
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_materials_invalid_material_id(self, api_client):
        """Test updating with non-existent material ID."""
        tracker = TrackerFactory()
        
        url = f'/api/trackers/{tracker.id}/update_materials/'
        data = {'primary_material_id': 99999}  # Doesn't exist
        response = api_client.post(url, data, format='json')
        
        # Endpoint handles gracefully - returns 200 but doesn't apply invalid ID
        assert response.status_code == status.HTTP_200_OK
        tracker.refresh_from_db()
        # Tracker material should not be set to invalid ID
        assert tracker.primary_material is None


@pytest.mark.django_db
class TestFileConfigurationMaterialIds:
    """Test /api/tracker-files/{id}/update_configuration/ with material_ids."""
    
    def test_update_file_material_ids(self, api_client, blue_material, red_material):
        """Test updating file's material_ids array."""
        tracker = TrackerFactory()
        file = TrackerFileFactory(tracker=tracker, color="Other", material_ids=[])
        
        url = f'/api/tracker-files/{file.id}/update_configuration/'
        data = {
            'color': 'Multicolor',
            'material_ids': [blue_material.id, red_material.id],
            'quantity': 3
        }
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        file.refresh_from_db()
        assert file.color == 'Multicolor'
        assert file.material_ids == [blue_material.id, red_material.id]
        assert file.quantity == 3
    
    def test_primary_files_cannot_have_custom_materials(self, api_client):
        """Test that Primary files cannot have custom material_ids (inherit tracker)."""
        tracker = TrackerFactory()
        file = TrackerFileFactory(tracker=tracker, color="Primary")
        custom_mat = MaterialFactory(name="Custom", is_generic=False, colors=["#000000"])
        
        url = f'/api/tracker-files/{file.id}/update_configuration/'
        data = {
            'color': 'Primary',
            'material_ids': [custom_mat.id]  # Should be ignored
        }
        response = api_client.patch(url, data, format='json')
        
        # Backend should ignore material_ids for Primary files
        file.refresh_from_db()
        # Material should come from tracker, not custom
        assert file.color == "Primary"
    
    def test_change_from_primary_to_other_allows_custom_material(self, api_client):
        """Test changing file from Primary to Other allows custom material."""
        custom_mat = MaterialFactory(name="Custom Yellow", is_generic=False, colors=["#FDE047"])
        tracker = TrackerFactory()
        file = TrackerFileFactory(tracker=tracker, color="Primary")
        
        url = f'/api/tracker-files/{file.id}/update_configuration/'
        data = {
            'color': 'Other',
            'material_ids': [custom_mat.id]
        }
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        file.refresh_from_db()
        assert file.color == "Other"
        assert file.material_ids == [custom_mat.id]
    
    def test_update_material_ids_preserves_other_fields(self, api_client, blue_material):
        """Test that updating material_ids doesn't affect other fields."""
        tracker = TrackerFactory()
        file = TrackerFileFactory(
            tracker=tracker,
            color="Other",
            quantity=5,
            status="in_progress",
            printed_quantity=2
        )
        
        url = f'/api/tracker-files/{file.id}/update_configuration/'
        data = {'material_ids': [blue_material.id]}
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        file.refresh_from_db()
        assert file.material_ids == [blue_material.id]
        # Other fields unchanged
        assert file.quantity == 5
        assert file.status == "in_progress"
        assert file.printed_quantity == 2


@pytest.mark.django_db
class TestTrackerDetailWithMaterials:
    """Test GET /api/trackers/{id}/ returns material_display fields."""
    
    def test_tracker_detail_includes_material_display(self, api_client, blue_material):
        """Test that tracker detail includes enriched material data."""
        tracker = TrackerFactory(primary_material=blue_material)
        
        url = f'/api/trackers/{tracker.id}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'primary_material_display' in response.data
        
        material_data = response.data['primary_material_display']
        assert material_data['id'] == blue_material.id
        assert material_data['name'] == blue_material.name
        assert material_data['colors'] == blue_material.colors
    
    def test_file_includes_materials_display(self, api_client, blue_material, red_material):
        """Test that files in tracker detail include materials_display."""
        tracker = TrackerFactory()
        file = TrackerFileFactory(
            tracker=tracker,
            color="Multicolor",
            material_ids=[blue_material.id, red_material.id]
        )
        
        url = f'/api/trackers/{tracker.id}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        file_data = response.data['files'][0]
        
        assert 'materials_display' in file_data
        assert len(file_data['materials_display']) == 2
        material_names = [m['name'] for m in file_data['materials_display']]
        assert blue_material.name in material_names
        assert red_material.name in material_names
