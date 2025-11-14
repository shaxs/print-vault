"""
Test suite for InventoryItemSerializer.

This serializer is complex with:
- Nested read-only serializers (Brand, PartType, Location, Vendor)
- Many-to-many project associations (read/write)
- Custom create() method with get_or_create_nested logic
- Custom update() method preserving nested relationships

Coverage targets:
- Field serialization (all fields)
- Nested object serialization
- Project associations (read-only associated_projects, write-only project_ids)
- Create with nested lookups
- Update with nested lookups
- M2M relationship handling
"""

import pytest
from rest_framework.test import APIRequestFactory
from inventory.serializers import InventoryItemSerializer
from inventory.tests.factories import (
    InventoryItemFactory,
    BrandFactory,
    PartTypeFactory,
    LocationFactory,
    VendorFactory,
    ProjectFactory
)


@pytest.mark.django_db
class TestInventoryItemSerializerRead:
    """Test InventoryItemSerializer read operations (serialization)."""

    def test_serializer_fields(self):
        """Verify serializer includes all expected fields."""
        item = InventoryItemFactory()
        serializer = InventoryItemSerializer(item)
        
        expected_fields = {
            'id', 'title', 'brand', 'part_type', 'quantity',
            'cost', 'location', 'photo', 'notes',
            'associated_projects', 'is_consumable', 'low_stock_threshold',
            'vendor', 'vendor_link', 'model'
        }
        assert set(serializer.data.keys()) == expected_fields

    def test_serialize_minimal_item(self):
        """Test serializing item with only required fields."""
        item = InventoryItemFactory(
            title="Test Nozzle",
            brand=None,
            part_type=None,
            location=None,
            vendor=None
        )
        serializer = InventoryItemSerializer(item)
        
        assert serializer.data['title'] == "Test Nozzle"
        assert serializer.data['brand'] is None
        assert serializer.data['part_type'] is None
        assert serializer.data['location'] is None
        assert serializer.data['vendor'] is None

    def test_serialize_with_nested_lookups(self):
        """Test serializing item with nested Brand, PartType, Location, Vendor."""
        brand = BrandFactory(name="Prusa")
        part_type = PartTypeFactory(name="Nozzle")
        location = LocationFactory(name="Shelf A")
        vendor = VendorFactory(name="Amazon")
        
        item = InventoryItemFactory(
            brand=brand,
            part_type=part_type,
            location=location,
            vendor=vendor
        )
        serializer = InventoryItemSerializer(item)
        
        # Nested objects should be serialized as dicts with id and name
        assert serializer.data['brand'] == {'id': brand.id, 'name': 'Prusa'}
        assert serializer.data['part_type'] == {'id': part_type.id, 'name': 'Nozzle'}
        assert serializer.data['location'] == {'id': location.id, 'name': 'Shelf A'}
        assert serializer.data['vendor'] == {'id': vendor.id, 'name': 'Amazon'}

    def test_serialize_with_projects(self):
        """Test serializing item with associated projects."""
        project1 = ProjectFactory(project_name="Project Alpha")
        project2 = ProjectFactory(project_name="Project Beta")
        item = InventoryItemFactory()
        item.associated_projects.add(project1, project2)
        
        serializer = InventoryItemSerializer(item)
        
        assert len(serializer.data['associated_projects']) == 2
        project_names = [p['project_name'] for p in serializer.data['associated_projects']]
        assert "Project Alpha" in project_names
        assert "Project Beta" in project_names

    def test_serialize_consumable_fields(self):
        """Test serializing consumable-specific fields."""
        item = InventoryItemFactory(
            is_consumable=True,
            low_stock_threshold=10
        )
        serializer = InventoryItemSerializer(item)
        
        assert serializer.data['is_consumable'] is True
        assert serializer.data['low_stock_threshold'] == 10


