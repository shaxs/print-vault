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
# Geometry render guards (memory-safety: a dense mesh must never OOM a worker)
# ============================================================================

def _binary_stl_bytes(face_count):
    """Minimal well-formed binary STL: 80-byte header + uint32 count + 50 bytes
    per triangle. Body is zeroed — enough to satisfy the size identity the guard
    checks, without generating real geometry."""
    import struct
    return b'\x00' * 80 + struct.pack('<I', face_count) + b'\x00' * (50 * face_count)


def _write_3mf(path, n_triangles):
    """Write a minimal .3mf (zip) whose model XML declares n_triangles <triangle>
    elements — enough for the streamed triangle-count guard to see, without real
    geometry."""
    import zipfile
    tris = '<triangle v1="0" v2="1" v3="2"/>' * n_triangles
    model = (
        '<?xml version="1.0"?>'
        '<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        f'<resources><object id="1"><mesh><vertices/><triangles>{tris}</triangles>'
        '</mesh></object></resources></model>'
    )
    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr('3D/3dmodel.model', model)


def _write_instanced_3mf(path, base_triangles, components, build_items):
    """Write a .3mf where a base mesh object (id=1, base_triangles tris) is
    referenced `components` times by object id=2, and <build> instantiates
    object 2 `build_items` times — so the rendered total is
    base_triangles * components * build_items."""
    import zipfile
    tris = '<triangle v1="0" v2="1" v3="2"/>' * base_triangles
    comps = '<component objectid="1"/>' * components
    items = '<item objectid="2"/>' * build_items
    model = (
        '<?xml version="1.0"?>'
        '<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        '<resources>'
        f'<object id="1"><mesh><vertices/><triangles>{tris}</triangles></mesh></object>'
        f'<object id="2"><components>{comps}</components></object>'
        '</resources>'
        f'<build>{items}</build>'
        '</model>'
    )
    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr('3D/3dmodel.model', model)


