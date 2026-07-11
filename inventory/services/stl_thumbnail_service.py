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
import multiprocessing
import os
import queue as queue_module
import tempfile
import xml.etree.ElementTree as ET
import zipfile
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

# Refuse to load models above this raw file size. This is the sole density
# guard: trimesh loads the full mesh first, multiplying on-disk size several
# times over in RAM (vertex/face/normal arrays plus a working copy), and a
# single huge binary STL can push a Django-Q worker past 1.5 GB RSS — enough
# to thrash a small self-hosted container. It also bounds render time, since
# the painter's-algorithm draw loop is linear in face count. Everything under
# this cap renders every face (see _render_mesh_image); a 256x256 preview
# gains nothing from a mesh denser than this, so skipping it is the right trade.
#
# Configurable via LIBRARY_MAX_RENDER_FILE_SIZE_MB (default 100) so operators on
# constrained hardware (e.g. a Raspberry Pi) can lower the ceiling: no single
# render can then spike memory past it. Files over the cap still appear in the
# library, just without a generated preview.
def _env_int(name, default):
    try:
        value = int(os.environ.get(name, "") or default)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


MAX_RENDER_FILE_SIZE_BYTES = _env_int("LIBRARY_MAX_RENDER_FILE_SIZE_MB", 100) * 1024 * 1024

# On-disk file size does NOT bound a mesh's memory cost. A compressed .3mf (a
# zip) or a multi-object model that _load_mesh concatenates can hold tens of
# millions of faces in well under MAX_RENDER_FILE_SIZE_BYTES, and both the
# rasterizer's setup (vertices[faces], mesh.copy()) and its per-face Python draw
# loop are linear in face count — so a dense mesh spikes RAM into the GBs and
# grinds for minutes inside a single render. That OOM-killed a worker mid-task
# on the first library index (July 2026), which the between-file RSS bail can't
# catch because it only runs after a file completes. These caps bound the render
# by GEOMETRY, skipping too-dense meshes (the file still appears, just without a
# preview). Both are env-tunable for constrained hardware.
MAX_RENDER_FACES = _env_int("LIBRARY_MAX_RENDER_FACES", 2_000_000)

# Skip a .3mf whose UNCOMPRESSED contents exceed this, read from the zip
# directory without extracting — a small .3mf can decompress to gigabytes of
# mesh, which would OOM during load (before any face count is known).
MAX_3MF_UNCOMPRESSED_BYTES = _env_int("LIBRARY_MAX_3MF_UNCOMPRESSED_MB", 500) * 1024 * 1024

# The geometry guards above are heuristics — they can't catch everything trimesh
# does in memory. The worst offender is an INSTANCED .3mf: a small base object
# referenced hundreds of times via build-items/components has a tiny <triangle>
# count in its XML, but trimesh.load(force='mesh') EXPANDS every instance into
# one giant mesh DURING load, spiking RAM to many GB before any post-load face
# check can run (this OOM-killed the first-index worker). Since a file's memory
# cost can't be predicted from static inspection, the render runs in a forked
# CHILD process whose address space is hard-capped: any allocation past the cap
# fails with MemoryError (or the child dies), the parent skips that file, and
# the container's memory PHYSICALLY cannot exceed the cap — whatever the file is.
#
# The cap is (the child's startup virtual size + this headroom), so it adapts to
# whatever baseline the forked worker inherited. At fork time the headroom is
# additionally clamped to a fraction of MemAvailable (_effective_headroom_bytes),
# so the default is safe even on a 1-2 GB Pi without touching .env. Env-tunable:
# raise it if legit large models get skipped on a big box.
RENDER_MEMORY_HEADROOM_BYTES = _env_int("LIBRARY_RENDER_HEADROOM_MB", 2048) * 1024 * 1024

# Wall-clock ceiling for a single render child. Also kills the pathological slow
# case (the pure-Python draw loop grinding for minutes on a dense mesh).
RENDER_TIMEOUT_SECONDS = _env_int("LIBRARY_RENDER_TIMEOUT_SECONDS", 120)

try:
    _PAGE_SIZE_BYTES = os.sysconf('SC_PAGE_SIZE')
except (AttributeError, ValueError, OSError):
    _PAGE_SIZE_BYTES = 4096  # non-Linux dev


