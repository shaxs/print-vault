"""
Tests for ExportDataView — GET /api/export/data/

ExportDataView produces a ZIP archive containing CSV files for all
Print Vault data (inventory, printers, projects, trackers, etc.).
Uses defensive error handling so partial failures don't break the export.
"""
import csv
import io
import zipfile
import pytest
from rest_framework.test import APIClient

from inventory.tests.factories import (
    PrinterFactory,
    ProjectFactory,
    ModFactory,
    TrackerFactory,
)
from inventory.models import InventoryItem, Brand, PartType, Location, Tracker


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


# ---------------------------------------------------------------------------
# TestTrackerSettingsExportImport
#
# Regression coverage: generate_thumbnails_for_linked_files and
# viewer_background were originally missing from trackers.csv, so a
# backup/restore cycle silently reset them to defaults.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTrackerSettingsExportImport:
    def _get_csv(self, client, filename):
        response = client.get(URL)
        zf = zipfile.ZipFile(io.BytesIO(response.content), 'r')
        return zf.read(filename).decode('utf-8')

    def test_trackers_csv_has_thumbnail_settings_columns(self, client):
        TrackerFactory()
        csv_content = self._get_csv(client, 'trackers.csv')

        header = next(csv.reader(io.StringIO(csv_content)))
        assert 'generate_thumbnails_for_linked_files' in header
        assert 'viewer_background' in header

    def test_trackers_csv_exports_thumbnail_settings_values(self, client):
        TrackerFactory(
            name="Settings Export Tracker",
            generate_thumbnails_for_linked_files=True,
            viewer_background='light',
        )
        csv_content = self._get_csv(client, 'trackers.csv')

        rows = [
            row for row in csv.DictReader(io.StringIO(csv_content))
            if row['name'] == 'Settings Export Tracker'
        ]
        assert rows, "Tracker not found in trackers.csv"
        assert rows[0]['generate_thumbnails_for_linked_files'] == 'True'
        assert rows[0]['viewer_background'] == 'light'

    def test_round_trip_restores_thumbnail_settings(self, client, settings, tmp_path):
        # Import wipes MEDIA_ROOT — point it at a temp dir before touching
        # the endpoint so the real media folder is never in play.
        settings.MEDIA_ROOT = str(tmp_path)
        TrackerFactory(
            name="Round Trip Tracker",
            generate_thumbnails_for_linked_files=True,
            viewer_background='light',
        )

        backup = io.BytesIO(client.get(URL).content)
        backup.name = 'backup.zip'
        response = client.post('/api/import-data/', {'backup_file': backup}, format='multipart')

        assert response.status_code == 200
        tracker = Tracker.objects.get(name="Round Trip Tracker")
        assert tracker.generate_thumbnails_for_linked_files is True
        assert tracker.viewer_background == 'light'

    def test_import_of_legacy_backup_defaults_new_settings(self, client, settings, tmp_path):
        """Backups created before the new columns existed must still import."""
        settings.MEDIA_ROOT = str(tmp_path)
        old_header = (
            'id,name,project_id,github_url,storage_type,primary_color,accent_color,'
            'total_quantity,printed_quantity_total,progress_percentage,created_date,'
            'updated_date,storage_path,total_storage_used,files_downloaded'
        )
        old_row = (
            '1,Legacy Tracker,,,link,#3B82F6,#EF4444,0,0,0,'
            '2024-01-01 00:00:00,2024-01-01 00:00:00,,0,false'
        )
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('trackers.csv', f'{old_header}\n{old_row}\n')
        zip_buffer.seek(0)
        zip_buffer.name = 'legacy_backup.zip'

        response = client.post('/api/import-data/', {'backup_file': zip_buffer}, format='multipart')

        assert response.status_code == 200
        tracker = Tracker.objects.get(name='Legacy Tracker')
        assert tracker.generate_thumbnails_for_linked_files is False
        assert tracker.viewer_background == 'dark'
