"""
Test suite for PrinterSerializer and ProjectSerializer.

PrinterSerializer:
- Nested manufacturer (Brand) handling
- Custom create/update with get_or_create_nested

ProjectSerializer:
- Multiple M2M relationships (inventory, printers, trackers)
- Computed fields (total_cost, trackers)
- Complex create/update with relationship management

Coverage targets:
- Serialization of all fields
- Create with nested relationships
- Update with M2M changes
- Computed field calculations
"""

import pytest
from rest_framework.test import APIRequestFactory
from inventory.serializers import PrinterSerializer, ProjectSerializer
from inventory.tests.factories import (
    PrinterFactory,
    BrandFactory,
    ProjectFactory,
    InventoryItemFactory,
    TrackerFactory
)


@pytest.mark.django_db
class TestPrinterSerializer:
    """Test PrinterSerializer."""

    def test_serializer_fields(self):
        """Verify serializer includes all printer fields."""
        printer = PrinterFactory()
        serializer = PrinterSerializer(printer)
        
        # Should include all model fields
        assert 'id' in serializer.data
        assert 'title' in serializer.data  # Printer uses 'title' not 'name'
        assert 'manufacturer' in serializer.data

    def test_serialize_with_manufacturer(self):
        """Test serializing printer with nested manufacturer."""
        manufacturer = BrandFactory(name="Prusa")
        printer = PrinterFactory(manufacturer=manufacturer)
        serializer = PrinterSerializer(printer)
        
        assert serializer.data['manufacturer'] == {'id': manufacturer.id, 'name': 'Prusa'}

    def test_create_with_manufacturer(self):
        """Test creating printer with manufacturer via get_or_create_nested."""
        factory = APIRequestFactory()
        request = factory.post('/api/printers/')
        request.data = {
            'title': 'Prusa i3 MK4',
            'manufacturer': '{"name": "Prusa Research"}'
        }
        
        serializer = PrinterSerializer(
            data={'title': 'Prusa i3 MK4'},
            context={'request': request}
        )
        assert serializer.is_valid()
        printer = serializer.save()
        
        assert printer.title == 'Prusa i3 MK4'
        assert printer.manufacturer.name == 'Prusa Research'

    def test_update_manufacturer(self):
        """Test updating printer manufacturer."""
        old_manufacturer = BrandFactory(name="Old Brand")
        printer = PrinterFactory(manufacturer=old_manufacturer)
        
        factory = APIRequestFactory()
        request = factory.put('/api/printers/')
        request.data = {'manufacturer': '{"name": "New Brand"}'}
        
        serializer = PrinterSerializer(
            printer,
            data={},
            partial=True,
            context={'request': request}
        )
        assert serializer.is_valid()
        updated = serializer.save()  # Variable used in assertion below
        
        assert updated.manufacturer.name == 'New Brand'