def _current_vsize_bytes():
    """This process's virtual memory size (VSZ) in bytes, from /proc/self/statm
    field 0. Returns 0 where /proc isn't available (non-Linux dev)."""
    try:
        with open('/proc/self/statm') as fh:
            vsize_pages = int(fh.read().split()[0])
    except (OSError, ValueError, IndexError):
        return 0
    return vsize_pages * _PAGE_SIZE_BYTES


# Fraction of MemAvailable a render child may claim. The configured headroom is
# clamped to this so the cap is meaningful on ANY box: the 2 GB default headroom
# is bigger than a 1-2 GB Pi's entire RAM, and an operator who never touches
# .env must still be protected. Under memory pressure the clamp tightens
# automatically — renders start failing with MemoryError (skipped files) instead
# of pushing the host into swap.
_MEMAVAILABLE_FRACTION = 0.8


def _meminfo_available_bytes():
    """MemAvailable from /proc/meminfo, in bytes — the kernel's estimate of what
    can be allocated without swapping. Returns 0 where unavailable (non-Linux
    dev), which disables the clamp."""
    try:
        with open('/proc/meminfo') as fh:
            for line in fh:
                if line.startswith('MemAvailable:'):
                    return int(line.split()[1]) * 1024  # value is in kB
    except (OSError, ValueError, IndexError):
        pass
    return 0


def _effective_headroom_bytes():
    """The render headroom actually applied to a child: the configured
    LIBRARY_RENDER_HEADROOM_MB, clamped to a fraction of the memory available
    right now. Self-tunes to the hardware — tight on a Pi, generous on a big
    box — so the env var is an override, not a load-bearing requirement."""
    headroom = RENDER_MEMORY_HEADROOM_BYTES
    available = _meminfo_available_bytes()
    if available:
        headroom = min(headroom, int(available * _MEMAVAILABLE_FRACTION))
    return headroom


def _cap_child_address_space():
    """In a forked render child, cap RLIMIT_AS to (current VSZ + headroom) so a
    pathological load/render can't exhaust the container — the allocation fails
    (MemoryError) instead of succeeding and OOMing the host. No-op where the
    resource module or /proc is unavailable (dev)."""
    try:
        import resource
    except ImportError:
        return
    baseline = _current_vsize_bytes()
    if not baseline:
        return
    cap = baseline + _effective_headroom_bytes()
    try:
        _soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        if hard != resource.RLIM_INFINITY:
            cap = min(cap, hard)
        resource.setrlimit(resource.RLIMIT_AS, (cap, hard))
    except (ValueError, OSError):
        pass


def _isolated_render_target(file_path, color_hex, png_out_path, result_queue):
    """Runs in the forked child: cap memory, then load + render, write the PNG
    to `png_out_path` (a parent-owned temp file), and report over the queue.
    Any allocation past the cap raises MemoryError (caught here) or kills the
    child outright (the parent notices the empty queue + non-zero exit).
    Never touches the DB.

    The PNG travels via the temp file, NOT the queue, on purpose: a
    multiprocessing.Queue feeds through an OS pipe (~64 KiB), and a child whose
    queued payload exceeds that blocks at exit until the parent reads — but the
    parent is in join(), waiting for the child to exit. Every queue message here
    is a few dozen bytes, so that deadlock is structurally impossible."""
    try:
        from django.db import connections
        connections.close_all()  # don't share the inherited DB connection
    except Exception:
        pass
    _cap_child_address_space()
    try:
        mesh = _load_mesh(Path(file_path))
        if mesh is None:
            result_queue.put(('skip', None))
            return
        extents = mesh.extents
        image = _render_mesh_image(mesh, base_color_hex=color_hex)
        image.save(png_out_path, format='PNG', optimize=True)
        result_queue.put(('ok', (
            float(extents[0]), float(extents[1]), float(extents[2]),
        )))
    except MemoryError:
        result_queue.put(('memory', None))
    except Exception as e:  # pragma: no cover - defensive
        result_queue.put(('error', repr(e)[:500]))


def _fork_context():
    """The 'fork' multiprocessing context (cheap COW start, inherits the already
    imported numpy/trimesh), or None where fork isn't available (Windows/macOS
    dev use 'spawn' — we fall back to in-process there)."""
    try:
        return multiprocessing.get_context('fork')
    except (ValueError, AttributeError):
        return None


