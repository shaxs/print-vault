"""
Test suite for MaterialFeature serializer and features handling in MaterialSerializer.

Tests:
- MaterialFeatureSerializer field serialization
- MaterialSerializer features array in response
- FilamentSpoolSerializer features inclusion in filament_type

Note: Create and update operations with features are tested in API tests
(test_views/test_material_feature_viewset.py) which provide proper DRF Request
objects through the APIClient.

Coverage targets:
- Field serialization
- Features in Material responses
- Features in FilamentSpool filament_type responses
"""

import pytest
from inventory.serializers import (
    MaterialFeatureSerializer,
    MaterialSerializer,
    FilamentSpoolSerializer
)
from inventory.models import MaterialFeature, Material
from inventory.tests.factories import (
    BrandFactory,
    FilamentSpoolFactory,
    FilamentBlueprintMaterialFactory
)


@pytest.fixture
def generic_pla(db):
    """Get or create a generic PLA material."""
    pla, _ = Material.objects.get_or_create(name='PLA', defaults={'is_generic': True})
    return pla


# ============================================================================
# MATERIAL FEATURE SERIALIZER TESTS
# ============================================================================

@pytest.mark.django_db
class TestMaterialFeatureSerializer:
    """Test MaterialFeatureSerializer serialization."""
    
    def test_serializer_fields(self):
        """Verify serializer includes correct fields."""
        feature = MaterialFeature.objects.create(name="Matte")
        serializer = MaterialFeatureSerializer(feature)
        
        assert 'id' in serializer.data
        assert 'name' in serializer.data
        assert len(serializer.data) == 2
    
    def test_serialize_single_feature(self):
        """Test serializing a single MaterialFeature instance."""
        feature = MaterialFeature.objects.create(name="Silk Finish")
        serializer = MaterialFeatureSerializer(feature)
        
        assert serializer.data['id'] == feature.id
        assert serializer.data['name'] == "Silk Finish"
    
    def test_serialize_multiple_features(self):
        """Test serializing multiple MaterialFeature instances."""
        features = [
            MaterialFeature.objects.create(name="Matte"),
            MaterialFeature.objects.create(name="Silk"),
            MaterialFeature.objects.create(name="High Speed")
        ]
        # Query to get ordered features
        ordered_features = MaterialFeature.objects.all()
        serializer = MaterialFeatureSerializer(ordered_features, many=True)
        
        assert len(serializer.data) == 3
        # Should be ordered alphabetically
        names = [f['name'] for f in serializer.data]
        assert names == ['High Speed', 'Matte', 'Silk']
    
    def test_deserialize_valid_data(self):
        """Test deserializing valid feature data."""
        data = {'name': 'UV Resistant'}
        serializer = MaterialFeatureSerializer(data=data)
        
        assert serializer.is_valid()
        feature = serializer.save()
        assert feature.name == 'UV Resistant'
    
    def test_deserialize_empty_name_fails(self):
        """Test that empty name fails validation."""
        data = {'name': ''}
        serializer = MaterialFeatureSerializer(data=data)
        
        assert not serializer.is_valid()
        assert 'name' in serializer.errors
    
    def test_deserialize_duplicate_name_fails(self):
        """Test that duplicate name fails validation."""
        MaterialFeature.objects.create(name="Matte")
        data = {'name': 'Matte'}
        serializer = MaterialFeatureSerializer(data=data)
        
        assert not serializer.is_valid()
        assert 'name' in serializer.errors


# ============================================================================
# MATERIAL SERIALIZER - FEATURES IN RESPONSE
# ============================================================================

