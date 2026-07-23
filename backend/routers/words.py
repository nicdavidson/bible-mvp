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

@router.get("/api/word-alignment")
def get_word_alignment(
    book: str,
    chapter: int,
    verse: int,
    word_position: int,
    translation: str = Query(default="KJV", description="Bible translation")
):
    """
    Look up the Hebrew/Greek original word for an English word by position.

    This enables deterministic word lookup when clicking English words.
    Returns the original word data including Strong's number and definition.
    """
    conn = get_db_connection()
    try:
        # Look up the alignment
        cursor = conn.execute("""
            SELECT ea.english_word, ea.original_word_position, ea.confidence,
                   wa.hebrew_text as original_text, wa.transliteration, wa.english_gloss,
                   wa.grammar as parsing,
                   CASE WHEN wa.strong_number LIKE 'H0%' THEN 'H' || CAST(CAST(SUBSTR(wa.strong_number, 2) AS INTEGER) AS TEXT)
                        WHEN wa.strong_number LIKE 'G0%' THEN 'G' || CAST(CAST(SUBSTR(wa.strong_number, 2) AS INTEGER) AS TEXT)
                        ELSE wa.strong_number END as strong_number
            FROM english_word_alignments ea
            JOIN word_alignments wa ON (
                wa.book = ea.book AND wa.chapter = ea.chapter
                AND wa.verse = ea.verse AND wa.word_position = ea.original_word_position
            )
            WHERE ea.translation_id = ?
              AND ea.book = ? AND ea.chapter = ? AND ea.verse = ?
              AND ea.english_word_position = ?
        """, (translation, book, chapter, verse, word_position))

        row = cursor.fetchone()
        if not row:
            return {"found": False, "message": "No alignment found for this word"}

        result = dict(row)
        strong_number = result.get('strong_number')

        # Get lexicon definition if we have a Strong's number
        if strong_number:
            cursor = conn.execute("""
                SELECT original, transliteration, pronunciation, definition,
                       extended_definition, derivation, language
                FROM lexicon
                WHERE strong_number = ?
            """, (strong_number,))

            lex_row = cursor.fetchone()
            if lex_row:
                lex_data = dict(lex_row)
                # Use lexicon transliteration if alignment doesn't have one
                if not result.get('transliteration'):
                    result['transliteration'] = lex_data.get('transliteration')
                result['pronunciation'] = lex_data.get('pronunciation')
                result['definition'] = lex_data.get('definition')
                result['extended_definition'] = lex_data.get('extended_definition')
                result['language'] = lex_data.get('language')

        return {"found": True, "alignment": result}
    finally:
        conn.close()


@router.get("/api/word/{strong_number}")
def get_word(
    strong_number: str,
    offset: int = Query(default=0, ge=0, description="Occurrence pagination offset"),
):
    """Get lexicon entry and occurrences (capped at 500/page) for a Strong's number."""
    conn = get_db_connection()
    try:
        # Get word details from lexicon
        cursor = conn.execute("""
            SELECT strong_number, original, transliteration,
                   pronunciation, definition, extended_definition, derivation, language
            FROM lexicon
            WHERE strong_number = ?
        """, (strong_number,))

        word = cursor.fetchone()
        if not word:
            raise HTTPException(status_code=404, detail=f"Word not found: {strong_number}")

        word_dict = dict(word)

        # If lexicon doesn't have transliteration, try to get from alignment data
        if not word_dict.get('transliteration'):
            # Normalize Strong's number format - alignment uses H0430, lexicon uses H430
            prefix = strong_number[0]  # H or G
            num = strong_number[1:]
            padded_strong = f"{prefix}{num.zfill(4)}"  # H430 -> H0430

            cursor = conn.execute("""
                SELECT transliteration FROM word_alignments
                WHERE strong_number = ? AND transliteration IS NOT NULL AND transliteration != ''
                LIMIT 1
            """, (padded_strong,))
            align_row = cursor.fetchone()
            if align_row and align_row['transliteration']:
                word_dict['transliteration'] = align_row['transliteration']

        # Get all occurrences from word_alignments (zero-padded Strong's)
        prefix = strong_number[0]  # H or G
        num = strong_number[1:]
        padded_strong = f"{prefix}{num.zfill(4)}"

        cursor = conn.execute("""
            SELECT COUNT(*) FROM word_alignments WHERE strong_number IN (?, ?)
        """, (strong_number, padded_strong))
        total = cursor.fetchone()[0]

        # Cap the payload — frequent words (e.g. H3068) have 6,000+ occurrences
        cursor = conn.execute("""
            SELECT book, chapter, verse, word_position as position, english_gloss as translation
            FROM word_alignments
            WHERE strong_number IN (?, ?)
            ORDER BY book, chapter, verse, word_position
            LIMIT 500 OFFSET ?
        """, (strong_number, padded_strong, offset))
        occurrences = cursor.fetchall()

        # Get translation variants (how the word is rendered in English)
        # Strip trailing/leading punctuation and normalize case for grouping
        cursor = conn.execute("""
            SELECT LOWER(TRIM(
                REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                    english_gloss, '.', ''), ',', ''), ';', ''), ':', ''), '!', '')
            )) as gloss, COUNT(*) as cnt
            FROM word_alignments
            WHERE strong_number = ?
              AND english_gloss IS NOT NULL AND english_gloss != ''
            GROUP BY gloss
            HAVING gloss != ''
            ORDER BY cnt DESC
            LIMIT 15
        """, (padded_strong,))
        glosses = [{"gloss": row["gloss"], "count": row["cnt"]} for row in cursor.fetchall()]

        # Get book frequency
        cursor = conn.execute("""
            SELECT book, COUNT(*) as cnt
            FROM word_alignments
            WHERE strong_number = ?
            GROUP BY book
            ORDER BY cnt DESC
        """, (padded_strong,))
        book_frequency = [{"book": row["book"], "count": row["cnt"]} for row in cursor.fetchall()]

        return {
            "word": word_dict,
            "occurrences": [dict(o) for o in occurrences],
            "count": len(occurrences),
            "total": total,
            "offset": offset,
            "glosses": glosses,
            "book_frequency": book_frequency
        }
    finally:
        conn.close()


