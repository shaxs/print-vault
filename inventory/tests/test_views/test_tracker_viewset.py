"""
Tests for Tracker ViewSet API endpoints.

Tests CRUD operations, custom actions, GitHub crawl integration, filtering, and search.
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from inventory.models import Tracker, TrackerFile
from inventory.tests.factories import TrackerFactory, TrackerFileFactory, ProjectFactory


@pytest.fixture
def api_client():
    """Provide an API client for making requests."""
    return APIClient()


@pytest.fixture
def sample_trackers(db):
    """Create sample trackers for testing."""
    project = ProjectFactory(project_name="Voron Build")
    
    tracker1 = TrackerFactory(
        name="Voron 0.2",
        project=project,
        github_url="https://github.com/VoronDesign/Voron-0",
        storage_type="link"
    )
    
    tracker2 = TrackerFactory(
        name="Voron Trident",
        github_url="https://github.com/VoronDesign/Voron-Trident",
        storage_type="local"
    )
    
    # Add files to tracker1
    TrackerFileFactory.create_batch(3, tracker=tracker1, status='completed')
    TrackerFileFactory.create_batch(2, tracker=tracker1, status='in_progress')
    
    return {
        'trackers': [tracker1, tracker2],
        'project': project
    }


# ============================================================================
# CRUD OPERATION TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrackerCRUD:
    """Test Create, Read, Update, Delete operations."""
    
    def test_list_trackers(self, api_client, sample_trackers):
        """Test listing all trackers."""
        url = '/api/trackers/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
    
    def test_retrieve_tracker(self, api_client, sample_trackers):
        """Test retrieving a single tracker."""
        tracker = sample_trackers['trackers'][0]
        url = f'/api/trackers/{tracker.pk}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == tracker.name
        assert 'files' in response.data
    
    def test_update_tracker(self, api_client, sample_trackers):
        """Test updating a tracker."""
        tracker = sample_trackers['trackers'][0]
        url = f'/api/trackers/{tracker.pk}/'
        
        data = {
            'name': 'Updated Tracker Name',
            'primary_color': '#FF0000'
        }
        
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        tracker.refresh_from_db()
        assert tracker.name == 'Updated Tracker Name'
        assert tracker.primary_color == '#FF0000'
    
    def test_delete_tracker(self, api_client, sample_trackers):
        """Test deleting a tracker."""
        tracker = sample_trackers['trackers'][0]
        url = f'/api/trackers/{tracker.pk}/'
        
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Tracker.objects.filter(pk=tracker.pk).exists()
    
    def test_delete_tracker_cascades_to_files(self, api_client, sample_trackers):
        """Test that deleting tracker also deletes its files."""
        tracker = sample_trackers['trackers'][0]
        file_ids = list(tracker.files.values_list('id', flat=True))
        
        url = f'/api/trackers/{tracker.pk}/'
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not TrackerFile.objects.filter(id__in=file_ids).exists()


# ============================================================================
# FILTERING TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrackerFiltering:
    """Test filtering functionality."""
    
    def test_filter_by_project(self, api_client, sample_trackers):
        """Test filtering trackers by project."""
        project = sample_trackers['project']
        url = '/api/trackers/'
        
        response = api_client.get(url, {'project': project.pk})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        for tracker in response.data:
            assert tracker['project'] == project.pk


# ============================================================================
# SEARCH TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrackerSearch:
    """Test search functionality."""
    
    def test_search_by_name(self, api_client, sample_trackers):
        """Test searching trackers by name."""
        url = '/api/trackers/'
        response = api_client.get(url, {'search': 'Voron'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert 'Voron' in response.data[0]['name']
    
    def test_search_by_github_url(self, api_client, sample_trackers):
        """Test searching trackers by GitHub URL."""
        url = '/api/trackers/'
        response = api_client.get(url, {'search': 'VoronDesign'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1


# ============================================================================
# ORDERING TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrackerOrdering:
    """Test ordering functionality."""
    
    def test_default_ordering(self, api_client, sample_trackers):
        """Test default ordering by created_date descending."""
        url = '/api/trackers/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Default ordering is -created_date (newest first)
    
    def test_order_by_name(self, api_client, sample_trackers):
        """Test ordering trackers by name."""
        url = '/api/trackers/'
        response = api_client.get(url, {'ordering': 'name'})
        
        assert response.status_code == status.HTTP_200_OK
        names = [tracker['name'] for tracker in response.data]
        assert names == sorted(names)


# ============================================================================
# SERIALIZER TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrackerSerializers:
    """Test different serializers for different actions."""
    
    def test_list_uses_list_serializer(self, api_client, sample_trackers):
        """Test list endpoint uses TrackerListSerializer (lightweight)."""
        url = '/api/trackers/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # TrackerListSerializer includes basic fields
        first_tracker = response.data[0]
        assert 'name' in first_tracker
        assert 'progress_percentage' in first_tracker
    
    def test_retrieve_uses_full_serializer(self, api_client, sample_trackers):
        """Test detail endpoint uses full TrackerSerializer with files."""
        tracker = sample_trackers['trackers'][0]
        url = f'/api/trackers/{tracker.pk}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'files' in response.data
        assert len(response.data['files']) == 5  # 3 completed + 2 in_progress


# ============================================================================
# TRACKER FILE VIEWSET TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrackerFileViewSet:
    """Test TrackerFile ViewSet operations."""
    
    def test_list_tracker_files(self, api_client, sample_trackers):
        """Test listing tracker files."""
        url = '/api/tracker-files/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 5
    
    def test_retrieve_tracker_file(self, api_client, sample_trackers):
        """Test retrieving a single tracker file."""
        tracker = sample_trackers['trackers'][0]
        file = tracker.files.first()
        url = f'/api/tracker-files/{file.pk}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['filename'] == file.filename
        assert response.data['tracker'] == tracker.pk
    
    def test_update_tracker_file(self, api_client, sample_trackers):
        """Test updating a tracker file."""
        tracker = sample_trackers['trackers'][0]
        file = tracker.files.first()
        url = f'/api/tracker-files/{file.pk}/'
        
        data = {
            'status': 'completed',
            'printed_quantity': file.quantity
        }
        
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        file.refresh_from_db()
        assert file.status == 'completed'
        assert file.printed_quantity == file.quantity
    
    def test_delete_tracker_file(self, api_client, sample_trackers):
        """Test deleting a tracker file."""
        tracker = sample_trackers['trackers'][0]
        file = tracker.files.first()
        url = f'/api/tracker-files/{file.pk}/'
        
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not TrackerFile.objects.filter(pk=file.pk).exists()


# ============================================================================
# TRACKER PROGRESS TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrackerProgress:
    """Test progress tracking and calculations."""
    
    def test_tracker_includes_progress_data(self, api_client, db):
        """Test tracker response includes progress statistics."""
        tracker = TrackerFactory()
        TrackerFileFactory(tracker=tracker, quantity=10, printed_quantity=5)
        TrackerFileFactory(tracker=tracker, quantity=10, printed_quantity=10)
        
        tracker.recalculate_stats()
        tracker.save()
        
        url = f'/api/trackers/{tracker.pk}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'progress_percentage' in response.data
        assert 'total_quantity' in response.data
        assert 'printed_quantity_total' in response.data
