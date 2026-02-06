#!/bin/bash
# Download the pre-built Bible database from GitHub Releases.
#
# Usage:
#   ./scripts/setup_db.sh           # Download if missing or outdated
#   ./scripts/setup_db.sh --force   # Re-download even if current
#
# This checks data/db-manifest.json for the expected SHA256 hash
# and skips the download if the local DB already matches.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_ROOT/data"
DB_PATH="${DATABASE_PATH:-$DATA_DIR/bible.db}"
MANIFEST="$DATA_DIR/db-manifest.json"

# GitHub repo for releases
GITHUB_REPO="milo/bible-mvp"  # Update this to your actual repo

FORCE=false
if [ "$1" = "--force" ]; then
    FORCE=true
fi

echo "BibleMVP Database Setup"
echo "======================="
echo "Database path: $DB_PATH"

# Ensure data directory exists
mkdir -p "$(dirname "$DB_PATH")"

# Check if manifest exists
if [ ! -f "$MANIFEST" ]; then
    echo ""
    echo "No manifest found at $MANIFEST"
    echo "Options:"
    echo "  1. Build locally: python scripts/build_db.py"
    echo "  2. Create a release first, then re-run this script"
    exit 1
fi

# Read expected hash from manifest
EXPECTED_HASH=$(python3 -c "import json; print(json.load(open('$MANIFEST'))['sha256'])" 2>/dev/null || echo "")
EXPECTED_SIZE=$(python3 -c "import json; print(json.load(open('$MANIFEST'))['size'])" 2>/dev/null || echo "0")
RELEASE_TAG=$(python3 -c "import json; m=json.load(open('$MANIFEST')); print(m.get('release_tag', m.get('version', 'latest')))" 2>/dev/null || echo "latest")

if [ -z "$EXPECTED_HASH" ]; then
    echo "Error: Could not read SHA256 from manifest"
    exit 1
fi

# Check if current DB matches
if [ -f "$DB_PATH" ] && [ "$FORCE" = false ]; then
    CURRENT_HASH=$(sha256sum "$DB_PATH" | cut -d' ' -f1)
    if [ "$CURRENT_HASH" = "$EXPECTED_HASH" ]; then
        SIZE_MB=$(echo "scale=1; $(stat -c%s "$DB_PATH" 2>/dev/null || stat -f%z "$DB_PATH") / 1048576" | bc)
        echo "Database is current (${SIZE_MB} MB, hash matches)"
        exit 0
    else
        echo "Database exists but hash doesn't match - will re-download"
    fi
fi

echo ""
echo "Downloading database (release: $RELEASE_TAG)..."

# Try GitHub Releases first
DOWNLOAD_URL="https://github.com/$GITHUB_REPO/releases/download/$RELEASE_TAG/bible.db.zst"
DOWNLOAD_GZ_URL="https://github.com/$GITHUB_REPO/releases/download/$RELEASE_TAG/bible.db.gz"

TEMP_FILE="$DATA_DIR/.bible.db.download"

# Try zstd first, then gzip
if command -v zstd &>/dev/null; then
    echo "Trying $DOWNLOAD_URL..."
    if curl -fSL --progress-bar "$DOWNLOAD_URL" -o "$TEMP_FILE.zst" 2>/dev/null; then
        echo "Decompressing (zstd)..."
        zstd -d "$TEMP_FILE.zst" -o "$DB_PATH" --force
        rm -f "$TEMP_FILE.zst"
    fi
fi

if [ ! -f "$DB_PATH" ] || [ "$(stat -c%s "$DB_PATH" 2>/dev/null || stat -f%z "$DB_PATH" 2>/dev/null || echo 0)" -lt 1000 ]; then
    echo "Trying $DOWNLOAD_GZ_URL..."
    if curl -fSL --progress-bar "$DOWNLOAD_GZ_URL" -o "$TEMP_FILE.gz" 2>/dev/null; then
        echo "Decompressing (gzip)..."
        gunzip -c "$TEMP_FILE.gz" > "$DB_PATH"
        rm -f "$TEMP_FILE.gz"
    fi
fi

# Verify download
if [ ! -f "$DB_PATH" ] || [ "$(stat -c%s "$DB_PATH" 2>/dev/null || stat -f%z "$DB_PATH" 2>/dev/null || echo 0)" -lt 1000 ]; then
    echo ""
    echo "Download failed. The release may not exist yet."
    echo ""
    echo "To build locally instead:"
    echo "  python scripts/build_db.py"
    echo ""
    echo "To create a release (after building):"
    echo "  # Compress the DB"
    echo "  zstd data/bible.db -o data/bible.db.zst"
    echo "  # Create a GitHub release and upload bible.db.zst"
    echo "  gh release create data-v1.0 data/bible.db.zst --title 'Database v1.0'"
    rm -f "$TEMP_FILE" "$TEMP_FILE.zst" "$TEMP_FILE.gz"
    exit 1
fi

# Verify hash
ACTUAL_HASH=$(sha256sum "$DB_PATH" | cut -d' ' -f1)
if [ "$ACTUAL_HASH" != "$EXPECTED_HASH" ]; then
    echo "WARNING: Hash mismatch!"
    echo "  Expected: $EXPECTED_HASH"
    echo "  Got:      $ACTUAL_HASH"
    echo "  The database may have been built with a different version."
fi

SIZE_MB=$(echo "scale=1; $(stat -c%s "$DB_PATH" 2>/dev/null || stat -f%z "$DB_PATH") / 1048576" | bc)
echo ""
echo "Done! Database ready: ${SIZE_MB} MB"
