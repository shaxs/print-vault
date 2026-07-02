"""
Tests for POST /api/inventoryitems/import/

Covers the inventory item CSV bulk import action:
  - Success: valid CSV creates items
  - Success: duplicate title is skipped (get_or_create semantics)
  - Success: FK lookups (brand, part_type, location, vendor) use get_or_create
  - Validation: missing 'file' field → 400
  - Validation: non-CSV file extension → 400
  - Validation: CSV with no 'title' column → 400
  - Validation: empty CSV (no header row) → 400
  - Row error: invalid quantity value → error entry, row not created
  - Row error: invalid cost value → error entry, row not created
  - Row error: missing title value → error entry (or skip)
  - Defaults: missing quantity defaults to 1
  - Defaults: missing cost is stored as None
"""
import io
import pytest
from rest_framework import status as http_status
from rest_framework.test import APIClient
from inventory.models import InventoryItem, Brand, Location, PartType, Vendor


@pytest.fixture
def api_client():
    return APIClient()


def _csv_file(content, filename='inventory.csv'):
    """Return a file-like object for multipart upload."""
    f = io.BytesIO(content.encode('utf-8'))
    f.name = filename
    return f


# ============================================================================
# VALIDATION — request-level errors return 400
# ============================================================================

@pytest.mark.django_db
class TestInventoryImportValidation:
    """Request-level validation for POST /api/inventoryitems/import/."""

    def test_missing_file_returns_400(self, api_client):
        """Sending no file returns 400."""
        response = api_client.post('/api/inventoryitems/import/', {}, format='multipart')
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_non_csv_file_returns_400(self, api_client):
        """Uploading a non-CSV file extension returns 400."""
        f = io.BytesIO(b'title\nPart A\n')
        f.name = 'inventory.xlsx'
        response = api_client.post(
            '/api/inventoryitems/import/', {'file': f}, format='multipart'
        )
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_csv_without_title_column_returns_400(self, api_client):
        """CSV missing required 'title' column returns 400."""
        csv_data = _csv_file('brand,quantity\nAcme,5\n')
        response = api_client.post(
            '/api/inventoryitems/import/', {'file': csv_data}, format='multipart'
        )
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert 'title' in response.data.get('error', '').lower()

    def test_empty_csv_returns_400(self, api_client):
        """An empty CSV file (no header) returns 400."""
        csv_data = _csv_file('')
        response = api_client.post(
            '/api/inventoryitems/import/', {'file': csv_data}, format='multipart'
        )
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST


# ============================================================================
# SUCCESS — items are created
# ============================================================================

