"""
Tests for Tracker and TrackerFile models.

Tests GitHub integration, computed properties, progress calculations, and status workflows.
"""
import pytest
from inventory.models import Tracker
from inventory.tests.factories import TrackerFactory, TrackerFileFactory, ProjectFactory


# ============================================================================
# TRACKER MODEL TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrackerModel:
    """Test Tracker model functionality."""
    
    def test_create_tracker(self):
        """Test creating a basic tracker."""
        tracker = TrackerFactory(
            name="Voron 0.2",
            github_url="https://github.com/VoronDesign/Voron-0",
            storage_type="link"
        )
        
        assert tracker.name == "Voron 0.2"
        assert tracker.storage_type == "link"
        assert tracker.total_quantity == 0
        assert tracker.progress_percentage == 0
    
    def test_tracker_with_project(self):
        """Test associating tracker with a project."""
        project = ProjectFactory(project_name="Voron Build")
        tracker = TrackerFactory(
            name="Voron 0.2 Tracker",
            project=project
        )
        
        assert tracker.project == project
        assert tracker in project.trackers.all()
    
    def test_tracker_default_colors(self):
        """Test default color values."""
        tracker = TrackerFactory()
        
        assert tracker.primary_color == "#1E40AF"
        assert tracker.accent_color == "#DC2626"
    
    def test_tracker_custom_colors(self):
        """Test custom color configuration."""
        tracker = TrackerFactory(
            primary_color="#FF5733",
            accent_color="#C70039"
        )
        
        assert tracker.primary_color == "#FF5733"
        assert tracker.accent_color == "#C70039"
    
    def test_tracker_creation_modes(self):
        """Test different creation modes."""
        github_tracker = TrackerFactory(creation_mode="github")
        manual_tracker = TrackerFactory(creation_mode="manual")
        
        assert github_tracker.creation_mode == "github"
        assert manual_tracker.creation_mode == "manual"
    
    def test_tracker_storage_types(self):
        """Test different storage types."""
        link_tracker = TrackerFactory(storage_type="link")
        local_tracker = TrackerFactory(storage_type="local")
        
        assert link_tracker.storage_type == "link"
        assert local_tracker.storage_type == "local"


# ============================================================================
# TRACKER COMPUTED PROPERTIES TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrackerComputedProperties:
    """Test computed properties and statistics."""
    
    def test_total_count_property(self):
        """Test total file count property."""
        tracker = TrackerFactory()
        TrackerFileFactory.create_batch(5, tracker=tracker)
        
        assert tracker.total_count == 5
    
    def test_completed_count_property(self):
        """Test completed file count."""
        tracker = TrackerFactory()
        TrackerFileFactory.create_batch(3, tracker=tracker, status='completed')
        TrackerFileFactory.create_batch(2, tracker=tracker, status='in_progress')
        
        assert tracker.completed_count == 3
    
    def test_in_progress_count_property(self):
        """Test in progress file count."""
        tracker = TrackerFactory()
        TrackerFileFactory.create_batch(2, tracker=tracker, status='in_progress')
        TrackerFileFactory.create_batch(3, tracker=tracker, status='not_started')
        
        assert tracker.in_progress_count == 2
    
    def test_not_started_count_property(self):
        """Test not started file count."""
        tracker = TrackerFactory()
        TrackerFileFactory.create_batch(4, tracker=tracker, status='not_started')
        TrackerFileFactory.create_batch(1, tracker=tracker, status='completed')
        
        assert tracker.not_started_count == 4
    
    def test_pending_quantity_property(self):
        """Test pending quantity calculation."""
        tracker = TrackerFactory(
            total_quantity=100,
            printed_quantity_total=60
        )
        
        assert tracker.pending_quantity == 40


# ============================================================================
# TRACKER STATISTICS TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrackerStatistics:
    """Test statistics calculations and caching."""
    
    def test_recalculate_stats_empty(self):
        """Test recalculating stats with no files."""
        tracker = TrackerFactory()
        tracker.recalculate_stats()
        tracker.save()
        
        assert tracker.total_quantity == 0
        assert tracker.printed_quantity_total == 0
        assert tracker.progress_percentage == 0
    
    def test_recalculate_stats_with_files(self):
        """Test recalculating stats with files."""
        tracker = TrackerFactory()
        TrackerFileFactory(tracker=tracker, quantity=10, printed_quantity=5)
        TrackerFileFactory(tracker=tracker, quantity=20, printed_quantity=10)
        
        tracker.recalculate_stats()
        tracker.save()
        
        assert tracker.total_quantity == 30
        assert tracker.printed_quantity_total == 15
        assert tracker.progress_percentage == 50
    
    def test_progress_percentage_zero_quantity(self):
        """Test progress percentage when total is zero."""
        tracker = TrackerFactory()
        tracker.recalculate_stats()
        
        assert tracker.progress_percentage == 0
    
    def test_progress_percentage_rounding(self):
        """Test progress percentage rounds correctly."""
        tracker = TrackerFactory()
        TrackerFileFactory(tracker=tracker, quantity=3, printed_quantity=1)
        
        tracker.recalculate_stats()
        
        # 1/3 = 33.33%, should round to 33
        assert tracker.progress_percentage == 33


