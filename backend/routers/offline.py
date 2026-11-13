import json
import logging
import re
import sqlite3
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response

from .. import alignment_store
from ..database import get_db_connection, get_writable_db_connection, DATABASE_PATH
from ..core import (OT_BOOKS, NT_BOOKS, CANONICAL_BOOKS, limiter,
                    parse_reference, get_cross_references, get_speaker_verses)

logger = logging.getLogger(__name__)
router = APIRouter()

# Small default for "download commentary for offline": brief, broad, modern + classic
DEFAULT_OFFLINE_SOURCES = ("tyndale-study-notes", "jamieson-fausset-brown")

SOURCES_HELP = ("Comma-separated commentary sources (name or slug). Omitted: every source "
                "(old behaviour). Empty: no commentary.")


def _resolve_sources(conn, sources: Optional[str]) -> Optional[list]:
    """None = all sources; [] = none; else the matching canonical source names."""
    if sources is None:
        return None
    from .study import load_sources  # local import: study imports nothing from here
    wanted = {w.strip() for w in sources.split(",") if w.strip()}
    if not wanted:
        return []
    known = load_sources(conn)
    return [m["source"] for m in known if m["source"] in wanted or m["slug"] in wanted]


def _source_clause(names: Optional[list]) -> tuple[str, tuple]:
    if names is None:
        return "", ()
    if not names:
        return " AND 0", ()
    return f" AND source IN ({','.join('?' * len(names))})", tuple(names)


_sizes_cache: dict = {"key": None, "rows": None}

_LEXICON_JOIN = """
    LEFT JOIN lexicon l ON l.strong_number = CASE
        WHEN w.strong_number LIKE 'H0%' THEN 'H' || CAST(CAST(SUBSTR(w.strong_number, 2) AS INTEGER) AS TEXT)
        WHEN w.strong_number LIKE 'G0%' THEN 'G' || CAST(CAST(SUBSTR(w.strong_number, 2) AS INTEGER) AS TEXT)
        ELSE w.strong_number END"""


def _chapter_alignments(conn, translation, book, chapter, source_cols) -> dict:
    """{chapter: [alignment row]} for one chapter (or the whole book when chapter is None).

    Each row: verse, position, word, original_word_position, then `source_cols`
    (from word_alignments w / lexicon l), in verse and English word order. Links
    whose source word is missing from word_alignments are skipped, like the
    inner join over the per-word table this replaces.
    """
    where, params = ("AND chapter = ?", (translation, book, chapter)) if chapter is not None \
        else ("", (translation, book))
    src = {}
    for r in conn.execute(f"""
            SELECT w.chapter AS _ch, w.verse AS _v, w.word_position AS _pos, {source_cols}
            FROM word_alignments w {_LEXICON_JOIN}
            WHERE w.book = ? {where.replace('chapter', 'w.chapter')}""", params[1:]):
        d = dict(r)
        src[(d.pop("_ch"), d.pop("_v"), d.pop("_pos"))] = d
    out = {} if chapter is None else {chapter: []}
    for r in conn.execute(f"""
            SELECT p.chapter, p.verse, p.method, p.links, v.text
            FROM {alignment_store.TABLE} p
            JOIN verses v ON v.translation_id = p.translation_id AND v.book = p.book
                 AND v.chapter = p.chapter AND v.verse = p.verse
            WHERE p.translation_id = ? AND p.book = ? {where.replace('chapter', 'p.chapter')}
            ORDER BY p.chapter, p.verse""", params):
        words = alignment_store.tappable_words(r["text"])
        rows = out.setdefault(r["chapter"], [])
        for epos, opos, conf, method in alignment_store.unpack(r["method"], r["links"]):
            s = src.get((r["chapter"], r["verse"], opos))
            if s is not None:
                rows.append({"verse": r["verse"], "position": epos, "word": words[epos - 1],
                             "original_word_position": opos, "confidence": conf,
                             "method": method, **s})
    return out

# ========== OFFLINE DATA EXPORT ENDPOINTS ==========

