"""
Test suite for FilamentSpoolSerializer.

This serializer is complex with:
- Dual mode support (Blueprint vs Quick Add)
- Nested read-only serializers (filament_type, location, assigned_printer, project)
- Computed read-only fields (is_quick_add, display_name, weight_remaining_percent)
- Custom create() and update() methods
- Standalone fields for Quick Add mode

Coverage targets:
- Field serialization for both modes
- Nested object serialization
- Computed field calculations
- Create in Blueprint mode
- Create in Quick Add mode
- Update operations
- Validation logic
"""

import pytest
from decimal import Decimal
from rest_framework.test import APIRequestFactory
from inventory.models import Material, FilamentSpool
from inventory.serializers import FilamentSpoolSerializer
from inventory.tests.factories import (
    FilamentSpoolFactory,
    QuickAddSpoolFactory,
    FilamentBlueprintMaterialFactory,
    BrandFactory,
    LocationFactory,
    PrinterFactory,
    ProjectFactory
)


@pytest.fixture
def generic_pla(db):
    """Get or create a generic PLA material type."""
    pla, _ = Material.objects.get_or_create(name='PLA', defaults={'is_generic': True})
    return pla


@pytest.fixture
def blueprint_material(db, generic_pla):
    """Create a filament blueprint material."""
    brand = BrandFactory(name="Polymaker")
    material, _ = Material.objects.get_or_create(
        name="PolyTerra PLA",
        defaults={
            "is_generic": False,
            "brand": brand,
            "base_material": generic_pla,
            "diameter": "1.75",
            "spool_weight": 1000,
            "price_per_spool": Decimal("24.99")
        }
    )
    return material


@pytest.mark.django_db
class TestFilamentSpoolSerializerRead:
    """Test FilamentSpoolSerializer read operations (serialization)."""

    def test_serializer_fields_blueprint_mode(self, blueprint_material):
        """Verify serializer includes all expected fields for blueprint spool."""
        location = LocationFactory(name="Rack A")
        spool = FilamentSpoolFactory(
            filament_type=blueprint_material,
            location=location,
            initial_weight=1000,
            current_weight=750
        )
        serializer = FilamentSpoolSerializer(spool)
        
        # Check key fields are present
        assert 'id' in serializer.data
        assert 'filament_type' in serializer.data
        assert 'is_quick_add' in serializer.data
        assert 'display_name' in serializer.data
        assert 'weight_remaining_percent' in serializer.data
        assert 'quantity' in serializer.data
        assert 'is_opened' in serializer.data
        assert 'initial_weight' in serializer.data
        assert 'current_weight' in serializer.data
        assert 'location' in serializer.data
        assert 'status' in serializer.data
        assert 'price_paid' in serializer.data
        
        # Check computed fields
        assert serializer.data['is_quick_add'] == False
        assert serializer.data['weight_remaining_percent'] == 75.0

    def test_serializer_fields_quick_add_mode(self, generic_pla):
        """Verify serializer includes all expected fields for Quick Add spool."""
        brand = BrandFactory(name="Unknown")
        spool = QuickAddSpoolFactory(
            standalone_name="Convention Special",
            standalone_brand=brand,
            standalone_material_type=generic_pla,
            standalone_colors=["#FF0000", "#00FF00"],
            standalone_color_family="multi",
            initial_weight=750,
            current_weight=500,
            price_paid=Decimal("15.00")
        )
        serializer = FilamentSpoolSerializer(spool)
        
        # Check Quick Add specific fields
        assert serializer.data['is_quick_add'] == True
        assert serializer.data['standalone_name'] == "Convention Special"
        assert serializer.data['standalone_colors'] == ["#FF0000", "#00FF00"]
        assert serializer.data['standalone_color_family'] == "multi"
        assert serializer.data['display_name'] == "Convention Special"
        assert serializer.data['price_paid'] == "15.00"

    def test_nested_filament_type_serialization(self, blueprint_material):
        """Test that filament_type is properly nested with brand info."""
        spool = FilamentSpoolFactory(filament_type=blueprint_material)
        serializer = FilamentSpoolSerializer(spool)
        
        filament_type_data = serializer.data['filament_type']
        assert filament_type_data is not None
        assert filament_type_data['name'] == "PolyTerra PLA"
        assert filament_type_data['brand']['name'] == "Polymaker"

    def test_nested_location_serialization(self, blueprint_material):
        """Test that location is properly nested."""
        location = LocationFactory(name="Dry Box 1")
        spool = FilamentSpoolFactory(
            filament_type=blueprint_material,
            location=location
        )
        serializer = FilamentSpoolSerializer(spool)
        
        assert serializer.data['location']['name'] == "Dry Box 1"

    def test_nested_printer_serialization(self, blueprint_material):
        """Test that assigned_printer is properly nested."""
        printer = PrinterFactory(title="Prusa MK4")
        spool = FilamentSpoolFactory(
            filament_type=blueprint_material,
            assigned_printer=printer,
            is_opened=True,
            status='in_use'
        )
        serializer = FilamentSpoolSerializer(spool)
        
        assert serializer.data['assigned_printer']['title'] == "Prusa MK4"

    def test_null_relations(self, blueprint_material):
        """Test serialization with null optional relationships."""
        spool = FilamentSpoolFactory(
            filament_type=blueprint_material,
            location=None,
            assigned_printer=None,
            project=None
        )
        serializer = FilamentSpoolSerializer(spool)
        
        assert serializer.data['location'] is None
        assert serializer.data['assigned_printer'] is None
        assert serializer.data['project'] is None


