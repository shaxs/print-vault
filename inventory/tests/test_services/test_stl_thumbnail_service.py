"""
Tests for inventory/services/stl_thumbnail_service.py

Covers the pure rendering pipeline (_load_mesh, _render_mesh_image) with a
synthetic trimesh box (no external STL fixture needed), the guard logic in
generate_auto_thumbnail(), and the batch behavior of
regenerate_tracker_thumbnails().

Network downloads (storage_type='link') are exercised by mocking
FileDownloadService.get_file_from_github rather than hitting real GitHub URLs.
"""
from unittest import mock

import pytest
import trimesh
from django.core.files.base import ContentFile
from PIL import Image

from inventory.models import TrackerFileImage
from inventory.services import stl_thumbnail_service as svc
from inventory.tests.factories import (
    TrackerFactory,
    TrackerFileFactory,
    TrackerFileImageFactory,
)


def _stl_bytes():
    """Export a tiny real STL (a unit box) as bytes."""
    box = trimesh.creation.box(extents=(10, 10, 10))
    return box.export(file_type='stl')


# ============================================================================
# _load_mesh
# ============================================================================

class TestLoadMesh:
    def test_loads_valid_stl(self, tmp_path):
        stl_path = tmp_path / "box.stl"
        stl_path.write_bytes(_stl_bytes())

        mesh = svc._load_mesh(stl_path)

        assert mesh is not None
        assert len(mesh.vertices) > 0
        assert len(mesh.faces) > 0

    def test_returns_none_for_missing_file(self, tmp_path):
        mesh = svc._load_mesh(tmp_path / "does_not_exist.stl")
        assert mesh is None

    def test_returns_none_for_garbage_content(self, tmp_path):
        bad_path = tmp_path / "not_a_model.stl"
        bad_path.write_text("this is not STL data")

        mesh = svc._load_mesh(bad_path)

        assert mesh is None


# ============================================================================
# _render_mesh_image
# ============================================================================

class TestRenderMeshImage:
    def test_renders_correct_size_rgba_image(self):
        box = trimesh.creation.box(extents=(10, 10, 10))

        image = svc._render_mesh_image(box)

        assert isinstance(image, Image.Image)
        assert image.size == svc.THUMBNAIL_SIZE
        assert image.mode == 'RGBA'

    def test_render_is_not_blank(self):
        """Sanity check the mesh actually got drawn (not just the background)."""
        box = trimesh.creation.box(extents=(10, 10, 10))

        image = svc._render_mesh_image(box)
        colors = set(image.getdata())

        assert len(colors) > 1

    def test_background_is_fully_transparent(self):
        """No slicer-style background/grid -- corners should be pure alpha=0."""
        box = trimesh.creation.box(extents=(10, 10, 10))

        image = svc._render_mesh_image(box)

        assert image.getpixel((0, 0))[3] == 0

    def test_mesh_pixels_are_fully_opaque(self):
        box = trimesh.creation.box(extents=(10, 10, 10))

        image = svc._render_mesh_image(box)
        alphas = {pixel[3] for pixel in image.getdata()}

        assert 255 in alphas

    def test_renders_using_the_supplied_base_color(self):
        box = trimesh.creation.box(extents=(10, 10, 10))

        image = svc._render_mesh_image(box, base_color_hex='#ff0000')
        opaque_pixels = [p for p in image.getdata() if p[3] == 255]

        # Every opaque (mesh) pixel should be a red-dominant shade (shading
        # only scales all channels by the same lighting intensity).
        assert all(p[0] >= p[1] and p[0] >= p[2] for p in opaque_pixels)


# ============================================================================
# _hex_to_rgb / _resolve_file_hex_color
# ============================================================================

class TestHexToRgb:
    def test_parses_a_valid_hex_color(self):
        assert svc._hex_to_rgb('#ff0000') == (255, 0, 0)

    def test_handles_missing_hash_prefix(self):
        assert svc._hex_to_rgb('00ff00') == (0, 255, 0)

    def test_falls_back_for_invalid_input(self):
        assert svc._hex_to_rgb('') == (148, 163, 184)
        assert svc._hex_to_rgb('not-a-color') == (148, 163, 184)


