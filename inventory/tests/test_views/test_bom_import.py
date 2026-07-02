"""
Tests for POST /api/projectbomitems/import/

Covers the BOM CSV bulk import action:
  - Success: valid CSV creates items with correct field mapping
  - Success: items append after any existing items (sort_order continues from max)
  - Validation: missing 'project' field → 400
  - Validation: missing 'file' field → 400
  - Validation: CSV with no 'description' column → 400
  - Validation: empty description rows are silently skipped
  - Validation: invalid quantity_needed → error entry (row not created)
  - Validation: invalid status value → error entry (row not created)
  - Defaults: missing quantity_needed defaults to 1
  - Defaults: missing status defaults to 'unlinked'
  - Feature: 'needs_purchase' is a valid importable status
  - Feature: notes column is optional
"""
import io
import pytest
from rest_framework import status as http_status
from rest_framework.test import APIClient
from inventory.models import ProjectBOMItem
from inventory.tests.factories import ProjectFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def active_project(db):
    return ProjectFactory(project_name='Import Test Build', status='Planning')


def _csv_file(content, filename='bom.csv'):
    """Return a file-like object for multipart upload."""
    f = io.BytesIO(content.encode('utf-8'))
    f.name = filename
    return f


# ============================================================================
# VALIDATION — request-level errors return 400
# ============================================================================