_warned_daemonic_parent = False


def _in_daemonic_process():
    """True when this process may not spawn children (multiprocessing asserts
    on it). Django-Q workers are daemonic unless Q_CLUSTER sets
    'daemonize_workers': False — which backend/settings.py does; this check is
    the backstop for any environment that loses that setting."""
    try:
        return bool(multiprocessing.current_process().daemon)
    except Exception:  # pragma: no cover - defensive
        return False


def render_file_to_assets(file_path, color_hex):
    """Load + render `file_path` and return {'png_bytes', 'bounding_box'} or None
    (skip). The work runs in a memory-capped, time-limited forked child so no
    single file — however dense, instanced, or malformed — can exhaust the host.
    Falls back to in-process rendering where fork is unavailable (dev)."""
    ctx = _fork_context()
    if ctx is None:
        return _render_file_inprocess(file_path, color_hex)

    if _in_daemonic_process():
        # A daemonic parent cannot start children — proc.start() would raise
        # for EVERY file and no thumbnail would ever render (bit us on the
        # first post-deploy scan, July 2026: Q_CLUSTER was missing
        # 'daemonize_workers': False). Rendering in-process keeps thumbnails
        # working — the geometry guards in _load_mesh still apply, and the
        # container-level mem_limit bounds the true worst case — but the
        # per-file hard cap is lost, so say exactly how to get it back.
        global _warned_daemonic_parent
        if not _warned_daemonic_parent:
            _warned_daemonic_parent = True
            logger.error(
                "Render worker is a daemonic process, so the memory-capped "
                "render subprocess cannot be used; falling back to in-process "
                "rendering. Set Q_CLUSTER['daemonize_workers'] = False to "
                "restore the per-file memory cap."
            )
        return _render_file_inprocess(file_path, color_hex)

    # Parent-owned temp file carries the PNG out of the child; the queue only
    # ever carries tiny status tuples (see _isolated_render_target for why).
    fd, png_out_path = tempfile.mkstemp(suffix='.png', prefix='pv_render_')
    os.close(fd)
    try:
        result_queue = ctx.Queue()
        proc = ctx.Process(
            target=_isolated_render_target,
            args=(str(file_path), color_hex, png_out_path, result_queue),
        )
        proc.start()
        proc.join(RENDER_TIMEOUT_SECONDS)

        if proc.is_alive():
            proc.terminate()
            proc.join(5)
            if proc.is_alive():
                proc.kill()
                proc.join()
            logger.info(
                f"Skipping mesh for {file_path}: render exceeded "
                f"{RENDER_TIMEOUT_SECONDS}s wall-clock limit"
            )
            return None

        try:
            status, payload = result_queue.get_nowait()
        except queue_module.Empty:
            # No result + process gone => it was killed (memory cap tripped / crash).
            logger.info(
                f"Skipping mesh for {file_path}: render child exited "
                f"{proc.exitcode} without a result (likely over the memory cap)"
            )
            return None

        if status == 'ok':
            try:
                with open(png_out_path, 'rb') as fh:
                    png_bytes = fh.read()
            except OSError as e:  # pragma: no cover - defensive
                logger.warning(f"Render output unreadable for {file_path}: {e}")
                return None
            if not png_bytes:  # pragma: no cover - defensive
                logger.warning(f"Render produced an empty PNG for {file_path}")
                return None
            return {'png_bytes': png_bytes, 'bounding_box': payload}
        if status == 'memory':
            logger.info(f"Skipping mesh for {file_path}: render hit the memory cap")
        elif status == 'error':
            logger.warning(f"Render failed for {file_path}: {payload}")
        return None  # 'skip' (unrenderable/too dense) or any non-ok status
    finally:
        try:
            os.unlink(png_out_path)
        except OSError:
            pass


def _render_file_inprocess(file_path, color_hex):
    """In-process load + render (dev fallback where fork is unavailable). The
    geometry guards in _load_mesh still apply; there is no hard memory cap."""
    mesh = _load_mesh(Path(file_path))
    if mesh is None:
        return None
    extents = mesh.extents
    image = _render_mesh_image(mesh, base_color_hex=color_hex)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    return {
        'png_bytes': buffer.getvalue(),
        'bounding_box': (float(extents[0]), float(extents[1]), float(extents[2])),
    }


