"""
Tests for MaterialViewSet — /api/materials/

MaterialViewSet supports:
- Full CRUD
- ?type=generic → filter to generic materials only
- ?type=blueprint → filter to blueprints only
- ?favorites=true → filter to favorites, ordered by favorite_order
- POST /api/materials/<id>/toggle-favorite/ → toggle favorite status
- GET  /api/materials/<id>/spools/ → list spools for a blueprint
"""
import pytest
from rest_framework.test import APIClient

from inventory.tests.factories import (
    FilamentBlueprintMaterialFactory,
    GenericMaterialFactory,
    FilamentSpoolFactory,
)
from inventory.models import Material


URL = "/api/materials/"
TOGGLE_FAVORITE_URL = lambda pk: f"/api/materials/{pk}/toggle-favorite/"
SPOOLS_URL = lambda pk: f"/api/materials/{pk}/spools/"


@pytest.fixture
def client():
    return APIClient()


# ---------------------------------------------------------------------------
# TestMaterialViewSetList
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMaterialViewSetList:
    def test_list_returns_200(self, client):
        response = client.get(URL)
        assert response.status_code == 200

    def test_list_contains_generic_material(self, client):
        mat = GenericMaterialFactory(name="TestPLA")
        response = client.get(URL)
        names = [r["name"] for r in response.data]
        assert "TestPLA" in names

    def test_list_contains_blueprint_material(self, client):
        bp = FilamentBlueprintMaterialFactory(name="Special PETG Blueprint")
        response = client.get(URL)
        ids = [r["id"] for r in response.data]
        assert bp.id in ids


# ---------------------------------------------------------------------------
# TestMaterialViewSetTypeFilter
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMaterialViewSetTypeFilter:
    def test_type_generic_returns_only_generics(self, client):
        generic = GenericMaterialFactory(name="PETG-Generic")
        blueprint = FilamentBlueprintMaterialFactory(name="PETG-Blueprint")
        response = client.get(URL, {"type": "generic"})
        ids = [r["id"] for r in response.data]
        assert generic.id in ids
        assert blueprint.id not in ids

    def test_type_blueprint_returns_only_blueprints(self, client):
        generic = GenericMaterialFactory(name="ABS-Generic")
        blueprint = FilamentBlueprintMaterialFactory(name="ABS-Blueprint")
        response = client.get(URL, {"type": "blueprint"})
        ids = [r["id"] for r in response.data]
        assert blueprint.id in ids
        assert generic.id not in ids

    def test_no_type_filter_returns_both(self, client):
        generic = GenericMaterialFactory(name="TPU-Generic")
        blueprint = FilamentBlueprintMaterialFactory(name="TPU-Blueprint")
        response = client.get(URL)
        ids = [r["id"] for r in response.data]
        assert generic.id in ids
        assert blueprint.id in ids


# ---------------------------------------------------------------------------
# TestMaterialViewSetFavoritesFilter
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMaterialViewSetFavoritesFilter:
    def test_favorites_filter_returns_only_favorites(self, client):
        fav = FilamentBlueprintMaterialFactory(is_favorite=True, favorite_order=1)
        non_fav = FilamentBlueprintMaterialFactory(is_favorite=False)
        response = client.get(URL, {"favorites": "true"})
        ids = [r["id"] for r in response.data]
        assert fav.id in ids
        assert non_fav.id not in ids

    def test_favorites_filter_excluded_when_false_not_set(self, client):
        """Without favorites=true param, non-favorites are included."""
        non_fav = FilamentBlueprintMaterialFactory(is_favorite=False)
        response = client.get(URL)
        ids = [r["id"] for r in response.data]
        assert non_fav.id in ids


# ---------------------------------------------------------------------------
# TestMaterialViewSetRetrieve
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMaterialViewSetRetrieve:
    def test_retrieve_returns_200(self, client):
        mat = GenericMaterialFactory(name="PLA")
        response = client.get(f"{URL}{mat.id}/")
        assert response.status_code == 200

    def test_retrieve_correct_data(self, client):
        mat = FilamentBlueprintMaterialFactory(name="Galaxy Black PETG")
        response = client.get(f"{URL}{mat.id}/")
        assert response.data["id"] == mat.id
        assert response.data["name"] == "Galaxy Black PETG"

    def test_retrieve_nonexistent_returns_404(self, client):
        response = client.get(f"{URL}99999/")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TestMaterialViewSetToggleFavorite
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMaterialToggleFavorite:
    def test_toggle_favorite_on_blueprint(self, client):
        mat = FilamentBlueprintMaterialFactory(is_favorite=False)
        response = client.post(TOGGLE_FAVORITE_URL(mat.id))
        assert response.status_code == 200
        assert response.data["status"] == "favorited"

    def test_toggle_favorite_sets_order(self, client):
        mat = FilamentBlueprintMaterialFactory(is_favorite=False)
        response = client.post(TOGGLE_FAVORITE_URL(mat.id))
        assert response.data["order"] >= 1

    def test_toggle_unfavorite(self, client):
        mat = FilamentBlueprintMaterialFactory(is_favorite=True, favorite_order=1)
        response = client.post(TOGGLE_FAVORITE_URL(mat.id))
        assert response.status_code == 200
        assert response.data["status"] == "unfavorited"

    def test_toggle_favorite_generic_material_returns_400(self, client):
        """Generic materials cannot be favorited."""
        mat = GenericMaterialFactory(name="PLA")
        response = client.post(TOGGLE_FAVORITE_URL(mat.id))
        assert response.status_code == 400
        assert "Cannot favorite generic materials" in response.data["error"]

    def test_max_5_favorites_returns_400(self, client):
        """Cannot add a 6th favorite."""
        # Create 5 favorites
        for i in range(5):
            FilamentBlueprintMaterialFactory(is_favorite=True, favorite_order=i + 1)
        # Try to favorite a 6th
        sixth = FilamentBlueprintMaterialFactory(is_favorite=False)
        response = client.post(TOGGLE_FAVORITE_URL(sixth.id))
        assert response.status_code == 400
        assert "Maximum 5 favorites" in response.data["error"]

    def test_toggle_on_nonexistent_returns_404(self, client):
        response = client.post(TOGGLE_FAVORITE_URL(99999))
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TestMaterialViewSetSpoolsAction
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMaterialSpoolsAction:
    def test_spools_on_generic_returns_400(self, client):
        """Generic materials have no spools."""
        mat = GenericMaterialFactory(name="PLA")
        response = client.get(SPOOLS_URL(mat.id))
        assert response.status_code == 400
        assert "Generic materials" in response.data["error"]

    def test_spools_on_blueprint_returns_200(self, client):
        mat = FilamentBlueprintMaterialFactory()
        response = client.get(SPOOLS_URL(mat.id))
        assert response.status_code == 200

    def test_spools_returns_linked_spools(self, client):
        mat = FilamentBlueprintMaterialFactory()
        spool = FilamentSpoolFactory(filament_type=mat)
        response = client.get(SPOOLS_URL(mat.id))
        ids = [r["id"] for r in response.data]
        assert spool.id in ids

    def test_spools_on_nonexistent_returns_404(self, client):
        response = client.get(SPOOLS_URL(99999))
        assert response.status_code == 404
