"""Commentary study view API: sources with per-selection availability, and entries.

Commentary comes at different granularities. Some sources comment verse by verse,
some on a passage, some on a whole chapter. Older imports also stored passage-level
entries with only a start verse (one chapter could be two rows, v1 and v22), which
made the passage invisible for any verse except its first. Every entry here
gets an *effective* range (`range_start`..`range_end`) so overlap with a selection
is answered the same way for every source.

Source metadata comes from `commentary_sources` when that table exists, otherwise
it is derived from the distinct `commentary_entries.source` values.
"""
import re
import threading

from fastapi import APIRouter, HTTPException, Query

from ..core import get_cross_references, parse_reference
from ..database import DATABASE_PATH, get_db_connection

router = APIRouter()

KINDS = ("verse", "passage", "chapter", "notes")

# Fallback metadata for sources imported before `commentary_sources` existed.
_KNOWN = {
    "John Gill": {
        "short_name": "Gill", "author": "John Gill", "year": "1746–63",
        "tradition": "Particular Baptist",
        "description": "Verse-by-verse exposition, strong on Jewish sources and the original languages.",
        "license": "Public domain",
    },
}

_META_COLUMNS = ("short_name", "author", "year", "tradition", "kind", "coverage", "license",
                 "attribution", "source_url", "sort_order", "description")

_cache_lock = threading.Lock()
_cache: dict = {"key": None, "sources": None}


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "source"


def requires_attribution(license_text) -> bool:
    """True when the license obliges us to credit the source wherever its text is shown.

    Public domain and CC0 do not; CC BY / BY-SA / anything else unrecognised does
    (fail safe: an unknown license keeps its credit visible).
    """
    if not license_text:
        return False
    lic = str(license_text).strip().lower()
    return not (lic.startswith("public domain") or lic in ("pd", "cc0", "cc0 1.0") or lic.startswith("cc0"))


