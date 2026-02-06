"""
Local source cache for import scripts.

Caches downloaded files in data/sources/ so subsequent builds
don't need network access. All network-fetching import scripts
should use these helpers instead of raw urllib calls.

Cache layout:
    data/sources/
        kjv/Genesis.json, Exodus.json, ...
        web/eng-web.usfx.xml
        strongs/strongs-greek-dictionary.js, strongs-hebrew-dictionary.js
        commentary-matthew-henry/books.json, GEN/1.json, ...
        commentary-john-gill/books.json, GEN/1.json, ...
        spurgeon/d0101am.html, d0101pm.html, ...

Usage:
    from source_cache import cached_fetch_json, cached_fetch_html, SOURCES_DIR

    # Fetches from network on first call, reads from cache on subsequent calls
    data = cached_fetch_json("kjv/Genesis.json", url)
    html = cached_fetch_html("spurgeon/d0101am.html", url)
"""
import json
import os
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SOURCES_DIR = PROJECT_ROOT / "data" / "sources"


def _ensure_dir(filepath: Path):
    """Ensure parent directory exists."""
    filepath.parent.mkdir(parents=True, exist_ok=True)


def _cache_path(key: str) -> Path:
    """Get the full cache path for a key like 'kjv/Genesis.json'."""
    return SOURCES_DIR / key


def is_cached(key: str) -> bool:
    """Check if a key exists in the cache."""
    p = _cache_path(key)
    return p.exists() and p.stat().st_size > 0


def read_cached(key: str) -> str | None:
    """Read raw text from cache. Returns None if not cached."""
    p = _cache_path(key)
    if p.exists() and p.stat().st_size > 0:
        return p.read_text(encoding="utf-8")
    return None


def write_cache(key: str, data: str):
    """Write raw text to cache."""
    p = _cache_path(key)
    _ensure_dir(p)
    p.write_text(data, encoding="utf-8")


def _fetch_url(url: str, timeout: int = 30) -> str | None:
    """Fetch raw text from URL."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BibleMVP/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except Exception as e:
        print(f"    Error fetching {url}: {e}")
        return None


def cached_fetch(key: str, url: str, timeout: int = 30) -> str | None:
    """
    Fetch text from cache or URL.

    Args:
        key: Cache key like 'kjv/Genesis.json'
        url: URL to fetch if not cached
        timeout: HTTP timeout in seconds

    Returns:
        Raw text content, or None on failure
    """
    # Check cache first
    cached = read_cached(key)
    if cached is not None:
        return cached

    # Fetch from network
    data = _fetch_url(url, timeout)
    if data is not None:
        write_cache(key, data)
    return data


def cached_fetch_json(key: str, url: str, timeout: int = 30) -> dict | list | None:
    """Fetch JSON from cache or URL. Returns parsed JSON."""
    raw = cached_fetch(key, url, timeout)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"    JSON parse error for {key}: {e}")
        return None


def cached_fetch_html(key: str, url: str, timeout: int = 30) -> str | None:
    """Fetch HTML from cache or URL. Returns raw HTML string."""
    return cached_fetch(key, url, timeout)


def cache_stats() -> dict:
    """Get cache statistics."""
    if not SOURCES_DIR.exists():
        return {"files": 0, "size_mb": 0, "categories": []}

    total_size = 0
    total_files = 0
    categories = set()

    for f in SOURCES_DIR.rglob("*"):
        if f.is_file():
            total_files += 1
            total_size += f.stat().st_size
            # First directory component is the category
            rel = f.relative_to(SOURCES_DIR)
            if len(rel.parts) > 1:
                categories.add(rel.parts[0])

    return {
        "files": total_files,
        "size_mb": round(total_size / 1024 / 1024, 1),
        "categories": sorted(categories),
    }


if __name__ == "__main__":
    stats = cache_stats()
    print(f"Source cache: {SOURCES_DIR}")
    print(f"  Files: {stats['files']}")
    print(f"  Size: {stats['size_mb']} MB")
    print(f"  Categories: {', '.join(stats['categories']) or '(empty)'}")
