"""
Auto-Thumbnail Generation Service for Tracker Files

Generates 2D preview images from STL/3MF tracker files using trimesh for mesh
loading and a hand-rolled orthographic rasterizer (numpy + Pillow) for
rendering — deliberately NOT trimesh's built-in Scene.render(), which depends
on pyglet/OpenGL and is unreliable in headless server environments (this
project runs in Docker in production, and self-hosted users' environments
vary widely). The rasterizer approach has zero system-graphics dependencies,
so it behaves identically in Docker and bare-metal dev.

Entry points:
    generate_auto_thumbnail(tracker_file) -> TrackerFileImage | None
        Single-file generation, used by the post_save signal and the
        Django-Q task wrapper in inventory/tasks.py.

    regenerate_tracker_thumbnails(tracker, include_linked=False) -> dict
        Tracker-scoped batch regeneration, used by the regenerate-thumbnails
        API action and the backfill_stl_thumbnails management command.
"""

import io
import logging
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import numpy as np
import trimesh
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw

from inventory.services.file_download_service import (
    DownloadError,
    DownloadTimeoutError,
    FileDownloadService,
    FileTooLargeError,
)

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = ('.stl', '.3mf')

THUMBNAIL_SIZE = (256, 256)

# Fallback colors mirror TrackerDetailView.vue's getColorBadgeStyle() cascade
# so a thumbnail with no resolvable material color still looks intentional.
FALLBACK_COLOR_HEX = '#94a3b8'
CLEAR_COLOR_HEX = '#e2e8f0'
OTHER_COLOR_HEX = '#78716c'
DEFAULT_PRIMARY_HEX = '#4a90e2'
DEFAULT_ACCENT_HEX = '#f5a623'

# Isometric-style viewing angle (matches the stashed renderer's original angles)
ROTATION_X_RADIANS = 0.4
ROTATION_Y_RADIANS = 0.6

# Bound worst-case render time for very dense meshes (large mechanical parts
# in this project's own tracker media routinely exceed this). Random face
# sampling is a reasonable tradeoff for a 256x256 preview.
MAX_FACES_FOR_RENDER = 150_000


def _load_mesh(file_path: Path) -> Optional[trimesh.Trimesh]:
    """Load an STL or 3MF file as a single trimesh object."""
    try:
        mesh = trimesh.load(str(file_path), force='mesh')

        if isinstance(mesh, trimesh.Scene):
            geometries = list(mesh.geometry.values())
            if not geometries:
                return None
            mesh = trimesh.util.concatenate(geometries)

        if mesh is None or len(mesh.vertices) == 0 or len(mesh.faces) == 0:
            return None

        return mesh
    except Exception as e:
        logger.warning(f"Failed to load mesh from {file_path}: {e}")
        return None


def _hex_to_rgb(hex_color: str):
    hex_color = (hex_color or '').lstrip('#')
    if len(hex_color) != 6:
        return (148, 163, 184)  # FALLBACK_COLOR_HEX as RGB
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _resolve_file_hex_color(tracker_file) -> str:
    """
    Mirror TrackerDetailView.vue's getColorBadgeStyle()/getFileHexColor()
    cascade, so the auto-generated thumbnail matches the color the UI (and
    the 3D viewer) already show for this file, instead of a fixed neutral gray.
    """
    from inventory.models import Material

    tracker = tracker_file.tracker
    color = (tracker_file.color or '').lower()

    primary = tracker.primary_color or DEFAULT_PRIMARY_HEX
    accent = tracker.accent_color or DEFAULT_ACCENT_HEX

    if tracker.primary_material_id and tracker.primary_material.colors:
        primary = tracker.primary_material.colors[0]
    if tracker.accent_material_id and tracker.accent_material.colors:
        accent = tracker.accent_material.colors[0]

    if tracker_file.material_ids:
        file_material = Material.objects.filter(id__in=tracker_file.material_ids).first()
        if file_material and file_material.colors and color in ('multicolor', 'other'):
            return file_material.colors[0]

    if color == 'primary':
        return primary
    if color == 'accent':
        return accent
    if color == 'multicolor':
        return primary
    if color == 'clear':
        return CLEAR_COLOR_HEX
    if color == 'other':
        return OTHER_COLOR_HEX
    return FALLBACK_COLOR_HEX


