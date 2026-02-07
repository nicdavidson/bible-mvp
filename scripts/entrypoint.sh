#!/bin/sh
# Entrypoint for Fly.io deployment
# Syncs the built DB from the Docker image to the persistent volume,
# then starts the app.

IMAGE_DB="/app/data/bible.db"
VOLUME_DB="/data/bible.db"
IMAGE_MANIFEST="/app/data/db-manifest.json"
VOLUME_MANIFEST="/data/db-manifest.json"

sync_db() {
    # If no DB on volume, copy from image
    if [ ! -f "$VOLUME_DB" ]; then
        echo "No DB on volume — copying from image..."
        cp "$IMAGE_DB" "$VOLUME_DB"
        cp "$IMAGE_MANIFEST" "$VOLUME_MANIFEST" 2>/dev/null || true
        echo "Done. DB size: $(du -h "$VOLUME_DB" | cut -f1)"
        return
    fi

    # If image has a manifest, compare with volume's
    if [ -f "$IMAGE_MANIFEST" ] && [ -f "$VOLUME_MANIFEST" ]; then
        IMAGE_SHA=$(python3 -c "import json; print(json.load(open('$IMAGE_MANIFEST')).get('sha256',''))" 2>/dev/null)
        VOLUME_SHA=$(python3 -c "import json; print(json.load(open('$VOLUME_MANIFEST')).get('sha256',''))" 2>/dev/null)

        if [ "$IMAGE_SHA" != "$VOLUME_SHA" ]; then
            echo "DB updated — syncing to volume..."
            echo "  Image:  $(printf '%.16s' "$IMAGE_SHA")..."
            echo "  Volume: $(printf '%.16s' "$VOLUME_SHA")..."
            cp "$IMAGE_DB" "$VOLUME_DB"
            cp "$IMAGE_MANIFEST" "$VOLUME_MANIFEST"
            echo "Done. DB size: $(du -h "$VOLUME_DB" | cut -f1)"
            return
        fi
    elif [ -f "$IMAGE_MANIFEST" ]; then
        # Volume has no manifest but image does — update
        echo "DB manifest missing on volume — syncing from image..."
        cp "$IMAGE_DB" "$VOLUME_DB"
        cp "$IMAGE_MANIFEST" "$VOLUME_MANIFEST"
        echo "Done."
        return
    fi

    echo "DB on volume is up to date."
}

# Only sync if we have a DB in the image
if [ -f "$IMAGE_DB" ]; then
    sync_db
else
    echo "Warning: No DB in image. Using existing volume DB."
fi

# Start the app
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