@pytest.mark.django_db
class TestResolveFileHexColor:
    def test_primary_file_uses_tracker_primary_material_color(self):
        tracker = TrackerFactory(primary_material=None, primary_color='#111111')
        tracker_file = TrackerFileFactory(tracker=tracker, color='Primary', material_ids=[])

        assert svc._resolve_file_hex_color(tracker_file) == '#111111'

    def test_accent_file_uses_tracker_accent_color(self):
        tracker = TrackerFactory(accent_material=None, accent_color='#222222')
        tracker_file = TrackerFileFactory(tracker=tracker, color='Accent', material_ids=[])

        assert svc._resolve_file_hex_color(tracker_file) == '#222222'

    def test_primary_material_blueprint_color_wins_over_hex_fallback(self):
        from inventory.tests.factories import MaterialFactory

        material = MaterialFactory(colors=['#abcdef'])
        tracker = TrackerFactory(primary_material=material, primary_color='#111111')
        tracker_file = TrackerFileFactory(tracker=tracker, color='Primary', material_ids=[])

        assert svc._resolve_file_hex_color(tracker_file) == '#abcdef'

    def test_other_color_uses_files_own_material(self):
        from inventory.tests.factories import MaterialFactory

        file_material = MaterialFactory(colors=['#123456'])
        tracker = TrackerFactory()
        tracker_file = TrackerFileFactory(
            tracker=tracker, color='Other', material_ids=[file_material.id]
        )

        assert svc._resolve_file_hex_color(tracker_file) == '#123456'

    def test_clear_uses_the_fixed_clear_color(self):
        tracker_file = TrackerFileFactory(color='Clear', material_ids=[])

        assert svc._resolve_file_hex_color(tracker_file) == svc.CLEAR_COLOR_HEX

    def test_unknown_color_falls_back_to_neutral_gray(self):
        tracker_file = TrackerFileFactory(color='', material_ids=[])

        assert svc._resolve_file_hex_color(tracker_file) == svc.FALLBACK_COLOR_HEX


# ============================================================================
# generate_auto_thumbnail — guards
# ============================================================================

@pytest.mark.django_db
class TestGenerateAutoThumbnailGuards:
    def test_skips_if_image_already_exists(self):
        tracker_file = TrackerFileFactory(storage_type='local', filename='part.stl')
        TrackerFileImageFactory(tracker_file=tracker_file)

        assert svc.generate_auto_thumbnail(tracker_file) is None

    def test_skips_non_stl_3mf_extension(self):
        tracker_file = TrackerFileFactory(storage_type='local', filename='readme.txt')

        assert svc.generate_auto_thumbnail(tracker_file) is None

    def test_skips_local_file_missing_on_disk(self):
        tracker_file = TrackerFileFactory(storage_type='local', filename='part.stl')

        assert svc.generate_auto_thumbnail(tracker_file) is None

    def test_skips_link_storage_when_tracker_setting_off(self):
        tracker = TrackerFactory(generate_thumbnails_for_linked_files=False)
        tracker_file = TrackerFileFactory(tracker=tracker, storage_type='link', filename='part.stl')

        assert svc.generate_auto_thumbnail(tracker_file) is None

    def test_never_raises_on_corrupt_local_file(self):
        """A failed render must never propagate — this is expected background-task handling."""
        tracker_file = TrackerFileFactory(storage_type='local', filename='part.stl')
        tracker_file.local_file.save('part.stl', ContentFile(b'not a real stl'), save=True)

        result = svc.generate_auto_thumbnail(tracker_file)

        assert result is None


# ============================================================================
# generate_auto_thumbnail — local storage success path
# ============================================================================

@pytest.mark.django_db
class TestGenerateAutoThumbnailLocalSuccess:
    def test_generates_thumbnail_for_valid_local_stl(self):
        tracker_file = TrackerFileFactory(storage_type='local', filename='part.stl')
        tracker_file.local_file.save('part.stl', ContentFile(_stl_bytes()), save=True)

        result = svc.generate_auto_thumbnail(tracker_file)

        assert result is not None
        assert isinstance(result, TrackerFileImage)
        assert result.is_auto_generated is True
        assert result.tracker_file_id == tracker_file.id
        assert tracker_file.images.count() == 1

    def test_generates_thumbnail_for_valid_local_3mf(self):
        tracker_file = TrackerFileFactory(storage_type='local', filename='part.3mf')
        box = trimesh.creation.box(extents=(10, 10, 10))
        three_mf_bytes = box.export(file_type='3mf')
        tracker_file.local_file.save('part.3mf', ContentFile(three_mf_bytes), save=True)

        result = svc.generate_auto_thumbnail(tracker_file)

        assert result is not None
        assert result.is_auto_generated is True