def _render_mesh_image(mesh: trimesh.Trimesh, base_color_hex: str = FALLBACK_COLOR_HEX, size=THUMBNAIL_SIZE) -> Image.Image:
    """
    Render a flat-shaded isometric preview via orthographic projection +
    painter's algorithm, onto a transparent background (no slicer-style grid)
    so it composites cleanly into the file list/edit modal in either theme.
    Not a physically-correct renderer, but a reasonable approximation for a
    small static preview image.
    """
    base_color = np.array(_hex_to_rgb(base_color_hex))
    working = mesh.copy()
    center = (working.bounds[0] + working.bounds[1]) / 2.0
    working.apply_translation(-center)

    rotation = (
        trimesh.transformations.rotation_matrix(ROTATION_Y_RADIANS, [0, 1, 0])
        @ trimesh.transformations.rotation_matrix(ROTATION_X_RADIANS, [1, 0, 0])
    )
    working.apply_transform(rotation)

    vertices = working.vertices
    faces = working.faces
    normals = working.face_normals

    if len(faces) > MAX_FACES_FOR_RENDER:
        sample = np.random.choice(len(faces), MAX_FACES_FOR_RENDER, replace=False)
        faces = faces[sample]
        normals = normals[sample]

    # Backface cull: camera sits at +Z looking toward the origin, so only
    # faces whose (rotated) normal points back toward the camera are visible.
    front_facing = normals[:, 2] > 0
    if front_facing.any():
        faces = faces[front_facing]
        normals = normals[front_facing]
    # else: degenerate/inside-out mesh — keep everything rather than render blank.

    # Painter's algorithm: draw back-to-front by average face depth.
    face_depths = vertices[faces].mean(axis=1)[:, 2]
    order = np.argsort(face_depths)
    faces = faces[order]
    normals = normals[order]

    mins = vertices[:, :2].min(axis=0)
    maxs = vertices[:, :2].max(axis=0)
    extent = max(float((maxs - mins).max()), 1e-6)
    padding = 0.82
    scale = (min(size) * padding) / extent
    mid = (mins + maxs) / 2.0

    def to_screen(xy):
        sx = size[0] / 2 + (xy[0] - mid[0]) * scale
        sy = size[1] / 2 - (xy[1] - mid[1]) * scale  # flip Y: image origin is top-left
        return (sx, sy)

    image = Image.new('RGBA', size, (0, 0, 0, 0))  # fully transparent background
    draw = ImageDraw.Draw(image, 'RGBA')

    light_dir = np.array([0.35, 0.5, 0.8])
    light_dir = light_dir / np.linalg.norm(light_dir)
    ambient = 0.35

    for face, normal in zip(faces, normals):
        triangle = vertices[face][:, :2]
        points = [to_screen(p) for p in triangle]
        intensity = ambient + (1 - ambient) * max(float(np.dot(normal, light_dir)), 0.0)
        color = tuple(int(c * intensity) for c in base_color) + (255,)  # fully opaque mesh
        draw.polygon(points, fill=color)

    return image


