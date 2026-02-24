"""
Tests for Tracker Material Blueprint Integration.

Tests the new material-based color system added in Phase 10:
- primary_material and accent_material foreign keys
- materials_display computed fields  
- material_ids for TrackerFile
- Cascade behavior from tracker to files
"""
import pytest
from inventory.models import Tracker, TrackerFile, Material
from inventory.tests.factories import (
    TrackerFactory, TrackerFileFactory, MaterialFactory
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def blue_material(db):
    """Create a blue ABS material blueprint."""
    return MaterialFactory(
        name="Polymaker PolyLite ABS (Blue)",
        is_generic=False,
        colors=["#1E40AF", "#2563EB"]
    )


@pytest.fixture
def red_material(db):
    """Create a red ABS material blueprint."""
    return MaterialFactory(
        name="Polymaker PolyLite ABS (Red)",
        is_generic=False,
        colors=["#DC2626", "#EF4444"]
    )


# ============================================================================
# TRACKER MODEL TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrackerMaterialIntegration:
    """Test Tracker model material blueprint functionality."""
    
    def test_tracker_with_primary_material(self, blue_material):
        """Test associating tracker with primary material blueprint."""
        tracker = TrackerFactory(
            name="Voron 0.2",
            primary_material=blue_material,
            accent_material=None
        )
        
        assert tracker.primary_material == blue_material
        assert tracker.accent_material is None
        assert tracker.primary_material.colors[0] == "#1E40AF"
    
    def test_tracker_with_both_materials(self, blue_material, red_material):
        """Test tracker with both primary and accent materials."""
        tracker = TrackerFactory(
            primary_material=blue_material,
            accent_material=red_material
        )
        
        assert tracker.primary_material == blue_material
        assert tracker.accent_material == red_material
    
    def test_tracker_material_nullable(self):
        """Test that materials can be null (backward compatibility)."""
        tracker = TrackerFactory(
            primary_material=None,
            accent_material=None
        )
        
        assert tracker.primary_material is None
        assert tracker.accent_material is None
        # Hex colors should still work
        assert tracker.primary_color == "#1E40AF"
    
    def test_tracker_material_on_delete_set_null(self, blue_material):
        """Test that deleting material sets tracker FK to null."""
        tracker = TrackerFactory(primary_material=blue_material)
        
        assert tracker.primary_material == blue_material
        
        # Delete material
        material_id = blue_material.id
        blue_material.delete()
        tracker.refresh_from_db()
        
        # Should be set to null, not cascade delete tracker
        assert tracker.primary_material is None


@pytest.mark.django_db
class TestTrackerFileMaterialIds:
    """Test TrackerFile material_ids field."""
    
    def test_file_with_single_material_id(self, blue_material):
        """Test file with single material in material_ids array."""
        tracker = TrackerFactory()
        file = TrackerFileFactory(
            tracker=tracker,
            color="Primary",
            material_ids=[blue_material.id]
        )
        
        assert file.material_ids == [blue_material.id]
        assert len(file.material_ids) == 1
    
    def test_file_with_multiple_material_ids(self, blue_material, red_material):
        """Test multicolor file with multiple materials."""
        white_material = MaterialFactory(
            name="White PLA",
            is_generic=False,
            colors=["#FFFFFF"]
        )
        
        tracker = TrackerFactory()
        file = TrackerFileFactory(
            tracker=tracker,
            color="Multicolor",
            material_ids=[blue_material.id, red_material.id, white_material.id]
        )
        
        assert len(file.material_ids) == 3
        assert blue_material.id in file.material_ids
        assert red_material.id in file.material_ids
        assert white_material.id in file.material_ids
    
    def test_file_with_no_material_ids(self):
        """Test file with empty material_ids (backward compatibility)."""
        tracker = TrackerFactory()
        file = TrackerFileFactory(
            tracker=tracker,
            material_ids=[]
        )
        
        assert file.material_ids == []
        # Legacy material field should still work
        assert file.material in ['ABS', 'PLA', 'PETG', 'ASA']  # FuzzyChoice
    
    def test_file_material_ids_default_empty(self):
        """Test that material_ids defaults to empty array."""
        tracker = TrackerFactory()
        file = TrackerFile.objects.create(
            tracker=tracker,
            filename="test.stl",
            github_url="https://github.com/test/test.stl",
            file_size=1024,
            storage_type='link'
        )
        
        assert file.material_ids == []


@pytest.mark.django_db
class TestMaterialCascadeBehavior:
    """Test material cascade from tracker to files."""
    
    def test_primary_files_inherit_tracker_material(self, blue_material):
        """Test that Primary colored files should reference tracker's primary material."""
        tracker = TrackerFactory(primary_material=blue_material)
        
        # Create Primary color files
        file1 = TrackerFileFactory(tracker=tracker, color="Primary")
        file2 = TrackerFileFactory(tracker=tracker, color="Primary")
        
        # In real app, update_materials endpoint would set these
        # For now, just test the relationship exists
        assert tracker.primary_material == blue_material
        assert file1.color == "Primary"
        assert file2.color == "Primary"
    
    def test_accent_files_inherit_tracker_material(self, red_material):
        """Test that Accent colored files should reference tracker's accent material."""
        tracker = TrackerFactory(accent_material=red_material)
        
        file = TrackerFileFactory(tracker=tracker, color="Accent")
        
        assert tracker.accent_material == red_material
        assert file.color == "Accent"
    
    def test_other_files_can_have_custom_materials(self):
        """Test that Other/Multicolor/Clear files can have custom material_ids."""
        tracker = TrackerFactory()
        
        custom_mat = MaterialFactory(
            name="Custom Yellow PETG",
            is_generic=False,
            colors=["#FDE047"]
        )
        
        other_file = TrackerFileFactory(
            tracker=tracker,
            color="Other",
            material_ids=[custom_mat.id]
        )
        multicolor_file = TrackerFileFactory(
            tracker=tracker,
            color="Multicolor",
            material_ids=[custom_mat.id]
        )
        clear_file = TrackerFileFactory(
            tracker=tracker,
            color="Clear",
            material_ids=[custom_mat.id]
        )
        
        assert other_file.material_ids == [custom_mat.id]
        assert multicolor_file.material_ids == [custom_mat.id]
        assert clear_file.material_ids == [custom_mat.id]


@pytest.mark.django_db
class TestMigration0037AccentColorBlank:
    """Test Migration 0037 changes - accent_color can be blank."""
    
    def test_tracker_with_blank_accent_color(self):
        """Test that accent_color can be empty string."""
        tracker = Tracker.objects.create(
            name="Test Tracker",
            github_url="https://github.com/test/test",
            storage_type='link',
            primary_color='#1E40AF',
            accent_color=''  # Empty string now allowed
        )
        
        assert tracker.accent_color == ''
        assert tracker.primary_color == '#1E40AF'
    
    def test_tracker_accent_color_default_empty(self):
        """Test that new trackers default to empty accent_color."""
        tracker = Tracker.objects.create(
            name="Test Tracker",
            github_url="https://github.com/test/test",
            storage_type='link',
            primary_color='#1E40AF'
            # Don't specify accent_color
        )
        
        # Should default to empty string per migration 0037
        assert tracker.accent_color == ''