@router.get("/api/passage/{reference}/interlinear")
def get_passage_interlinear(
    reference: str,
    translation: str = Query(default="WEB", description="Bible translation")
):
    """Get interlinear (original language) data for an entire chapter.

    The interlinear data comes from word_alignments which contains the original
    Hebrew/Greek text with English glosses. For Greek NT, words are filtered by
    the active translation's source text edition (BSB→SBLGNT, KJV→TR, WEB→Byzantine).
    Hebrew OT is the same for all translations (Masoretic/WLCM).
    """
    conn = get_db_connection()
    try:
        parsed = parse_reference(reference)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")

        book, chapter, _, _, _ = parsed

        # Build edition filter for Greek NT based on translation
        # BSB→SBL, KJV→TR, WEB→Byz. Hebrew has no edition data, so no filter needed.
        EDITION_FILTERS = {
            'BSB': "SBL",
            'KJV': "TR",
            'WEB': "Byz",
        }
        edition_key = EDITION_FILTERS.get(translation)

        # Query alignment data with variant info.
        # For Greek NT, filter to only show words present in the translation's source edition.
        # Words with no editions data (Hebrew OT, or legacy data) are always included.
        cursor = conn.execute("""
            SELECT a.verse, a.word_position as position, a.hebrew_text as original_text,
                   a.book || '.' || a.chapter || '.' || a.verse || '.' || a.word_position as word_id,
                   CASE WHEN a.strong_number LIKE 'H0%%' THEN 'H' || CAST(CAST(SUBSTR(a.strong_number, 2) AS INTEGER) AS TEXT)
                        WHEN a.strong_number LIKE 'G0%%' THEN 'G' || CAST(CAST(SUBSTR(a.strong_number, 2) AS INTEGER) AS TEXT)
                        ELSE a.strong_number END as strong_number,
                   a.grammar as parsing,
                   a.english_gloss as translation,
                   l.original as lexeme,
                   COALESCE(NULLIF(a.transliteration, ''), l.transliteration) as transliteration,
                   l.pronunciation,
                   l.definition,
                   l.extended_definition,
                   l.language,
                   a.word_type,
                   a.editions
            FROM word_alignments a
            LEFT JOIN lexicon l ON l.strong_number = CASE
                WHEN a.strong_number LIKE 'H0%%' THEN 'H' || CAST(CAST(SUBSTR(a.strong_number, 2) AS INTEGER) AS TEXT)
                WHEN a.strong_number LIKE 'G0%%' THEN 'G' || CAST(CAST(SUBSTR(a.strong_number, 2) AS INTEGER) AS TEXT)
                ELSE a.strong_number END
            WHERE a.book = ? AND a.chapter = ?
              AND (a.editions IS NULL OR ? IS NULL OR a.editions LIKE '%%' || ? || '%%')
            ORDER BY a.verse, a.word_position
        """, (book, chapter, edition_key, edition_key))

        rows = cursor.fetchall()

        # Group words by verse
        verses_data = {}
        language = None
        for row in rows:
            verse_num = row['verse']
            if verse_num not in verses_data:
                verses_data[verse_num] = []
            word_data = dict(row)
            del word_data['verse']  # Remove verse from individual word
            verses_data[verse_num].append(word_data)
            if not language and word_data.get('language'):
                language = word_data['language']

        # Fallback language detection based on testament
        if not language and verses_data:
            language = 'hebrew' if book in OT_BOOKS else 'greek' if book in NT_BOOKS else None

        # Determine source text based on language and translation
        # Different translations use different Greek source texts:
        #   BSB → SBLGNT (Critical Text), KJV → Textus Receptus, WEB → Byzantine Majority Text
        # All translations use the same Hebrew source (Masoretic Text / WLCM)
        GREEK_SOURCE_LABELS = {
            'BSB': 'SBL Greek New Testament',
            'KJV': 'Textus Receptus (Scrivener 1894)',
            'WEB': 'Byzantine Majority Text (Robinson-Pierpont)',
        }
        source_text = None
        if language == 'hebrew':
            source_text = 'Westminster Leningrad Codex'
        elif language == 'greek':
            source_text = GREEK_SOURCE_LABELS.get(translation, 'SBL Greek New Testament')

        return {
            "reference": reference,
            "book": book,
            "chapter": chapter,
            "language": language,
            "source_text": source_text,
            "verses": verses_data,
            "has_interlinear": len(verses_data) > 0
        }
    finally:
        conn.close()


