"""
Tests for MaterialFeature ViewSet API endpoints.

Tests CRUD operations for MaterialFeature and filtering FilamentSpools by feature.
Uses pytest-django and factory-boy for efficient test setup.
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from inventory.models import MaterialFeature, Material
from inventory.tests.factories import (
    FilamentSpoolFactory,
    BrandFactory
)


@pytest.fixture
def api_client():
    """Provide an API client for making requests."""
    return APIClient()


@pytest.fixture
def sample_features(db):
    """Create sample features for testing."""
    feature_matte = MaterialFeature.objects.create(name="Matte")
    feature_silk = MaterialFeature.objects.create(name="Silk")
    feature_highspeed = MaterialFeature.objects.create(name="High Speed")
    feature_uv = MaterialFeature.objects.create(name="UV Resistant")
    
    return {
        'matte': feature_matte,
        'silk': feature_silk,
        'highspeed': feature_highspeed,
        'uv': feature_uv,
        'all': [feature_matte, feature_silk, feature_highspeed, feature_uv]
    }


@pytest.fixture
def materials_with_features(db, sample_features):
    """Create materials with features attached."""
    brand = BrandFactory(name="Test Brand")
    
    # Generic PLA as base material
    pla, _ = Material.objects.get_or_create(name='PLA', defaults={'is_generic': True})
    
    # Material with matte feature
    mat_matte = Material.objects.create(
        name="Matte PLA Black",
        is_generic=False,
        brand=brand,
        base_material=pla,
        diameter="1.75"
    )
    mat_matte.features.add(sample_features['matte'])
    
    # Material with silk feature
    mat_silk = Material.objects.create(
        name="Silk PLA Gold",
        is_generic=False,
        brand=brand,
        base_material=pla,
        diameter="1.75"
    )
    mat_silk.features.add(sample_features['silk'])
    
    # Material with multiple features
    mat_multi = Material.objects.create(
        name="High Speed Matte PLA",
        is_generic=False,
        brand=brand,
        base_material=pla,
        diameter="1.75"
    )
    mat_multi.features.add(sample_features['matte'], sample_features['highspeed'])
    
    # Material with no features
    mat_basic = Material.objects.create(
        name="Basic PLA White",
        is_generic=False,
        brand=brand,
        base_material=pla,
        diameter="1.75"
    )
    
    return {
        'matte': mat_matte,
        'silk': mat_silk,
        'multi': mat_multi,
        'basic': mat_basic,
        'brand': brand,
        'base_material': pla
    }


# ============================================================================
# CRUD OPERATION TESTS
# ============================================================================

@pytest.mark.django_db
class TestMaterialFeatureCRUD:
    """Test Create, Read, Update, Delete operations for MaterialFeature."""
    
    def test_list_features_empty(self, api_client, db):
        """Test listing features when none exist."""
        url = '/api/material-features/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0
    
    def test_list_features(self, api_client, sample_features):
        """Test listing all features."""
        url = '/api/material-features/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 4
        
        # Should be ordered alphabetically
        names = [f['name'] for f in response.data]
        assert names == ['High Speed', 'Matte', 'Silk', 'UV Resistant']
    
    def test_create_feature(self, api_client, db):
        """Test creating a new feature."""
        url = '/api/material-features/'
        data = {'name': 'Glow in Dark'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Glow in Dark'
        assert 'id' in response.data
        
        # Verify in database
        assert MaterialFeature.objects.filter(name='Glow in Dark').exists()
    
    def test_create_feature_duplicate_name(self, api_client, sample_features):
        """Test creating a feature with duplicate name fails."""
        url = '/api/material-features/'
        data = {'name': 'Matte'}  # Already exists
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_feature_empty_name(self, api_client, db):
        """Test creating a feature with empty name fails."""
        url = '/api/material-features/'
        data = {'name': ''}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_retrieve_feature(self, api_client, sample_features):
        """Test retrieving a single feature by ID."""
        feature = sample_features['matte']
        url = f'/api/material-features/{feature.id}/'
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == feature.id
        assert response.data['name'] == 'Matte'
    
    def test_retrieve_feature_not_found(self, api_client, db):
        """Test retrieving a non-existent feature returns 404."""
        url = '/api/material-features/99999/'
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_feature(self, api_client, sample_features):
        """Test updating a feature name."""
        feature = sample_features['silk']
        url = f'/api/material-features/{feature.id}/'
        data = {'name': 'Silk Finish'}
        
        response = api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Silk Finish'
        
        # Verify in database
        feature.refresh_from_db()
        assert feature.name == 'Silk Finish'
    
    def test_update_feature_duplicate_name(self, api_client, sample_features):
        """Test updating feature to duplicate name fails."""
        feature = sample_features['silk']
        url = f'/api/material-features/{feature.id}/'
        data = {'name': 'Matte'}  # Already exists
        
        response = api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_partial_update_feature(self, api_client, sample_features):
        """Test PATCH update on a feature."""
        feature = sample_features['uv']
        url = f'/api/material-features/{feature.id}/'
        data = {'name': 'UV Protection'}
        
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'UV Protection'
    
    def test_delete_feature(self, api_client, sample_features):
        """Test deleting a feature."""
        feature = sample_features['uv']
        feature_id = feature.id
        url = f'/api/material-features/{feature.id}/'
        
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not MaterialFeature.objects.filter(id=feature_id).exists()
    
    def test_delete_feature_removes_from_materials(self, api_client, materials_with_features, sample_features):
        """Test that deleting a feature removes it from associated materials."""
        mat_multi = materials_with_features['multi']
        feature_matte = sample_features['matte']
        
        # Verify material has the feature
        assert mat_multi.features.count() == 2
        assert feature_matte in mat_multi.features.all()
        
        # Delete the feature
        url = f'/api/material-features/{feature_matte.id}/'
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify feature is removed from material
        mat_multi.refresh_from_db()
        assert mat_multi.features.count() == 1
        assert feature_matte.id not in [f.id for f in mat_multi.features.all()]


# ============================================================================
# FILTER TESTS - Filtering spools by feature
# ============================================================================

@pytest.mark.django_db
class TestFilamentSpoolFeatureFilter:
    """Test filtering FilamentSpools by material feature."""
    
    @pytest.fixture
    def spools_with_features(self, materials_with_features, sample_features):
        """Create spools linked to materials with features."""
        # Spool with matte material
        spool_matte = FilamentSpoolFactory(
            filament_type=materials_with_features['matte'],
            quantity=2,
            is_opened=False,
            status='new'
        )
        
        # Spool with silk material
        spool_silk = FilamentSpoolFactory(
            filament_type=materials_with_features['silk'],
            quantity=1,
            is_opened=True,
            status='opened'
        )
        
        # Spool with multi-feature material (matte + high speed)
        spool_multi = FilamentSpoolFactory(
            filament_type=materials_with_features['multi'],
            quantity=1,
            is_opened=True,
            status='in_use'
        )
        
        # Spool with basic material (no features)
        spool_basic = FilamentSpoolFactory(
            filament_type=materials_with_features['basic'],
            quantity=3,
            is_opened=False,
            status='new'
        )
        
        return {
            'matte': spool_matte,
            'silk': spool_silk,
            'multi': spool_multi,
            'basic': spool_basic,
            'all': [spool_matte, spool_silk, spool_multi, spool_basic]
        }
    
    def test_filter_by_feature_single(self, api_client, spools_with_features, sample_features):
        """Test filtering spools by a single feature."""
        url = f'/api/filament-spools/?feature={sample_features["silk"].id}'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['id'] == spools_with_features['silk'].id
    
    def test_filter_by_feature_multiple_matches(self, api_client, spools_with_features, sample_features):
        """Test filtering by feature that matches multiple spools."""
        # Matte feature should match both spool_matte and spool_multi
        url = f'/api/filament-spools/?feature={sample_features["matte"].id}'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        
        spool_ids = [s['id'] for s in response.data]
        assert spools_with_features['matte'].id in spool_ids
        assert spools_with_features['multi'].id in spool_ids
    
    def test_filter_by_feature_no_matches(self, api_client, spools_with_features, sample_features):
        """Test filtering by feature with no matching spools."""
        # UV feature is not assigned to any material with spools
        url = f'/api/filament-spools/?feature={sample_features["uv"].id}'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0
    
    def test_filter_by_feature_combined_with_status(self, api_client, spools_with_features, sample_features):
        """Test combining feature filter with status filter."""
        # Matte feature + opened status
        url = f'/api/filament-spools/?feature={sample_features["matte"].id}&status=new'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['id'] == spools_with_features['matte'].id
    
    def test_filter_by_feature_invalid_id(self, api_client, spools_with_features):
        """Test filtering by invalid feature ID returns empty results."""
        url = '/api/filament-spools/?feature=99999'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0


# ============================================================================
# MATERIAL SERIALIZER - Features in response
# ============================================================================

@pytest.mark.django_db
class TestMaterialFeaturesInResponse:
    """Test that features are properly included in Material responses."""
    
    def test_material_list_includes_features(self, api_client, materials_with_features, sample_features):
        """Test that material list includes features array."""
        url = '/api/materials/?type=blueprint'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Handle both paginated and non-paginated responses
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        
        # Find the multi-feature material
        mat_multi_data = next(
            (m for m in results if m['name'] == 'High Speed Matte PLA'),
            None
        )
        
        assert mat_multi_data is not None
        assert 'features' in mat_multi_data
        assert len(mat_multi_data['features']) == 2
        
        feature_names = [f['name'] for f in mat_multi_data['features']]
        assert 'Matte' in feature_names
        assert 'High Speed' in feature_names
    
    def test_material_detail_includes_features(self, api_client, materials_with_features, sample_features):
        """Test that material detail includes features array."""
        mat_silk = materials_with_features['silk']
        url = f'/api/materials/{mat_silk.id}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'features' in response.data
        assert len(response.data['features']) == 1
        assert response.data['features'][0]['name'] == 'Silk'
    
    def test_material_with_no_features(self, api_client, materials_with_features):
        """Test that material without features returns empty array."""
        mat_basic = materials_with_features['basic']
        url = f'/api/materials/{mat_basic.id}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'features' in response.data
        assert len(response.data['features']) == 0


# ============================================================================
# FILAMENT SPOOL - Features in filament_type
# ============================================================================

@pytest.mark.django_db
class TestFilamentSpoolFeaturesInResponse:
    """Test that features are properly included in FilamentSpool filament_type."""
    
    def test_spool_detail_includes_features(self, api_client, materials_with_features, sample_features):
        """Test that spool detail includes features in filament_type."""
        spool = FilamentSpoolFactory(
            filament_type=materials_with_features['multi']
        )
        
        url = f'/api/filament-spools/{spool.id}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'filament_type' in response.data
        assert 'features' in response.data['filament_type']
        
        features = response.data['filament_type']['features']
        assert len(features) == 2
        
        feature_names = [f['name'] for f in features]
        assert 'Matte' in feature_names
        assert 'High Speed' in feature_names
    
    def test_spool_list_includes_features(self, api_client, materials_with_features, sample_features):
        """Test that spool list includes features in filament_type."""
        FilamentSpoolFactory(filament_type=materials_with_features['silk'])
        FilamentSpoolFactory(filament_type=materials_with_features['basic'])
        
        url = '/api/filament-spools/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Find the silk spool
        silk_spool_data = next(
            (s for s in response.data if s['filament_type']['name'] == 'Silk PLA Gold'),
            None
        )
        
        assert silk_spool_data is not None
        assert 'features' in silk_spool_data['filament_type']
        assert len(silk_spool_data['filament_type']['features']) == 1
        assert silk_spool_data['filament_type']['features'][0]['name'] == 'Silk'
