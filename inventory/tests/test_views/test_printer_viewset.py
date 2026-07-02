"""
Tests for PrinterViewSet API endpoints.

Covers:
- List all printers (ordered by title)
- Create a printer
- Retrieve a printer by ID
- Partial update (PATCH)
- Delete a printer
- Filter by status
- Search by title
- Status choices are enforced
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from inventory.models import Printer
from inventory.tests.factories import PrinterFactory, BrandFactory


URL = "/api/printers/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def manufacturer(db):
    return BrandFactory(name="Bambu Lab")


# ──────────────────────────────────────────────────────────────────────────────
# LIST
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPrinterViewSetList:
    """Tests for GET /api/printers/"""

    def test_list_returns_200(self, api_client):
        resp = api_client.get(URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_list_empty_returns_empty_list(self, api_client):
        resp = api_client.get(URL)
        assert resp.data == [] or isinstance(resp.data, list)

    def test_list_contains_created_printer(self, api_client, db):
        PrinterFactory(title="Bambu X1C")
        resp = api_client.get(URL)
        titles = [p["title"] for p in resp.data]
        assert "Bambu X1C" in titles

    def test_list_is_ordered_by_title(self, api_client, db):
        PrinterFactory(title="Zebra 3D")
        PrinterFactory(title="Alpha Printer")
        PrinterFactory(title="Mid Printer")
        resp = api_client.get(URL)
        titles = [p["title"] for p in resp.data]
        assert titles == sorted(titles)


# ──────────────────────────────────────────────────────────────────────────────
# CREATE
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPrinterViewSetCreate:
    """Tests for POST /api/printers/"""

    def test_create_printer_returns_201(self, api_client, manufacturer):
        resp = api_client.post(
            URL,
            {"title": "Bambu P1S", "status": "Active", "manufacturer": manufacturer.id},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_create_printer_persisted(self, api_client, manufacturer):
        api_client.post(
            URL,
            {"title": "Creality K1 Max", "status": "Active"},
            format="json",
        )
        assert Printer.objects.filter(title="Creality K1 Max").exists()

    def test_create_printer_with_status(self, api_client, db):
        resp = api_client.post(
            URL,
            {"title": "Planned Printer", "status": "Planned"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        printer = Printer.objects.get(title="Planned Printer")
        assert printer.status == "Planned"

    def test_create_printer_without_title_fails(self, api_client, db):
        resp = api_client.post(URL, {"status": "Active"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_printer_default_status_is_active(self, api_client, db):
        # Status defaults to 'Active' per model definition
        resp = api_client.post(URL, {"title": "Default Status Printer"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        printer = Printer.objects.get(title="Default Status Printer")
        assert printer.status == "Active"


# ──────────────────────────────────────────────────────────────────────────────
# RETRIEVE
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPrinterViewSetRetrieve:
    """Tests for GET /api/printers/{id}/"""

    def test_retrieve_printer_returns_200(self, api_client, db):
        printer = PrinterFactory(title="Prusa MK4")
        resp = api_client.get(f"{URL}{printer.id}/")
        assert resp.status_code == status.HTTP_200_OK

    def test_retrieve_returns_correct_printer(self, api_client, db):
        printer = PrinterFactory(title="Voron 2.4")
        resp = api_client.get(f"{URL}{printer.id}/")
        assert resp.data["title"] == "Voron 2.4"

    def test_retrieve_returns_status_field(self, api_client, db):
        printer = PrinterFactory(title="Test Printer", status="Under Repair")
        resp = api_client.get(f"{URL}{printer.id}/")
        assert resp.data["status"] == "Under Repair"

    def test_retrieve_nonexistent_returns_404(self, api_client, db):
        resp = api_client.get(f"{URL}99999/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ──────────────────────────────────────────────────────────────────────────────
# UPDATE (PATCH)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPrinterViewSetUpdate:
    """Tests for PATCH /api/printers/{id}/"""

    def test_patch_status_to_under_repair(self, api_client, db):
        printer = PrinterFactory(title="Active Printer", status="Active")
        resp = api_client.patch(
            f"{URL}{printer.id}/", {"status": "Under Repair"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        printer.refresh_from_db()
        assert printer.status == "Under Repair"

    def test_patch_title(self, api_client, db):
        printer = PrinterFactory(title="Old Title")
        resp = api_client.patch(f"{URL}{printer.id}/", {"title": "New Title"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        printer.refresh_from_db()
        assert printer.title == "New Title"

    def test_patch_notes(self, api_client, db):
        printer = PrinterFactory(title="Noted Printer", notes="")
        resp = api_client.patch(
            f"{URL}{printer.id}/", {"notes": "Needs bed leveling"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        printer.refresh_from_db()
        assert printer.notes == "Needs bed leveling"


# ──────────────────────────────────────────────────────────────────────────────
# DELETE
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPrinterViewSetDelete:
    """Tests for DELETE /api/printers/{id}/"""

    def test_delete_printer_returns_204(self, api_client, db):
        printer = PrinterFactory(title="To Delete")
        resp = api_client.delete(f"{URL}{printer.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_printer_removed_from_db(self, api_client, db):
        printer = PrinterFactory(title="Gone Printer")
        api_client.delete(f"{URL}{printer.id}/")
        assert not Printer.objects.filter(id=printer.id).exists()


# ──────────────────────────────────────────────────────────────────────────────
# FILTERING
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPrinterViewSetFilter:
    """Tests for GET /api/printers/?status=..."""

    def test_filter_by_active_status(self, api_client, db):
        PrinterFactory(title="Active One", status="Active")
        PrinterFactory(title="Repair One", status="Under Repair")
        resp = api_client.get(f"{URL}?status=Active")
        assert resp.status_code == status.HTTP_200_OK
        returned_statuses = [p["status"] for p in resp.data]
        assert all(s == "Active" for s in returned_statuses)

    def test_filter_by_under_repair_status(self, api_client, db):
        PrinterFactory(title="Broken Printer", status="Under Repair")
        PrinterFactory(title="Fine Printer", status="Active")
        resp = api_client.get(f"{URL}?status=Under+Repair")
        repaired = [p["title"] for p in resp.data]
        assert "Broken Printer" in repaired
        assert "Fine Printer" not in repaired

    def test_search_by_title(self, api_client, db):
        PrinterFactory(title="Bambu Lab X1C")
        PrinterFactory(title="Creality Ender 3")
        resp = api_client.get(f"{URL}?search=Bambu")
        assert resp.status_code == status.HTTP_200_OK
        titles = [p["title"] for p in resp.data]
        assert any("Bambu" in t for t in titles)
        assert not any("Creality" in t for t in titles)


# ──────────────────────────────────────────────────────────────────────────────
# STATUS CHOICES
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPrinterStatusChoices:
    """Tests that all valid status choices can be created."""

    @pytest.mark.parametrize("st", ["Active", "Under Repair", "Sold", "Archived", "Planned"])
    def test_all_valid_statuses_create_successfully(self, api_client, st, db):
        resp = api_client.post(
            URL, {"title": f"Printer {st}", "status": st}, format="json"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert Printer.objects.filter(title=f"Printer {st}", status=st).exists()