def _table_exists(conn, name: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return row is not None


def _derive_kind(entries: int, chapters: int) -> str:
    # Verse-by-verse sources average many rows per chapter; passage sources a few.
    return "verse" if chapters and entries / chapters >= 6 else "passage"


def load_sources(conn) -> list[dict]:
    """All commentary sources, ordered, with metadata (cached per DB file version)."""
    try:
        st = DATABASE_PATH.stat()
        key = (st.st_mtime_ns, st.st_size)
    except OSError:
        key = None
    with _cache_lock:
        if key is not None and _cache["key"] == key:
            return _cache["sources"]

    stats = {
        r["source"]: (r["n"], r["chapters"])
        for r in conn.execute(
            "SELECT source, COUNT(*) AS n, COUNT(DISTINCT book || '|' || chapter) AS chapters "
            "FROM commentary_entries GROUP BY source")
    }
    table_rows = {}
    if _table_exists(conn, "commentary_sources"):
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(commentary_sources)")}
        wanted = ["source"] + [c for c in _META_COLUMNS if c in cols]
        for r in conn.execute(f"SELECT {', '.join(wanted)} FROM commentary_sources"):  # noqa: S608 (column allowlist)
            table_rows[r["source"]] = dict(r)

    sources = []
    for name, (n, chapters) in stats.items():
        meta = {**_KNOWN.get(name, {}), **{k: v for k, v in table_rows.get(name, {}).items() if v not in (None, "")}}
        kind = meta.get("kind")
        if kind not in KINDS:
            kind = _derive_kind(n, chapters)
        sources.append({
            "source": name,
            "slug": slugify(name),
            "short_name": meta.get("short_name") or name,
            "author": meta.get("author") or name,
            "year": str(meta["year"]) if meta.get("year") not in (None, "") else None,
            "tradition": meta.get("tradition"),
            "kind": kind,
            "coverage": meta.get("coverage"),
            "license": meta.get("license"),
            "attribution": meta.get("attribution"),
            "source_url": meta.get("source_url"),
            "sort_order": meta.get("sort_order") if isinstance(meta.get("sort_order"), int) else 1000,
            "description": meta.get("description"),
            "entry_count": n,
            "requires_attribution": requires_attribution(meta.get("license")),
        })
    sources.sort(key=lambda s: (s["sort_order"], s["source"].lower()))
    with _cache_lock:
        _cache.update(key=key, sources=sources)
    return sources


def effective_ranges(rows: list[dict], kind: str, last_verse: int) -> list[tuple[int, int]]:
    """Effective (start, end) for one source's entries in one chapter, in row order.

    rows must be sorted by reference_start. A passage entry stored with no end verse
    runs until the next entry of the same source begins (or the chapter ends).
    """
    starts = [r["reference_start"] or 1 for r in rows]
    out = []
    for i, r in enumerate(rows):
        start = starts[i]
        end = r["reference_end"]
        if kind == "chapter":
            out.append((1, max(last_verse, start)))
        elif end is not None and end > start:
            out.append((start, end))
        elif kind == "passage" and end is None:
            # Old imports stored passage rows with a start verse only
            nxt = next((s for s in starts[i + 1:] if s > start), None)
            out.append((start, nxt - 1 if nxt else max(last_verse, start)))
        else:
            out.append((start, end or start))
    return out


def _last_verse(conn, book: str, chapter: int) -> int:
    row = conn.execute("SELECT MAX(verse) FROM verses WHERE book = ? AND chapter = ?",
                       (book, chapter)).fetchone()
    return row[0] or 0


def _parse(reference: str):
    parsed = parse_reference(reference)
    if not parsed:
        raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")
    return parsed


def _canonical(book, chapter, vs, ve, has_verse):
    if not has_verse:
        return f"{book} {chapter}"
    return f"{book} {chapter}:{vs}" if vs == ve else f"{book} {chapter}:{vs}-{ve}"


@router.get("/api/commentary/sources")
def get_commentary_sources():
    """Every commentary source with its metadata (who, when, tradition, license)."""
    conn = get_db_connection()
    try:
        return {"sources": load_sources(conn)}
    finally:
        conn.close()


@router.get("/api/passage/{reference}/study")
def get_study(reference: str, translation: str = Query(default="BSB", max_length=10)):
    """Everything the study view needs for a selection in one call.

    The selected verses' text, plus every source with how many of its entries
    touch the selection (`selection_entries`), their effective ranges, and the
    nearest entry in the chapter when the source says nothing on the selection.
    """
    book, chapter, vs, ve, has_verse = _parse(reference)
    conn = get_db_connection()
    try:
        last = _last_verse(conn, book, chapter)
        if not last:
            raise HTTPException(status_code=404, detail=f"Passage not found: {reference}")
        ve = min(ve, last)
        if vs > last:
            raise HTTPException(status_code=404, detail=f"Passage not found: {reference}")

        verses = [dict(r) for r in conn.execute(
            "SELECT verse, text FROM verses WHERE book = ? AND chapter = ? AND translation_id = ? "
            "AND verse BETWEEN ? AND ? ORDER BY verse", (book, chapter, translation, vs, ve))]

        by_source: dict[str, list[dict]] = {}
        for r in conn.execute(
                "SELECT source, reference_start, reference_end FROM commentary_entries "
                "WHERE book = ? AND chapter = ? ORDER BY source, reference_start, id",
                (book, chapter)):
            by_source.setdefault(r["source"], []).append(dict(r))

        out = []
        for meta in load_sources(conn):
            rows = by_source.get(meta["source"], [])
            ranges = effective_ranges(rows, meta["kind"], last)
            hits = [(s, e) for s, e in ranges if s <= ve and e >= vs]
            nearest = None
            if rows and not hits:
                s, e = min(ranges, key=lambda r: min(abs(r[0] - vs), abs(r[1] - ve)))
                nearest = {"start": s, "end": e}
            out.append({**meta, "selection_entries": len(hits), "chapter_entries": len(rows),
                        "ranges": [{"start": s, "end": e} for s, e in hits], "nearest": nearest})
        return {
            "reference": _canonical(book, chapter, vs, ve, has_verse),
            "book": book, "chapter": chapter,
            "verse_start": vs, "verse_end": ve, "chapter_verses": last,
            "translation": translation, "verses": verses, "sources": out,
        }
    finally:
        conn.close()


@router.get("/api/passage/{reference}/commentary")
def get_commentary(reference: str, source: str | None = Query(default=None, max_length=200)):
    """Commentary entries overlapping a passage (whole chapter when no verse given).

    `source` filters to one source (name or slug). Each entry carries its effective
    `range_start`/`range_end`, so passage-level entries match every verse they cover.
    """
    book, chapter, vs, ve, _ = _parse(reference)
    conn = get_db_connection()
    try:
        sources = {s["source"]: s for s in load_sources(conn)}
        if source:
            match = next((s for s in sources.values() if source in (s["source"], s["slug"])), None)
            if not match:
                return {"reference": reference, "entries": []}
            rows = conn.execute(
                "SELECT source, content, reference_start, reference_end FROM commentary_entries "
                "WHERE book = ? AND chapter = ? AND source = ? ORDER BY reference_start, id",
                (book, chapter, match["source"])).fetchall()
        else:
            rows = conn.execute(
                "SELECT source, content, reference_start, reference_end FROM commentary_entries "
                "WHERE book = ? AND chapter = ? ORDER BY source, reference_start, id",
                (book, chapter)).fetchall()
        last = _last_verse(conn, book, chapter) if rows else 0

        grouped: dict[str, list[dict]] = {}
        for r in rows:
            grouped.setdefault(r["source"], []).append(dict(r))
        entries = []
        for name, items in grouped.items():
            kind = sources.get(name, {}).get("kind", "verse")
            for item, (s, e) in zip(items, effective_ranges(items, kind, last)):
                if s <= ve and e >= vs:
                    entries.append({**item, "range_start": s, "range_end": e})
        # Several rows of one source can overlap (overview + verse notes): start, then shortest
        entries.sort(key=lambda x: (x["range_start"], x["range_end"] - x["range_start"], x["source"]))
        return {"reference": reference, "entries": entries}
    finally:
        conn.close()



XREF_CREDIT = "Cross-references: OpenBible.info, CC BY 4.0 (based on the Treasury of Scripture Knowledge)"


@router.get("/api/passage/{reference}/study/crossrefs")
def get_study_crossrefs(reference: str, translation: str = Query(default="BSB", max_length=10)):
    """Cross-references for a selection with each target verse's text, for the study view.

    Same links as /api/passage/{ref}/crossrefs (both directions), plus `text` in the
    reader's translation, so the pane can show the verses inline in one request.
    `votes` is OpenBible.info's count of readers who found the link helpful; the
    client ranks by it.
    """
    book, chapter, vs, ve, has_verse = _parse(reference)
    conn = get_db_connection()
    try:
        last = _last_verse(conn, book, chapter)
        if not last or vs > last:
            raise HTTPException(status_code=404, detail=f"Passage not found: {reference}")
        ve = min(ve, last)
        refs = get_cross_references(conn, book, chapter, vs, ve)
        texts = {}
        keys = sorted({(r["target_book"], r["target_chapter"], r["target_verse"]) for r in refs})
        for i in range(0, len(keys), 300):   # SQLite's bound-parameter limit
            chunk = keys[i:i + 300]
            rows = conn.execute(
                "SELECT book, chapter, verse, text FROM verses WHERE translation_id = ? AND ("
                + " OR ".join(["(book = ? AND chapter = ? AND verse = ?)"] * len(chunk)) + ")",
                (translation, *[x for k in chunk for x in k]))
            for row in rows:
                texts[(row["book"], row["chapter"], row["verse"])] = row["text"]
        out = [{
            "source_verse": r["source_verse"],
            "target_book": r["target_book"], "target_chapter": r["target_chapter"],
            "target_verse": r["target_verse"], "votes": r["votes"] or 0,
            "text": texts.get((r["target_book"], r["target_chapter"], r["target_verse"])),
        } for r in refs]
        return {
            "reference": _canonical(book, chapter, vs, ve, has_verse),
            "book": book, "chapter": chapter, "verse_start": vs, "verse_end": ve,
            "translation": translation, "credit": XREF_CREDIT, "cross_references": out,
        }
    finally:
        conn.close()
