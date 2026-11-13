#!/bin/sh
# Fly entrypoint: install the DB baked into the image onto the volume when the
# manifest sha differs (scripts/sync_db.py), then drop to appuser for uvicorn.
set -eu

# Verified install of the image DB onto the volume; works when old + new do not both fit
# (docs/DB_UPDATE_PATH_2026-11.md). Exits non-zero, failing the boot, rather than serve a
# missing or unverified DB.
python3 /app/scripts/sync_db.py

chown -R appuser:appuser /data
exec gosu appuser uvicorn backend.main:app --host 0.0.0.0 --port 8000 \
    --proxy-headers --forwarded-allow-ips='*'  # trust Fly's proxy for https redirects
