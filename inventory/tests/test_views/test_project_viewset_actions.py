"""
Tests for ProjectViewSet custom actions.

Covers:
  - POST /api/projects/{id}/remove-inventory/  (remove associated inventory item)
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from inventory.models import ProjectInventory
from inventory.tests.factories import (
    ProjectFactory,
    InventoryItemFactory,
)


@pytest.fixture
def api_client():
    """Provide an API client for making requests."""
    return APIClient()


@pytest.fixture
def project_with_inventory(db):
    """Create a project with two associated inventory items."""
    project = ProjectFactory(project_name="Test Project")
    item_a = InventoryItemFactory(title="M3x8 SHCS")
    item_b = InventoryItemFactory(title="608ZZ Bearing")

    # Associate both items via the through table
    pi_a = ProjectInventory.objects.create(project=project, inventory_item=item_a)
    pi_b = ProjectInventory.objects.create(project=project, inventory_item=item_b)

    return {
        "project": project,
        "item_a": item_a,
        "item_b": item_b,
        "pi_a": pi_a,
        "pi_b": pi_b,
    }


# ============================================================================
# REMOVE-INVENTORY ACTION TESTS
# ============================================================================


@pytest.mark.django_db
class TestProjectRemoveInventoryAction:
    """Tests for POST /api/projects/{id}/remove-inventory/"""

    def test_remove_associated_inventory_item(self, api_client, project_with_inventory):
        """Successfully removes a linked inventory item from the project."""
        project = project_with_inventory["project"]
        item_a = project_with_inventory["item_a"]

        url = f"/api/projects/{project.pk}/remove-inventory/"
        response = api_client.post(url, {"inventory_item_id": item_a.pk}, format="json")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ProjectInventory.objects.filter(
            project=project, inventory_item=item_a
        ).exists()

    def test_remove_does_not_affect_other_associations(
        self, api_client, project_with_inventory
    ):
        """Removing one item leaves other associations intact."""
        project = project_with_inventory["project"]
        item_a = project_with_inventory["item_a"]
        item_b = project_with_inventory["item_b"]

        url = f"/api/projects/{project.pk}/remove-inventory/"
        api_client.post(url, {"inventory_item_id": item_a.pk}, format="json")

        # item_b should still be associated
        assert ProjectInventory.objects.filter(
            project=project, inventory_item=item_b
        ).exists()

    def test_remove_nonexistent_association_returns_404(
        self, api_client, project_with_inventory
    ):
        """Trying to remove an item not associated with the project returns 404."""
        project = project_with_inventory["project"]
        unrelated_item = InventoryItemFactory(title="Random Part")

        url = f"/api/projects/{project.pk}/remove-inventory/"
        response = api_client.post(
            url, {"inventory_item_id": unrelated_item.pk}, format="json"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_remove_without_inventory_item_id_returns_400(
        self, api_client, project_with_inventory
    ):
        """Omitting inventory_item_id in the request body returns 400."""
        project = project_with_inventory["project"]
        url = f"/api/projects/{project.pk}/remove-inventory/"
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_remove_with_nonexistent_project_returns_404(self, api_client, db):
        """Trying to remove inventory from a non-existent project returns 404."""
        url = "/api/projects/99999/remove-inventory/"
        response = api_client.post(url, {"inventory_item_id": 1}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_remove_does_not_delete_inventory_item_itself(
        self, api_client, project_with_inventory
    ):
        """Removing an item from a project does NOT delete the InventoryItem record."""
        from inventory.models import InventoryItem

        project = project_with_inventory["project"]
        item_a = project_with_inventory["item_a"]
        item_a_pk = item_a.pk

        url = f"/api/projects/{project.pk}/remove-inventory/"
        api_client.post(url, {"inventory_item_id": item_a.pk}, format="json")

        # The InventoryItem itself must still exist
        assert InventoryItem.objects.filter(pk=item_a_pk).exists()