class TestGeometryGuards:
    def test_binary_stl_face_count_exact(self, tmp_path):
        p = tmp_path / "m.stl"
        p.write_bytes(_binary_stl_bytes(7))
        assert svc._binary_stl_face_count(p) == 7

    def test_binary_stl_face_count_none_for_ascii(self, tmp_path):
        """ASCII STL must not be misread as binary — the size identity fails, so
        we return None and let it load normally instead of wrongly skipping."""
        p = tmp_path / "a.stl"
        p.write_text("solid x\nendsolid x\n")
        assert svc._binary_stl_face_count(p) is None

    def test_load_mesh_skips_dense_binary_stl_without_loading(self, tmp_path, monkeypatch):
        """A binary STL over the face cap is skipped from its header alone —
        trimesh.load must never be called (that's the whole point: don't pull
        gigabytes of geometry into RAM)."""
        monkeypatch.setattr(svc, "MAX_RENDER_FACES", 100)
        p = tmp_path / "dense.stl"
        p.write_bytes(_binary_stl_bytes(101))

        called = mock.Mock(side_effect=AssertionError("trimesh.load should not run"))
        monkeypatch.setattr(svc.trimesh, "load", called)

        assert svc._load_mesh(p) is None
        called.assert_not_called()

    def test_load_mesh_allows_stl_under_face_cap(self, tmp_path, monkeypatch):
        monkeypatch.setattr(svc, "MAX_RENDER_FACES", 1_000_000)
        p = tmp_path / "box.stl"
        p.write_bytes(_stl_bytes())
        assert svc._load_mesh(p) is not None

    def test_threemf_uncompressed_bytes(self, tmp_path):
        import zipfile
        p = tmp_path / "m.3mf"
        with zipfile.ZipFile(p, 'w') as zf:
            zf.writestr('3D/model.model', b'x' * 2048)
        assert svc._threemf_uncompressed_bytes(p) == 2048

    def test_load_mesh_skips_3mf_over_uncompressed_cap(self, tmp_path, monkeypatch):
        """A .3mf whose uncompressed contents exceed the cap is skipped before
        loading — protects against a decompression bomb OOMing during load."""
        import zipfile
        monkeypatch.setattr(svc, "MAX_3MF_UNCOMPRESSED_BYTES", 1024)
        p = tmp_path / "big.3mf"
        with zipfile.ZipFile(p, 'w') as zf:
            zf.writestr('3D/model.model', b'x' * 4096)

        called = mock.Mock(side_effect=AssertionError("trimesh.load should not run"))
        monkeypatch.setattr(svc.trimesh, "load", called)

        assert svc._load_mesh(p) is None
        called.assert_not_called()

    def test_threemf_triangle_count_streams_and_early_bails(self, tmp_path):
        sparse = tmp_path / "sparse.3mf"
        _write_3mf(sparse, n_triangles=25)
        assert svc._threemf_instanced_triangle_count(sparse, limit=2_000_000) == 25

        dense = tmp_path / "dense.3mf"
        _write_3mf(dense, n_triangles=500)
        # Early-bail: one object alone is over the limit -> returns limit+1.
        assert svc._threemf_instanced_triangle_count(dense, limit=100) == 101

    def test_threemf_count_multiplies_instanced_geometry(self, tmp_path):
        """The whole point of #3: a small base object referenced many times must
        resolve to the INSTANCED total, not the raw triangle count in the XML."""
        p = tmp_path / "instanced.3mf"
        # base object 1 has 100 triangles; object 2 references it 3x; build
        # instantiates object 2 twice -> 100 * 3 * 2 = 600 rendered triangles.
        _write_instanced_3mf(p, base_triangles=100, components=3, build_items=2)

        assert svc._threemf_instanced_triangle_count(p, limit=2_000_000) == 600
        # With a cap below the instanced total it's rejected, even though the raw
        # XML only holds 100 <triangle> elements.
        assert svc._threemf_instanced_triangle_count(p, limit=500) == 501

    def test_load_mesh_skips_dense_3mf_without_loading(self, tmp_path, monkeypatch):
        """The guard that matters: a .3mf with more triangles than the cap is
        rejected from a STREAMED count, before trimesh builds its in-memory DOM
        of the model (which is what actually OOMs on dense .3mf files)."""
        monkeypatch.setattr(svc, "MAX_RENDER_FACES", 100)
        # keep the uncompressed cap high so the triangle count is what trips
        monkeypatch.setattr(svc, "MAX_3MF_UNCOMPRESSED_BYTES", 10 ** 9)
        p = tmp_path / "dense.3mf"
        _write_3mf(p, n_triangles=500)

        called = mock.Mock(side_effect=AssertionError("trimesh.load should not run"))
        monkeypatch.setattr(svc.trimesh, "load", called)

        assert svc._load_mesh(p) is None
        called.assert_not_called()


# ============================================================================
# render_file_to_assets — memory-capped subprocess wrapper
# ============================================================================

