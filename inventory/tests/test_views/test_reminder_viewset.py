"""
Tests for ReminderViewSet — GET /api/reminders/

ReminderViewSet is a ReadOnlyViewSet that returns Printer objects
where at least one reminder date (maintenance_reminder_date or
carbon_reminder_date) is set.
"""
import pytest
from datetime import date, timedelta
from rest_framework.test import APIClient

from inventory.tests.factories import PrinterFactory


URL = "/api/reminders/"


@pytest.fixture
def client():
    return APIClient()


# ---------------------------------------------------------------------------
# TestReminderViewSetList
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReminderViewSetList:
    def test_list_returns_200(self, client):
        response = client.get(URL)
        assert response.status_code == 200

    def test_empty_when_no_reminders(self, client):
        """Printers without any reminder date should NOT appear."""
        PrinterFactory(maintenance_reminder_date=None, carbon_reminder_date=None)
        response = client.get(URL)
        assert response.data == []

    def test_includes_printer_with_maintenance_reminder(self, client):
        """Printer with maintenance_reminder_date set should appear."""
        printer = PrinterFactory(
            maintenance_reminder_date=date.today(),
            carbon_reminder_date=None,
        )
        response = client.get(URL)
        ids = [r["id"] for r in response.data]
        assert printer.id in ids

    def test_includes_printer_with_carbon_reminder(self, client):
        """Printer with carbon_reminder_date set should appear."""
        printer = PrinterFactory(
            maintenance_reminder_date=None,
            carbon_reminder_date=date.today(),
        )
        response = client.get(URL)
        ids = [r["id"] for r in response.data]
        assert printer.id in ids

    def test_includes_printer_with_both_reminders(self, client):
        """Printer with both reminder dates set should appear."""
        printer = PrinterFactory(
            maintenance_reminder_date=date.today(),
            carbon_reminder_date=date.today() + timedelta(days=30),
        )
        response = client.get(URL)
        ids = [r["id"] for r in response.data]
        assert printer.id in ids

    def test_excludes_printer_with_no_reminders(self, client):
        """Printer where both reminder dates are null should be excluded."""
        no_reminder = PrinterFactory(
            maintenance_reminder_date=None,
            carbon_reminder_date=None,
        )
        with_reminder = PrinterFactory(
            maintenance_reminder_date=date.today(),
            carbon_reminder_date=None,
        )
        response = client.get(URL)
        ids = [r["id"] for r in response.data]
        assert no_reminder.id not in ids
        assert with_reminder.id in ids

    def test_response_contains_title_field(self, client):
        """Response items should include the printer title."""
        PrinterFactory(
            title="Test Reminder Printer",
            maintenance_reminder_date=date.today(),
            carbon_reminder_date=None,
        )
        response = client.get(URL)
        assert any(r["title"] == "Test Reminder Printer" for r in response.data)

    def test_response_contains_maintenance_reminder_date(self, client):
        """Response items should include the maintenance_reminder_date field."""
        today = date.today()
        PrinterFactory(
            maintenance_reminder_date=today,
            carbon_reminder_date=None,
        )
        response = client.get(URL)
        assert len(response.data) > 0
        first = response.data[0]
        assert "maintenance_reminder_date" in first

    def test_response_contains_carbon_reminder_date(self, client):
        """Response items should include the carbon_reminder_date field."""
        today = date.today()
        PrinterFactory(
            maintenance_reminder_date=None,
            carbon_reminder_date=today,
        )
        response = client.get(URL)
        assert len(response.data) > 0
        first = response.data[0]
        assert "carbon_reminder_date" in first

    def test_multiple_printers_with_reminders_all_included(self, client):
        """Multiple printers with reminders should all be returned."""
        p1 = PrinterFactory(maintenance_reminder_date=date.today(), carbon_reminder_date=None)
        p2 = PrinterFactory(maintenance_reminder_date=None, carbon_reminder_date=date.today())
        p3 = PrinterFactory(maintenance_reminder_date=date.today(), carbon_reminder_date=date.today())
        # One printer without reminder — should NOT appear
        PrinterFactory(maintenance_reminder_date=None, carbon_reminder_date=None)

        response = client.get(URL)
        ids = [r["id"] for r in response.data]
        assert p1.id in ids
        assert p2.id in ids
        assert p3.id in ids
        assert len(ids) == 3

    def test_future_reminder_date_is_included(self, client):
        """Printers with future reminder dates should still appear."""
        future = date.today() + timedelta(days=90)
        printer = PrinterFactory(maintenance_reminder_date=future, carbon_reminder_date=None)
        response = client.get(URL)
        ids = [r["id"] for r in response.data]
        assert printer.id in ids

    def test_past_reminder_date_is_included(self, client):
        """Printers with past reminder dates (overdue) should still appear."""
        past = date.today() - timedelta(days=30)
        printer = PrinterFactory(maintenance_reminder_date=past, carbon_reminder_date=None)
        response = client.get(URL)
        ids = [r["id"] for r in response.data]
        assert printer.id in ids


# ---------------------------------------------------------------------------
# TestReminderViewSetReadOnly  (no write operations allowed)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReminderViewSetReadOnly:
    def test_post_not_allowed(self, client):
        """ReadOnlyViewSet should reject POST requests."""
        response = client.post(URL, {"title": "New Printer"}, format="json")
        assert response.status_code == 405

    def test_retrieve_single_printer_by_id(self, client):
        """GET /api/reminders/<id>/ should return the printer if it has a reminder."""
        printer = PrinterFactory(
            maintenance_reminder_date=date.today(),
            carbon_reminder_date=None,
        )
        response = client.get(f"{URL}{printer.id}/")
        assert response.status_code == 200
        assert response.data["id"] == printer.id

    def test_retrieve_nonexistent_returns_404(self, client):
        """GET /api/reminders/<nonexistent_id>/ should return 404."""
        response = client.get(f"{URL}99999/")
        assert response.status_code == 404
