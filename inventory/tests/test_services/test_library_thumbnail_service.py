"""
Tests for the library thumbnail/geometry service — neutral-color renders,
bounding-box extraction, and the never-raises contract for bad inputs.
"""
import io

import pytest
import trimesh
from PIL import Image

from inventory.services.library_thumbnail_service import generate_library_file_assets

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def write_box_stl(path, extents=(10, 20, 30)):
    trimesh.creation.box(extents=extents).export(str(path))
    return path


def test_renders_valid_stl(tmp_path):
    """A valid STL yields PNG bytes and its axis-aligned bounding box."""
    file_path = write_box_stl(tmp_path / "box.stl", extents=(10, 20, 30))

    result = generate_library_file_assets(file_path)

    assert result is not None
    assert result["png_bytes"].startswith(PNG_MAGIC)
    assert result["bounding_box"] == pytest.approx((10.0, 20.0, 30.0))


def test_bounding_box_reflects_model_axes(tmp_path):
    """Bounding box is the model's own AABB, not the rotated render view."""
    file_path = write_box_stl(tmp_path / "box_axes.stl", extents=(5, 10, 40))

    result = generate_library_file_assets(file_path)

    assert result is not None
    assert result["bounding_box"] == pytest.approx((5.0, 10.0, 40.0))


def test_png_is_openable_image(tmp_path):
    """The returned bytes decode as a 256x256 RGBA PNG."""
    file_path = write_box_stl(tmp_path / "box_img.stl", extents=(10, 10, 10))

    result = generate_library_file_assets(file_path)

    assert result is not None
    img = Image.open(io.BytesIO(result["png_bytes"]))
    assert img.size == (256, 256)
    assert img.mode == "RGBA"


def test_unsupported_extension_returns_none(tmp_path):
    """Non-STL/3MF files are refused."""
    file_path = tmp_path / "notes.txt"
    file_path.write_text("Just some notes")

    assert generate_library_file_assets(file_path) is None


def test_missing_file_returns_none(tmp_path):
    """A path that doesn't exist returns None instead of raising."""
    assert generate_library_file_assets(tmp_path / "ghost.stl") is None


def test_corrupt_stl_returns_none(tmp_path):
    """Garbage bytes with an .stl extension return None instead of raising."""
    file_path = tmp_path / "broken.stl"
    file_path.write_bytes(b"not a real stl file")

    assert generate_library_file_assets(file_path) is None


def test_renders_3mf(tmp_path):
    """3MF input renders the same as STL (trimesh handles both)."""
    file_path = tmp_path / "box.3mf"
    trimesh.creation.box(extents=(10, 10, 10)).export(str(file_path))

    result = generate_library_file_assets(file_path)

    assert result is not None
    assert result["png_bytes"].startswith(PNG_MAGIC)


def test_render_color_respected(tmp_path):
    """color_hex drives the rendered mesh color (red box → red center pixel)."""
    file_path = write_box_stl(tmp_path / "box_red.stl", extents=(10, 10, 10))

    result = generate_library_file_assets(file_path, color_hex='#ff0000')

    img = Image.open(io.BytesIO(result["png_bytes"])).convert('RGBA')
    center = img.getpixel((128, 128))
    assert center[3] == 255  # opaque mesh pixel, not background
    assert center[0] > 80 and center[1] < 50 and center[2] < 50