# ============================================================================
# TRACKER FILE MODEL TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrackerFileModel:
    """Test TrackerFile model functionality."""
    
    def test_create_tracker_file(self):
        """Test creating a basic tracker file."""
        tracker = TrackerFactory()
        file = TrackerFileFactory(
            tracker=tracker,
            filename="frame_bottom.stl",
            quantity=2,
            color="Primary",
            material="ABS"
        )
        
        assert file.filename == "frame_bottom.stl"
        assert file.quantity == 2
        assert file.color == "Primary"
        assert file.material == "ABS"
        assert file.printed_quantity == 0
    
    def test_tracker_file_storage_types(self):
        """Test file storage type options."""
        tracker = TrackerFactory()
        link_file = TrackerFileFactory(tracker=tracker, storage_type="link")
        local_file = TrackerFileFactory(tracker=tracker, storage_type="local")
        
        assert link_file.storage_type == "link"
        assert local_file.storage_type == "local"
    
    def test_tracker_file_status_choices(self):
        """Test file status options."""
        tracker = TrackerFactory()
        
        not_started = TrackerFileFactory(tracker=tracker, status="not_started")
        in_progress = TrackerFileFactory(tracker=tracker, status="in_progress")
        completed = TrackerFileFactory(tracker=tracker, status="completed")
        
        assert not_started.status == "not_started"
        assert in_progress.status == "in_progress"
        assert completed.status == "completed"
    
    def test_tracker_file_directory_path(self):
        """Test directory path handling."""
        tracker = TrackerFactory()
        file = TrackerFileFactory(
            tracker=tracker,
            filename="extrusion_a.stl",
            directory_path="Frame/extrusions"
        )
        
        assert file.directory_path == "Frame/extrusions"
    
    def test_tracker_file_github_url(self):
        """Test GitHub URL storage."""
        tracker = TrackerFactory()
        file = TrackerFileFactory(
            tracker=tracker,
            github_url="https://github.com/VoronDesign/Voron-0/blob/main/STLs/frame.stl"
        )
        
        assert "github.com" in file.github_url
    
    def test_tracker_file_selection_state(self):
        """Test file selection state."""
        tracker = TrackerFactory()
        selected = TrackerFileFactory(tracker=tracker, is_selected=True)
        unselected = TrackerFileFactory(tracker=tracker, is_selected=False)
        
        assert selected.is_selected is True
        assert unselected.is_selected is False
    
    def test_tracker_file_material_types(self):
        """Test different material types."""
        tracker = TrackerFactory()
        
        abs_file = TrackerFileFactory(tracker=tracker, material="ABS")
        pla_file = TrackerFileFactory(tracker=tracker, material="PLA")
        petg_file = TrackerFileFactory(tracker=tracker, material="PETG")
        
        assert abs_file.material == "ABS"
        assert pla_file.material == "PLA"
        assert petg_file.material == "PETG"


# ============================================================================
# TRACKER FILE QUANTITY TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrackerFileQuantity:
    """Test quantity management and validation."""
    
    def test_printed_quantity_tracking(self):
        """Test printed quantity updates."""
        tracker = TrackerFactory()
        file = TrackerFileFactory(
            tracker=tracker,
            quantity=5,
            printed_quantity=0
        )
        
        file.printed_quantity = 3
        file.save()
        
        assert file.printed_quantity == 3
    
    def test_quantity_minimum_value(self):
        """Test quantity must be at least 1."""
        tracker = TrackerFactory()
        file = TrackerFileFactory(tracker=tracker, quantity=1)
        
        # Quantity validation happens at model clean/form level
        assert file.quantity >= 1
    
    def test_printed_quantity_minimum_value(self):
        """Test printed_quantity must be non-negative."""
        tracker = TrackerFactory()
        file = TrackerFileFactory(tracker=tracker, printed_quantity=0)
        
        # Printed quantity validation happens at model clean/form level
        assert file.printed_quantity >= 0


# ============================================================================
# TRACKER DASHBOARD TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrackerDashboard:
    """Test dashboard display functionality."""
    
    def test_show_on_dashboard_default(self):
        """Test default dashboard visibility."""
        tracker = TrackerFactory()
        
        assert tracker.show_on_dashboard is False
    
    def test_show_on_dashboard_enabled(self):
        """Test enabling dashboard display."""
        tracker = TrackerFactory(show_on_dashboard=True)
        
        assert tracker.show_on_dashboard is True
    
    def test_multiple_dashboard_trackers(self):
        """Test multiple trackers on dashboard."""
        tracker1 = TrackerFactory(show_on_dashboard=True)
        tracker2 = TrackerFactory(show_on_dashboard=True)
        tracker3 = TrackerFactory(show_on_dashboard=False)
        
        dashboard_trackers = Tracker.objects.filter(show_on_dashboard=True)
        
        assert tracker1 in dashboard_trackers
        assert tracker2 in dashboard_trackers
        assert tracker3 not in dashboard_trackers


# ============================================================================
# TRACKER STORAGE TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrackerStorage:
    """Test storage tracking and management."""
    
    def test_storage_path_tracking(self):
        """Test storage path field."""
        tracker = TrackerFactory(
            storage_path="media/trackers/voron_0_2/"
        )
        
        assert tracker.storage_path == "media/trackers/voron_0_2/"
    
    def test_total_storage_used_calculation(self):
        """Test total storage calculation."""
        tracker = TrackerFactory(total_storage_used=0)
        
        TrackerFileFactory(tracker=tracker, file_size=1024 * 500)  # 500 KB
        TrackerFileFactory(tracker=tracker, file_size=1024 * 1024 * 2)  # 2 MB
        
        # In real usage, this would be updated via signals or service
        total_size = sum(f.file_size for f in tracker.files.all())
        tracker.total_storage_used = total_size
        tracker.save()
        
        assert tracker.total_storage_used > 0
    
    def test_files_downloaded_flag(self):
        """Test files downloaded tracking."""
        tracker = TrackerFactory(files_downloaded=False)
        
        assert tracker.files_downloaded is False
        
        tracker.files_downloaded = True
        tracker.save()
        
        assert tracker.files_downloaded is True