def _binary_stl_face_count(path: Path):
    """Exact triangle count from a binary STL's header (the uint32 at byte 80),
    or None if the file isn't a binary STL. A binary STL is exactly
    84 + 50*count bytes, so that identity both confirms the format and yields
    the count from an 84-byte read — letting us skip a too-dense mesh before
    trimesh pulls the whole thing into memory."""
    try:
        size = path.stat().st_size
        if size < 84:
            return None
        with open(path, 'rb') as fh:
            fh.seek(80)
            count = int.from_bytes(fh.read(4), 'little')
        return count if 84 + count * 50 == size else None
    except OSError:
        return None


def _threemf_uncompressed_bytes(path: Path):
    """Total uncompressed size of a .3mf (zip) from its central directory, or
    None if it isn't a readable zip. Read without extracting, so a decompression
    bomb is never loaded into memory."""
    try:
        with zipfile.ZipFile(path) as zf:
            return sum(info.file_size for info in zf.infolist())
    except (zipfile.BadZipFile, OSError):
        return None


def _threemf_instanced_triangle_count(path: Path, limit):
    """Total RENDERED triangle count of a .3mf, accounting for INSTANCING, or
    None if the model can't be read. Result is capped at limit+1.

    This is the guard that matters for .3mf. trimesh.load(force='mesh') builds a
    full in-memory DOM and then EXPANDS instances — build <item>s instantiate
    objects, and <component>s reference other objects (often many times) — so
    the mesh it materializes can be vastly larger than the raw <triangle> count
    in the XML. A tiny base object referenced hundreds of times is exactly the
    instanced monster that OOMed during load. Streaming the model with iterparse
    (never a DOM), we accumulate only small per-object bookkeeping — direct
    triangle counts and the component/build graph, never the triangles
    themselves — then resolve the instanced total. Early-bails so memory/time
    never scale with a monster's true size."""
    try:
        with zipfile.ZipFile(path) as zf:
            model_members = [n for n in zf.namelist() if n.lower().endswith('.model')]
            if not model_members:
                return None

            direct = {}       # object id -> its own <triangle> count
            components = {}    # object id -> [referenced object ids]
            build_items = []   # object ids instantiated by <build><item>
            obj_stack = []

            for member in model_members:
                with zf.open(member) as fh:
                    for event, elem in ET.iterparse(fh, events=('start', 'end')):
                        tag = elem.tag.rsplit('}', 1)[-1]
                        if event == 'start':
                            if tag == 'object':
                                oid = elem.get('id')
                                obj_stack.append(oid)
                                direct.setdefault(oid, 0)
                            continue
                        if tag == 'triangle':
                            if obj_stack:
                                cur = obj_stack[-1]
                                direct[cur] += 1
                                if direct[cur] > limit:
                                    return limit + 1  # one object alone is over
                        elif tag == 'component':
                            ref = elem.get('objectid')
                            if obj_stack and ref is not None:
                                components.setdefault(obj_stack[-1], []).append(ref)
                        elif tag == 'item':
                            ref = elem.get('objectid')
                            if ref is not None:
                                build_items.append(ref)
                        elif tag == 'object' and obj_stack:
                            obj_stack.pop()
                        elem.clear()

            memo = {}

            def resolve(oid, seen):
                if oid in memo:
                    return memo[oid]
                if oid in seen:  # component cycle in a malformed file
                    return 0
                seen = seen | {oid}
                total = direct.get(oid, 0)
                for ref in components.get(oid, ()):
                    total += resolve(ref, seen)
                    if total > limit:
                        break
                memo[oid] = total
                return total

            if build_items:
                grand = 0
                for oid in build_items:
                    grand += resolve(oid, frozenset())
                    if grand > limit:
                        return limit + 1
                return grand
            # No <build> items (single implicit object / malformed): the raw
            # per-object triangle sum is the best estimate.
            total = sum(direct.values())
            return min(total, limit + 1)
    except (zipfile.BadZipFile, OSError, ET.ParseError):
        return None


