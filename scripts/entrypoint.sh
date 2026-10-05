#!/bin/sh
# Fly entrypoint: sync the DB baked into the image onto the volume when the
# manifest sha differs, then drop to appuser for uvicorn.
#
# The copy is atomic and verified: copy to a temp file, check its sha256 against
# the image manifest, then rename into place and write the manifest LAST. A
# failed or partial copy aborts the boot (Fly health check fails, old machine
# keeps serving) instead of leaving a truncated DB marked "up to date".
set -eu

IMAGE_DB=/app/data/bible.db
IMAGE_MANIFEST=/app/data/db-manifest.json
VOLUME_DB=/data/bible.db
VOLUME_MANIFEST=/data/db-manifest.json

sha_of_manifest() { python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('sha256',''))" "$1" 2>/dev/null || true; }

if [ -f "$IMAGE_DB" ]; then
    want=$(sha_of_manifest "$IMAGE_MANIFEST")
    have=""
    [ -f "$VOLUME_DB" ] && [ -f "$VOLUME_MANIFEST" ] && have=$(sha_of_manifest "$VOLUME_MANIFEST")
    if [ -z "$want" ] || [ "$want" != "$have" ]; then
        echo "Syncing DB to volume (image ${want:-no-manifest})..."
        rm -f "$VOLUME_DB.tmp"
        cp "$IMAGE_DB" "$VOLUME_DB.tmp"
        if [ -n "$want" ]; then
            got=$(sha256sum "$VOLUME_DB.tmp" | cut -d' ' -f1)
            if [ "$got" != "$want" ]; then
                echo "FATAL: copied DB sha $got != manifest $want" >&2
                rm -f "$VOLUME_DB.tmp"
                exit 1
            fi
        fi
        # A hot journal from a crashed migration must not replay into the new DB
        rm -f "$VOLUME_DB-journal" "$VOLUME_DB-wal" "$VOLUME_DB-shm"
        mv "$VOLUME_DB.tmp" "$VOLUME_DB"
        cp "$IMAGE_MANIFEST" "$VOLUME_MANIFEST.tmp" && mv "$VOLUME_MANIFEST.tmp" "$VOLUME_MANIFEST"
        echo "Done. DB size: $(du -h "$VOLUME_DB" | cut -f1)"
    else
        echo "DB on volume is up to date."
    fi
else
    echo "Warning: no DB in image; using existing volume DB."
fi

chown -R appuser:appuser /data
exec gosu appuser uvicorn backend.main:app --host 0.0.0.0 --port 8000 \
    --proxy-headers --forwarded-allow-ips='*'  # trust Fly's proxy for https redirects