@contextmanager
def _resolve_file_path(tracker_file):
    """
    Yield a local Path to render from. For 'local' files this is the file
    already on disk. For 'link' files this temporarily downloads the file
    from GitHub and deletes it again on exit — no local copy is persisted.
    Yields None if the file isn't available (missing on disk, download
    failed, etc.) so the caller can bail out cleanly.
    """
    if tracker_file.storage_type == 'local':
        if not tracker_file.local_file or not tracker_file.local_file.name:
            yield None
            return
        path = Path(tracker_file.local_file.path)
        yield path if path.exists() else None
        return

    # storage_type == 'link'
    suffix = Path(tracker_file.filename).suffix or '.stl'
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.close()
    tmp_path = Path(tmp.name)
    try:
        FileDownloadService().get_file_from_github(tracker_file.github_url, str(tmp_path))
        yield tmp_path
    except (DownloadError, DownloadTimeoutError, FileTooLargeError) as e:
        logger.warning(
            f"Could not download {tracker_file.filename} for thumbnail generation: {e}"
        )
        yield None
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def generate_auto_thumbnail(tracker_file, *, allow_linked_download: bool = False):
    """
    Generate an auto-thumbnail for a single TrackerFile.

    Guards (in order): skip if any image already exists (manual or
    auto-generated — never clobber, never double-generate); skip non-STL/3MF
    files; for storage_type='link' files, skip unless allow_linked_download
    is True or the tracker's generate_thumbnails_for_linked_files is True.

    Never raises — a corrupt/unparseable file is an expected outcome for a
    background task, not an error condition for the caller.

    Returns the created TrackerFileImage, or None if nothing was generated.
    """
    from inventory.models import TrackerFileImage

    try:
        # Query TrackerFileImage.objects directly rather than
        # tracker_file.images.exists() -- a bare .exists()/.all() on a
        # relation with a populated prefetch_related cache (e.g. a view
        # queryset that prefetched 'images') reuses that cache instead of
        # re-querying, even if a row was deleted moments earlier in the same
        # request. See queue_auto_thumbnail_generation in models.py for the
        # concrete bug this caused.
        if TrackerFileImage.objects.filter(tracker_file_id=tracker_file.pk).exists():
            return None

        if not tracker_file.filename.lower().endswith(SUPPORTED_EXTENSIONS):
            return None

        storage_type = tracker_file.storage_type
        if storage_type == 'local':
            pass
        elif storage_type == 'link':
            if not (allow_linked_download or tracker_file.tracker.generate_thumbnails_for_linked_files):
                return None
        else:
            return None

        with _resolve_file_path(tracker_file) as file_path:
            if file_path is None:
                return None

            mesh = _load_mesh(file_path)
            if mesh is None:
                return None

            base_color_hex = _resolve_file_hex_color(tracker_file)
            image = _render_mesh_image(mesh, base_color_hex=base_color_hex)

        buffer = io.BytesIO()
        image.save(buffer, format='PNG', optimize=True)
        buffer.seek(0)

        base_name = Path(tracker_file.filename).stem
        return TrackerFileImage.objects.create(
            tracker_file=tracker_file,
            image=ContentFile(buffer.read(), name=f"{base_name}_auto_thumb.png"),
            caption='Auto-generated preview',
            order=0,
            is_auto_generated=True,
        )
    except Exception:
        logger.exception(
            f"Auto-thumbnail generation failed for TrackerFile {tracker_file.pk} "
            f"({tracker_file.filename})"
        )
        return None


def regenerate_tracker_thumbnails(tracker, include_linked: bool = False) -> dict:
    """
    (Re)generate thumbnails for every eligible STL/3MF file in a tracker.

    Skips files with a manually-uploaded image (never overwrites a manual
    upload). Files with an existing auto-generated image are regenerated
    (the stale auto image is deleted first so generate_auto_thumbnail's
    "already has an image" guard doesn't just no-op).
    """
    results = {'processed': 0, 'generated': 0, 'skipped_manual': 0, 'failed': 0}
    storage_types = ['local', 'link'] if include_linked else ['local']
    queryset = tracker.files.filter(storage_type__in=storage_types)

    for tracker_file in queryset:
        if not tracker_file.filename.lower().endswith(SUPPORTED_EXTENSIONS):
            continue
        results['processed'] += 1

        if tracker_file.images.filter(is_auto_generated=False).exists():
            results['skipped_manual'] += 1
            continue

        tracker_file.images.filter(is_auto_generated=True).delete()

        image = generate_auto_thumbnail(tracker_file, allow_linked_download=include_linked)
        if image:
            results['generated'] += 1
        else:
            results['failed'] += 1

    return results
