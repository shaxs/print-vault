"""
Tests for InventoryItem ViewSet API endpoints.

Tests CRUD operations, filtering, search, ordering, and low stock functionality.
Uses pytest-django and factory-boy for efficient test setup.
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from inventory.models import InventoryItem
from inventory.tests.factories import (
    InventoryItemFactory, 
    BrandFactory, 
    PartTypeFactory, 
    LocationFactory,
    ProjectFactory
)


@pytest.fixture
def api_client():
    """Provide an API client for making requests."""
    return APIClient()


@pytest.fixture
def sample_inventory_items(db):
    """Create sample inventory items for testing."""
    brand1 = BrandFactory(name="Prusa")
    brand2 = BrandFactory(name="Creality")
    part_type1 = PartTypeFactory(name="Nozzle")
    part_type2 = PartTypeFactory(name="Hot End")
    location1 = LocationFactory(name="Shelf A")
    location2 = LocationFactory(name="Drawer 1")
    
    # Create items with varying quantities and consumable status
    item1 = InventoryItemFactory(
        title="Brass Nozzle 0.4mm",
        brand=brand1,
        part_type=part_type1,
        location=location1,
        quantity=50,
        is_consumable=True,
        low_stock_threshold=10
    )
    
    item2 = InventoryItemFactory(
        title="Steel Nozzle 0.6mm",
        brand=brand1,
        part_type=part_type1,
        location=location1,
        quantity=5,  # Below threshold
        is_consumable=True,
        low_stock_threshold=10
    )
    
    item3 = InventoryItemFactory(
        title="V6 Hot End",
        brand=brand2,
        part_type=part_type2,
        location=location2,
        quantity=2,
        is_consumable=False
    )
    
    return {
        'items': [item1, item2, item3],
        'brands': [brand1, brand2],
        'part_types': [part_type1, part_type2],
        'locations': [location1, location2]
    }


# ============================================================================
# CRUD OPERATION TESTS
# ============================================================================

@pytest.mark.django_db
class TestInventoryItemCRUD:
    """Test Create, Read, Update, Delete operations."""
    
    def test_list_inventory_items(self, api_client, sample_inventory_items):
        """Test listing all inventory items."""
        url = '/api/inventoryitems/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3
    
    def test_retrieve_inventory_item(self, api_client, sample_inventory_items):
        """Test retrieving a single inventory item."""
        item = sample_inventory_items['items'][0]
        url = f'/api/inventoryitems/{item.pk}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == item.title
        assert response.data['brand']['name'] == item.brand.name
    
    def test_create_inventory_item(self, api_client, db):
        """Test creating a new inventory item."""
        brand = BrandFactory(name="Test Brand")
        part_type = PartTypeFactory(name="Test Part")
        location = LocationFactory(name="Test Location")
        
        url = '/api/inventoryitems/'
        data = {
            'title': 'New Test Item',
            'brand_data': {'name': brand.name},
            'part_type_data': {'name': part_type.name},
            'location_data': {'name': location.name},
            'quantity': 10,
            'cost': '25.99',
            'is_consumable': True,
            'low_stock_threshold': 5
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert InventoryItem.objects.filter(title='New Test Item').exists()
    
    def test_update_inventory_item(self, api_client, sample_inventory_items):
        """Test updating an existing inventory item."""
        item = sample_inventory_items['items'][0]
        url = f'/api/inventoryitems/{item.pk}/'
        
        data = {
            'quantity': 100,
            'cost': '30.00'
        }
        
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        item.refresh_from_db()
        assert item.quantity == 100
    
    def test_delete_inventory_item(self, api_client, sample_inventory_items):
        """Test deleting an inventory item."""
        item = sample_inventory_items['items'][0]
        url = f'/api/inventoryitems/{item.pk}/'
        
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not InventoryItem.objects.filter(pk=item.pk).exists()


# ============================================================================
# FILTERING TESTS
# ============================================================================

@pytest.mark.django_db
class TestInventoryItemFiltering:
    """Test filtering functionality."""
    
    def test_filter_by_brand(self, api_client, sample_inventory_items):
        """Test filtering items by brand."""
        brand = sample_inventory_items['brands'][0]
        url = '/api/inventoryitems/'
        
        response = api_client.get(url, {'brand__name': brand.name})
        
        assert response.status_code == status.HTTP_200_OK
        assert all(item['brand']['name'] == brand.name for item in response.data)
    
    def test_filter_by_part_type(self, api_client, sample_inventory_items):
        """Test filtering items by part type."""
        part_type = sample_inventory_items['part_types'][0]
        url = '/api/inventoryitems/'
        
        response = api_client.get(url, {'part_type__name': part_type.name})
        
        assert response.status_code == status.HTTP_200_OK
        assert all(item['part_type']['name'] == part_type.name for item in response.data)
    
    def test_filter_by_location(self, api_client, sample_inventory_items):
        """Test filtering items by location."""
        location = sample_inventory_items['locations'][0]
        url = '/api/inventoryitems/'
        
        response = api_client.get(url, {'location__name': location.name})
        
        assert response.status_code == status.HTTP_200_OK
        assert all(item['location']['name'] == location.name for item in response.data)


# ============================================================================
# SEARCH TESTS
# ============================================================================

@pytest.mark.django_db
class TestInventoryItemSearch:
    """Test search functionality."""
    
    def test_search_by_title(self, api_client, sample_inventory_items):
        """Test searching items by title."""
        url = '/api/inventoryitems/'
        response = api_client.get(url, {'search': 'Brass'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert 'Brass' in response.data[0]['title']
    
    def test_search_by_brand_name(self, api_client, sample_inventory_items):
        """Test searching items by brand name."""
        url = '/api/inventoryitems/'
        response = api_client.get(url, {'search': 'Prusa'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1


# ============================================================================
# ORDERING TESTS
# ============================================================================

@pytest.mark.django_db
class TestInventoryItemOrdering:
    """Test ordering functionality."""
    
    def test_order_by_title(self, api_client, sample_inventory_items):
        """Test ordering items by title."""
        url = '/api/inventoryitems/'
        response = api_client.get(url, {'ordering': 'title'})
        
        assert response.status_code == status.HTTP_200_OK
        titles = [item['title'] for item in response.data]
        assert titles == sorted(titles)
    
    def test_order_by_quantity(self, api_client, sample_inventory_items):
        """Test ordering items by quantity."""
        url = '/api/inventoryitems/'
        response = api_client.get(url, {'ordering': 'quantity'})
        
        assert response.status_code == status.HTTP_200_OK
        quantities = [item['quantity'] for item in response.data]
        assert quantities == sorted(quantities)


# ============================================================================
# LOW STOCK TESTS
# ============================================================================

@pytest.mark.django_db
class TestLowStockItems:
    """Test low stock functionality."""
    
    def test_low_stock_filter(self, api_client, sample_inventory_items):
        """Test retrieving low stock items."""
        url = '/api/low-stock/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Should return item2 (quantity=5, threshold=10)
        assert len(response.data) >= 1
        for item in response.data:
            assert item['quantity'] <= item['low_stock_threshold']
    
    def test_low_stock_only_consumables(self, api_client, sample_inventory_items):
        """Test that low stock filter only includes consumables."""
        url = '/api/low-stock/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        for item in response.data:
            assert item['is_consumable'] is True


# ============================================================================
# PROJECT ASSOCIATION TESTS
# ============================================================================

@pytest.mark.django_db
class TestInventoryItemProjectAssociation:
    """Test project association functionality."""
    
    def test_associate_item_with_project(self, api_client, db):
        """Test associating inventory item with a project."""
        item = InventoryItemFactory()
        project = ProjectFactory()
        
        url = f'/api/inventoryitems/{item.pk}/'
        data = {
            'project_ids': [project.pk]
        }
        
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert project in item.associated_projects.all()
    
    def test_retrieve_item_with_projects(self, api_client, db):
        """Test retrieving item with associated projects."""
        item = InventoryItemFactory()
        project1 = ProjectFactory()
        project2 = ProjectFactory()
        item.associated_projects.add(project1, project2)
        
        url = f'/api/inventoryitems/{item.pk}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['associated_projects']) == 2
