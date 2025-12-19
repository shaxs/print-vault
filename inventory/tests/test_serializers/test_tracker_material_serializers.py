"""
Tests for Tracker serializer material blueprint enhancements.

Tests the new computed fields and material serialization:
- primary_material_display
- accent_material_display  
- materials_display (for TrackerFile)
"""
import pytest
from inventory.serializers import TrackerSerializer, TrackerFileSerializer
from inventory.tests.factories import (
    TrackerFactory, TrackerFileFactory, MaterialFactory, BrandFactory
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def blue_material(db):
    """Create a blue ABS material blueprint."""
    brand = BrandFactory(name="Polymaker")
    return MaterialFactory(
        name="Polymaker PolyLite ABS (Blue)",
        brand=brand,
        is_generic=False,
        colors=["#1E40AF", "#2563EB"]
    )


@pytest.fixture
def red_material(db):
    """Create a red ABS material blueprint."""
    return MaterialFactory(
        name="eSUN ABS+ (Red)",
        is_generic=False,
        colors=["#DC2626", "#EF4444"]
    )


# ============================================================================
# TRACKER SERIALIZER TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrackerSerializerMaterialDisplay:
    """Test TrackerSerializer material_display computed fields."""
    
    def test_primary_material_display_field(self, blue_material):
        """Test that primary_material_display returns full Material object."""
        tracker = TrackerFactory(primary_material=blue_material)
        serializer = TrackerSerializer(tracker)
        
        assert 'primary_material_display' in serializer.data
        material_data = serializer.data['primary_material_display']
        
        assert material_data is not None
        assert material_data['id'] == blue_material.id
        assert material_data['name'] == blue_material.name
        assert material_data['colors'] == ["#1E40AF", "#2563EB"]
    
    def test_accent_material_display_field(self, red_material):
        """Test that accent_material_display returns full Material object."""
        tracker = TrackerFactory(accent_material=red_material)
        serializer = TrackerSerializer(tracker)
        
        assert 'accent_material_display' in serializer.data
        material_data = serializer.data['accent_material_display']
        
        assert material_data is not None
        assert material_data['id'] == red_material.id
        assert material_data['name'] == red_material.name
        assert "#DC2626" in material_data['colors']
    
    def test_material_display_null_when_no_material(self):
        """Test that material_display fields are null when no material set."""
        tracker = TrackerFactory(
            primary_material=None,
            accent_material=None
        )
        serializer = TrackerSerializer(tracker)
        
        assert serializer.data['primary_material_display'] is None
        assert serializer.data['accent_material_display'] is None
    
    def test_both_materials_display(self, blue_material, red_material):
        """Test tracker with both primary and accent materials."""
        tracker = TrackerFactory(
            primary_material=blue_material,
            accent_material=red_material
        )
        serializer = TrackerSerializer(tracker)
        
        assert serializer.data['primary_material_display']['name'] == blue_material.name
        assert serializer.data['accent_material_display']['name'] == red_material.name
    
    def test_serializer_includes_material_fields(self):
        """Verify serializer includes all material-related fields."""
        tracker = TrackerFactory()
        serializer = TrackerSerializer(tracker)
        
        expected_material_fields = {
            'primary_material',
            'accent_material',
            'primary_material_display',
            'accent_material_display'
        }
        
        assert expected_material_fields.issubset(set(serializer.data.keys()))


@pytest.mark.django_db
class TestTrackerFileSerializerMaterialsDisplay:
    """Test TrackerFileSerializer materials_display computed field."""
    
    def test_materials_display_single_material(self, blue_material):
        """Test materials_display with single material ID."""
        tracker = TrackerFactory()
        file = TrackerFileFactory(
            tracker=tracker,
            material_ids=[blue_material.id]
        )
        
        serializer = TrackerFileSerializer(file)
        
        assert 'materials_display' in serializer.data
        materials = serializer.data['materials_display']
        
        assert len(materials) == 1
        assert materials[0]['id'] == blue_material.id
        assert materials[0]['name'] == blue_material.name
        assert materials[0]['colors'] == ["#1E40AF", "#2563EB"]
    
    def test_materials_display_multiple_materials(self, blue_material, red_material):
        """Test materials_display with multiple material IDs (multicolor)."""
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
        
        serializer = TrackerFileSerializer(file)
        materials = serializer.data['materials_display']
        
        assert len(materials) == 3
        material_names = [m['name'] for m in materials]
        assert blue_material.name in material_names
        assert red_material.name in material_names
        assert white_material.name in material_names
    
    def test_materials_display_empty_when_no_materials(self):
        """Test materials_display is empty array when no material_ids."""
        tracker = TrackerFactory()
        file = TrackerFileFactory(
            tracker=tracker,
            material_ids=[]
        )
        
        serializer = TrackerFileSerializer(file)
        
        assert serializer.data['materials_display'] == []
    
    def test_materials_display_ignores_invalid_ids(self, blue_material):
        """Test materials_display gracefully handles non-existent material IDs."""
        tracker = TrackerFactory()
        file = TrackerFileFactory(
            tracker=tracker,
            material_ids=[blue_material.id, 99999]  # 99999 doesn't exist
        )
        
        serializer = TrackerFileSerializer(file)
        materials = serializer.data['materials_display']
        
        # Should only include the valid material
        assert len(materials) == 1
        assert materials[0]['id'] == blue_material.id
    
    def test_serializer_includes_material_ids_field(self):
        """Verify serializer includes material_ids field."""
        file = TrackerFileFactory(material_ids=[])
        serializer = TrackerFileSerializer(file)
        
        assert 'material_ids' in serializer.data
        assert isinstance(serializer.data['material_ids'], list)


@pytest.mark.django_db
class TestBackwardCompatibility:
    """Test that legacy hex color fields still work alongside materials."""
    
    def test_tracker_serializer_includes_legacy_colors(self):
        """Test that primary_color and accent_color are still included."""
        tracker = TrackerFactory(
            primary_color="#1E40AF",
            accent_color="#DC2626"
        )
        serializer = TrackerSerializer(tracker)
        
        assert 'primary_color' in serializer.data
        assert 'accent_color' in serializer.data
        assert serializer.data['primary_color'] == "#1E40AF"
        assert serializer.data['accent_color'] == "#DC2626"
    
    def test_file_serializer_includes_legacy_material_field(self):
        """Test that legacy material string field is still included."""
        file = TrackerFileFactory(material="ABS")
        serializer = TrackerFileSerializer(file)
        
        assert 'material' in serializer.data
        assert serializer.data['material'] == "ABS"
