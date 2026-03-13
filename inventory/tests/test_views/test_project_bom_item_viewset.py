"""
Tests for ProjectBOMItemViewSet.

Covers the inventory reservation model:
  - Creating a linked BOM item decrements inventory quantity
  - Deleting a linked BOM item restores inventory quantity
  - Updating qty/link adjusts the reservation delta
  - Projects that are not active (Completed/Canceled) are never adjusted
  - needs_purchase items never trigger inventory adjustments
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from inventory.models import InventoryItem, ProjectBOMItem
from inventory.tests.factories import (
    ProjectBOMItemFactory,
    ProjectFactory,
    InventoryItemFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def active_project(db):
    """A project with Planning status (active for BOM reservation)."""
    return ProjectFactory(project_name='Test Build', status='Planning')


@pytest.fixture
def inv_item(db):
    """An inventory item with a known quantity."""
    return InventoryItemFactory(title='NEMA17 Motor', quantity=10)


# ============================================================================
# CREATE — reservation decrements inventory
# ============================================================================

@pytest.mark.django_db
class TestBOMItemCreate:
    """POST /api/projectbomitems/ — inventory reservation on create."""

    def test_create_linked_decrements_inventory(self, api_client, active_project, inv_item):
        """Creating a linked BOM item on an active project decrements inventory qty."""
        payload = {
            'project': active_project.pk,
            'description': 'NEMA17 Stepper',
            'quantity_needed': 4,
            'inventory_item': inv_item.pk,
            'status': 'linked',
        }
        response = api_client.post('/api/projectbomitems/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        inv_item.refresh_from_db()
        assert inv_item.quantity == 6  # 10 - 4

    def test_create_unlinked_no_inventory_change(self, api_client, active_project, inv_item):
        """Creating an unlinked BOM item does not touch inventory."""
        payload = {
            'project': active_project.pk,
            'description': 'Some Part',
            'quantity_needed': 4,
            'status': 'unlinked',
        }
        api_client.post('/api/projectbomitems/', payload, format='json')
        inv_item.refresh_from_db()
        assert inv_item.quantity == 10  # unchanged

    def test_create_needs_purchase_no_inventory_change(self, api_client, active_project, inv_item):
        """Creating a needs_purchase BOM item does not touch inventory."""
        payload = {
            'project': active_project.pk,
            'description': 'Part to Order',
            'quantity_needed': 5,
            'inventory_item': inv_item.pk,
            'status': 'needs_purchase',
        }
        api_client.post('/api/projectbomitems/', payload, format='json')
        inv_item.refresh_from_db()
        assert inv_item.quantity == 10  # unchanged

    def test_create_on_inactive_project_no_adjustment(self, api_client, inv_item):
        """Creating a BOM item on a Completed project does not affect inventory."""
        completed_project = ProjectFactory(status='Completed')
        payload = {
            'project': completed_project.pk,
            'description': 'Motor',
            'quantity_needed': 4,
            'inventory_item': inv_item.pk,
            'status': 'linked',
        }
        api_client.post('/api/projectbomitems/', payload, format='json')
        inv_item.refresh_from_db()
        assert inv_item.quantity == 10  # unchanged

    def test_create_can_make_inventory_negative(self, api_client, active_project, inv_item):
        """Inventory can go negative (overallocated); no floor enforced."""
        payload = {
            'project': active_project.pk,
            'description': 'Motor',
            'quantity_needed': 15,  # More than the 10 in stock
            'inventory_item': inv_item.pk,
            'status': 'linked',
        }
        api_client.post('/api/projectbomitems/', payload, format='json')
        inv_item.refresh_from_db()
        assert inv_item.quantity == -5  # 10 - 15


# ============================================================================
# DELETE — reservation restores inventory
# ============================================================================

@pytest.mark.django_db
class TestBOMItemDelete:
    """DELETE /api/projectbomitems/{id}/ — inventory restoration on delete."""

    def test_delete_linked_restores_inventory(self, api_client, active_project, inv_item):
        """Deleting a linked BOM item on an active project restores inventory."""
        bom_item = ProjectBOMItemFactory(
            project=active_project,
            inventory_item=inv_item,
            quantity_needed=4,
            status='linked',
        )
        # Manually set qty to simulate the decrement that happened on create
        inv_item.quantity = 6  # 10 - 4
        inv_item.save()

        response = api_client.delete(f'/api/projectbomitems/{bom_item.pk}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

        inv_item.refresh_from_db()
        assert inv_item.quantity == 10  # restored

    def test_delete_unlinked_no_inventory_change(self, api_client, active_project, inv_item):
        """Deleting an unlinked BOM item does not touch inventory."""
        bom_item = ProjectBOMItemFactory(
            project=active_project,
            inventory_item=None,
            quantity_needed=4,
            status='unlinked',
        )
        api_client.delete(f'/api/projectbomitems/{bom_item.pk}/')
        inv_item.refresh_from_db()
        assert inv_item.quantity == 10  # unchanged

    def test_delete_on_inactive_project_no_adjustment(self, api_client, inv_item):
        """Deleting a BOM item from a Completed project does not restore inventory."""
        completed_project = ProjectFactory(status='Completed')
        bom_item = ProjectBOMItemFactory(
            project=completed_project,
            inventory_item=inv_item,
            quantity_needed=4,
            status='linked',
        )
        inv_item.quantity = 6
        inv_item.save()

        api_client.delete(f'/api/projectbomitems/{bom_item.pk}/')
        inv_item.refresh_from_db()
        assert inv_item.quantity == 6  # NOT restored (project was completed)


# ============================================================================
# UPDATE — delta adjustment on quantity/link changes
# ============================================================================

@pytest.mark.django_db
class TestBOMItemUpdate:
    """PATCH /api/projectbomitems/{id}/ — delta adjustments on update."""

    def test_increase_quantity_decrements_more(self, api_client, active_project, inv_item):
        """Increasing qty_needed reserves more from inventory."""
        bom_item = ProjectBOMItemFactory(
            project=active_project,
            inventory_item=inv_item,
            quantity_needed=4,
            status='linked',
        )
        inv_item.quantity = 6  # simulating post-creation state
        inv_item.save()

        api_client.patch(f'/api/projectbomitems/{bom_item.pk}/', {'quantity_needed': 7}, format='json')
        inv_item.refresh_from_db()
        # restored old (4) → 6+4=10, then decremented new (7) → 10-7=3
        assert inv_item.quantity == 3

    def test_decrease_quantity_restores_partial(self, api_client, active_project, inv_item):
        """Decreasing qty_needed returns the difference to inventory."""
        bom_item = ProjectBOMItemFactory(
            project=active_project,
            inventory_item=inv_item,
            quantity_needed=4,
            status='linked',
        )
        inv_item.quantity = 6
        inv_item.save()

        api_client.patch(f'/api/projectbomitems/{bom_item.pk}/', {'quantity_needed': 2}, format='json')
        inv_item.refresh_from_db()
        # restored old (4) → 6+4=10, decremented new (2) → 10-2=8
        assert inv_item.quantity == 8

    def test_swap_inventory_item_adjusts_both(self, api_client, active_project, inv_item):
        """Changing the linked inventory item restores old and decrements new."""
        new_inv_item = InventoryItemFactory(title='Stepper Alt', quantity=20)
        bom_item = ProjectBOMItemFactory(
            project=active_project,
            inventory_item=inv_item,
            quantity_needed=4,
            status='linked',
        )
        inv_item.quantity = 6
        inv_item.save()

        api_client.patch(
            f'/api/projectbomitems/{bom_item.pk}/',
            {'inventory_item': new_inv_item.pk},
            format='json',
        )
        inv_item.refresh_from_db()
        new_inv_item.refresh_from_db()
        assert inv_item.quantity == 10      # old item restored
        assert new_inv_item.quantity == 16  # new item decremented: 20 - 4

    def test_set_needs_purchase_restores_inventory(self, api_client, active_project, inv_item):
        """Changing status to needs_purchase (with inventory_item cleared) restores the reservation."""
        bom_item = ProjectBOMItemFactory(
            project=active_project,
            inventory_item=inv_item,
            quantity_needed=4,
            status='linked',
        )
        inv_item.quantity = 6
        inv_item.save()

        # Serializer requires inventory_item=null when switching to needs_purchase
        response = api_client.patch(
            f'/api/projectbomitems/{bom_item.pk}/',
            {'status': 'needs_purchase', 'inventory_item': None},
            format='json',
        )
        assert response.status_code == 200
        inv_item.refresh_from_db()
        assert inv_item.quantity == 10  # restored because linked reservation was released

    def test_update_description_no_inventory_change(self, api_client, active_project, inv_item):
        """Updating non-allocation fields doesn't touch inventory."""
        bom_item = ProjectBOMItemFactory(
            project=active_project,
            inventory_item=inv_item,
            quantity_needed=4,
            status='linked',
        )
        inv_item.quantity = 6
        inv_item.save()

        api_client.patch(
            f'/api/projectbomitems/{bom_item.pk}/',
            {'description': 'Updated Description'},
            format='json',
        )
        inv_item.refresh_from_db()
        assert inv_item.quantity == 6  # unchanged

    def test_update_on_inactive_project_no_adjustment(self, api_client, inv_item):
        """Updating a BOM item on a Completed project does not adjust inventory."""
        completed = ProjectFactory(status='Completed')
        bom_item = ProjectBOMItemFactory(
            project=completed,
            inventory_item=inv_item,
            quantity_needed=4,
            status='linked',
        )
        inv_item.quantity = 6
        inv_item.save()

        api_client.patch(f'/api/projectbomitems/{bom_item.pk}/', {'quantity_needed': 8}, format='json')
        inv_item.refresh_from_db()
        assert inv_item.quantity == 6  # unchanged


# ============================================================================
# LIST / FILTER
# ============================================================================

@pytest.mark.django_db
class TestBOMItemList:
    """GET /api/projectbomitems/ — listing and filtering."""

    def test_list_all_bom_items(self, api_client, active_project):
        """List endpoint returns all BOM items."""
        ProjectBOMItemFactory(project=active_project, description='Part A')
        ProjectBOMItemFactory(project=active_project, description='Part B')

        response = api_client.get('/api/projectbomitems/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_filter_by_project(self, api_client):
        """?project= filters to only that project's BOM items."""
        project_a = ProjectFactory(status='Planning')
        project_b = ProjectFactory(status='Planning')
        ProjectBOMItemFactory(project=project_a, description='Part A')
        ProjectBOMItemFactory(project=project_b, description='Part B')

        response = api_client.get(f'/api/projectbomitems/?project={project_a.pk}')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['description'] == 'Part A'
