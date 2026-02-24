"""
Tests for custom InventoryItem ViewSet actions.

Covers the GET /api/inventoryitems/{id}/allocation/ endpoint which
provides BOM-aware allocation summary for an inventory item.
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from inventory.tests.factories import (
    InventoryItemFactory,
    ProjectFactory,
    ProjectBOMItemFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestInventoryAllocationAction:
    """
    Tests for GET /api/inventoryitems/{id}/allocation/

    Verifies:
    - Response structure and field presence
    - qty_on_hand, qty_needed, qty_available calculations
    - is_overallocated flag
    - Active vs closed project breakdown
    - Items with no BOM links
    """

    def test_allocation_returns_200(self, api_client):
        """Allocation endpoint returns HTTP 200."""
        item = InventoryItemFactory(quantity=10)
        response = api_client.get(f'/api/inventoryitems/{item.id}/allocation/')
        assert response.status_code == status.HTTP_200_OK

    def test_allocation_404_for_missing_item(self, api_client):
        """Allocation endpoint returns 404 for non-existent item."""
        response = api_client.get('/api/inventoryitems/99999/allocation/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_allocation_response_fields(self, api_client):
        """Response contains all expected fields."""
        item = InventoryItemFactory(quantity=10)
        response = api_client.get(f'/api/inventoryitems/{item.id}/allocation/')
        expected_keys = {
            'qty_on_hand', 'qty_needed', 'qty_available',
            'is_overallocated', 'low_stock_threshold', 'is_consumable',
            'active_projects', 'closed_projects',
        }
        assert expected_keys == set(response.data.keys())

    def test_allocation_no_bom_links(self, api_client):
        """Item with no BOM links shows qty_needed=0 and no projects."""
        item = InventoryItemFactory(quantity=20)
        response = api_client.get(f'/api/inventoryitems/{item.id}/allocation/')
        assert response.data['qty_on_hand'] == 20
        assert response.data['qty_needed'] == 0
        assert response.data['qty_available'] == 20
        assert response.data['is_overallocated'] is False
        assert response.data['active_projects'] == []
        assert response.data['closed_projects'] == []

    def test_allocation_with_single_active_project(self, api_client):
        """qty_needed reflects single active BOM item allocation."""
        item = InventoryItemFactory(quantity=10)
        project = ProjectFactory(status='Planning')
        ProjectBOMItemFactory(project=project, inventory_item=item, quantity_needed=4)
        response = api_client.get(f'/api/inventoryitems/{item.id}/allocation/')
        assert response.data['qty_on_hand'] == 10
        assert response.data['qty_needed'] == 4
        assert response.data['qty_available'] == 6
        assert response.data['is_overallocated'] is False

    def test_allocation_sums_multiple_active_projects(self, api_client):
        """qty_needed sums across all active BOM items."""
        item = InventoryItemFactory(quantity=15)
        project1 = ProjectFactory(status='Planning')
        project2 = ProjectFactory(status='In Progress')
        project3 = ProjectFactory(status='On Hold')
        ProjectBOMItemFactory(project=project1, inventory_item=item, quantity_needed=3)
        ProjectBOMItemFactory(project=project2, inventory_item=item, quantity_needed=5)
        ProjectBOMItemFactory(project=project3, inventory_item=item, quantity_needed=4)
        response = api_client.get(f'/api/inventoryitems/{item.id}/allocation/')
        assert response.data['qty_needed'] == 12
        assert response.data['qty_available'] == 3
        assert len(response.data['active_projects']) == 3

    def test_allocation_overallocated_flag(self, api_client):
        """is_overallocated is True when qty_available < 0."""
        item = InventoryItemFactory(quantity=2)
        project = ProjectFactory(status='In Progress')
        ProjectBOMItemFactory(project=project, inventory_item=item, quantity_needed=5)
        response = api_client.get(f'/api/inventoryitems/{item.id}/allocation/')
        assert response.data['qty_available'] == -3
        assert response.data['is_overallocated'] is True

    def test_allocation_closed_projects_not_in_active(self, api_client):
        """Completed/Canceled projects appear in closed_projects, not active."""
        item = InventoryItemFactory(quantity=10)
        active = ProjectFactory(status='Planning')
        completed = ProjectFactory(status='Completed')
        canceled = ProjectFactory(status='Canceled')
        ProjectBOMItemFactory(project=active, inventory_item=item, quantity_needed=2)
        ProjectBOMItemFactory(project=completed, inventory_item=item, quantity_needed=3)
        ProjectBOMItemFactory(project=canceled, inventory_item=item, quantity_needed=1)
        response = api_client.get(f'/api/inventoryitems/{item.id}/allocation/')
        # Only active projects affect qty_needed
        assert response.data['qty_needed'] == 2
        assert len(response.data['active_projects']) == 1
        assert len(response.data['closed_projects']) == 2

    def test_allocation_active_project_entry_structure(self, api_client):
        """Each entry in active_projects has required fields."""
        item = InventoryItemFactory(quantity=10)
        project = ProjectFactory(project_name="Voron 2.4", status='Planning')
        bom_item = ProjectBOMItemFactory(project=project, inventory_item=item, quantity_needed=3)
        response = api_client.get(f'/api/inventoryitems/{item.id}/allocation/')
        entry = response.data['active_projects'][0]
        assert entry['id'] == project.id
        assert entry['project_name'] == "Voron 2.4"
        assert entry['qty_allocated'] == 3
        assert entry['bom_item_id'] == bom_item.id
        assert 'project_status' in entry

    def test_allocation_project_status_snake_case(self, api_client):
        """project_status is converted to snake_case."""
        item = InventoryItemFactory(quantity=10)
        project = ProjectFactory(status='In Progress')
        ProjectBOMItemFactory(project=project, inventory_item=item, quantity_needed=1)
        response = api_client.get(f'/api/inventoryitems/{item.id}/allocation/')
        assert response.data['active_projects'][0]['project_status'] == 'in_progress'

    def test_allocation_does_not_count_unlinked_bom_items(self, api_client):
        """BOM items without an inventory_item link don't affect this item's allocation."""
        item = InventoryItemFactory(quantity=10)
        project = ProjectFactory(status='Planning')
        # Unlinked BOM item — no inventory_item set
        ProjectBOMItemFactory(project=project, inventory_item=None)
        response = api_client.get(f'/api/inventoryitems/{item.id}/allocation/')
        assert response.data['qty_needed'] == 0
        assert response.data['active_projects'] == []