@pytest.mark.django_db
class TestFilamentSpoolSerializerComputedFields:
    """Test computed/read-only fields."""

    def test_weight_remaining_percent_full(self, blueprint_material):
        """Test weight percent when spool is full."""
        spool = FilamentSpoolFactory(
            filament_type=blueprint_material,
            initial_weight=1000,
            current_weight=1000
        )
        serializer = FilamentSpoolSerializer(spool)
        
        assert serializer.data['weight_remaining_percent'] == 100.0

    def test_weight_remaining_percent_partial(self, blueprint_material):
        """Test weight percent when spool is partially used."""
        spool = FilamentSpoolFactory(
            filament_type=blueprint_material,
            initial_weight=1000,
            current_weight=300
        )
        serializer = FilamentSpoolSerializer(spool)
        
        assert serializer.data['weight_remaining_percent'] == 30.0

    def test_weight_remaining_percent_empty(self, blueprint_material):
        """Test weight percent when spool is empty."""
        spool = FilamentSpoolFactory(
            filament_type=blueprint_material,
            initial_weight=1000,
            current_weight=0,
            is_opened=True,
            status='empty'
        )
        serializer = FilamentSpoolSerializer(spool)
        
        assert serializer.data['weight_remaining_percent'] == 0.0

    def test_display_name_blueprint(self, blueprint_material):
        """Test display_name uses filament_type str for blueprint spools."""
        spool = FilamentSpoolFactory(filament_type=blueprint_material)
        serializer = FilamentSpoolSerializer(spool)
        
        # Should contain the material name from blueprint
        assert "PolyTerra" in serializer.data['display_name']

    def test_display_name_quick_add(self, generic_pla):
        """Test display_name uses standalone_name for Quick Add spools."""
        spool = QuickAddSpoolFactory(
            standalone_name="My Custom Filament",
            standalone_material_type=generic_pla
        )
        serializer = FilamentSpoolSerializer(spool)
        
        assert serializer.data['display_name'] == "My Custom Filament"

    def test_is_quick_add_true(self, generic_pla):
        """Test is_quick_add is True when filament_type is None."""
        spool = QuickAddSpoolFactory(standalone_material_type=generic_pla)
        serializer = FilamentSpoolSerializer(spool)
        
        assert serializer.data['is_quick_add'] == True
        assert serializer.data['filament_type'] is None

    def test_is_quick_add_false(self, blueprint_material):
        """Test is_quick_add is False when filament_type is set."""
        spool = FilamentSpoolFactory(filament_type=blueprint_material)
        serializer = FilamentSpoolSerializer(spool)
        
        assert serializer.data['is_quick_add'] == False
        assert serializer.data['filament_type'] is not None


class MockRequest:
    """Mock request object for serializer context."""
    def __init__(self, data):
        self.data = data
    
    def build_absolute_uri(self, url):
        return f"http://testserver{url}"