@pytest.mark.django_db
class TestProjectSerializer:
    """Test ProjectSerializer."""

    def test_serializer_fields(self):
        """Verify serializer includes all expected fields."""
        project = ProjectFactory()
        serializer = ProjectSerializer(project)
        
        expected_fields = {
            'id', 'project_name', 'description', 'status', 'start_date', 'due_date',
            'notes', 'photo', 'associated_inventory_items', 'associated_printers',
            'total_cost', 'links', 'files', 'trackers'
        }
        assert set(serializer.data.keys()) == expected_fields

    def test_serialize_minimal_project(self):
        """Test serializing project with only required fields."""
        project = ProjectFactory(project_name="Test Project")
        serializer = ProjectSerializer(project)
        
        assert serializer.data['project_name'] == "Test Project"
        assert serializer.data['associated_inventory_items'] == []
        assert serializer.data['associated_printers'] == []
        assert serializer.data['total_cost'] == 0

    def test_total_cost_calculation(self):
        """Test get_total_cost method sums inventory item costs."""
        project = ProjectFactory()
        item1 = InventoryItemFactory(cost=10.50)
        item2 = InventoryItemFactory(cost=25.75)
        item3 = InventoryItemFactory(cost=None)  # Should be ignored
        
        project.associated_inventory_items.add(item1, item2, item3)
        
        serializer = ProjectSerializer(project)
        assert serializer.data['total_cost'] == 36.25

    def test_serialize_with_relationships(self):
        """Test serializing project with associated items and printers."""
        project = ProjectFactory()
        item = InventoryItemFactory(title="Test Item")
        printer = PrinterFactory(title="Test Printer")
        
        project.associated_inventory_items.add(item)
        project.associated_printers.add(printer)
        
        serializer = ProjectSerializer(project)
        
        assert len(serializer.data['associated_inventory_items']) == 1
        assert len(serializer.data['associated_printers']) == 1
        assert serializer.data['associated_inventory_items'][0]['title'] == "Test Item"
        assert serializer.data['associated_printers'][0]['title'] == "Test Printer"

    def test_create_project_with_relationships(self):
        """Test creating project with inventory and printer associations."""
        item1 = InventoryItemFactory()
        item2 = InventoryItemFactory()
        printer = PrinterFactory()
        
        factory = APIRequestFactory()
        request = factory.post('/api/projects/')
        request.data = {'project_name': 'New Project'}
        
        serializer = ProjectSerializer(
            data={
                'project_name': 'New Project',
                'status': 'Planning',  # Capital P (matches model choices)
                'inventory_item_ids': [item1.id, item2.id],
                'printer_ids': [printer.id]
            },
            context={'request': request}
        )
        assert serializer.is_valid(), serializer.errors
        project = serializer.save()
        
        assert project.project_name == 'New Project'
        assert project.associated_inventory_items.count() == 2
        assert project.associated_printers.count() == 1

    def test_create_project_with_trackers(self):
        """Test creating project with tracker associations."""
        tracker1 = TrackerFactory(project=None)
        tracker2 = TrackerFactory(project=None)
        
        factory = APIRequestFactory()
        request = factory.post('/api/projects/')
        request.data = {'project_name': 'Tracker Project'}
        
        serializer = ProjectSerializer(
            data={
                'project_name': 'Tracker Project',
                'tracker_ids': [tracker1.id, tracker2.id]
            },
            context={'request': request}
        )
        assert serializer.is_valid()
        project = serializer.save()
        
        tracker1.refresh_from_db()
        tracker2.refresh_from_db()
        assert tracker1.project == project
        assert tracker2.project == project

    def test_update_project_relationships(self):
        """Test updating project's inventory/printer associations."""
        project = ProjectFactory()
        old_item = InventoryItemFactory()
        new_item = InventoryItemFactory()
        old_printer = PrinterFactory()
        new_printer = PrinterFactory()
        
        project.associated_inventory_items.add(old_item)
        project.associated_printers.add(old_printer)
        
        factory = APIRequestFactory()
        request = factory.put('/api/projects/')
        request.data = {}
        
        serializer = ProjectSerializer(
            project,
            data={
                'inventory_item_ids': [new_item.id],
                'printer_ids': [new_printer.id]
            },
            partial=True,
            context={'request': request}
        )
        assert serializer.is_valid()
        updated = serializer.save()  # Variable used in assertions below
        
        # Old associations removed, new ones added
        assert old_item not in updated.associated_inventory_items.all()
        assert new_item in updated.associated_inventory_items.all()
        assert old_printer not in updated.associated_printers.all()
        assert new_printer in updated.associated_printers.all()

    def test_update_project_trackers(self):
        """Test updating project's tracker associations."""
        project = ProjectFactory()
        old_tracker = TrackerFactory(project=project)
        new_tracker = TrackerFactory(project=None)
        keep_tracker = TrackerFactory(project=project)
        
        factory = APIRequestFactory()
        request = factory.put('/api/projects/')
        request.data = {}
        
        serializer = ProjectSerializer(
            project,
            data={'tracker_ids': [keep_tracker.id, new_tracker.id]},
            partial=True,
            context={'request': request}
        )
        assert serializer.is_valid()
        updated = serializer.save()  # Triggers tracker relationship updates tested below
        
        old_tracker.refresh_from_db()
        new_tracker.refresh_from_db()
        keep_tracker.refresh_from_db()
        
        # Old tracker unassigned, new tracker assigned, kept tracker remains
        assert old_tracker.project is None
        assert new_tracker.project == project
        assert keep_tracker.project == project