@router.get("/api/offline/chapter")
@limiter.limit("120/minute")
def get_chapter_offline_data(
    request: Request,
    book: str,
    chapter: int,
    translation: str = Query(default="BSB"),
    sources: Optional[str] = Query(default=None, max_length=1000, description=SOURCES_HELP),
):
    """
    Get all data needed for offline access to a chapter.
    Includes verses, alignments, interlinear, cross-refs, and commentary.
    """
    conn = get_db_connection()
    try:
        # Get verses
        cursor = conn.execute("""
            SELECT verse, text FROM verses
            WHERE book = ? AND chapter = ? AND translation_id = ?
            ORDER BY verse
        """, (book, chapter, translation))
        verses = [dict(v) for v in cursor.fetchall()]

        # Word alignments for this chapter (packed per verse; same rows as the old join)
        alignments = _chapter_alignments(
            conn, translation, book, chapter,
            "w.hebrew_text as original_text, w.transliteration, w.english_gloss as gloss, "
            "w.strong_number, w.grammar, l.definition, l.extended_definition, l.language")[chapter]

        # Get interlinear data
        cursor = conn.execute("""
            SELECT verse, word_position as position, hebrew_text as original_text,
                   transliteration, english_gloss as gloss, strong_number, grammar
            FROM word_alignments
            WHERE book = ? AND chapter = ?
            ORDER BY verse, word_position
        """, (book, chapter))
        interlinear = [dict(i) for i in cursor.fetchall()]

        # Get cross-references
        cursor = conn.execute("""
            SELECT source_verse, target_book, target_chapter, target_verse
            FROM cross_references
            WHERE source_book = ? AND source_chapter = ?
            ORDER BY source_verse, target_book_order, target_chapter, target_verse
        """, (book, chapter))
        cross_refs = [dict(c) for c in cursor.fetchall()]

        # Get commentary (only the requested sources: all of them is ~190 KB a chapter)
        clause, params = _source_clause(_resolve_sources(conn, sources))
        cursor = conn.execute(f"""
            SELECT source, reference_start, reference_end, content
            FROM commentary_entries
            WHERE book = ? AND chapter = ?{clause}
            ORDER BY reference_start, reference_end
        """, (book, chapter, *params))
        commentary = [dict(c) for c in cursor.fetchall()]

        return {
            "book": book,
            "chapter": chapter,
            "translation": translation,
            "verses": verses,
            "alignments": alignments,
            "interlinear": interlinear,
            "crossRefs": cross_refs,
            "commentary": commentary
        }
    finally:
        conn.close()


@router.get("/api/offline/lexicon")
@limiter.limit("5/minute")
def get_lexicon_offline(request: Request):
    """Get the complete lexicon for offline use."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            SELECT strong_number, language, original, transliteration,
                   pronunciation, definition, extended_definition
            FROM lexicon
            ORDER BY strong_number
        """)
        entries = [dict(e) for e in cursor.fetchall()]
        return {"entries": entries, "count": len(entries)}
    finally:
        conn.close()