# ============================================================================
# generate_auto_thumbnail — link storage (mocked download)
# ============================================================================

@pytest.mark.django_db
class TestGenerateAutoThumbnailLinkStorage:
    @staticmethod
    def _fake_download(url, destination, progress_callback=None):
        with open(destination, 'wb') as f:
            f.write(_stl_bytes())
        return {'success': True}

    def test_downloads_and_renders_when_tracker_setting_on(self):
        tracker = TrackerFactory(generate_thumbnails_for_linked_files=True)
        tracker_file = TrackerFileFactory(
            tracker=tracker,
            storage_type='link',
            filename='part.stl',
            github_url='https://github.com/example/repo/blob/main/part.stl',
        )

        with mock.patch.object(
            svc.FileDownloadService, 'get_file_from_github', side_effect=self._fake_download
        ):
            result = svc.generate_auto_thumbnail(tracker_file)

        assert result is not None
        assert result.is_auto_generated is True

    def test_allow_linked_download_overrides_tracker_setting(self):
        tracker = TrackerFactory(generate_thumbnails_for_linked_files=False)
        tracker_file = TrackerFileFactory(
            tracker=tracker,
            storage_type='link',
            filename='part.stl',
            github_url='https://github.com/example/repo/blob/main/part.stl',
        )

        with mock.patch.object(
            svc.FileDownloadService, 'get_file_from_github', side_effect=self._fake_download
        ):
            result = svc.generate_auto_thumbnail(tracker_file, allow_linked_download=True)

        assert result is not None

    def test_download_failure_returns_none(self):
        tracker = TrackerFactory(generate_thumbnails_for_linked_files=True)
        tracker_file = TrackerFileFactory(
            tracker=tracker,
            storage_type='link',
            filename='part.stl',
            github_url='https://github.com/example/repo/blob/main/part.stl',
        )

        with mock.patch.object(
            svc.FileDownloadService, 'get_file_from_github',
            side_effect=svc.DownloadError("network exploded"),
        ):
            result = svc.generate_auto_thumbnail(tracker_file)

        assert result is None


# ============================================================================
# regenerate_tracker_thumbnails
# ============================================================================

@pytest.mark.django_db
class TestRegenerateTrackerThumbnails:
    def test_skips_files_with_manual_image(self):
        tracker = TrackerFactory()
        tracker_file = TrackerFileFactory(tracker=tracker, storage_type='local', filename='part.stl')
        TrackerFileImageFactory(tracker_file=tracker_file, is_auto_generated=False)

        results = svc.regenerate_tracker_thumbnails(tracker)

        assert results['skipped_manual'] == 1
        assert results['generated'] == 0

    def test_regenerates_existing_auto_image(self):
        tracker = TrackerFactory()
        tracker_file = TrackerFileFactory(tracker=tracker, storage_type='local', filename='part.stl')
        tracker_file.local_file.save('part.stl', ContentFile(_stl_bytes()), save=True)
        old_image = TrackerFileImageFactory(tracker_file=tracker_file, is_auto_generated=True)
        old_image_id = old_image.pk

        results = svc.regenerate_tracker_thumbnails(tracker)

        assert results['generated'] == 1
        assert not TrackerFileImage.objects.filter(pk=old_image_id).exists()
        assert tracker_file.images.get().is_auto_generated is True

    def test_excludes_link_storage_unless_include_linked(self):
        tracker = TrackerFactory()
        TrackerFileFactory(tracker=tracker, storage_type='link', filename='part.stl')

        results = svc.regenerate_tracker_thumbnails(tracker, include_linked=False)

        assert results['processed'] == 0

    def test_includes_link_storage_when_requested(self):
        tracker = TrackerFactory()
        TrackerFileFactory(
            tracker=tracker, storage_type='link', filename='part.stl',
            github_url='https://github.com/example/repo/blob/main/part.stl',
        )

        with mock.patch.object(
            svc.FileDownloadService, 'get_file_from_github',
            side_effect=TestGenerateAutoThumbnailLinkStorage._fake_download,
        ):
            results = svc.regenerate_tracker_thumbnails(tracker, include_linked=True)

        assert results['processed'] == 1
        assert results['generated'] == 1

    def test_skips_non_stl_3mf_files(self):
        tracker = TrackerFactory()
        TrackerFileFactory(tracker=tracker, storage_type='local', filename='readme.txt')

        results = svc.regenerate_tracker_thumbnails(tracker)

        assert results['processed'] == 0
