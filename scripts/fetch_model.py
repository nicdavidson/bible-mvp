#!/usr/bin/env python3
"""Fetch the meaning-search model that data/bible.db's vectors were built with.

Used by CI after scripts/fetch_db.py, so the image's data/models/ holds exactly the model
the DB release needs (the Dockerfile copies data/models/). Reads semantic_meta.model_key
from the DB, resolves it in backend/semantic.py (pinned revision, sha256 per file, source:
Hugging Face or the release bucket), downloads, verifies, and checks the combined
fingerprint against semantic_meta.model_sha256. Exit 1 on any mismatch.

A DB without vectors is fine (prints a note, exit 0): the app falls back to keyword search.
"""
import os
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.semantic import fetch_model, get_spec, model_fingerprint  # noqa: E402

DB = Path(os.environ.get("DATABASE_PATH", PROJECT_ROOT / "data" / "bible.db"))


def main() -> int:
    try:
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        meta = dict(conn.execute("SELECT key, value FROM semantic_meta").fetchall())
        conn.close()
    except sqlite3.Error:
        print("[fetch_model] DB has no semantic vectors; nothing to fetch")
        return 0
    spec = get_spec(meta["model_key"])
    directory = fetch_model(spec)
    got = model_fingerprint(spec, directory)
    if got != meta["model_sha256"]:
        print(f"[fetch_model] {directory}: fingerprint {got[:12]} != DB's "
              f"{meta['model_sha256'][:12]}", file=sys.stderr)
        return 1
    print(f"[fetch_model] {spec.key} ready in {directory}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