@pytest.mark.django_db
class TestBOMImportValidation:
    """Request-level validation for POST /api/projectbomitems/import/."""

    def test_missing_project_returns_400(self, api_client, active_project):
        """Omitting the 'project' field returns 400."""
        csv_data = _csv_file('description,quantity_needed\nNEMA17,2\n')
        response = api_client.post(
            '/api/projectbomitems/import/',
            {'file': csv_data},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert 'project' in response.data.get('error', '').lower()

    def test_missing_file_returns_400(self, api_client, active_project):
        """Omitting the 'file' field returns 400."""
        response = api_client.post(
            '/api/projectbomitems/import/',
            {'project': active_project.pk},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert 'file' in response.data.get('error', '').lower()

    def test_nonexistent_project_returns_404(self, api_client, db):
        """Providing a non-existent project PK returns 404."""
        csv_data = _csv_file('description,quantity_needed\nNEMA17,2\n')
        response = api_client.post(
            '/api/projectbomitems/import/',
            {'project': 99999, 'file': csv_data},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_404_NOT_FOUND

    def test_csv_without_description_column_returns_400(self, api_client, active_project):
        """CSV missing the required 'description' column returns 400."""
        csv_data = _csv_file('quantity_needed,notes\n2,some note\n')
        response = api_client.post(
            '/api/projectbomitems/import/',
            {'project': active_project.pk, 'file': csv_data},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert 'description' in response.data.get('error', '').lower()

    def test_empty_csv_returns_400(self, api_client, active_project):
        """An empty CSV file (no headers) returns 400."""
        csv_data = _csv_file('')
        response = api_client.post(
            '/api/projectbomitems/import/',
            {'project': active_project.pk, 'file': csv_data},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST


# ============================================================================
# SUCCESS — rows are created
# ============================================================================

@pytest.mark.django_db
class TestBOMImportSuccess:
    """BOM CSV import creates items from valid CSV data."""

    def test_valid_csv_creates_items(self, api_client, active_project):
        """Full valid CSV creates BOM items and returns counts."""
        csv_content = (
            'description,quantity_needed,status,notes\n'
            'NEMA17 Stepper,4,unlinked,Main motors\n'
            'M3 Hex Nut,20,needs_purchase,\n'
        )
        response = api_client.post(
            '/api/projectbomitems/import/',
            {'project': active_project.pk, 'file': _csv_file(csv_content)},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data['created'] == 2
        assert response.data['skipped'] == 0
        assert response.data['errors'] == []

        items = ProjectBOMItem.objects.filter(project=active_project).order_by('sort_order')
        assert items.count() == 2
        motor = items.get(description='NEMA17 Stepper')
        assert motor.quantity_needed == 4
        assert motor.status == 'unlinked'
        assert motor.notes == 'Main motors'

    def test_minimal_csv_uses_defaults(self, api_client, active_project):
        """CSV with only 'description' column uses defaults: qty=1, status=unlinked."""
        csv_content = 'description\nLinear Rail\n'
        response = api_client.post(
            '/api/projectbomitems/import/',
            {'project': active_project.pk, 'file': _csv_file(csv_content)},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data['created'] == 1

        item = ProjectBOMItem.objects.get(project=active_project, description='Linear Rail')
        assert item.quantity_needed == 1
        assert item.status == 'unlinked'

    def test_needs_purchase_status_is_imported(self, api_client, active_project):
        """'needs_purchase' is a valid status value that can be imported."""
        csv_content = 'description,status\nPTFE Tube,needs_purchase\n'
        response = api_client.post(
            '/api/projectbomitems/import/',
            {'project': active_project.pk, 'file': _csv_file(csv_content)},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_200_OK
        item = ProjectBOMItem.objects.get(project=active_project, description='PTFE Tube')
        assert item.status == 'needs_purchase'

    def test_sort_order_continues_after_existing(self, api_client, active_project):
        """Imported items append after existing BOM items (sort_order is max+1...)."""
        # Create two existing items with sort_order 0 and 1
        ProjectBOMItem.objects.create(
            project=active_project, description='Existing A', quantity_needed=1,
            status='unlinked', sort_order=0,
        )
        ProjectBOMItem.objects.create(
            project=active_project, description='Existing B', quantity_needed=1,
            status='unlinked', sort_order=1,
        )
        csv_content = 'description,quantity_needed\nImported C,1\nImported D,2\n'
        api_client.post(
            '/api/projectbomitems/import/',
            {'project': active_project.pk, 'file': _csv_file(csv_content)},
            format='multipart',
        )
        items = list(ProjectBOMItem.objects.filter(project=active_project).order_by('sort_order'))
        assert [i.description for i in items] == ['Existing A', 'Existing B', 'Imported C', 'Imported D']
        assert items[2].sort_order == 2
        assert items[3].sort_order == 3

    def test_empty_description_rows_are_skipped(self, api_client, active_project):
        """Rows with an empty description are counted as skipped, not errored."""
        csv_content = 'description,quantity_needed\nReal Part,2\n,3\n'
        response = api_client.post(
            '/api/projectbomitems/import/',
            {'project': active_project.pk, 'file': _csv_file(csv_content)},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data['created'] == 1
        assert response.data['skipped'] == 1
        assert ProjectBOMItem.objects.filter(project=active_project).count() == 1


# ============================================================================
# ROW-LEVEL ERRORS — row not created but import continues
# ============================================================================

@pytest.mark.django_db
class TestBOMImportRowErrors:
    """Row-level errors are collected; other valid rows are still imported."""

    def test_invalid_quantity_produces_error_entry(self, api_client, active_project):
        """A non-integer quantity_needed is reported as an error; row is skipped."""
        csv_content = 'description,quantity_needed\nGood Part,2\nBad Part,abc\n'
        response = api_client.post(
            '/api/projectbomitems/import/',
            {'project': active_project.pk, 'file': _csv_file(csv_content)},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data['created'] == 1
        assert len(response.data['errors']) == 1
        assert response.data['errors'][0]['description'] == 'Bad Part'

    def test_invalid_status_produces_error_entry(self, api_client, active_project):
        """A status value other than 'unlinked'/'needs_purchase' is an error."""
        csv_content = 'description,status\nGood Part,unlinked\nBad Status,linked\n'
        response = api_client.post(
            '/api/projectbomitems/import/',
            {'project': active_project.pk, 'file': _csv_file(csv_content)},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data['created'] == 1
        assert len(response.data['errors']) == 1

    def test_zero_quantity_produces_error_entry(self, api_client, active_project):
        """quantity_needed of 0 (< 1) is treated as an error."""
        csv_content = 'description,quantity_needed\nBad Qty,0\n'
        response = api_client.post(
            '/api/projectbomitems/import/',
            {'project': active_project.pk, 'file': _csv_file(csv_content)},
            format='multipart',
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data['created'] == 0
        assert len(response.data['errors']) == 1