@router.get("/api/offline/book")
@limiter.limit("5/minute")
def get_book_offline_data(
    request: Request,
    book: str,
    translation: str = Query(default="BSB"),
    include_alignments: bool = Query(default=True),
    include_interlinear: bool = Query(default=True),
    include_crossrefs: bool = Query(default=True),
    include_commentary: bool = Query(default=True),
    sources: Optional[str] = Query(default=None, max_length=1000, description=SOURCES_HELP),
):
    """
    Get all data for an entire book for offline use.
    Can selectively include/exclude data types to manage download size.
    """
    conn = get_db_connection()
    try:
        result = {
            "book": book,
            "translation": translation,
            "chapters": {}
        }

        # One whole-book query per data type (instead of 5 queries per
        # chapter), grouped by chapter in Python. Row shapes and per-chapter
        # ordering match the old per-chapter queries exactly; the leading
        # chapter column is popped before output.
        def _group_by_chapter(cursor, chapter_col):
            grouped = {}
            for row in cursor:
                d = dict(row)
                grouped.setdefault(d.pop(chapter_col), []).append(d)
            return grouped

        # Verses (always included) — also defines which chapters exist
        cursor = conn.execute("""
            SELECT chapter, verse, text FROM verses
            WHERE book = ? AND translation_id = ?
            ORDER BY chapter, verse
        """, (book, translation))
        verses_by_ch = _group_by_chapter(cursor, "chapter")
        chapters = list(verses_by_ch.keys())  # insertion order = chapter order

        alignments_by_ch = {}
        if include_alignments:
            alignments_by_ch = _chapter_alignments(
                conn, translation, book, None,
                "w.hebrew_text as original_text, w.strong_number, l.definition, l.language")

        interlinear_by_ch = {}
        if include_interlinear:
            cursor = conn.execute("""
                SELECT chapter, verse, word_position as position, hebrew_text as original_text,
                       transliteration, english_gloss as gloss, strong_number
                FROM word_alignments
                WHERE book = ?
                ORDER BY chapter, verse, word_position
            """, (book,))
            interlinear_by_ch = _group_by_chapter(cursor, "chapter")

        crossrefs_by_ch = {}
        if include_crossrefs:
            cursor = conn.execute("""
                SELECT source_chapter, source_verse, target_book, target_chapter, target_verse
                FROM cross_references
                WHERE source_book = ?
            """, (book,))
            crossrefs_by_ch = _group_by_chapter(cursor, "source_chapter")

        commentary_by_ch = {}
        if include_commentary:
            clause, params = _source_clause(_resolve_sources(conn, sources))
            cursor = conn.execute(f"""
                SELECT chapter, source, reference_start, reference_end, content
                FROM commentary_entries
                WHERE book = ?{clause}
            """, (book, *params))
            commentary_by_ch = _group_by_chapter(cursor, "chapter")

        for chapter in chapters:
            chapter_data = {"verses": verses_by_ch[chapter]}
            if include_alignments:
                chapter_data["alignments"] = alignments_by_ch.get(chapter, [])
            if include_interlinear:
                chapter_data["interlinear"] = interlinear_by_ch.get(chapter, [])
            if include_crossrefs:
                chapter_data["crossRefs"] = crossrefs_by_ch.get(chapter, [])
            if include_commentary:
                chapter_data["commentary"] = commentary_by_ch.get(chapter, [])
            result["chapters"][chapter] = chapter_data

        return result
    finally:
        conn.close()


@router.get("/api/offline/commentary")
@limiter.limit("30/minute")
def get_commentary_offline_data(
    request: Request,
    book: str,
    sources: Optional[str] = Query(default=None, max_length=1000, description=SOURCES_HELP),
):
    """Commentary entries for a book for offline use, optionally for chosen sources only."""
    conn = get_db_connection()
    try:
        clause, params = _source_clause(_resolve_sources(conn, sources))
        cursor = conn.execute(f"""
            SELECT book, chapter, source, reference_start, reference_end, content
            FROM commentary_entries
            WHERE book = ?{clause}
            ORDER BY chapter, reference_start, reference_end
        """, (book, *params))
        entries = [dict(row) for row in cursor.fetchall()]
        return {"book": book, "entries": entries}
    finally:
        conn.close()


@router.get("/api/offline/commentary/sources")
@limiter.limit("30/minute")
def get_commentary_offline_sources(request: Request):
    """Each source with its full-download size, for the Settings offline list.

    `bytes` is the uncompressed text size of every entry (JSON adds a little;
    gzip on the wire is roughly a third). Computed once per DB file and cached:
    the first call reads every entry (a few seconds on a cold disk).
    """
    from .study import load_sources
    conn = get_db_connection()
    try:
        try:
            st = DATABASE_PATH.stat()
            key = (st.st_mtime_ns, st.st_size)
        except OSError:
            key = None
        if key is None or _sizes_cache["key"] != key:
            sizes = {r["source"]: (r["bytes"], r["books"]) for r in conn.execute(
                "SELECT source, SUM(LENGTH(content)) AS bytes, COUNT(DISTINCT book) AS books "
                "FROM commentary_entries GROUP BY source")}
            _sizes_cache.update(key=key, rows=sizes)
        sizes = _sizes_cache["rows"]
        out = []
        for m in load_sources(conn):
            b, books = sizes.get(m["source"], (0, 0))
            out.append({
                "source": m["source"], "slug": m["slug"], "short_name": m["short_name"],
                "kind": m["kind"], "coverage": m["coverage"], "entries": m["entry_count"],
                "books": books, "bytes": b or 0,
                "default": m["slug"] in DEFAULT_OFFLINE_SOURCES,
            })
        return {"sources": out}
    finally:
        conn.close()


