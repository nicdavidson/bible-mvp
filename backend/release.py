"""Which database release and image this process serves, for cache validators.

Search results depend on the loaded database (verse text, FTS index, vectors) and on the
code and model in the image, so their ETag is built from both. A new DB release or a new
image changes every search ETag; clients revalidate cheaply (304) within one release.
"""
from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache

from .database import DATABASE_PATH


@lru_cache(maxsize=1)
def db_release() -> str:
    """sha256 (12 chars) from the db-manifest.json beside the DB, else size+mtime."""
    manifest = DATABASE_PATH.with_name("db-manifest.json")
    try:
        sha = json.loads(manifest.read_text()).get("sha256")
        if sha:
            return sha[:12]
    except (OSError, ValueError):
        pass
    try:
        st = DATABASE_PATH.stat()
        return f"s{st.st_size:x}m{int(st.st_mtime):x}"
    except OSError:
        return "nodb"


def search_etag(url: str) -> str:
    """Weak ETag for one search URL (path + query) under this DB release and image."""
    image = os.environ.get("FLY_IMAGE_REF", "local")
    h = hashlib.sha256(f"{db_release()}|{image}|{url}".encode()).hexdigest()[:20]
    return f'W/"{db_release()}-{h}"'
