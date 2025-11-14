"""
Test suite for simple lookup serializers (Brand, PartType, Location, Material, Vendor).

These serializers are simple read-only representations of lookup models
with only id and name fields.

Coverage targets:
- Field serialization
- Multiple instance serialization
- Read-only behavior
"""

import pytest
from inventory.serializers import (
    BrandSerializer,
    PartTypeSerializer,
    LocationSerializer,
    MaterialSerializer,
    VendorSerializer
)
from inventory.tests.factories import (
    BrandFactory,
    PartTypeFactory,
    LocationFactory,
    MaterialFactory,
    VendorFactory
)


@pytest.mark.django_db
class TestBrandSerializer:
    """Test BrandSerializer basic serialization."""

    def test_serializer_fields(self):
        """Verify serializer includes correct fields."""
        brand = BrandFactory()
        serializer = BrandSerializer(brand)
        
        assert 'id' in serializer.data
        assert 'name' in serializer.data
        assert len(serializer.data) == 2

    def test_serialize_single_brand(self):
        """Test serializing a single Brand instance."""
        brand = BrandFactory(name="Prusa")
        serializer = BrandSerializer(brand)
        
        assert serializer.data['id'] == brand.id
        assert serializer.data['name'] == "Prusa"

    def test_serialize_multiple_brands(self):
        """Test serializing multiple Brand instances."""
        brands = [
            BrandFactory(name="Prusa"),
            BrandFactory(name="Bambu Lab"),
            BrandFactory(name="Creality")
        ]
        serializer = BrandSerializer(brands, many=True)
        
        assert len(serializer.data) == 3
        assert serializer.data[0]['name'] == "Prusa"
        assert serializer.data[1]['name'] == "Bambu Lab"


@pytest.mark.django_db
class TestPartTypeSerializer:
    """Test PartTypeSerializer basic serialization."""

    def test_serializer_fields(self):
        """Verify serializer includes correct fields."""
        part_type = PartTypeFactory()
        serializer = PartTypeSerializer(part_type)
        
        assert 'id' in serializer.data
        assert 'name' in serializer.data
        assert len(serializer.data) == 2

    def test_serialize_single_part_type(self):
        """Test serializing a single PartType instance."""
        part_type = PartTypeFactory(name="Nozzle")
        serializer = PartTypeSerializer(part_type)
        
        assert serializer.data['id'] == part_type.id
        assert serializer.data['name'] == "Nozzle"

    def test_serialize_multiple_part_types(self):
        """Test serializing multiple PartType instances."""
        part_types = [
            PartTypeFactory(name="Nozzle"),
            PartTypeFactory(name="Hotend"),
            PartTypeFactory(name="Extruder")
        ]
        serializer = PartTypeSerializer(part_types, many=True)
        
        assert len(serializer.data) == 3
        assert serializer.data[2]['name'] == "Extruder"


@pytest.mark.django_db
class TestLocationSerializer:
    """Test LocationSerializer basic serialization."""

    def test_serializer_fields(self):
        """Verify serializer includes correct fields."""
        location = LocationFactory()
        serializer = LocationSerializer(location)
        
        assert 'id' in serializer.data
        assert 'name' in serializer.data
        assert len(serializer.data) == 2

    def test_serialize_single_location(self):
        """Test serializing a single Location instance."""
        location = LocationFactory(name="Shelf A")
        serializer = LocationSerializer(location)
        
        assert serializer.data['id'] == location.id
        assert serializer.data['name'] == "Shelf A"

    def test_serialize_multiple_locations(self):
        """Test serializing multiple Location instances."""
        locations = [
            LocationFactory(name="Shelf A"),
            LocationFactory(name="Drawer 1"),
            LocationFactory(name="Cabinet B")
        ]
        serializer = LocationSerializer(locations, many=True)
        
        assert len(serializer.data) == 3


@pytest.mark.django_db
class TestMaterialSerializer:
    """Test MaterialSerializer basic serialization."""

    def test_serializer_fields(self):
        """Verify serializer includes correct fields."""
        material = MaterialFactory()
        serializer = MaterialSerializer(material)
        
        assert 'id' in serializer.data
        assert 'name' in serializer.data
        assert len(serializer.data) == 2

    def test_serialize_single_material(self):
        """Test serializing a single Material instance."""
        material = MaterialFactory()  # Use Faker-generated name
        serializer = MaterialSerializer(material)
        
        assert serializer.data['id'] == material.id
        assert serializer.data['name'] == material.name

    def test_serialize_multiple_materials(self):
        """Test serializing multiple Material instances."""
        materials = [
            MaterialFactory(),
            MaterialFactory(),
            MaterialFactory()
        ]
        serializer = MaterialSerializer(materials, many=True)
        
        assert len(serializer.data) == 3


@pytest.mark.django_db
class TestVendorSerializer:
    """Test VendorSerializer basic serialization."""

    def test_serializer_fields(self):
        """Verify serializer includes correct fields."""
        vendor = VendorFactory()
        serializer = VendorSerializer(vendor)
        
        assert 'id' in serializer.data
        assert 'name' in serializer.data
        assert len(serializer.data) == 2

    def test_serialize_single_vendor(self):
        """Test serializing a single Vendor instance."""
        vendor = VendorFactory(name="Amazon")
        serializer = VendorSerializer(vendor)
        
        assert serializer.data['id'] == vendor.id
        assert serializer.data['name'] == "Amazon"

    def test_serialize_multiple_vendors(self):
        """Test serializing multiple Vendor instances."""
        vendors = [
            VendorFactory(name="Amazon"),
            VendorFactory(name="AliExpress"),
            VendorFactory(name="MatterHackers")
        ]
        serializer = VendorSerializer(vendors, many=True)
        
        assert len(serializer.data) == 3
        assert serializer.data[0]['name'] == "Amazon"
