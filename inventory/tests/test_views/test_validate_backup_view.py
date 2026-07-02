"""
Tests for ValidateBackupView: POST /api/validate-backup/

Validates a ZIP backup file without modifying the database.
Returns: { valid, stats, errors_by_type, total_errors }
"""

import io
import zipfile
import csv
import pytest
from django.urls import reverse
from rest_framework.test import APIClient


URL = "/api/validate-backup/"


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_zip(*csv_files):
    """
    Build an in-memory ZIP bytes containing the given CSV files.
    csv_files: list of (filename, rows_list_of_dicts)
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, rows in csv_files:
            if not rows:
                # Empty CSV with no rows
                text = ""
            else:
                headers = list(rows[0].keys())
                out = io.StringIO()
                writer = csv.DictWriter(out, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
                text = out.getvalue()
            zf.writestr(filename, text)
    buf.seek(0)
    return buf


def post_zip(client, zip_buf, field_name="backup_file", zip_name="backup.zip"):
    zip_buf.seek(0)
    return client.post(
        URL,
        {"backup_file": zip_buf} if field_name == "backup_file" else {field_name: zip_buf},
        format="multipart",
    )


@pytest.fixture
def client():
    return APIClient()


# ── Basics ────────────────────────────────────────────────────────────────────

class TestValidateBackupBasics:
    def test_no_file_returns_400(self, client):
        response = client.post(URL, {}, format="multipart")
        assert response.status_code == 400
        assert "error" in response.data
        assert "No backup file provided" in response.data["error"]

    def test_wrong_field_name_returns_400(self, client):
        """Sending file under wrong key → treated as missing file."""
        buf = make_zip(("projects.csv", [{"id": "1", "project_name": "P"}]))
        response = client.post(URL, {"file": buf}, format="multipart")
        assert response.status_code == 400

    def test_invalid_zip_returns_500(self, client):
        """Non-ZIP bytes → cannot open → 500 error response."""
        bad = io.BytesIO(b"this is not a zip file at all")
        response = client.post(URL, {"backup_file": bad}, format="multipart")
        assert response.status_code == 500
        assert "error" in response.data

    def test_empty_zip_returns_200(self, client):
        """Valid ZIP with no CSV files → 200, valid=True, zero totals."""
        buf = make_zip()
        response = post_zip(client, buf)
        assert response.status_code == 200
        assert response.data["valid"] is True
        assert response.data["total_errors"] == 0
        assert response.data["stats"]["total_records"] == 0

    def test_response_has_required_keys(self, client):
        buf = make_zip()
        response = post_zip(client, buf)
        assert response.status_code == 200
        for key in ("valid", "stats", "errors_by_type", "total_errors"):
            assert key in response.data, f"Missing key: {key}"

    def test_stats_shape(self, client):
        buf = make_zip()
        response = post_zip(client, buf)
        stats = response.data["stats"]
        for key in ("total_records", "valid_records", "invalid_records", "sections"):
            assert key in stats, f"Stats missing key: {key}"


# ── Project CSV Validation ────────────────────────────────────────────────────

class TestProjectCsvValidation:
    def test_valid_projects_csv_accepted(self, client):
        rows = [
            {"id": "1", "project_name": "Alpha"},
            {"id": "2", "project_name": "Beta"},
        ]
        buf = make_zip(("projects.csv", rows))
        response = post_zip(client, buf)
        assert response.status_code == 200
        assert response.data["valid"] is True
        assert response.data["stats"]["sections"]["projects"]["valid"] == 2
        assert response.data["stats"]["sections"]["projects"]["invalid"] == 0

    def test_project_missing_project_name_creates_error(self, client):
        rows = [{"id": "1", "project_name": ""}]
        buf = make_zip(("projects.csv", rows))
        response = post_zip(client, buf)
        assert response.status_code == 200
        assert response.data["valid"] is False
        assert "project" in response.data["errors_by_type"]
        assert response.data["errors_by_type"]["project"]["count"] == 1

    def test_project_missing_id_creates_error(self, client):
        rows = [{"id": "", "project_name": "Alpha"}]
        buf = make_zip(("projects.csv", rows))
        response = post_zip(client, buf)
        assert response.status_code == 200
        assert response.data["valid"] is False
        assert response.data["errors_by_type"]["project"]["count"] == 1

    def test_project_error_sample_shape(self, client):
        rows = [{"id": "", "project_name": ""}]
        buf = make_zip(("projects.csv", rows))
        response = post_zip(client, buf)
        samples = response.data["errors_by_type"]["project"]["samples"]
        assert len(samples) >= 1
        assert "error" in samples[0]
        assert "Missing required fields" in samples[0]["error"]

    def test_projects_section_total_correct(self, client):
        rows = [
            {"id": "1", "project_name": "Good"},
            {"id": "", "project_name": ""},
        ]
        buf = make_zip(("projects.csv", rows))
        response = post_zip(client, buf)
        section = response.data["stats"]["sections"]["projects"]
        assert section["total"] == 2
        assert section["valid"] == 1
        assert section["invalid"] == 1


# ── Printer CSV Validation ────────────────────────────────────────────────────

class TestPrinterCsvValidation:
    def test_valid_printers_csv_accepted(self, client):
        rows = [{"id": "10", "title": "Ender 3"}]
        buf = make_zip(("printers.csv", rows))
        response = post_zip(client, buf)
        assert response.status_code == 200
        assert response.data["stats"]["sections"]["printers"]["valid"] == 1

    def test_printer_missing_title_creates_error(self, client):
        rows = [{"id": "10", "title": ""}]
        buf = make_zip(("printers.csv", rows))
        response = post_zip(client, buf)
        assert response.data["valid"] is False
        assert "printer" in response.data["errors_by_type"]
        assert response.data["errors_by_type"]["printer"]["count"] == 1

    def test_printer_missing_id_creates_error(self, client):
        rows = [{"id": "", "title": "Ender 3"}]
        buf = make_zip(("printers.csv", rows))
        response = post_zip(client, buf)
        assert response.data["valid"] is False
        assert response.data["errors_by_type"]["printer"]["count"] == 1


# ── Inventory CSV Validation ──────────────────────────────────────────────────

class TestInventoryCsvValidation:
    def test_valid_inventory_csv_accepted(self, client):
        rows = [{"id": "5", "title": "PLA Black"}]
        buf = make_zip(("inventory.csv", rows))
        response = post_zip(client, buf)
        assert response.status_code == 200
        assert response.data["stats"]["sections"]["inventory"]["valid"] == 1

    def test_inventory_missing_title_creates_error(self, client):
        rows = [{"id": "5", "title": ""}]
        buf = make_zip(("inventory.csv", rows))
        response = post_zip(client, buf)
        assert response.data["valid"] is False
        assert "inventory" in response.data["errors_by_type"]


# ── Tracker CSV Validation ────────────────────────────────────────────────────

class TestTrackerCsvValidation:
    def test_valid_tracker_with_matching_project(self, client):
        project_rows = [{"id": "1", "project_name": "Proj A"}]
        tracker_rows = [{"id": "100", "name": "Tracker 1", "project_id": "1"}]
        buf = make_zip(("projects.csv", project_rows), ("trackers.csv", tracker_rows))
        response = post_zip(client, buf)
        assert response.status_code == 200
        assert response.data["stats"]["sections"]["trackers"]["valid"] == 1

    def test_tracker_with_unmatched_project_id_creates_error(self, client):
        project_rows = [{"id": "1", "project_name": "Proj A"}]
        tracker_rows = [{"id": "100", "name": "Tracker 1", "project_id": "999"}]
        buf = make_zip(("projects.csv", project_rows), ("trackers.csv", tracker_rows))
        response = post_zip(client, buf)
        assert response.data["valid"] is False
        assert "tracker" in response.data["errors_by_type"]

    def test_tracker_missing_name_creates_error(self, client):
        tracker_rows = [{"id": "100", "name": "", "project_id": ""}]
        buf = make_zip(("trackers.csv", tracker_rows))
        response = post_zip(client, buf)
        assert response.data["valid"] is False
        assert "tracker" in response.data["errors_by_type"]


# ── Relational CSV Validation (depends on parent IDs) ─────────────────────────

class TestRelationalCsvValidation:
    def test_project_links_with_valid_project_id(self, client):
        project_rows = [{"id": "1", "project_name": "P"}]
        link_rows = [{"id": "10", "project_id": "1", "url": "http://x.com"}]
        buf = make_zip(("projects.csv", project_rows), ("project_links.csv", link_rows))
        response = post_zip(client, buf)
        assert response.status_code == 200
        assert response.data["stats"]["sections"]["project_links"]["valid"] == 1

    def test_project_links_with_invalid_project_id(self, client):
        project_rows = [{"id": "1", "project_name": "P"}]
        link_rows = [{"id": "10", "project_id": "999", "url": "http://x.com"}]
        buf = make_zip(("projects.csv", project_rows), ("project_links.csv", link_rows))
        response = post_zip(client, buf)
        assert response.data["valid"] is False
        assert "projectlink" in response.data["errors_by_type"]

    def test_project_files_with_invalid_project_id(self, client):
        project_rows = [{"id": "1", "project_name": "P"}]
        file_rows = [{"id": "20", "project_id": "999", "file": "x.stl"}]
        buf = make_zip(("projects.csv", project_rows), ("project_files.csv", file_rows))
        response = post_zip(client, buf)
        assert response.data["valid"] is False
        assert "projectfile" in response.data["errors_by_type"]

    def test_tracker_files_with_valid_tracker_id(self, client):
        tracker_rows = [{"id": "100", "name": "T1", "project_id": ""}]
        tfile_rows = [{"id": "200", "tracker_id": "100", "file": "x.stl"}]
        buf = make_zip(("trackers.csv", tracker_rows), ("tracker_files.csv", tfile_rows))
        response = post_zip(client, buf)
        assert response.status_code == 200
        assert response.data["stats"]["sections"]["tracker_files"]["valid"] == 1

    def test_tracker_files_with_invalid_tracker_id(self, client):
        tfile_rows = [{"id": "200", "tracker_id": "999", "file": "x.stl"}]
        buf = make_zip(("tracker_files.csv", tfile_rows))
        response = post_zip(client, buf)
        assert response.data["valid"] is False
        assert "trackerfile" in response.data["errors_by_type"]


# ── errors_by_type Format ─────────────────────────────────────────────────────

class TestErrorsByTypeFormat:
    def test_errors_by_type_has_count_samples_has_more(self, client):
        rows = [{"id": "", "project_name": ""}]
        buf = make_zip(("projects.csv", rows))
        response = post_zip(client, buf)
        entry = response.data["errors_by_type"]["project"]
        assert "count" in entry
        assert "samples" in entry
        assert "has_more" in entry

    def test_has_more_false_for_small_error_list(self, client):
        """Fewer than 10 errors → has_more=False."""
        rows = [{"id": "", "project_name": ""}] * 3
        buf = make_zip(("projects.csv", rows))
        response = post_zip(client, buf)
        assert response.data["errors_by_type"]["project"]["has_more"] is False

    def test_has_more_true_for_large_error_list(self, client):
        """More than 10 errors → has_more=True, samples capped at 10."""
        rows = [{"id": "", "project_name": ""}] * 15
        buf = make_zip(("projects.csv", rows))
        response = post_zip(client, buf)
        entry = response.data["errors_by_type"]["project"]
        assert entry["has_more"] is True
        assert entry["count"] == 15
        assert len(entry["samples"]) == 10

    def test_total_errors_matches_sum(self, client):
        """total_errors should equal sum of all type counts."""
        project_rows = [{"id": "", "project_name": ""}, {"id": "1", "project_name": "Good"}]
        printer_rows = [{"id": "", "title": ""}]
        buf = make_zip(("projects.csv", project_rows), ("printers.csv", printer_rows))
        response = post_zip(client, buf)
        total_from_types = sum(
            v["count"] for v in response.data["errors_by_type"].values()
        )
        assert response.data["total_errors"] == total_from_types


# ── stats Accumulation ────────────────────────────────────────────────────────

class TestStatsAccumulation:
    def test_stats_aggregate_across_multiple_sections(self, client):
        project_rows = [{"id": "1", "project_name": "P"}]
        printer_rows = [{"id": "10", "title": "T"}, {"id": "11", "title": "T2"}]
        buf = make_zip(("projects.csv", project_rows), ("printers.csv", printer_rows))
        response = post_zip(client, buf)
        stats = response.data["stats"]
        # 1 project + 2 printers = 3 total
        assert stats["total_records"] == 3
        assert stats["valid_records"] == 3
        assert stats["invalid_records"] == 0

    def test_valid_equals_true_only_when_no_errors(self, client):
        buf = make_zip(("projects.csv", [{"id": "1", "project_name": "OK"}]))
        response = post_zip(client, buf)
        assert response.data["valid"] is True
        assert response.data["total_errors"] == 0

    def test_valid_equals_false_when_errors_present(self, client):
        buf = make_zip(("projects.csv", [{"id": "", "project_name": ""}]))
        response = post_zip(client, buf)
        assert response.data["valid"] is False
        assert response.data["total_errors"] > 0
