#!/usr/bin/env python3
"""Install the DB baked into the image onto the Fly volume, safely, before the app starts.

Called by scripts/entrypoint.sh (as root, before uvicorn). Replaces the shell copy that
needed old + new DB on the volume at once (2 x 850 MB does not fit a 1 GB volume).

Order of operations (docs/DB_UPDATE_PATH_2026-11.md):
  1. Up to date (volume manifest sha == image manifest sha, file size matches): exit 0.
  2. Verify the *source* first: sha256 of the image DB must match the image manifest.
     Mismatch -> exit 1 with the volume untouched (old DB keeps working on rollback).
  3. If the volume has room for the new file beside the old one: copy to bible.db.tmp,
     fsync, check size + sha256, atomic rename over bible.db, write the manifest last.
  4. Otherwise, if old + free covers the new file: delete the volume manifest, then the
     old DB, then do step 3. The image is the durable source, so a crash at any point is
     repaired by the next boot (no manifest -> copy again).
  5. Otherwise refuse (exit 1) before deleting anything.
A reader never sees a partial DB: the app only starts after this script exits 0.

Exit codes: 0 ok / up to date, 1 refused or failed (machine fails its health check).
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

RESERVE = 64 * 1024 * 1024   # SQLite journal for startup migrations + filesystem slack
CHUNK = 1 << 20


def log(msg: str):
    print(f"[sync_db] {msg}", flush=True)


def read_manifest(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def free_bytes(directory: Path) -> int:
    st = os.statvfs(directory)
    return st.f_bavail * st.f_frsize


def copy_verified(src: Path, tmp: Path, want_sha: str, want_size: int, opener=open):
    """Stream src -> tmp with fsync; raise ValueError on size/sha mismatch. tmp removed
    on any failure (including ENOSPC and interruption)."""
    h = hashlib.sha256()
    try:
        with open(src, "rb") as fin, opener(tmp, "wb") as fout:
            while chunk := fin.read(CHUNK):
                fout.write(chunk)
                h.update(chunk)
            fout.flush()
            os.fsync(fout.fileno())
        size = tmp.stat().st_size
        if size != want_size or h.hexdigest() != want_sha:
            raise ValueError(f"copied file is {size} bytes, sha {h.hexdigest()[:12]}; "
                             f"want {want_size} bytes, sha {want_sha[:12]}")
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def fsync_dir(directory: Path):
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def sync(image_db: Path, image_manifest: Path, volume_db: Path, volume_manifest: Path,
         free=free_bytes, opener=open, source_check=True) -> str:
    """Returns 'up-to-date' | 'side-by-side' | 'delete-first'. Raises SystemExit(1) on refusal."""
    want = read_manifest(image_manifest)
    if not want or not want.get("sha256"):
        log("FATAL: no usable image manifest; refusing to touch the volume")
        raise SystemExit(1)
    want_sha, want_size = want["sha256"], int(want.get("size") or image_db.stat().st_size)
    have = read_manifest(volume_manifest)
    tmp = volume_db.with_name(volume_db.name + ".tmp")
    tmp.unlink(missing_ok=True)  # leftover from an interrupted boot

    if (have and have.get("sha256") == want_sha and volume_db.exists()
            and volume_db.stat().st_size == want_size):
        log(f"volume DB is up to date ({want.get('version')})")
        return "up-to-date"

    if source_check:
        got = sha256_file(image_db)
        if got != want_sha:
            log(f"FATAL: image DB sha {got[:12]} != image manifest {want_sha[:12]}; volume untouched")
            raise SystemExit(1)

    old_size = volume_db.stat().st_size if volume_db.exists() else 0
    room = free(volume_db.parent)
    if room >= want_size + RESERVE:
        mode = "side-by-side"
    elif room + old_size >= want_size + RESERVE:
        mode = "delete-first"
    else:
        log(f"FATAL: need {(want_size + RESERVE) >> 20} MB, volume has {room >> 20} MB free "
            f"+ {old_size >> 20} MB old DB; grow the volume. Old DB left in place")
        raise SystemExit(1)
    log(f"installing {want.get('version')} ({want_size >> 20} MB) {mode}; "
        f"free {room >> 20} MB, old {old_size >> 20} MB")

    if mode == "delete-first":
        # Manifest first: from here until the final write a crash leaves "no manifest",
        # which the next boot treats as "copy again".
        volume_manifest.unlink(missing_ok=True)
        fsync_dir(volume_db.parent)
        volume_db.unlink(missing_ok=True)
        fsync_dir(volume_db.parent)
    try:
        copy_verified(image_db, tmp, want_sha, want_size, opener=opener)
    except OSError as e:
        if e.errno == errno.ENOSPC:
            log(f"FATAL: volume full while copying ({mode}); "
                + ("old DB left in place" if mode == "side-by-side" else "will retry next boot"))
        else:
            log(f"FATAL: copy failed: {e}")
        raise SystemExit(1) from e
    except ValueError as e:
        log(f"FATAL: {e}")
        raise SystemExit(1) from e

    # A hot journal from a crashed migration must not replay into the new DB
    for suffix in ("-journal", "-wal", "-shm"):
        Path(str(volume_db) + suffix).unlink(missing_ok=True)
    os.replace(tmp, volume_db)
    fsync_dir(volume_db.parent)
    mtmp = volume_manifest.with_name(volume_manifest.name + ".tmp")
    shutil.copyfile(image_manifest, mtmp)
    os.replace(mtmp, volume_manifest)
    fsync_dir(volume_db.parent)
    log(f"done: {want.get('version')} installed ({mode})")
    return mode


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--image-db", type=Path, default=Path("/app/data/bible.db"))
    ap.add_argument("--image-manifest", type=Path, default=Path("/app/data/db-manifest.json"))
    ap.add_argument("--volume-db", type=Path, default=Path("/data/bible.db"))
    ap.add_argument("--volume-manifest", type=Path, default=Path("/data/db-manifest.json"))
    a = ap.parse_args()
    if not a.image_db.exists():
        log("no DB in image; using the existing volume DB")
        return
    sync(a.image_db, a.image_manifest, a.volume_db, a.volume_manifest)


if __name__ == "__main__":
    sys.exit(main())