def _load_mesh(file_path: Path) -> Optional[trimesh.Trimesh]:
    """Load an STL or 3MF file as a single trimesh object.

    Returns None (skip, no preview) not only for corrupt/empty meshes but also
    for meshes too dense to rasterize within a safe memory/time budget — see
    MAX_RENDER_FACES / MAX_3MF_UNCOMPRESSED_BYTES. Callers already treat None as
    'no thumbnail', so both the library and tracker pipelines inherit the guard.
    """
    ext = file_path.suffix.lower()
    # Pre-load guards: refuse a mesh we can tell is too big BEFORE trimesh reads
    # it in — the only protection against an OOM during load itself.
    if ext == '.stl':
        stl_faces = _binary_stl_face_count(file_path)
        if stl_faces is not None and stl_faces > MAX_RENDER_FACES:
            logger.info(
                f"Skipping mesh for {file_path}: binary STL has {stl_faces} "
                f"faces, over cap {MAX_RENDER_FACES}"
            )
            return None
    elif ext == '.3mf':
        uncompressed = _threemf_uncompressed_bytes(file_path)
        if uncompressed is not None and uncompressed > MAX_3MF_UNCOMPRESSED_BYTES:
            logger.info(
                f"Skipping mesh for {file_path}: 3MF uncompressed size "
                f"{uncompressed} B exceeds cap {MAX_3MF_UNCOMPRESSED_BYTES} B"
            )
            return None
        # The real guard: trimesh builds a full DOM and expands instances, so a
        # dense or instanced .3mf OOMs during load itself. Reject by the
        # instancing-aware streamed triangle count first.
        tri_count = _threemf_instanced_triangle_count(file_path, MAX_RENDER_FACES)
        if tri_count is not None and tri_count > MAX_RENDER_FACES:
            logger.info(
                f"Skipping mesh for {file_path}: 3MF resolves to >{MAX_RENDER_FACES} "
                f"triangles (instancing-aware count), too dense to load safely"
            )
            return None

    try:
        mesh = trimesh.load(str(file_path), force='mesh')

        if isinstance(mesh, trimesh.Scene):
            geometries = list(mesh.geometry.values())
            if not geometries:
                return None
            mesh = trimesh.util.concatenate(geometries)

        if mesh is None or len(mesh.vertices) == 0 or len(mesh.faces) == 0:
            return None

        # Post-load backstop: catches ASCII STL and any multi-object/3MF mesh
        # that got past the pre-load checks but is still too dense to rasterize
        # safely. Bounds the render's vertices[faces]/draw-loop cost.
        if len(mesh.faces) > MAX_RENDER_FACES:
            logger.info(
                f"Skipping mesh for {file_path}: {len(mesh.faces)} faces "
                f"exceeds render cap {MAX_RENDER_FACES}"
            )
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

    # Draw every face. An earlier version randomly subsampled faces above a cap
    # to bound draw time, but on a dense mesh (~640k tris for a 30 MB STL) that
    # dropped ~3 of every 4 triangles uniformly across the surface, leaving a
    # sparse, hole-riddled preview that didn't match the solid model. The draw
    # loop is linear and the on-disk size cap (MAX_RENDER_FILE_SIZE_BYTES)
    # already bounds worst-case face count, so rendering all faces is fine.

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

        # Two-stage size guard: the recorded file_size (GitHub metadata /
        # download bookkeeping) lets linked files be refused before wasting
        # a download; the on-disk stat afterwards is authoritative, since
        # file_size can be 0 or stale for local files.
        if tracker_file.file_size and tracker_file.file_size > MAX_RENDER_FILE_SIZE_BYTES:
            logger.info(
                f"Skipping thumbnail for TrackerFile {tracker_file.pk} "
                f"({tracker_file.filename}): recorded size {tracker_file.file_size} "
                f"exceeds render cap {MAX_RENDER_FILE_SIZE_BYTES}"
            )
            return None

        with _resolve_file_path(tracker_file) as file_path:
            if file_path is None:
                return None

            actual_size = file_path.stat().st_size
            if actual_size > MAX_RENDER_FILE_SIZE_BYTES:
                logger.info(
                    f"Skipping thumbnail for TrackerFile {tracker_file.pk} "
                    f"({tracker_file.filename}): on-disk size {actual_size} "
                    f"exceeds render cap {MAX_RENDER_FILE_SIZE_BYTES}"
                )
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
