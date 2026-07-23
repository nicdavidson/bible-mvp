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

@router.get("/api/passage/{reference}")
def get_passage(
    reference: str,
    translation: str = Query(default="WEB", description="Bible translation")
):
    """
    Get verse(s) with interlinear data and cross-references.

    Reference formats:
    - John 3:16 (single verse) - returns full chapter, highlights verse 16
    - John 3:16-18 (verse range) - returns full chapter, highlights verses 16-18
    - John 3 (full chapter) - returns full chapter, no highlighting
    - Rom 3:25 (abbreviations supported)
    """
    conn = get_db_connection()
    try:
        # Parse reference and fetch verses
        parsed = parse_reference(reference)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")

        book, chapter, verse_start, verse_end, has_verse = parsed

        # Always fetch the full chapter
        cursor = conn.execute("""
            SELECT v.id, v.book, v.chapter, v.verse, v.text
            FROM verses v
            WHERE v.book = ? AND v.chapter = ?
                  AND v.translation_id = ?
            ORDER BY v.verse
        """, (book, chapter, translation))

        verses = cursor.fetchall()
        if not verses:
            raise HTTPException(status_code=404, detail=f"Passage not found: {reference}")

        # Build highlighted verses list (only if specific verse was requested)
        highlighted_verses = []
        if has_verse:
            highlighted_verses = list(range(verse_start, verse_end + 1))

        # Get cross-references for the requested verses
        cross_refs = get_cross_references(conn, book, chapter, verse_start, verse_end)

        # Get verses with divine speech for red-letter display
        speaker_verses = get_speaker_verses(conn, book, chapter)

        return {
            "reference": f"{book} {chapter}" if not has_verse else reference,
            "translation": translation,
            "verses": [dict(v) for v in verses],
            "cross_references": cross_refs,
            "highlighted_verses": highlighted_verses,
            "speaker_verses": speaker_verses
        }
    finally:
        conn.close()


@router.get("/api/passage/{reference}/parallel")
def get_parallel_passage(
    reference: str,
    translations: str = Query(default="BSB,KJV,WEB", description="Comma-separated translation IDs")
):
    """
    Get verse(s) for multiple translations in parallel.
    Returns all requested translations for the same passage.
    """
    conn = get_db_connection()
    try:
        parsed = parse_reference(reference)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")

        book, chapter, verse_start, verse_end, has_verse = parsed

        translation_list = [t.strip() for t in translations.split(",") if t.strip()]
        if not translation_list:
            raise HTTPException(status_code=400, detail="No translations specified")

        result_translations = {}
        for tid in translation_list:
            cursor = conn.execute("""
                SELECT v.verse, v.text
                FROM verses v
                WHERE v.book = ? AND v.chapter = ? AND v.translation_id = ?
                ORDER BY v.verse
            """, (book, chapter, tid))
            result_translations[tid] = [dict(row) for row in cursor.fetchall()]

        return {
            "reference": f"{book} {chapter}",
            "book": book,
            "chapter": chapter,
            "translations": result_translations
        }
    finally:
        conn.close()


@router.get("/api/passage/{reference}/commentary")
def get_commentary(reference: str):
    """Get commentary entries for a passage."""
    conn = get_db_connection()
    try:
        parsed = parse_reference(reference)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")

        book, chapter, verse_start, verse_end, _ = parsed

        # If viewing full chapter (verse_end=999), get all commentary for chapter
        # Otherwise, get commentary that overlaps with the requested verse range
        if verse_end == 999:
            cursor = conn.execute("""
                SELECT source, content, reference_start, reference_end
                FROM commentary_entries
                WHERE book = ? AND chapter = ?
                ORDER BY reference_start, source
            """, (book, chapter))
        else:
            cursor = conn.execute("""
                SELECT source, content, reference_start, reference_end
                FROM commentary_entries
                WHERE book = ? AND chapter = ?
                      AND reference_start <= ?
                      AND COALESCE(reference_end, reference_start) >= ?
                ORDER BY reference_start, source
            """, (book, chapter, verse_end, verse_start))

        entries = cursor.fetchall()
        return {"reference": reference, "entries": [dict(e) for e in entries]}
    finally:
        conn.close()


@router.get("/api/passage/{reference}/crossrefs")
def get_crossrefs(reference: str):
    """Get cross-references for a passage."""
    conn = get_db_connection()
    try:
        parsed = parse_reference(reference)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")

        book, chapter, verse_start, verse_end, _ = parsed
        cross_refs = get_cross_references(conn, book, chapter, verse_start, verse_end)
        return {"reference": reference, "cross_references": cross_refs}
    finally:
        conn.close()


@router.get("/api/verse/{reference}")
def get_single_verse(
    reference: str,
    translation: str = Query(default="WEB", description="Bible translation")
):
    """Get a single verse text for previews."""
    conn = get_db_connection()
    try:
        parsed = parse_reference(reference)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")

        book, chapter, verse_start, _, _ = parsed

        cursor = conn.execute("""
            SELECT text FROM verses
            WHERE book = ? AND chapter = ? AND verse = ? AND translation_id = ?
        """, (book, chapter, verse_start, translation))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Verse not found: {reference}")

        return {"reference": reference, "text": row["text"]}
    finally:
        conn.close()


