"""
Tests for simple lookup viewsets: Brand, PartType, Location, Vendor.

These ModelViewSets share the same pattern:
- GET /api/{resource}/ → list all items
- GET /api/{resource}/{id}/ → retrieve one
- POST /api/{resource}/ → create
- PATCH /api/{resource}/{id}/ → partial update
- DELETE /api/{resource}/{id}/ → delete

All use AllowAny permission and order by name.
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from inventory.models import Brand, PartType, Location, Vendor
from inventory.tests.factories import (
    BrandFactory,
    PartTypeFactory,
    LocationFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


# ──────────────────────────────────────────────────────────────────────────────
# BrandViewSet
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBrandViewSet:
    """Tests for /api/brands/ endpoints."""

    URL = "/api/brands/"

    def test_list_returns_200(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_list_returns_all_brands(self, api_client):
        BrandFactory(name="Bambu Lab")
        BrandFactory(name="Creality")
        resp = api_client.get(self.URL)
        names = [b["name"] for b in resp.data]
        assert "Bambu Lab" in names
        assert "Creality" in names

    def test_list_is_ordered_alphabetically(self, api_client):
        BrandFactory(name="Zebra")
        BrandFactory(name="Alpha")
        resp = api_client.get(self.URL)
        names = [b["name"] for b in resp.data]
        assert names == sorted(names)

    def test_create_brand(self, api_client):
        resp = api_client.post(self.URL, {"name": "Prusament"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert Brand.objects.filter(name="Prusament").exists()

    def test_retrieve_brand(self, api_client):
        brand = BrandFactory(name="Hatchbox")
        resp = api_client.get(f"{self.URL}{brand.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == "Hatchbox"

    def test_partial_update_brand(self, api_client):
        brand = BrandFactory(name="OldName")
        resp = api_client.patch(f"{self.URL}{brand.id}/", {"name": "NewName"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        brand.refresh_from_db()
        assert brand.name == "NewName"

    def test_delete_brand(self, api_client):
        brand = BrandFactory(name="ToDelete")
        resp = api_client.delete(f"{self.URL}{brand.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Brand.objects.filter(id=brand.id).exists()

    def test_retrieve_nonexistent_returns_404(self, api_client):
        resp = api_client.get(f"{self.URL}99999/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ──────────────────────────────────────────────────────────────────────────────
# PartTypeViewSet
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPartTypeViewSet:
    """Tests for /api/parttypes/ endpoints."""

    URL = "/api/parttypes/"

    def test_list_returns_200(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_create_part_type(self, api_client):
        resp = api_client.post(self.URL, {"name": "Nozzle"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert PartType.objects.filter(name="Nozzle").exists()

    def test_retrieve_part_type(self, api_client):
        pt = PartTypeFactory(name="Extruder")
        resp = api_client.get(f"{self.URL}{pt.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == "Extruder"

    def test_list_includes_created_part_type(self, api_client):
        PartTypeFactory(name="Belt")
        resp = api_client.get(self.URL)
        names = [p["name"] for p in resp.data]
        assert "Belt" in names

    def test_delete_part_type(self, api_client):
        pt = PartTypeFactory(name="TempDelete")
        resp = api_client.delete(f"{self.URL}{pt.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not PartType.objects.filter(id=pt.id).exists()

    def test_partial_update_part_type(self, api_client):
        pt = PartTypeFactory(name="Bearing")
        resp = api_client.patch(f"{self.URL}{pt.id}/", {"name": "Linear Bearing"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        pt.refresh_from_db()
        assert pt.name == "Linear Bearing"


# ──────────────────────────────────────────────────────────────────────────────
# LocationViewSet
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLocationViewSet:
    """Tests for /api/locations/ endpoints."""

    URL = "/api/locations/"

    def test_list_returns_200(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_create_location(self, api_client):
        resp = api_client.post(self.URL, {"name": "Workshop Shelf A"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert Location.objects.filter(name="Workshop Shelf A").exists()

    def test_retrieve_location(self, api_client):
        loc = LocationFactory(name="Storage Box 1")
        resp = api_client.get(f"{self.URL}{loc.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == "Storage Box 1"

    def test_list_includes_created_location(self, api_client):
        LocationFactory(name="Drawer C")
        resp = api_client.get(self.URL)
        names = [l["name"] for l in resp.data]
        assert "Drawer C" in names

    def test_delete_location(self, api_client):
        loc = LocationFactory(name="TempLoc")
        resp = api_client.delete(f"{self.URL}{loc.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Location.objects.filter(id=loc.id).exists()

    def test_partial_update_location(self, api_client):
        loc = LocationFactory(name="OldLoc")
        resp = api_client.patch(f"{self.URL}{loc.id}/", {"name": "NewLoc"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        loc.refresh_from_db()
        assert loc.name == "NewLoc"


# ──────────────────────────────────────────────────────────────────────────────
# VendorViewSet
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestVendorViewSet:
    """Tests for /api/vendors/ endpoints."""

    URL = "/api/vendors/"

    def test_list_returns_200(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_create_vendor(self, api_client):
        resp = api_client.post(self.URL, {"name": "Amazon"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert Vendor.objects.filter(name="Amazon").exists()

    def test_retrieve_vendor(self, api_client):
        vendor = Vendor.objects.create(name="eBay")
        resp = api_client.get(f"{self.URL}{vendor.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == "eBay"

    def test_list_includes_created_vendor(self, api_client):
        Vendor.objects.create(name="Aliexpress")
        resp = api_client.get(self.URL)
        names = [v["name"] for v in resp.data]
        assert "Aliexpress" in names

    def test_delete_vendor(self, api_client):
        vendor = Vendor.objects.create(name="TempVendor")
        resp = api_client.delete(f"{self.URL}{vendor.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Vendor.objects.filter(id=vendor.id).exists()

    def test_partial_update_vendor(self, api_client):
        vendor = Vendor.objects.create(name="OldVendor")
        resp = api_client.patch(f"{self.URL}{vendor.id}/", {"name": "NewVendor"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        vendor.refresh_from_db()
        assert vendor.name == "NewVendor"

    def test_retrieve_nonexistent_vendor_returns_404(self, api_client):
        resp = api_client.get(f"{self.URL}99999/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