@pytest.mark.django_db
class TestFilamentSpoolSerializerWrite:
    """Test FilamentSpoolSerializer write operations (deserialization)."""

    def test_create_blueprint_spool(self, blueprint_material):
        """Test creating a blueprint-based spool via serializer."""
        location = LocationFactory()
        
        data = {
            'filament_type_id': blueprint_material.pk,
            'quantity': 2,
            'is_opened': False,
            'initial_weight': 1000,
            'current_weight': 1000,
            'location': {'name': location.name},
            'status': 'new'
        }
        
        # Serializer requires request context for create/update
        mock_request = MockRequest(data)
        serializer = FilamentSpoolSerializer(data=data, context={'request': mock_request})
        assert serializer.is_valid(), serializer.errors
        
        spool = serializer.save()
        assert spool.filament_type == blueprint_material
        assert spool.quantity == 2
        assert spool.is_opened == False

    def test_create_quick_add_spool(self, generic_pla):
        """Test creating a Quick Add spool via serializer."""
        brand = BrandFactory(name="Test Brand")
        
        data = {
            'is_quick_add': True,  # Flag required for Quick Add mode
            'standalone_name': 'Test Quick Add Spool',
            'standalone_brand': {'name': brand.name},
            'standalone_material_type_id': generic_pla.pk,
            'standalone_colors': ['#123456'],
            'standalone_color_family': 'blue',
            'quantity': 1,
            'is_opened': False,
            'initial_weight': 800,
            'current_weight': 800,
            'status': 'new',
            'price_paid': '19.99'
        }
        
        mock_request = MockRequest(data)
        serializer = FilamentSpoolSerializer(data=data, context={'request': mock_request})
        assert serializer.is_valid(), serializer.errors
        
        spool = serializer.save()
        assert spool.filament_type is None
        assert spool.is_quick_add == True
        assert spool.standalone_name == 'Test Quick Add Spool'
        assert spool.standalone_colors == ['#123456']

    def test_update_weight(self, blueprint_material):
        """Test updating spool weight via serializer."""
        spool = FilamentSpoolFactory(
            filament_type=blueprint_material,
            initial_weight=1000,
            current_weight=1000,
            is_opened=True,
            status='opened'
        )
        
        data = {'current_weight': 600}
        mock_request = MockRequest(data)
        serializer = FilamentSpoolSerializer(spool, data=data, partial=True, context={'request': mock_request})
        assert serializer.is_valid(), serializer.errors
        
        updated_spool = serializer.save()
        assert updated_spool.current_weight == 600

    def test_update_location(self, blueprint_material):
        """Test updating spool location via serializer."""
        old_location = LocationFactory(name="Old Location")
        new_location = LocationFactory(name="New Location")
        
        spool = FilamentSpoolFactory(
            filament_type=blueprint_material,
            location=old_location
        )
        
        data = {'location_id': new_location.pk}
        mock_request = MockRequest(data)
        serializer = FilamentSpoolSerializer(spool, data=data, partial=True, context={'request': mock_request})
        assert serializer.is_valid(), serializer.errors
        
        updated_spool = serializer.save()
        assert updated_spool.location == new_location

    def test_update_price_paid(self, blueprint_material):
        """Test updating price_paid field."""
        spool = FilamentSpoolFactory(
            filament_type=blueprint_material,
            price_paid=None
        )
        
        data = {'price_paid': '22.50'}
        mock_request = MockRequest(data)
        serializer = FilamentSpoolSerializer(spool, data=data, partial=True, context={'request': mock_request})
        assert serializer.is_valid(), serializer.errors
        
        updated_spool = serializer.save()
        assert updated_spool.price_paid == Decimal('22.50')


@pytest.mark.django_db
class TestFilamentSpoolSerializerValidation:
    """Test validation logic in FilamentSpoolSerializer."""

    def test_initial_weight_required(self, blueprint_material):
        """Test that initial_weight is required."""
        data = {
            'filament_type_id': blueprint_material.pk,
            'quantity': 1,
            'is_opened': False,
            'current_weight': 1000,
            'status': 'new'
            # Missing initial_weight
        }
        
        serializer = FilamentSpoolSerializer(data=data)
        assert not serializer.is_valid()
        assert 'initial_weight' in serializer.errors

    def test_current_weight_required(self, blueprint_material):
        """Test that current_weight is required."""
        data = {
            'filament_type_id': blueprint_material.pk,
            'quantity': 1,
            'is_opened': False,
            'initial_weight': 1000,
            'status': 'new'
            # Missing current_weight
        }
        
        serializer = FilamentSpoolSerializer(data=data)
        assert not serializer.is_valid()
        assert 'current_weight' in serializer.errors

    def test_status_choices(self, blueprint_material):
        """Test that status must be a valid choice."""
        data = {
            'filament_type_id': blueprint_material.pk,
            'quantity': 1,
            'is_opened': False,
            'initial_weight': 1000,
            'current_weight': 1000,
            'status': 'invalid_status'
        }
        
        serializer = FilamentSpoolSerializer(data=data)
        assert not serializer.is_valid()
        assert 'status' in serializer.errors

    def test_standalone_color_family_accepts_any_value(self, generic_pla):
        """Test that standalone_color_family accepts any string (no validation on this field)."""
        brand = BrandFactory()
        data = {
            'is_quick_add': True,
            'standalone_name': 'Test',
            'standalone_brand': {'name': brand.name},
            'standalone_material_type_id': generic_pla.pk,
            'standalone_colors': ['#FF0000'],
            'standalone_color_family': 'custom_color_family',
            'quantity': 1,
            'is_opened': False,
            'initial_weight': 1000,
            'current_weight': 1000,
            'status': 'new'
        }
        
        mock_request = MockRequest(data)
        serializer = FilamentSpoolSerializer(data=data, context={'request': mock_request})
        # standalone_color_family is a free-text field, no validation
        assert serializer.is_valid(), serializer.errors
