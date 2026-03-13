"""
Tests for ProjectBOMItem model.

Covers model creation, defaults, __str__, validation,
and the relationship to Project and InventoryItem.
"""
import pytest
from django.core.exceptions import ValidationError
from inventory.models import ProjectBOMItem
from inventory.tests.factories import (
    ProjectBOMItemFactory,
    ProjectFactory,
    InventoryItemFactory,
)


@pytest.mark.django_db
class TestProjectBOMItemModel:
    """Test suite for ProjectBOMItem model."""

    def test_create_minimal(self):
        """BOM item requires only project and description."""
        project = ProjectFactory(status='Planning')
        item = ProjectBOMItem.objects.create(
            project=project,
            description='M3×8 SHCS',
        )
        assert item.pk is not None
        assert item.description == 'M3×8 SHCS'

    def test_str_representation(self):
        """__str__ returns 'ProjectName — Description'."""
        project = ProjectFactory(project_name='Voron 2.4')
        item = ProjectBOMItemFactory(project=project, description='M3×8 SHCS')
        assert str(item) == 'Voron 2.4 — M3×8 SHCS'

    def test_default_values(self):
        """Verify defaults: quantity_needed=1, status='unlinked', is_ordered=False."""
        item = ProjectBOMItemFactory()
        assert item.quantity_needed == 1
        assert item.status == 'unlinked'
        assert item.is_ordered is False
        assert item.inventory_item is None

    def test_quantity_needed_minimum_one(self):
        """quantity_needed must be >= 1 (MinValueValidator)."""
        item = ProjectBOMItemFactory(quantity_needed=0)
        with pytest.raises(ValidationError) as exc_info:
            item.full_clean()
        assert 'quantity_needed' in exc_info.value.error_dict

    def test_link_to_inventory_item(self):
        """BOM item can be linked to an InventoryItem."""
        inv_item = InventoryItemFactory(title='NEMA17')
        bom_item = ProjectBOMItemFactory(
            inventory_item=inv_item,
            status='linked',
        )
        assert bom_item.inventory_item == inv_item
        assert bom_item.status == 'linked'

    def test_cascade_delete_project(self):
        """Deleting the project cascades and removes BOM items."""
        project = ProjectFactory(status='Planning')
        ProjectBOMItemFactory(project=project)
        ProjectBOMItemFactory(project=project)

        project_id = project.pk
        project.delete()
        assert ProjectBOMItem.objects.filter(project_id=project_id).count() == 0

    def test_inventory_item_set_null_on_delete(self):
        """Deleting the linked InventoryItem sets inventory_item to NULL."""
        inv_item = InventoryItemFactory()
        bom_item = ProjectBOMItemFactory(inventory_item=inv_item, status='linked')

        inv_item.delete()
        bom_item.refresh_from_db()
        assert bom_item.inventory_item is None

    def test_needs_purchase_status_allowed(self):
        """BOM item can be flagged as needs_purchase without an inventory link."""
        item = ProjectBOMItemFactory(status='needs_purchase', inventory_item=None)
        item.full_clean()  # should not raise
        assert item.status == 'needs_purchase'

    def test_is_ordered_flag_toggles(self):
        """is_ordered flag can be set and cleared."""
        item = ProjectBOMItemFactory(is_ordered=False)
        item.is_ordered = True
        item.save()
        item.refresh_from_db()
        assert item.is_ordered is True

        item.is_ordered = False
        item.save()
        item.refresh_from_db()
        assert item.is_ordered is False

    def test_ordering_by_sort_order(self):
        """Items are ordered by sort_order, then id."""
        project = ProjectFactory(status='Planning')
        item_b = ProjectBOMItemFactory(project=project, sort_order=2)
        item_a = ProjectBOMItemFactory(project=project, sort_order=1)

        ordered = list(ProjectBOMItem.objects.filter(project=project))
        assert ordered[0].pk == item_a.pk
        assert ordered[1].pk == item_b.pk
