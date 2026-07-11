# STL/3MF Library — User Guide

> **Status:** Draft. The Library feature is still being built; this document
> captures the setup, configuration, and behavior that already exist so they can
> be folded into the full user guide later.
>
> **Last Updated:** 2026-07-11

## What the Library does

The File Library indexes the STL/3MF files on a mounted folder (typically a NAS
share) into a browsable catalog inside Print Vault — a generated thumbnail plus
metadata (size, bounding box, embedded slicer settings for `.3mf`). Files are
indexed **in place**; they are never copied into Print Vault's own storage.

You configure one or more **roots** (folders to index) in **Settings → File
Library**. Each root can be scanned on demand or on a periodic schedule.

## Setup: mounting the share

The library scan runs as a background job in the **`qcluster`** container, so the
share must be mounted into `qcluster` (not just `backend`). Both are driven by
two variables in `.env`:

| Variable | Meaning |
| --- | --- |
| `LIBRARY_HOST_PATH` | Path on the Docker host to your library folder (e.g. a bind-mounted NAS share, `/mnt/nas/stls`). |
| `LIBRARY_MOUNT_PATH` | Path **inside** the container. This **must match** the root path you enter in the Library settings UI. Default `/mnt/nas/stls`. |

The bundled `docker-compose.yml` mounts `${LIBRARY_HOST_PATH}:${LIBRARY_MOUNT_PATH}`
into **both** `backend` and `qcluster`. After setting these, rebuild and recreate:

```bash
docker compose build backend qcluster
docker compose up -d
# confirm the worker can see the share:
docker compose exec qcluster ls -la /mnt/nas/stls
```

### Multiple libraries

- **Several folders under one share:** point `LIBRARY_HOST_PATH` at the parent
  (e.g. `/mnt/nas`) and add each subfolder as its own root in the UI
  (`/mnt/nas/stls`, `/mnt/nas/minis`, …). No compose changes needed.
- **Separate mounts** (e.g. two different NAS boxes): add extra volume entries by
  hand to **both** `backend` and `qcluster`, ideally in a
  `docker-compose.override.yml` so app upgrades don't overwrite them.

## Thumbnails, dense files, and "no preview"

Print Vault renders each thumbnail by loading the mesh and rasterizing it. Some
files are **too heavy to render safely** — a single dense or instanced model can
try to use many gigabytes of RAM. To keep a scan from ever exhausting the host
(this matters on small boxes — a Raspberry Pi or a 2 GB LXC), such files are
**skipped**: they still appear in the library, just **without a generated
preview**. This is expected, not an error. You'll see `Skipping mesh …` lines in
`docker compose logs qcluster` explaining why (too many triangles, too large,
unparseable, etc.).

Each render runs in a **memory-capped subprocess**, so even a pathological file
can't crash the worker or thrash the box — the worst case is a skipped preview.

## Configuration (`.env`) — all optional, safe defaults

Defaults are tuned for the **weakest supported hardware**. Raise the limits on a
capable NAS/server to index faster; lower them on a Pi. All take effect after a
restart/rebuild of `qcluster`.

| Variable | Default | What it does |
| --- | --- | --- |
| `Q_WORKERS` | `1` | Parallel background workers. Each multiplies peak memory — raise only if you have RAM to spare (e.g. 2–4 on 8 GB+). |
| `Q_WORKER_MEMORY_LIMIT_MB` | `600` | Recycle a worker once it exceeds this resident memory; also the mid-scan threshold at which a task hands its remaining files to a fresh one. |
| `LIBRARY_MAX_RENDER_FILE_SIZE_MB` | `100` | Skip rendering meshes larger than this on disk. |
| `LIBRARY_MAX_RENDER_FACES` | `2000000` | Skip meshes with more than this many triangles (the main density guard; on-disk size doesn't bound triangle count for `.3mf`). |
| `LIBRARY_MAX_3MF_UNCOMPRESSED_MB` | `500` | Skip a `.3mf` whose uncompressed contents exceed this (guards against decompression bombs). |
| `LIBRARY_RENDER_HEADROOM_MB` | `2048` | Hard memory ceiling for each render subprocess = its startup size + this. Any file that would allocate past it is skipped. Lower on a Pi (e.g. `1024`); raise if legit large models get skipped. |
| `LIBRARY_RENDER_TIMEOUT_SECONDS` | `120` | Kill a single render that runs longer than this (skips the file). |

### First index expectations

The first scan of a large library is the heaviest thing the app does. With the
default single worker it can take a while (a big share is hours, not minutes) —
that's the deliberate trade for **never** exhausting a small box. Re-scans are
incremental (already-indexed, unchanged files are skipped), so they're fast.

## Troubleshooting

- **"Scanning… stuck near 99%":** usually the `qcluster` worker isn't running
  (`docker compose ps qcluster` shows nothing) — start it with
  `docker compose start qcluster`. A scan whose worker died mid-run is also
  auto-finalized by a periodic reaper within ~10 minutes.
- **Manually clear a wedged scan / queue:**
  ```bash
  docker compose exec backend python manage.py clear_stuck_jobs
  ```
  This purges the background task queue, marks any running scan errored, and
  resets the root's status badge. Restart `qcluster` afterward.
- **A scan exhausted the host before these safeguards existed:** stop the worker
  (`docker compose stop qcluster`), run `clear_stuck_jobs`, then rebuild to the
  current version — the memory caps above make a runaway scan impossible.