@pytest.mark.django_db
class TestInventoryItemSerializerCreate:
    """Test InventoryItemSerializer create operations."""

    def test_create_minimal(self):
        """Test creating item with minimal data (no context needed)."""
        factory = APIRequestFactory()
        request = factory.post('/api/inventory/')
        request.data = {'title': 'Basic Nozzle'}
        
        serializer = InventoryItemSerializer(
            data={'title': 'Basic Nozzle'},
            context={'request': request}
        )
        assert serializer.is_valid()
        item = serializer.save()
        
        assert item.title == 'Basic Nozzle'
        assert item.brand is None

    def test_create_with_nested_lookups_string(self):
        """Test creating item with nested lookups from JSON strings."""
        factory = APIRequestFactory()
        request = factory.post('/api/inventory/')
        request.data = {
            'title': 'E3D V6 Nozzle',
            'brand': '{"name": "E3D"}',
            'part_type': '{"name": "Nozzle"}',
            'location': '{"name": "Shelf B"}',
            'vendor': '{"name": "MatterHackers"}'
        }
        
        serializer = InventoryItemSerializer(
            data={'title': 'E3D V6 Nozzle'},
            context={'request': request}
        )
        assert serializer.is_valid()
        item = serializer.save()
        
        assert item.brand.name == 'E3D'
        assert item.part_type.name == 'Nozzle'
        assert item.location.name == 'Shelf B'
        assert item.vendor.name == 'MatterHackers'

    def test_create_with_project_associations(self):
        """Test creating item with associated projects via project_ids."""
        project1 = ProjectFactory()
        project2 = ProjectFactory()
        
        factory = APIRequestFactory()
        request = factory.post('/api/inventory/')
        request.data = {'title': 'Shared Component'}
        
        serializer = InventoryItemSerializer(
            data={
                'title': 'Shared Component',
                'project_ids': [project1.id, project2.id]
            },
            context={'request': request}
        )
        assert serializer.is_valid()
        item = serializer.save()
        
        assert item.associated_projects.count() == 2
        assert project1 in item.associated_projects.all()
        assert project2 in item.associated_projects.all()


@pytest.mark.django_db
class TestInventoryItemSerializerUpdate:
    """Test InventoryItemSerializer update operations."""

    def test_update_title(self):
        """Test updating item title."""
        item = InventoryItemFactory(title="Old Title")
        
        factory = APIRequestFactory()
        request = factory.put('/api/inventory/')
        request.data = {}
        
        serializer = InventoryItemSerializer(
            item,
            data={'title': 'New Title'},
            partial=True,
            context={'request': request}
        )
        assert serializer.is_valid()
        updated = serializer.save()
        
        assert updated.title == 'New Title'

    def test_update_nested_lookups(self):
        """Test updating nested lookup relationships."""
        old_brand = BrandFactory(name="Old Brand")
        item = InventoryItemFactory(brand=old_brand)
        
        factory = APIRequestFactory()
        request = factory.put('/api/inventory/')
        request.data = {
            'brand': '{"name": "New Brand"}',
            'part_type': '{"name": "Hotend"}'
        }
        
        serializer = InventoryItemSerializer(
            item,
            data={},  # Nested updates come from request.data
            partial=True,
            context={'request': request}
        )
        assert serializer.is_valid()
        updated = serializer.save()
        
        assert updated.brand.name == 'New Brand'
        assert updated.part_type.name == 'Hotend'

    def test_update_project_associations(self):
        """Test updating project associations via project_ids."""
        project1 = ProjectFactory()
        project2 = ProjectFactory()
        project3 = ProjectFactory()
        
        item = InventoryItemFactory()
        item.associated_projects.add(project1, project2)
        
        factory = APIRequestFactory()
        request = factory.put('/api/inventory/')
        request.data = {}
        
        # Replace with new set of projects
        serializer = InventoryItemSerializer(
            item,
            data={'project_ids': [project2.id, project3.id]},
            partial=True,
            context={'request': request}
        )
        assert serializer.is_valid()
        updated = serializer.save()
        
        assert updated.associated_projects.count() == 2
        assert project2 in updated.associated_projects.all()
        assert project3 in updated.associated_projects.all()
        assert project1 not in updated.associated_projects.all()

    def test_update_preserves_unmodified_fields(self):
        """Test partial update preserves fields not included in update data."""
        item = InventoryItemFactory(
            title="Original",
            quantity=5,
            cost=10.99
        )
        
        factory = APIRequestFactory()
        request = factory.put('/api/inventory/')
        request.data = {}
        
        serializer = InventoryItemSerializer(
            item,
            data={'quantity': 10},  # Only update quantity
            partial=True,
            context={'request': request}
        )
        assert serializer.is_valid()
        updated = serializer.save()
        
        assert updated.title == "Original"  # Preserved
        assert updated.cost == 10.99  # Preserved
        assert updated.quantity == 10  # Updated