@pytest.mark.django_db
class TestInventoryImportSuccess:
    """Inventory CSV import creates items from valid CSV data."""

    def test_valid_csv_creates_items(self, api_client):
        """A full valid CSV row creates an InventoryItem."""
        csv_content = (
            'title,brand,part_type,location,quantity,cost,notes\n'
            'NEMA17 Motor,StepperCo,Stepper Motor,Bin A2,5,12.50,Standard motor\n'
        )
        response = api_client.post(
            '/api/inventoryitems/import/',
            {'file': _csv_file(csv_content)},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data['created'] == 1
        assert response.data['skipped'] == 0
        assert response.data['errors'] == []

        item = InventoryItem.objects.get(title='NEMA17 Motor')
        assert item.quantity == 5
        assert float(item.cost) == 12.50
        assert item.notes == 'Standard motor'
        assert item.brand.name == 'StepperCo'
        assert item.location.name == 'Bin A2'

    def test_fk_lookups_use_get_or_create(self, api_client, db):
        """Brand, location, part_type, vendor are created if they don't exist."""
        csv_content = 'title,brand,location\nMy Part,NewBrand,Shelf 3\n'
        api_client.post(
            '/api/inventoryitems/import/',
            {'file': _csv_file(csv_content)},
            format='multipart',
        )
        assert Brand.objects.filter(name='NewBrand').exists()
        assert Location.objects.filter(name='Shelf 3').exists()

    def test_fk_lookups_reuse_existing(self, api_client, db):
        """Existing Brand/Location are reused (not duplicated)."""
        Brand.objects.create(name='ExistingBrand')
        Location.objects.create(name='ExistingLocation')
        csv_content = 'title,brand,location\nPart X,ExistingBrand,ExistingLocation\n'
        api_client.post(
            '/api/inventoryitems/import/',
            {'file': _csv_file(csv_content)},
            format='multipart',
        )
        assert Brand.objects.filter(name='ExistingBrand').count() == 1
        assert Location.objects.filter(name='ExistingLocation').count() == 1

    def test_duplicate_title_is_skipped(self, api_client, db):
        """An item matching an existing title is skipped (get_or_create skips)."""
        InventoryItem.objects.create(title='Existing Part', quantity=10)
        csv_content = 'title,quantity\nExisting Part,99\n'
        response = api_client.post(
            '/api/inventoryitems/import/',
            {'file': _csv_file(csv_content)},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data['created'] == 0
        assert response.data['skipped'] == 1
        # Original item not modified
        assert InventoryItem.objects.get(title='Existing Part').quantity == 10

    def test_missing_quantity_defaults_to_1(self, api_client):
        """CSV with no quantity column creates item with quantity=1."""
        csv_content = 'title\nBearing 608\n'
        api_client.post(
            '/api/inventoryitems/import/',
            {'file': _csv_file(csv_content)},
            format='multipart',
        )
        assert InventoryItem.objects.get(title='Bearing 608').quantity == 1

    def test_missing_cost_stored_as_none(self, api_client):
        """CSV with no cost column creates item with cost=None."""
        csv_content = 'title\nUncosted Part\n'
        api_client.post(
            '/api/inventoryitems/import/',
            {'file': _csv_file(csv_content)},
            format='multipart',
        )
        assert InventoryItem.objects.get(title='Uncosted Part').cost is None

    def test_excel_bom_utf8_handled(self, api_client):
        """UTF-8 BOM (from Excel export) is stripped correctly."""
        content_with_bom = '\ufefftitle,quantity\nBOM Part,3\n'
        f = io.BytesIO(content_with_bom.encode('utf-8-sig'))
        f.name = 'items.csv'
        response = api_client.post(
            '/api/inventoryitems/import/', {'file': f}, format='multipart'
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert InventoryItem.objects.filter(title='BOM Part').exists()


# ============================================================================
# ROW-LEVEL ERRORS — row not created but import continues
# ============================================================================

@pytest.mark.django_db
class TestInventoryImportRowErrors:
    """Row-level validation errors are collected; valid rows are still imported."""

    def test_invalid_quantity_produces_error_skips_row(self, api_client):
        """Non-integer quantity creates an error entry; row is skipped."""
        csv_content = 'title,quantity\nGood Part,5\nBad Part,not-a-number\n'
        response = api_client.post(
            '/api/inventoryitems/import/',
            {'file': _csv_file(csv_content)},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data['created'] == 1
        assert len(response.data['errors']) == 1
        assert response.data['errors'][0]['title'] == 'Bad Part'

    def test_invalid_cost_produces_error_skips_row(self, api_client):
        """Non-numeric cost creates an error entry; row is skipped."""
        csv_content = 'title,cost\nGood Part,9.99\nBad Part,free!\n'
        response = api_client.post(
            '/api/inventoryitems/import/',
            {'file': _csv_file(csv_content)},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data['created'] == 1
        assert len(response.data['errors']) == 1

    def test_missing_title_value_creates_error(self, api_client):
        """A row with an empty title cell creates an error entry."""
        csv_content = 'title,quantity\n,5\n'
        response = api_client.post(
            '/api/inventoryitems/import/',
            {'file': _csv_file(csv_content)},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data['errors']) == 1
