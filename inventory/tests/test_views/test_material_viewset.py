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
    BrandFactory,
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
# TestMaterialViewSetLowStockFilter
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMaterialViewSetLowStockFilter:
    """Regression tests: ?low_stock=true used to be a no-op (`pass`)."""

    def test_low_stock_filter_returns_only_below_threshold(self, client):
        low = FilamentBlueprintMaterialFactory(name="Low Stock PETG", low_stock_threshold=500)
        FilamentSpoolFactory(
            filament_type=low, status='opened', is_opened=True,
            quantity=1, initial_weight=1000, current_weight=200
        )

        healthy = FilamentBlueprintMaterialFactory(name="Healthy Stock PETG", low_stock_threshold=500)
        FilamentSpoolFactory(
            filament_type=healthy, status='opened', is_opened=True,
            quantity=1, initial_weight=1000, current_weight=900
        )

        response = client.get(URL, {"low_stock": "true", "type": "blueprint"})
        ids = [r["id"] for r in response.data]
        assert low.id in ids
        assert healthy.id not in ids

    def test_low_stock_filter_excludes_material_without_threshold(self, client):
        """A material with no low_stock_threshold set is never considered low stock."""
        no_threshold = FilamentBlueprintMaterialFactory(name="No Threshold PETG", low_stock_threshold=None)
        FilamentSpoolFactory(
            filament_type=no_threshold, status='empty', is_opened=True,
            quantity=1, initial_weight=1000, current_weight=0
        )

        response = client.get(URL, {"low_stock": "true", "type": "blueprint"})
        ids = [r["id"] for r in response.data]
        assert no_threshold.id not in ids

    def test_no_low_stock_param_returns_all(self, client):
        mat = FilamentBlueprintMaterialFactory(name="Any Stock PETG")
        response = client.get(URL, {"type": "blueprint"})
        ids = [r["id"] for r in response.data]
        assert mat.id in ids


# ---------------------------------------------------------------------------
# TestMaterialViewSetLookupFilters (brand / base_material / color_family)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMaterialViewSetLookupFilters:
    """Regression tests: brand/base_material/color_family filters used to be
    inert (no filterset_class was wired up on MaterialViewSet)."""

    def test_brand_filter(self, client):
        brand_a = BrandFactory(name="Prusament")
        brand_b = BrandFactory(name="Overture")
        mat_a = FilamentBlueprintMaterialFactory(name="Brand A Filament", brand=brand_a)
        mat_b = FilamentBlueprintMaterialFactory(name="Brand B Filament", brand=brand_b)

        response = client.get(URL, {"brand": brand_a.id})
        ids = [r["id"] for r in response.data]
        assert mat_a.id in ids
        assert mat_b.id not in ids

    def test_base_material_filter(self, client):
        pla = GenericMaterialFactory(name="PLA")
        petg = GenericMaterialFactory(name="PETG")
        pla_blueprint = FilamentBlueprintMaterialFactory(name="PLA Blueprint", base_material=pla)
        petg_blueprint = FilamentBlueprintMaterialFactory(name="PETG Blueprint", base_material=petg)

        response = client.get(URL, {"base_material": pla.id})
        ids = [r["id"] for r in response.data]
        assert pla_blueprint.id in ids
        assert petg_blueprint.id not in ids

    def test_color_family_filter(self, client):
        red_mat = FilamentBlueprintMaterialFactory(name="Red Filament", color_family="red")
        blue_mat = FilamentBlueprintMaterialFactory(name="Blue Filament", color_family="blue")

        response = client.get(URL, {"color_family": "red"})
        ids = [r["id"] for r in response.data]
        assert red_mat.id in ids
        assert blue_mat.id not in ids


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
