"""
Tests for ExportDataView — GET /api/export/data/

ExportDataView produces a ZIP archive containing CSV files for all
Print Vault data (inventory, printers, projects, trackers, etc.).
Uses defensive error handling so partial failures don't break the export.
"""
import io
import zipfile
import pytest
from rest_framework.test import APIClient

from inventory.tests.factories import (
    PrinterFactory,
    ProjectFactory,
    ModFactory,
)
from inventory.models import InventoryItem, Brand, PartType, Location


URL = "/api/export/data/"


@pytest.fixture
def client():
    return APIClient()


# ---------------------------------------------------------------------------
# TestExportDataViewBasic
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExportDataViewBasic:
    def test_export_returns_200(self, client):
        response = client.get(URL)
        assert response.status_code == 200

    def test_export_content_type_is_zip(self, client):
        response = client.get(URL)
        assert response['Content-Type'] == 'application/zip'

    def test_export_content_disposition_is_attachment(self, client):
        response = client.get(URL)
        disposition = response['Content-Disposition']
        assert 'attachment' in disposition

    def test_export_filename_contains_print_vault_backup(self, client):
        response = client.get(URL)
        disposition = response['Content-Disposition']
        assert 'print-vault-backup' in disposition

    def test_export_filename_ends_with_zip(self, client):
        response = client.get(URL)
        disposition = response['Content-Disposition']
        assert '.zip' in disposition

    def test_export_response_is_non_empty(self, client):
        response = client.get(URL)
        assert len(response.content) > 0


# ---------------------------------------------------------------------------
# TestExportDataViewZipContents
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExportDataViewZipContents:
    def _get_zip(self, client):
        response = client.get(URL)
        return zipfile.ZipFile(io.BytesIO(response.content), 'r')

    def test_zip_is_valid(self, client):
        """Response content should be a valid ZIP file."""
        assert zipfile.is_zipfile(io.BytesIO(client.get(URL).content))

    def test_zip_contains_inventory_csv(self, client):
        zf = self._get_zip(client)
        assert 'inventory.csv' in zf.namelist()

    def test_zip_contains_printers_csv(self, client):
        zf = self._get_zip(client)
        assert 'printers.csv' in zf.namelist()

    def test_zip_contains_mods_csv(self, client):
        zf = self._get_zip(client)
        assert 'mods.csv' in zf.namelist()

    def test_zip_contains_projects_csv(self, client):
        zf = self._get_zip(client)
        assert 'projects.csv' in zf.namelist()

    def test_zip_contains_trackers_csv(self, client):
        zf = self._get_zip(client)
        assert 'trackers.csv' in zf.namelist()

    def test_zip_contains_tracker_files_csv(self, client):
        zf = self._get_zip(client)
        assert 'tracker_files.csv' in zf.namelist()

    def test_zip_contains_project_links_csv(self, client):
        zf = self._get_zip(client)
        assert 'project_links.csv' in zf.namelist()

    def test_zip_no_error_file_when_no_errors(self, client):
        """EXPORT_ERRORS.txt should NOT be present in a clean export."""
        zf = self._get_zip(client)
        assert 'EXPORT_ERRORS.txt' not in zf.namelist()


# ---------------------------------------------------------------------------
# TestExportDataViewCSVContent
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExportDataViewCSVContent:
    def _get_csv(self, client, filename):
        response = client.get(URL)
        zf = zipfile.ZipFile(io.BytesIO(response.content), 'r')
        return zf.read(filename).decode('utf-8')

    def test_inventory_csv_has_header_row(self, client):
        csv_content = self._get_csv(client, 'inventory.csv')
        assert 'id' in csv_content
        assert 'title' in csv_content

    def test_printers_csv_has_header_row(self, client):
        csv_content = self._get_csv(client, 'printers.csv')
        assert 'id' in csv_content
        assert 'title' in csv_content

    def test_printers_csv_includes_printer_data(self, client):
        PrinterFactory(title="Test Export Printer")
        csv_content = self._get_csv(client, 'printers.csv')
        assert 'Test Export Printer' in csv_content

    def test_projects_csv_has_header_row(self, client):
        csv_content = self._get_csv(client, 'projects.csv')
        assert 'id' in csv_content
        assert 'project_name' in csv_content

    def test_projects_csv_includes_project_data(self, client):
        ProjectFactory(project_name="Test Export Project")
        csv_content = self._get_csv(client, 'projects.csv')
        assert 'Test Export Project' in csv_content

    def test_mods_csv_has_header_row(self, client):
        csv_content = self._get_csv(client, 'mods.csv')
        assert 'id' in csv_content

    def test_mods_csv_includes_mod_data(self, client):
        printer = PrinterFactory()
        ModFactory(printer=printer, name="Exported Mod")
        csv_content = self._get_csv(client, 'mods.csv')
        assert 'Exported Mod' in csv_content
