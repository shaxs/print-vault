"""
Thumbnail + geometry extraction for STL/3MF Library files.

Thin adapter over the tracker feature's mesh pipeline
(inventory/services/stl_thumbnail_service.py): same trimesh loading and
numpy/Pillow orthographic rasterizer, but rendered in a fixed neutral color —
library files have no tracker/material context to resolve a color from — and
returning raw PNG bytes plus the mesh's bounding box instead of creating a
TrackerFileImage row. Persistence is the scanner's job, not this module's.
"""

import io
import logging
from pathlib import Path
from typing import Optional

from inventory.services.stl_thumbnail_service import (
    FALLBACK_COLOR_HEX,
    MAX_RENDER_FILE_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
    _load_mesh,
    _render_mesh_image,
)

logger = logging.getLogger(__name__)

# Same neutral slate the tracker pipeline falls back to when no material
# color resolves — library thumbnails always render in this.
NEUTRAL_COLOR_HEX = FALLBACK_COLOR_HEX


def generate_library_file_assets(file_path, color_hex=NEUTRAL_COLOR_HEX) -> Optional[dict]:
    """
    Load an STL/3MF from `file_path` and return
    ``{'png_bytes': bytes, 'bounding_box': (x_mm, y_mm, z_mm)}``.

    `color_hex` is the flat render color — the root's user-configured
    thumbnail_color in practice, defaulting to the same neutral slate the
    tracker pipeline falls back to.

    The bounding box is the axis-aligned extent of the mesh in its own
    coordinate system (taken before the isometric render rotation).

    Never raises — returns None for unsupported extensions, oversized files
    (same render cap as tracker thumbnails), and corrupt/unloadable meshes.
    """
    try:
        path_str = str(file_path)
        if not path_str.lower().endswith(SUPPORTED_EXTENSIONS):
            return None

        path = Path(path_str)
        if not path.exists():
            return None
        if path.stat().st_size > MAX_RENDER_FILE_SIZE_BYTES:
            logger.info(
                f"Skipping library thumbnail for {path_str}: size exceeds "
                f"render cap {MAX_RENDER_FILE_SIZE_BYTES}"
            )
            return None

        mesh = _load_mesh(path)
        if mesh is None:
            return None

        extents = mesh.extents  # before render rotation — the model's own AABB
        image = _render_mesh_image(mesh, base_color_hex=color_hex or NEUTRAL_COLOR_HEX)

        buffer = io.BytesIO()
        image.save(buffer, format='PNG', optimize=True)
        return {
            'png_bytes': buffer.getvalue(),
            'bounding_box': (float(extents[0]), float(extents[1]), float(extents[2])),
        }
    except Exception:
        logger.exception(f"Library thumbnail generation failed for {file_path}")
        return None
