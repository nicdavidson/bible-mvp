import json
import logging
import re
import sqlite3
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response

from ..database import get_db_connection, get_writable_db_connection, DATABASE_PATH
from ..core import (OT_BOOKS, NT_BOOKS, CANONICAL_BOOKS, limiter,
                    parse_reference, get_cross_references, get_speaker_verses)

logger = logging.getLogger(__name__)
router = APIRouter()

# ========== OFFLINE DATA EXPORT ENDPOINTS ==========

@router.get("/api/offline/chapter")
@limiter.limit("20/minute")
def get_chapter_offline_data(
    request: Request,
    book: str,
    chapter: int,
    translation: str = Query(default="BSB")
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

        # Get word alignments for this chapter (BSB only has deterministic alignments)
        cursor = conn.execute("""
            SELECT e.verse, e.english_word_position as position,
                   e.english_word as word, e.original_word_position,
                   w.hebrew_text as original_text, w.transliteration,
                   w.english_gloss as gloss, w.strong_number, w.grammar,
                   l.definition, l.extended_definition, l.language
            FROM english_word_alignments e
            JOIN word_alignments w ON w.book = e.book AND w.chapter = e.chapter
                 AND w.verse = e.verse AND w.word_position = e.original_word_position
            LEFT JOIN lexicon l ON l.strong_number = CASE
                WHEN w.strong_number LIKE 'H0%' THEN 'H' || CAST(CAST(SUBSTR(w.strong_number, 2) AS INTEGER) AS TEXT)
                WHEN w.strong_number LIKE 'G0%' THEN 'G' || CAST(CAST(SUBSTR(w.strong_number, 2) AS INTEGER) AS TEXT)
                ELSE w.strong_number END
            WHERE e.translation_id = ? AND e.book = ? AND e.chapter = ?
            ORDER BY e.verse, e.english_word_position
        """, (translation, book, chapter))
        alignments = [dict(a) for a in cursor.fetchall()]

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

        # Get commentary
        cursor = conn.execute("""
            SELECT source, reference_start, reference_end, content
            FROM commentary_entries
            WHERE book = ? AND chapter = ?
            ORDER BY reference_start
        """, (book, chapter))
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
    include_commentary: bool = Query(default=True)
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
            cursor = conn.execute("""
                SELECT e.chapter, e.verse, e.english_word_position as position,
                       e.english_word as word, e.original_word_position,
                       w.hebrew_text as original_text, w.strong_number,
                       l.definition, l.language
                FROM english_word_alignments e
                JOIN word_alignments w ON w.book = e.book AND w.chapter = e.chapter
                     AND w.verse = e.verse AND w.word_position = e.original_word_position
                LEFT JOIN lexicon l ON l.strong_number = CASE
                    WHEN w.strong_number LIKE 'H0%' THEN 'H' || CAST(CAST(SUBSTR(w.strong_number, 2) AS INTEGER) AS TEXT)
                    WHEN w.strong_number LIKE 'G0%' THEN 'G' || CAST(CAST(SUBSTR(w.strong_number, 2) AS INTEGER) AS TEXT)
                    ELSE w.strong_number END
                WHERE e.translation_id = ? AND e.book = ?
                ORDER BY e.chapter, e.verse, e.english_word_position
            """, (translation, book))
            alignments_by_ch = _group_by_chapter(cursor, "chapter")

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
            cursor = conn.execute("""
                SELECT chapter, source, reference_start, reference_end, content
                FROM commentary_entries
                WHERE book = ?
            """, (book,))
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
@limiter.limit("10/minute")
def get_commentary_offline_data(request: Request, book: str):
    """Get all commentary entries for a book for offline use."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            SELECT book, chapter, source, reference_start, reference_end, content
            FROM commentary_entries
            WHERE book = ?
            ORDER BY chapter, reference_start
        """, (book,))
        entries = [dict(row) for row in cursor.fetchall()]
        return {"book": book, "entries": entries}
    finally:
        conn.close()


@router.get("/api/offline/crossrefs")
@limiter.limit("10/minute")
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

        # Alignments by translation
        cursor = conn.execute("""
            SELECT translation_id, COUNT(*) as count
            FROM english_word_alignments GROUP BY translation_id
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