@router.get("/api/search")
@limiter.limit("30/minute")
def search(
    request: Request,
    q: str = Query(..., min_length=2, description="Search query"),
    scope: str = Query(default="all", description="Search scope: bible, ot, nt, book:BookName, commentary, all")
):
    """Full-text search across Bible text, notes, and commentaries."""
    conn = get_db_connection()
    try:
        results = []

        # Check if this is a Strong's number search (G### or H###)
        strongs_match = re.match(r'^([GH])(\d+)$', q.strip(), re.IGNORECASE)
        if strongs_match:
            prefix = strongs_match.group(1).upper()
            number = strongs_match.group(2)
            strongs_num = f"{prefix}{number}"

            # Get the lexicon entry for this Strong's number
            lex_cursor = conn.execute("""
                SELECT original, transliteration, definition
                FROM lexicon
                WHERE strong_number = ?
            """, (strongs_num,))
            lex_row = lex_cursor.fetchone()
            word_info = None
            if lex_row:
                word_info = {
                    "strong_number": strongs_num,
                    "original": lex_row["original"],
                    "transliteration": lex_row["transliteration"],
                    "definition": lex_row["definition"]
                }

            # word_alignments stores zero-padded Strong's numbers (H430 -> H0430)
            padded_strong = f"{prefix}{number.zfill(4)}"

            # Search for verses with this Strong's number, including the original word
            cursor = conn.execute("""
                SELECT 'verse' as type, v.book, v.chapter, v.verse,
                       v.text as snippet, wa.hebrew_text as original_word,
                       wa.english_gloss as gloss
                FROM word_alignments wa
                JOIN verses v ON v.book = wa.book
                    AND v.chapter = wa.chapter
                    AND v.verse = wa.verse
                    AND v.translation_id = 'WEB'
                WHERE wa.strong_number IN (?, ?)
                GROUP BY v.book, v.chapter, v.verse
                ORDER BY v.book_order, v.chapter, v.verse
                LIMIT 50
            """, (strongs_num, padded_strong))

            for row in cursor.fetchall():
                result = dict(row)
                # Highlight the translated word in the snippet if we have a gloss
                if result.get("gloss"):
                    gloss = result["gloss"]
                    snippet = result["snippet"]
                    # Try to highlight the gloss word in the verse text
                    pattern = re.compile(r'\b(' + re.escape(gloss) + r')\b', re.IGNORECASE)
                    result["snippet"] = pattern.sub(r'<mark>\1</mark>', snippet, count=1)
                results.append(result)

            return {"query": q, "scope": scope, "results": results, "word_info": word_info}

        # Check if searching within a specific book
        book_filter = None
        testament_filter = None
        if scope.startswith("book:"):
            book_filter = scope[5:]
            scope = "bible"
        elif scope == "ot":
            testament_filter = OT_BOOKS
            scope = "bible"
        elif scope == "nt":
            testament_filter = NT_BOOKS
            scope = "bible"

        # Build FTS query - handle phrase search with quotes
        # Sanitize FTS5 special characters to prevent OperationalError
        fts_query = q
        if '"' in q:
            # FTS5 handles quoted phrases natively, but ensure balanced quotes
            if q.count('"') % 2 != 0:
                fts_query = q.replace('"', '')
        else:
            # Strip FTS5 special operators that could cause syntax errors
            # Includes: * ( ) { } ^ ~ + - : which are all FTS5 syntax characters
            sanitized = re.sub(r'[*(){}^~+\-:]', '', q)
            # Add wildcard for partial matching on last word
            words = sanitized.split()
            if words:
                words[-1] = words[-1] + '*'
                fts_query = ' '.join(words)

        # Scope MATCH to the text column — the FTS tables also index book/chapter/verse
        # metadata, so a bare match on "john" returns every verse in the books of John.
        verses_query = f"text: ({fts_query})"
        commentary_query = f"searchable_text: ({fts_query})"

        try:
            if scope in ("all", "bible"):
                if book_filter:
                    cursor = conn.execute("""
                        SELECT 'verse' as type, book, chapter, verse,
                               snippet(verses_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
                        FROM verses_fts
                        WHERE verses_fts MATCH ? AND book = ?
                        ORDER BY rank
                        LIMIT 50
                    """, (verses_query, book_filter))
                elif testament_filter:
                    placeholders = ','.join('?' * len(testament_filter))
                    cursor = conn.execute(f"""
                        SELECT 'verse' as type, book, chapter, verse,
                               snippet(verses_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
                        FROM verses_fts
                        WHERE verses_fts MATCH ? AND book IN ({placeholders})
                        ORDER BY rank
                        LIMIT 50
                    """, (verses_query, *testament_filter))
                else:
                    cursor = conn.execute("""
                        SELECT 'verse' as type, book, chapter, verse,
                               snippet(verses_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
                        FROM verses_fts
                        WHERE verses_fts MATCH ?
                        ORDER BY rank
                        LIMIT 50
                    """, (verses_query,))
                results.extend([dict(r) for r in cursor.fetchall()])

            if scope in ("all", "commentary"):
                cursor = conn.execute("""
                    SELECT 'commentary' as type, source, book, chapter,
                           snippet(commentary_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
                    FROM commentary_fts
                    WHERE commentary_fts MATCH ?
                    ORDER BY rank
                    LIMIT 50
                """, (commentary_query,))
                results.extend([dict(r) for r in cursor.fetchall()])
        except sqlite3.OperationalError as e:
            # Malformed FTS query - return empty results rather than 500
            logger.warning("FTS query error for %r: %s", q, e)

        return {"query": q, "scope": scope, "results": results}
    finally:
        conn.close()