class TestRenderFileToAssets:
    """The forked, memory-capped path only runs on Linux; these exercise the
    orchestration and the in-process fallback that runs on dev (no fork)."""

    def test_returns_assets_for_valid_stl(self, tmp_path):
        p = tmp_path / "box.stl"
        p.write_bytes(_stl_bytes())

        result = svc.render_file_to_assets(p, svc.FALLBACK_COLOR_HEX)

        assert result is not None
        assert result['png_bytes'][:8] == b'\x89PNG\r\n\x1a\n'  # real PNG
        assert len(result['bounding_box']) == 3

    def test_returns_none_when_mesh_is_skipped(self, tmp_path, monkeypatch):
        """A file _load_mesh rejects (too dense) yields None, no crash."""
        monkeypatch.setattr(svc, "MAX_RENDER_FACES", 100)
        monkeypatch.setattr(svc, "MAX_3MF_UNCOMPRESSED_BYTES", 10 ** 9)
        p = tmp_path / "dense.3mf"
        _write_3mf(p, n_triangles=500)

        assert svc.render_file_to_assets(p, svc.FALLBACK_COLOR_HEX) is None

    def test_parent_handles_child_killed_over_memory_cap(self, monkeypatch, tmp_path):
        """When the render child is killed without producing a result (the
        memory cap tripping shows up exactly like this), the parent skips the
        file rather than raising."""
        p = tmp_path / "box.stl"
        p.write_bytes(_stl_bytes())

        class _DeadProc:
            exitcode = -9

            def __init__(self, *a, **k):
                pass

            def start(self):
                pass

            def join(self, timeout=None):
                pass

            def is_alive(self):
                return False

        class _EmptyQueue:
            def get_nowait(self):
                import queue as q
                raise q.Empty

        class _Ctx:
            def Queue(self):
                return _EmptyQueue()

            def Process(self, *a, **k):
                return _DeadProc()

        monkeypatch.setattr(svc, "_fork_context", lambda: _Ctx())

        assert svc.render_file_to_assets(p, svc.FALLBACK_COLOR_HEX) is None


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

    def test_dense_mesh_render_is_deterministic(self):
        """
        Regression for the hole-riddled thumbnail bug (Multi_Lane_Base-Expander
        .stl, ~644k faces): the renderer used to randomly subsample faces down
        to a 150k cap via an *unseeded* np.random.choice. On thin-walled /
        elongated parts that dropped enough triangles to break the surface into
        scattered specks (see the 30 MB STL that rendered as a ghostly outline
        instead of the solid part), and because the sample was unseeded, every
        regeneration produced a *different* speckle pattern.

        Rendering must now be deterministic and draw every face. A dense mesh
        (over the old cap) rendered twice must be byte-identical; if random
        face-dropping is ever reintroduced this fails.
        """
        dense = trimesh.creation.icosphere(subdivisions=7)  # 327,680 faces > old 150k cap
        assert len(dense.faces) > 150_000

        first = svc._render_mesh_image(dense).tobytes()
        second = svc._render_mesh_image(dense).tobytes()

        assert first == second


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
# generate_auto_thumbnail — file-size render cap
#
# Regression coverage for the July 2026 pv-test incident: a Django-Q worker
# loading a very large mesh ballooned past 1.8 GB RSS and thrashed the
# container. Oversized files must be skipped before any mesh load, and
# oversized *linked* files before any download.
# ============================================================================

@pytest.mark.django_db
class TestGenerateAutoThumbnailSizeGuard:
    def test_skips_local_file_exceeding_render_cap(self, monkeypatch):
        # file_size=0 so only the on-disk stat() check can trigger the skip
        tracker_file = TrackerFileFactory(storage_type='local', filename='part.stl', file_size=0)
        tracker_file.local_file.save('part.stl', ContentFile(_stl_bytes()), save=True)
        monkeypatch.setattr(svc, 'MAX_RENDER_FILE_SIZE_BYTES', 10)

        result = svc.generate_auto_thumbnail(tracker_file)

        assert result is None
        assert tracker_file.images.count() == 0

    def test_skips_oversized_linked_file_without_downloading(self):
        tracker = TrackerFactory(generate_thumbnails_for_linked_files=True)
        tracker_file = TrackerFileFactory(
            tracker=tracker,
            storage_type='link',
            filename='part.stl',
            file_size=svc.MAX_RENDER_FILE_SIZE_BYTES + 1,
            github_url='https://github.com/user/repo/blob/main/part.stl',
        )

        with mock.patch.object(svc.FileDownloadService, 'get_file_from_github') as mock_download:
            result = svc.generate_auto_thumbnail(tracker_file)

        assert result is None
        mock_download.assert_not_called()

    def test_recorded_size_at_cap_still_renders(self):
        """Boundary control: a file exactly at the cap is not skipped."""
        tracker_file = TrackerFileFactory(
            storage_type='local', filename='part.stl',
            file_size=svc.MAX_RENDER_FILE_SIZE_BYTES,
        )
        tracker_file.local_file.save('part.stl', ContentFile(_stl_bytes()), save=True)

        result = svc.generate_auto_thumbnail(tracker_file)

        assert result is not None


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


# ============================================================================
# Self-tuning render headroom (Pi safety: cap must fit the actual hardware)
# ============================================================================

