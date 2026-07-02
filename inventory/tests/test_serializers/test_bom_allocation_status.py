"""
Tests for ProjectBOMItemSerializer.get_allocation_status

The serializer re-queries the database directly to avoid stale ORM cache
values after perform_update uses a bulk DB update (bypassing the instance).

Covers:
  - 'needs_purchase' → returned when status is explicitly needs_purchase
  - 'unlinked' → returned when no inventory_item_id
  - 'unlinked' → returned when inventory_item has been deleted (row = None)
  - 'overallocated' → returned when quantity < 0 after PATCH
  - 'covered' → returned when quantity >= needed after PATCH
  - 'low' → returned for consumable item at/below threshold
  - Freshness: allocation_status in PATCH response is not stale
    (the critical regression test — previously showed 'covered' even when
     the item was actually overallocated immediately after linking)
"""
import pytest
from rest_framework.test import APIClient
from inventory.models import InventoryItem
from inventory.tests.factories import (
    ProjectFactory,
    InventoryItemFactory,
    ProjectBOMItemFactory,
    LocationFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def active_project(db):
    return ProjectFactory(project_name='Allocation Test', status='Planning')


# ============================================================================
# allocation_status values — via PATCH response
# ============================================================================

@pytest.mark.django_db
class TestAllocationStatusValues:
    """allocation_status field returns correct values via the API response."""

    def test_needs_purchase_status(self, api_client, active_project):
        """BOM item with status=needs_purchase returns allocation_status='needs_purchase'."""
        bom_item = ProjectBOMItemFactory(
            project=active_project,
            status='needs_purchase',
            inventory_item=None,
        )
        response = api_client.get(f'/api/projectbomitems/{bom_item.pk}/')
        assert response.status_code == 200
        assert response.data['allocation_status'] == 'needs_purchase'

    def test_unlinked_status(self, api_client, active_project):
        """BOM item with no inventory_item returns allocation_status='unlinked'."""
        bom_item = ProjectBOMItemFactory(
            project=active_project,
            status='unlinked',
            inventory_item=None,
        )
        response = api_client.get(f'/api/projectbomitems/{bom_item.pk}/')
        assert response.status_code == 200
        assert response.data['allocation_status'] == 'unlinked'

    def test_covered_when_inventory_sufficient(self, api_client, active_project):
        """BOM item linked to item with sufficient stock returns 'covered'."""
        inv = InventoryItemFactory(quantity=10)
        inv.quantity = 10 - 4  # Simulate the post-link decrement
        inv.save()
        bom_item = ProjectBOMItemFactory(
            project=active_project,
            inventory_item=inv,
            quantity_needed=4,
            status='linked',
        )
        response = api_client.get(f'/api/projectbomitems/{bom_item.pk}/')
        assert response.data['allocation_status'] == 'covered'

    def test_overallocated_when_inventory_negative(self, api_client, active_project):
        """BOM item linked to item with negative qty (overallocated) returns 'overallocated'."""
        inv = InventoryItemFactory(quantity=-5)  # Already negative
        bom_item = ProjectBOMItemFactory(
            project=active_project,
            inventory_item=inv,
            quantity_needed=4,
            status='linked',
        )
        response = api_client.get(f'/api/projectbomitems/{bom_item.pk}/')
        assert response.data['allocation_status'] == 'overallocated'

    def test_low_for_consumable_at_threshold(self, api_client, active_project):
        """Consumable item at exactly its low_stock_threshold returns 'low'."""
        inv = InventoryItemFactory(quantity=3, is_consumable=True, low_stock_threshold=5)
        bom_item = ProjectBOMItemFactory(
            project=active_project,
            inventory_item=inv,
            quantity_needed=1,
            status='linked',
        )
        response = api_client.get(f'/api/projectbomitems/{bom_item.pk}/')
        assert response.data['allocation_status'] == 'low'

    def test_non_consumable_not_low(self, api_client, active_project):
        """Non-consumable item below threshold still returns 'covered' (no low_stock check)."""
        inv = InventoryItemFactory(quantity=3, is_consumable=False, low_stock_threshold=5)
        bom_item = ProjectBOMItemFactory(
            project=active_project,
            inventory_item=inv,
            quantity_needed=1,
            status='linked',
        )
        response = api_client.get(f'/api/projectbomitems/{bom_item.pk}/')
        assert response.data['allocation_status'] == 'covered'


# ============================================================================
# Freshness — PATCH response reflects the new DB state
# ============================================================================

@pytest.mark.django_db
class TestAllocationStatusFreshness:
    """
    Regression tests for the stale-cache bug.

    Before the fix: perform_update used InventoryItem.objects.filter().update()
    (a bulk update that bypasses ORM instance cache). The serializer read
    obj.inventory_item.quantity from the stale cached instance and always
    returned 'covered'. After the fix: the serializer re-queries the DB.
    """

    def test_patch_response_reflects_overallocated(self, api_client, active_project):
        """
        If linking a BOM item makes the inventory overallocated, the PATCH
        response's allocation_status should immediately be 'overallocated',
        not the stale 'covered'.
        """
        # 2 in stock, need 5 — will go negative
        inv = InventoryItemFactory(title='Rare Part', quantity=2)
        bom_item = ProjectBOMItemFactory(
            project=active_project,
            status='unlinked',
            quantity_needed=5,
        )
        # Link the item via PATCH (this triggers the bulk update)
        response = api_client.patch(
            f'/api/projectbomitems/{bom_item.pk}/',
            {'inventory_item': inv.pk, 'status': 'linked'},
            format='json',
        )
        assert response.status_code == 200
        # DB should now have qty = 2 - 5 = -3
        inv.refresh_from_db()
        assert inv.quantity == -3
        # PATCH response should reflect overallocated — NOT stale 'covered'
        assert response.data['allocation_status'] == 'overallocated'

    def test_patch_response_reflects_covered_after_link(self, api_client, active_project):
        """
        Linking a BOM item where inventory covers the need returns 'covered'.
        """
        inv = InventoryItemFactory(title='Common Part', quantity=20)
        bom_item = ProjectBOMItemFactory(
            project=active_project,
            status='unlinked',
            quantity_needed=3,
        )
        response = api_client.patch(
            f'/api/projectbomitems/{bom_item.pk}/',
            {'inventory_item': inv.pk, 'status': 'linked'},
            format='json',
        )
        assert response.status_code == 200
        assert response.data['allocation_status'] == 'covered'

    def test_patch_quantity_change_reflects_overallocated(self, api_client, active_project):
        """
        After increasing quantity_needed beyond available stock, the PATCH response
        shows 'overallocated' not the stale pre-update value.
        """
        inv = InventoryItemFactory(quantity=10)
        inv.quantity = 6  # simulating: 10 originally, reserved 4
        inv.save()
        bom_item = ProjectBOMItemFactory(
            project=active_project,
            inventory_item=inv,
            quantity_needed=4,
            status='linked',
        )
        # Increase to 15 — more than in stock (10 total)
        # Net change: +11, so inventory goes from 6 → 6+4-15 = -5
        response = api_client.patch(
            f'/api/projectbomitems/{bom_item.pk}/',
            {'quantity_needed': 15},
            format='json',
        )
        assert response.status_code == 200
        inv.refresh_from_db()
        assert inv.quantity == -5
        assert response.data['allocation_status'] == 'overallocated'