@router.get("/api/offline/crossrefs")
@limiter.limit("30/minute")
def get_crossrefs_offline_data(request: Request, book: str):
    """Get all cross-references for a book for offline use."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            SELECT source_chapter as chapter, source_verse as verse,
                   target_book, target_chapter, target_verse
            FROM cross_references
            WHERE source_book = ?
            ORDER BY source_chapter, source_verse
        """, (book,))
        entries = [dict(row) for row in cursor.fetchall()]
        return {"book": book, "entries": entries}
    finally:
        conn.close()


@router.get("/api/offline/stats")
@limiter.limit("10/minute")
def get_offline_stats(request: Request):
    """Get statistics about available data for offline download planning."""
    conn = get_db_connection()
    try:
        stats = {}

        # Verses by translation
        cursor = conn.execute("""
            SELECT translation_id, COUNT(*) as count,
                   SUM(LENGTH(text)) as size_bytes
            FROM verses GROUP BY translation_id
        """)
        stats["verses"] = {row['translation_id']: {
            "count": row['count'],
            "size_mb": round(row['size_bytes'] / 1024 / 1024, 2)
        } for row in cursor.fetchall()}

        # Alignments by translation (linked words)
        cursor = conn.execute(f"""
            SELECT translation_id, SUM(n_links) as count
            FROM {alignment_store.TABLE} GROUP BY translation_id
        """)
        stats["alignments"] = {row['translation_id']: {
            "count": row['count'],
            "size_mb": round(row['count'] * 100 / 1024 / 1024, 2)  # Estimate ~100 bytes per alignment
        } for row in cursor.fetchall()}

        # Interlinear
        cursor = conn.execute("SELECT COUNT(*) as count FROM word_alignments")
        count = cursor.fetchone()['count']
        stats["interlinear"] = {"count": count, "size_mb": round(count * 80 / 1024 / 1024, 2)}

        # Lexicon
        cursor = conn.execute("SELECT COUNT(*) as count FROM lexicon")
        count = cursor.fetchone()['count']
        stats["lexicon"] = {"count": count, "size_mb": 1}

        # Cross-references
        cursor = conn.execute("SELECT COUNT(*) as count FROM cross_references")
        count = cursor.fetchone()['count']
        stats["crossRefs"] = {"count": count, "size_mb": round(count * 60 / 1024 / 1024, 2)}

        # Commentary by source
        cursor = conn.execute("""
            SELECT source, COUNT(*) as count, SUM(LENGTH(content)) as size_bytes
            FROM commentary_entries
            GROUP BY source
        """)
        stats["commentary"] = {}
        for row in cursor.fetchall():
            stats["commentary"][row['source']] = {
                "count": row['count'],
                "size_mb": round((row['size_bytes'] or 0) / 1024 / 1024, 2)
            }

        # Devotionals
        cursor = conn.execute("""
            SELECT source, COUNT(*) as count, SUM(LENGTH(content)) as size_bytes
            FROM devotionals
            GROUP BY source
        """)
        stats["devotionals"] = {}
        for row in cursor.fetchall():
            stats["devotionals"][row['source']] = {
                "count": row['count'],
                "size_mb": round((row['size_bytes'] or 0) / 1024 / 1024, 2)
            }

        return stats
    finally:
        conn.close()


@router.get("/api/offline/devotionals")
@limiter.limit("5/minute")
def get_devotionals_offline(request: Request, source: Optional[str] = None):
    """Get all devotionals for offline use."""
    conn = get_db_connection()
    try:
        if source:
            cursor = conn.execute("""
                SELECT source, month, day, time_of_day, title, verse_ref, content
                FROM devotionals
                WHERE source = ?
                ORDER BY month, day, time_of_day
            """, (source,))
        else:
            cursor = conn.execute("""
                SELECT source, month, day, time_of_day, title, verse_ref, content
                FROM devotionals
                ORDER BY source, month, day, time_of_day
            """)
        entries = [dict(row) for row in cursor.fetchall()]
        return {"entries": entries, "count": len(entries)}
    finally:
        conn.close()


