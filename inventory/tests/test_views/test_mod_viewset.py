"""
Tests for ModViewSet — /api/mods/

ModViewSet is a full ModelViewSet for Mod objects (printer modifications).
Each Mod belongs to a Printer and has: name, link (optional), status.
"""
import pytest
from rest_framework.test import APIClient

from inventory.tests.factories import ModFactory, PrinterFactory


URL = "/api/mods/"


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def printer(db):
    return PrinterFactory()


# ---------------------------------------------------------------------------
# TestModViewSetList
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestModViewSetList:
    def test_list_returns_200(self, client):
        response = client.get(URL)
        assert response.status_code == 200

    def test_empty_list(self, client):
        response = client.get(URL)
        assert isinstance(response.data, list)
        assert len(response.data) == 0

    def test_list_contains_created_mod(self, client, printer):
        mod = ModFactory(printer=printer, name="Bambu Extruder Mod")
        response = client.get(URL)
        ids = [r["id"] for r in response.data]
        assert mod.id in ids

    def test_list_contains_multiple_mods(self, client, printer):
        m1 = ModFactory(printer=printer)
        m2 = ModFactory(printer=printer)
        response = client.get(URL)
        ids = [r["id"] for r in response.data]
        assert m1.id in ids
        assert m2.id in ids

    def test_response_contains_name_field(self, client, printer):
        ModFactory(printer=printer, name="Direct Drive Upgrade")
        response = client.get(URL)
        assert any(r["name"] == "Direct Drive Upgrade" for r in response.data)

    def test_response_contains_status_field(self, client, printer):
        ModFactory(printer=printer, status="Planned")
        response = client.get(URL)
        assert len(response.data) > 0
        assert "status" in response.data[0]


# ---------------------------------------------------------------------------
# TestModViewSetCreate
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestModViewSetCreate:
    def test_create_mod_returns_201(self, client, printer):
        payload = {
            "printer": printer.id,
            "name": "Hotend Upgrade",
            "status": "Planned",
        }
        response = client.post(URL, payload, format="json")
        assert response.status_code == 201

    def test_create_mod_persisted(self, client, printer):
        payload = {
            "printer": printer.id,
            "name": "Nozzle Upgrade",
            "status": "Planned",
        }
        client.post(URL, payload, format="json")
        response = client.get(URL)
        assert any(r["name"] == "Nozzle Upgrade" for r in response.data)

    def test_create_mod_with_link(self, client, printer):
        payload = {
            "printer": printer.id,
            "name": "Belt Tensioner",
            "status": "In Progress",
            "link": "https://www.printables.com/model/123",
        }
        response = client.post(URL, payload, format="json")
        assert response.status_code == 201
        assert response.data["link"] == "https://www.printables.com/model/123"

    def test_create_mod_without_name_returns_400(self, client, printer):
        payload = {"printer": printer.id, "status": "Planned"}
        response = client.post(URL, payload, format="json")
        assert response.status_code == 400

    def test_create_mod_link_optional(self, client, printer):
        """Link field is optional (null=True, blank=True)."""
        payload = {
            "printer": printer.id,
            "name": "Enclosure Fan",
            "status": "Planned",
        }
        response = client.post(URL, payload, format="json")
        assert response.status_code == 201


# ---------------------------------------------------------------------------
# TestModViewSetRetrieve
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestModViewSetRetrieve:
    def test_retrieve_returns_200(self, client, printer):
        mod = ModFactory(printer=printer)
        response = client.get(f"{URL}{mod.id}/")
        assert response.status_code == 200

    def test_retrieve_correct_data(self, client, printer):
        mod = ModFactory(printer=printer, name="AMS Upgrade")
        response = client.get(f"{URL}{mod.id}/")
        assert response.data["id"] == mod.id
        assert response.data["name"] == "AMS Upgrade"

    def test_retrieve_contains_printer_field(self, client, printer):
        mod = ModFactory(printer=printer)
        response = client.get(f"{URL}{mod.id}/")
        assert "printer" in response.data

    def test_retrieve_nonexistent_returns_404(self, client):
        response = client.get(f"{URL}99999/")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TestModViewSetUpdate
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestModViewSetUpdate:
    def test_patch_name(self, client, printer):
        mod = ModFactory(printer=printer, name="Old Name")
        response = client.patch(f"{URL}{mod.id}/", {"name": "New Name"}, format="json")
        assert response.status_code == 200
        assert response.data["name"] == "New Name"

    def test_patch_status(self, client, printer):
        mod = ModFactory(printer=printer, status="Planned")
        response = client.patch(f"{URL}{mod.id}/", {"status": "Completed"}, format="json")
        assert response.status_code == 200
        assert response.data["status"] == "Completed"

    def test_patch_link(self, client, printer):
        mod = ModFactory(printer=printer)
        new_link = "https://github.com/example/mod"
        response = client.patch(f"{URL}{mod.id}/", {"link": new_link}, format="json")
        assert response.status_code == 200
        assert response.data["link"] == new_link


# ---------------------------------------------------------------------------
# TestModViewSetDelete
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestModViewSetDelete:
    def test_delete_returns_204(self, client, printer):
        mod = ModFactory(printer=printer)
        response = client.delete(f"{URL}{mod.id}/")
        assert response.status_code == 204

    def test_delete_removes_from_db(self, client, printer):
        mod = ModFactory(printer=printer)
        client.delete(f"{URL}{mod.id}/")
        response = client.get(f"{URL}{mod.id}/")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TestModStatusChoices
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize("status_value", ["Planned", "In Progress", "Completed"])
def test_all_valid_statuses_create_successfully(client, status_value):
    printer = PrinterFactory()
    payload = {"printer": printer.id, "name": f"Mod - {status_value}", "status": status_value}
    response = client.post(URL, payload, format="json")
    assert response.status_code == 201
    assert response.data["status"] == status_value