@pytest.mark.django_db
class TestMaterialSerializerFeaturesResponse:
    """Test MaterialSerializer features array in response."""
    
    def test_material_includes_features_array(self, generic_pla):
        """Test that serialized material includes features array."""
        brand = BrandFactory()
        material = Material.objects.create(
            name="Test Material",
            is_generic=False,
            brand=brand,
            base_material=generic_pla
        )
        
        serializer = MaterialSerializer(material)
        
        assert 'features' in serializer.data
        assert isinstance(serializer.data['features'], list)
    
    def test_material_with_no_features(self, generic_pla):
        """Test that material with no features has empty array."""
        brand = BrandFactory()
        material = Material.objects.create(
            name="Basic Material",
            is_generic=False,
            brand=brand,
            base_material=generic_pla
        )
        
        serializer = MaterialSerializer(material)
        
        assert serializer.data['features'] == []
    
    def test_material_with_single_feature(self, generic_pla):
        """Test that material with one feature shows in array."""
        brand = BrandFactory()
        feature = MaterialFeature.objects.create(name="Matte")
        material = Material.objects.create(
            name="Matte Material",
            is_generic=False,
            brand=brand,
            base_material=generic_pla
        )
        material.features.add(feature)
        
        serializer = MaterialSerializer(material)
        
        assert len(serializer.data['features']) == 1
        assert serializer.data['features'][0]['name'] == 'Matte'
    
    def test_material_with_multiple_features(self, generic_pla):
        """Test that material with multiple features shows all in array."""
        brand = BrandFactory()
        feature_matte = MaterialFeature.objects.create(name="Matte")
        feature_highspeed = MaterialFeature.objects.create(name="High Speed")
        material = Material.objects.create(
            name="Multi-Feature Material",
            is_generic=False,
            brand=brand,
            base_material=generic_pla
        )
        material.features.add(feature_matte, feature_highspeed)
        
        serializer = MaterialSerializer(material)
        
        assert len(serializer.data['features']) == 2
        feature_names = [f['name'] for f in serializer.data['features']]
        assert 'Matte' in feature_names
        assert 'High Speed' in feature_names


# ============================================================================
# Note: Create and Update with features are tested in API tests
# (test_views/test_material_feature_viewset.py) which provide proper
# DRF Request objects through the APIClient. Direct serializer tests
# for create/update would require mocking request.data which is already
# covered by the integration tests.
# ============================================================================


# ============================================================================
# FILAMENT SPOOL SERIALIZER - FEATURES IN FILAMENT_TYPE
# ============================================================================

@pytest.mark.django_db
class TestFilamentSpoolSerializerFeatures:
    """Test FilamentSpoolSerializer includes features in filament_type."""
    
    def test_spool_filament_type_includes_features(self):
        """Test that spool's filament_type includes features array."""
        feature = MaterialFeature.objects.create(name="Silk")
        blueprint = FilamentBlueprintMaterialFactory()
        blueprint.features.add(feature)
        
        spool = FilamentSpoolFactory(filament_type=blueprint)
        
        serializer = FilamentSpoolSerializer(spool)
        
        assert 'filament_type' in serializer.data
        assert 'features' in serializer.data['filament_type']
        assert len(serializer.data['filament_type']['features']) == 1
        assert serializer.data['filament_type']['features'][0]['name'] == 'Silk'
    
    def test_spool_filament_type_no_features(self):
        """Test spool with blueprint that has no features."""
        blueprint = FilamentBlueprintMaterialFactory()
        spool = FilamentSpoolFactory(filament_type=blueprint)
        
        serializer = FilamentSpoolSerializer(spool)
        
        assert 'filament_type' in serializer.data
        assert 'features' in serializer.data['filament_type']
        assert serializer.data['filament_type']['features'] == []
    
    def test_spool_filament_type_multiple_features(self):
        """Test spool with blueprint that has multiple features."""
        feature1 = MaterialFeature.objects.create(name="Matte")
        feature2 = MaterialFeature.objects.create(name="High Speed")
        blueprint = FilamentBlueprintMaterialFactory()
        blueprint.features.add(feature1, feature2)
        
        spool = FilamentSpoolFactory(filament_type=blueprint)
        
        serializer = FilamentSpoolSerializer(spool)
        
        assert len(serializer.data['filament_type']['features']) == 2
        feature_names = [f['name'] for f in serializer.data['filament_type']['features']]
        assert 'Matte' in feature_names
        assert 'High Speed' in feature_names
