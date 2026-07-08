"""
Tests for the AppConfiguration singleton (sidebar module visibility) feature.

Covers:
- AppConfiguration model: singleton behaviour (pk pinned to 1), load(), default.
- AppConfigurationSerializer: hideable allow-list validation + de-duplication.
- GET/PATCH /api/app-config/ endpoint: read default, persist, reject bad keys.
- Backup export/restore round-trip for the app_config.json section.

See chat_docs/planning/MODULE_VISIBILITY_FEATURE_PLAN.md.
"""
import json
import zipfile
from io import BytesIO

import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from inventory.models import AppConfiguration, HIDEABLE_MODULE_KEYS
from inventory.serializers import AppConfigurationSerializer


@pytest.fixture
def api_client():
    return APIClient()


# ──────────────────────────────────────────────────────────────────────────────
# Model
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAppConfigurationModel:
    def test_save_pins_pk_to_1(self):
        config = AppConfiguration()
        config.save()
        assert config.pk == 1

    def test_two_saves_leave_one_row(self):
        AppConfiguration().save()
        AppConfiguration().save()
        assert AppConfiguration.objects.count() == 1

    def test_load_returns_singleton(self):
        config = AppConfiguration.load()
        assert config.pk == 1
        # A second load() returns the same row, not a new one.
        assert AppConfiguration.load().pk == 1
        assert AppConfiguration.objects.count() == 1

    def test_default_hidden_modules_is_empty_list(self):
        assert AppConfiguration.load().hidden_modules == []


# ──────────────────────────────────────────────────────────────────────────────
# Serializer
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAppConfigurationSerializer:
    def test_valid_subset_accepted(self):
        serializer = AppConfigurationSerializer(data={"hidden_modules": ["inventory", "printers"]})
        assert serializer.is_valid(), serializer.errors

    def test_empty_list_accepted(self):
        serializer = AppConfigurationSerializer(data={"hidden_modules": []})
        assert serializer.is_valid(), serializer.errors

    def test_unknown_key_rejected(self):
        serializer = AppConfigurationSerializer(data={"hidden_modules": ["bogus"]})
        assert not serializer.is_valid()
        assert "hidden_modules" in serializer.errors

    def test_settings_key_rejected(self):
        # Settings must never be hideable — anti-lockout guarantee.
        serializer = AppConfigurationSerializer(data={"hidden_modules": ["settings"]})
        assert not serializer.is_valid()

    def test_dashboard_key_rejected(self):
        # Dashboard is the root-URL landing target and stays always-visible.
        serializer = AppConfigurationSerializer(data={"hidden_modules": ["dashboard"]})
        assert not serializer.is_valid()

    def test_non_list_rejected(self):
        serializer = AppConfigurationSerializer(data={"hidden_modules": "inventory"})
        assert not serializer.is_valid()

    def test_duplicates_deduped_preserving_order(self):
        serializer = AppConfigurationSerializer(
            data={"hidden_modules": ["printers", "printers", "inventory"]}
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["hidden_modules"] == ["printers", "inventory"]

    def test_all_hideable_keys_are_accepted(self):
        serializer = AppConfigurationSerializer(data={"hidden_modules": list(HIDEABLE_MODULE_KEYS)})
        assert serializer.is_valid(), serializer.errors


# ──────────────────────────────────────────────────────────────────────────────
# Endpoint: GET / PATCH /api/app-config/
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAppConfigurationEndpoint:
    def test_get_default_returns_empty(self, api_client):
        response = api_client.get(reverse("app-config"))
        assert response.status_code == 200
        assert response.json()["hidden_modules"] == []

    def test_patch_valid_persists(self, api_client):
        url = reverse("app-config")
        response = api_client.patch(url, {"hidden_modules": ["inventory", "printers"]}, format="json")
        assert response.status_code == 200
        assert response.json()["hidden_modules"] == ["inventory", "printers"]
        # A follow-up GET reflects the saved state.
        assert api_client.get(url).json()["hidden_modules"] == ["inventory", "printers"]

    def test_patch_invalid_key_returns_400(self, api_client):
        response = api_client.patch(reverse("app-config"), {"hidden_modules": ["bogus"]}, format="json")
        assert response.status_code == 400

    def test_patch_settings_returns_400(self, api_client):
        response = api_client.patch(reverse("app-config"), {"hidden_modules": ["settings"]}, format="json")
        assert response.status_code == 400

    def test_patch_clearing_restores_all_visible(self, api_client):
        url = reverse("app-config")
        api_client.patch(url, {"hidden_modules": ["trackers"]}, format="json")
        response = api_client.patch(url, {"hidden_modules": []}, format="json")
        assert response.status_code == 200
        assert response.json()["hidden_modules"] == []


# ──────────────────────────────────────────────────────────────────────────────
# Backup export / restore round-trip (app_config.json section)
# ──────────────────────────────────────────────────────────────────────────────

def _make_backup_zip(members: dict) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in members.items():
            zf.writestr(name, content)
    buf.seek(0)
    return buf.read()


@pytest.mark.django_db
class TestAppConfigBackup:
    def test_export_includes_app_config(self, api_client):
        config = AppConfiguration.load()
        config.hidden_modules = ["projects"]
        config.save()

        response = api_client.get(reverse("export-data"))
        assert response.status_code == 200

        with zipfile.ZipFile(BytesIO(response.content)) as zf:
            assert "app_config.json" in zf.namelist()
            data = json.loads(zf.read("app_config.json").decode("utf-8"))
            assert data["hidden_modules"] == ["projects"]

    def test_import_restores_app_config(self, api_client):
        zip_bytes = _make_backup_zip(
            {"app_config.json": json.dumps({"hidden_modules": ["trackers", "printers"]})}
        )
        upload = SimpleUploadedFile("backup.zip", zip_bytes, content_type="application/zip")

        response = api_client.post(
            reverse("import-data"), {"backup_file": upload}, format="multipart"
        )
        assert response.status_code == 200
        assert AppConfiguration.load().hidden_modules == ["trackers", "printers"]

    def test_import_filters_out_non_hideable_keys(self, api_client):
        # A hand-edited / tampered backup can't sneak a non-hideable key past restore.
        zip_bytes = _make_backup_zip(
            {"app_config.json": json.dumps({"hidden_modules": ["settings", "trackers", "bogus"]})}
        )
        upload = SimpleUploadedFile("backup.zip", zip_bytes, content_type="application/zip")

        response = api_client.post(
            reverse("import-data"), {"backup_file": upload}, format="multipart"
        )
        assert response.status_code == 200
        assert AppConfiguration.load().hidden_modules == ["trackers"]

    def test_import_without_app_config_is_tolerated(self, api_client):
        # Older backups won't have app_config.json — restore must not fail.
        zip_bytes = _make_backup_zip({"README.txt": "no app config here"})
        upload = SimpleUploadedFile("backup.zip", zip_bytes, content_type="application/zip")

        response = api_client.post(
            reverse("import-data"), {"backup_file": upload}, format="multipart"
        )
        assert response.status_code == 200