class TestMemoryHeadroom:
    def test_effective_headroom_uses_configured_value_when_meminfo_unavailable(self, monkeypatch):
        """No /proc/meminfo (non-Linux dev): the configured headroom applies as-is."""
        monkeypatch.setattr(svc, '_meminfo_available_bytes', lambda: 0)
        assert svc._effective_headroom_bytes() == svc.RENDER_MEMORY_HEADROOM_BYTES

    def test_effective_headroom_clamps_to_fraction_of_available(self, monkeypatch):
        """The 2 GB default must shrink on a box with less memory than that —
        the whole point of the clamp is a Pi that never edits .env."""
        monkeypatch.setattr(svc, '_meminfo_available_bytes', lambda: 1024**3)
        monkeypatch.setattr(svc, 'RENDER_MEMORY_HEADROOM_BYTES', 2 * 1024**3)
        assert svc._effective_headroom_bytes() == int(1024**3 * svc._MEMAVAILABLE_FRACTION)

    def test_effective_headroom_keeps_configured_when_smaller(self, monkeypatch):
        """Plenty of free memory: the operator's configured value wins."""
        monkeypatch.setattr(svc, '_meminfo_available_bytes', lambda: 8 * 1024**3)
        monkeypatch.setattr(svc, 'RENDER_MEMORY_HEADROOM_BYTES', 512 * 1024**2)
        assert svc._effective_headroom_bytes() == 512 * 1024**2

    def test_meminfo_parser_reads_memavailable(self):
        """Parses the kernel's kB line format into bytes."""
        fake_meminfo = (
            "MemTotal:       16000000 kB\n"
            "MemFree:         1000000 kB\n"
            "MemAvailable:    2000000 kB\n"
        )
        with mock.patch('builtins.open', mock.mock_open(read_data=fake_meminfo)):
            assert svc._meminfo_available_bytes() == 2000000 * 1024


class TestRenderTempFileProtocol:
    """The PNG travels from the render child to the parent via a temp file, not
    the result queue — a queued payload over the ~64 KiB pipe buffer would
    deadlock child-exit against the parent's join(). These verify the parent
    side of that protocol with a fake fork context (real fork is Linux-only)."""

    def test_success_path_reads_png_from_temp_file_and_cleans_up(self, monkeypatch, tmp_path):
        import os
        captured_paths = []

        class _FakeQueue:
            def get_nowait(self):
                return ('ok', (1.0, 2.0, 3.0))

        class _FakeProcess:
            exitcode = 0

            def __init__(self, *args, **kwargs):
                self.args = kwargs.get('args') or args
                self._png_path = self.args[2]
                captured_paths.append(self._png_path)

            def start(self):
                # Stand in for the child: write the PNG to the parent-owned path.
                with open(self._png_path, 'wb') as f:
                    f.write(b'\x89PNG\r\n\x1a\nfakedata')

            def join(self, timeout=None):
                pass

            def is_alive(self):
                return False

        class _FakeCtx:
            def Queue(self):
                return _FakeQueue()

            def Process(self, *args, **kwargs):
                return _FakeProcess(*args, **kwargs)

        stl_path = tmp_path / 'mesh.stl'
        stl_path.write_bytes(_stl_bytes())
        monkeypatch.setattr(svc, '_fork_context', lambda: _FakeCtx())

        result = svc.render_file_to_assets(str(stl_path), '#000000')

        assert result['png_bytes'].startswith(b'\x89PNG')
        assert result['bounding_box'] == (1.0, 2.0, 3.0)
        # finally-block hygiene: the temp handoff file must not outlive the call
        assert not os.path.exists(captured_paths[0])

    def test_temp_file_removed_when_child_dies(self, monkeypatch, tmp_path):
        import os
        import queue
        captured_paths = []

        class _FakeQueue:
            def get_nowait(self):
                raise queue.Empty()

        class _FakeProcess:
            exitcode = -9

            def __init__(self, *args, **kwargs):
                self.args = kwargs.get('args') or args
                captured_paths.append(self.args[2])

            def start(self):
                pass

            def join(self, timeout=None):
                pass

            def is_alive(self):
                return False

        class _FakeCtx:
            def Queue(self):
                return _FakeQueue()

            def Process(self, *args, **kwargs):
                return _FakeProcess(*args, **kwargs)

        stl_path = tmp_path / 'mesh.stl'
        stl_path.write_bytes(_stl_bytes())
        monkeypatch.setattr(svc, '_fork_context', lambda: _FakeCtx())

        result = svc.render_file_to_assets(str(stl_path), '#000000')

        assert result is None
        assert not os.path.exists(captured_paths[0])
