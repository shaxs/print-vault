"""
Tests for DismissAlertView, DismissAllAlertsView API endpoints
and the parse_date utility function.

Covers:
- DismissAlertView POST: valid dismissal, missing fields, state hash stored
- DismissAllAlertsView POST: batch dismissal, invalid input, count returned
- parse_date: multiple date formats, empty/None handling
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from inventory.models import AlertDismissal
from inventory.views import parse_date


@pytest.fixture
def api_client():
    return APIClient()


# ──────────────────────────────────────────────────────────────────────────────
# parse_date()
# ──────────────────────────────────────────────────────────────────────────────

class TestParseDate:
    """Tests for parse_date() utility function."""

    def test_parses_iso_format(self):
        result = parse_date("2025-06-15")
        assert result is not None
        assert result.year == 2025
        assert result.month == 6
        assert result.day == 15

    def test_parses_us_format(self):
        result = parse_date("06/15/2025")
        assert result is not None
        assert result.year == 2025
        assert result.month == 6
        assert result.day == 15

    def test_parses_european_format(self):
        result = parse_date("15/06/2025")
        assert result is not None
        assert result.day == 15
        assert result.month == 6
        assert result.year == 2025

    def test_returns_none_for_empty_string(self):
        assert parse_date("") is None

    def test_returns_none_for_none(self):
        assert parse_date(None) is None

    def test_returns_none_for_whitespace_only(self):
        assert parse_date("   ") is None

    def test_returns_none_for_invalid_date(self):
        assert parse_date("not-a-date") is None

    def test_returns_none_for_partial_date(self):
        # "2025-06" doesn't match any supported format
        assert parse_date("2025-06") is None

    def test_strips_whitespace_around_date(self):
        result = parse_date("  2025-06-15  ")
        assert result is not None
        assert result.year == 2025


# ──────────────────────────────────────────────────────────────────────────────
# DismissAlertView
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDismissAlertView:
    """Tests for POST /api/dismiss-alert/"""

    URL = "/api/alerts/dismiss/"

    def test_requires_alert_type(self, api_client):
        resp = api_client.post(self.URL, {"alert_id": "printer_repair_1"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "required" in resp.data["error"].lower()

    def test_requires_alert_id(self, api_client):
        resp = api_client.post(self.URL, {"alert_type": "printer_repair"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "required" in resp.data["error"].lower()

    def test_both_fields_missing_returns_400(self, api_client):
        resp = api_client.post(self.URL, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_valid_dismissal_returns_200(self, api_client):
        resp = api_client.post(
            self.URL,
            {
                "alert_type": "printer_repair",
                "alert_id": "printer_repair_1",
                "state_data": {"id": 1, "status": "Under Repair"},
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["success"] is True

    def test_dismissal_response_contains_alert_info(self, api_client):
        resp = api_client.post(
            self.URL,
            {
                "alert_type": "printer_repair",
                "alert_id": "printer_repair_7",
                "state_data": {},
            },
            format="json",
        )
        dismissed = resp.data["dismissed"]
        assert dismissed["alert_type"] == "printer_repair"
        assert dismissed["alert_id"] == "printer_repair_7"

    def test_dismissal_creates_database_record(self, api_client):
        api_client.post(
            self.URL,
            {
                "alert_type": "printer_repair",
                "alert_id": "printer_repair_42",
            },
            format="json",
        )
        assert AlertDismissal.objects.filter(
            alert_type="printer_repair", alert_id="printer_repair_42"
        ).exists()

    def test_repeated_dismissal_upserts_record(self, api_client):
        payload = {
            "alert_type": "low_stock",
            "alert_id": "low_stock_5",
            "state_data": {"quantity": 2},
        }
        api_client.post(self.URL, payload, format="json")
        api_client.post(self.URL, payload, format="json")
        # Should have exactly one record (upserted, not duplicated)
        count = AlertDismissal.objects.filter(
            alert_type="low_stock", alert_id="low_stock_5"
        ).count()
        assert count == 1

    def test_state_data_produces_state_hash(self, api_client):
        resp = api_client.post(
            self.URL,
            {
                "alert_type": "overdue_project",
                "alert_id": "overdue_project_3",
                "state_data": {"id": 3, "due_date": "2025-01-01"},
            },
            format="json",
        )
        assert resp.data["dismissed"]["state_hash"] is not None

    def test_empty_state_data_still_succeeds(self, api_client):
        resp = api_client.post(
            self.URL,
            {"alert_type": "test_type", "alert_id": "test_id_1"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK


# ──────────────────────────────────────────────────────────────────────────────
# DismissAllAlertsView
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDismissAllAlertsView:
    """Tests for POST /api/dismiss-all-alerts/"""

    URL = "/api/alerts/dismiss-all/"

    def test_requires_alerts_array(self, api_client):
        resp = api_client.post(self.URL, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "required" in resp.data["error"].lower()

    def test_empty_alerts_array_returns_400(self, api_client):
        resp = api_client.post(self.URL, {"alerts": []}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_list_alerts_returns_400(self, api_client):
        resp = api_client.post(self.URL, {"alerts": "not-a-list"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_valid_batch_returns_200(self, api_client):
        resp = api_client.post(
            self.URL,
            {
                "alerts": [
                    {"alert_type": "printer_repair", "alert_id": "printer_repair_1"},
                    {"alert_type": "low_stock", "alert_id": "low_stock_2"},
                ]
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["success"] is True

    def test_returns_dismissed_count(self, api_client):
        resp = api_client.post(
            self.URL,
            {
                "alerts": [
                    {"alert_type": "printer_repair", "alert_id": "printer_repair_1"},
                    {"alert_type": "low_stock", "alert_id": "low_stock_2"},
                    {"alert_type": "overdue", "alert_id": "overdue_3"},
                ]
            },
            format="json",
        )
        assert resp.data["dismissed_count"] == 3

    def test_creates_database_records_for_each_alert(self, api_client):
        api_client.post(
            self.URL,
            {
                "alerts": [
                    {"alert_type": "batch_type", "alert_id": "batch_1"},
                    {"alert_type": "batch_type", "alert_id": "batch_2"},
                ]
            },
            format="json",
        )
        assert AlertDismissal.objects.filter(alert_type="batch_type").count() == 2

    def test_skips_alerts_missing_required_fields(self, api_client):
        """Alerts missing alert_type or alert_id are skipped silently."""
        resp = api_client.post(
            self.URL,
            {
                "alerts": [
                    {"alert_type": "valid_type", "alert_id": "valid_1"},
                    {"alert_id": "missing_type"},   # no alert_type → skipped
                    {"alert_type": "missing_id"},   # no alert_id → skipped
                ]
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["dismissed_count"] == 1

    def test_single_alert_batch(self, api_client):
        resp = api_client.post(
            self.URL,
            {"alerts": [{"alert_type": "single", "alert_id": "single_1"}]},
            format="json",
        )
        assert resp.data["dismissed_count"] == 1
