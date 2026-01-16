"""
BibleMVP - FastAPI Backend
A free, open-source Bible study platform.
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Optional
import sqlite3

from .database import get_db_connection, init_db
from .models import Passage, SearchResult, WordDetail, CommentaryEntry

app = FastAPI(
    title="BibleMVP API",
    description="Free Bible study platform with cross-resource linking",
    version="0.1.0"
)

# Static files
frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_path / "static"), name="static")


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db()


@app.get("/")
async def root():
    """Serve the main application page."""
    return FileResponse(frontend_path / "index.html")


@app.get("/api/passage/{reference}")
async def get_passage(
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
            SELECT v.id, v.book, v.chapter, v.verse, v.text,
                   GROUP_CONCAT(w.id) as word_ids
            FROM verses v
            LEFT JOIN words w ON w.verse_id = v.id
            WHERE v.book = ? AND v.chapter = ?
                  AND v.translation_id = ?
            GROUP BY v.id
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

        return {
            "reference": f"{book} {chapter}" if not has_verse else reference,
            "translation": translation,
            "verses": [dict(v) for v in verses],
            "cross_references": cross_refs,
            "highlighted_verses": highlighted_verses
        }
    finally:
        conn.close()


@app.get("/api/passage/{reference}/commentary")
async def get_commentary(reference: str):
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
                      AND reference_start <= ? AND reference_end >= ?
                ORDER BY reference_start, source
            """, (book, chapter, verse_end, verse_start))

        entries = cursor.fetchall()
        return {"reference": reference, "entries": [dict(e) for e in entries]}
    finally:
        conn.close()


@app.get("/api/passage/{reference}/crossrefs")
async def get_crossrefs(reference: str):
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


@app.get("/api/verse/{reference}")
async def get_single_verse(
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


@app.get("/api/search")
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    scope: str = Query(default="all", description="Search scope: bible, book:BookName, notes, commentary, all")
):
    """Full-text search across Bible text, notes, and commentaries."""
    conn = get_db_connection()
    try:
        results = []

        # Check if searching within a specific book
        book_filter = None
        if scope.startswith("book:"):
            book_filter = scope[5:]
            scope = "bible"

        if scope in ("all", "bible"):
            if book_filter:
                cursor = conn.execute("""
                    SELECT 'verse' as type, book, chapter, verse,
                           snippet(verses_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
                    FROM verses_fts
                    WHERE verses_fts MATCH ? AND book = ?
                    LIMIT 50
                """, (q, book_filter))
            else:
                cursor = conn.execute("""
                    SELECT 'verse' as type, book, chapter, verse,
                           snippet(verses_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
                    FROM verses_fts
                    WHERE verses_fts MATCH ?
                    LIMIT 50
                """, (q,))
            results.extend([dict(r) for r in cursor.fetchall()])

        if scope in ("all", "commentary"):
            cursor = conn.execute("""
                SELECT 'commentary' as type, source, book, chapter,
                       snippet(commentary_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
                FROM commentary_fts
                WHERE commentary_fts MATCH ?
                LIMIT 50
            """, (q,))
            results.extend([dict(r) for r in cursor.fetchall()])

        return {"query": q, "scope": scope, "results": results}
    finally:
        conn.close()


@app.get("/api/word/{strong_number}")
async def get_word(strong_number: str):
    """Get lexicon entry and all occurrences for a Strong's number."""
    conn = get_db_connection()
    try:
        # Get word details
        cursor = conn.execute("""
            SELECT strong_number, original, transliteration,
                   pronunciation, definition, extended_definition, derivation, language
            FROM lexicon
            WHERE strong_number = ?
        """, (strong_number,))

        word = cursor.fetchone()
        if not word:
            raise HTTPException(status_code=404, detail=f"Word not found: {strong_number}")

        # Get all occurrences
        cursor = conn.execute("""
            SELECT v.book, v.chapter, v.verse, w.position, w.translation
            FROM words w
            JOIN verses v ON w.verse_id = v.id
            WHERE w.strong_number = ?
            ORDER BY v.book_order, v.chapter, v.verse, w.position
        """, (strong_number,))

        occurrences = cursor.fetchall()

        return {
            "word": dict(word),
            "occurrences": [dict(o) for o in occurrences],
            "count": len(occurrences)
        }
    finally:
        conn.close()


@app.get("/api/passage/{reference}/interlinear")
async def get_passage_interlinear(
    reference: str,
    translation: str = Query(default="WEB", description="Bible translation")
):
    """Get interlinear (original language) data for an entire chapter."""
    conn = get_db_connection()
    try:
        parsed = parse_reference(reference)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")

        book, chapter, _, _, _ = parsed

        # Get all words for the chapter with lexicon data
        cursor = conn.execute("""
            SELECT v.verse, w.position, w.text as original_text, w.strong_number, w.parsing, w.translation,
                   l.original as lexeme, l.transliteration, l.pronunciation, l.definition,
                   l.language
            FROM words w
            JOIN verses v ON w.verse_id = v.id
            LEFT JOIN lexicon l ON w.strong_number = l.strong_number
            WHERE v.book = ? AND v.chapter = ? AND v.translation_id = ?
            ORDER BY v.verse, w.position
        """, (book, chapter, translation))

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

        # Fallback language detection
        if not language and verses_data:
            language = 'hebrew' if book == 'Genesis' else 'greek' if book == 'Matthew' else None

        return {
            "reference": reference,
            "book": book,
            "chapter": chapter,
            "language": language,
            "verses": verses_data,
            "has_interlinear": len(verses_data) > 0
        }
    finally:
        conn.close()


@app.get("/api/devotional")
async def get_devotional(date: Optional[str] = None):
    """Get today's devotional or specified date (MM-DD format)."""
    from datetime import datetime

    if date is None:
        date = datetime.now().strftime("%m-%d")

    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            SELECT date, source, title, content, scripture_refs
            FROM devotionals
            WHERE date = ?
        """, (date,))

        entries = cursor.fetchall()
        if not entries:
            raise HTTPException(status_code=404, detail=f"No devotional for: {date}")

        return {"date": date, "entries": [dict(e) for e in entries]}
    finally:
        conn.close()


# Helper functions

def parse_reference(reference: str) -> Optional[tuple]:
    """
    Parse a Bible reference into (book, chapter, verse_start, verse_end, has_verse).
    Returns None if invalid.
    has_verse indicates whether a specific verse was requested (for highlighting).
    """
    import re

    # Book name abbreviations
    abbrevs = {
        "gen": "Genesis", "ex": "Exodus", "lev": "Leviticus", "num": "Numbers",
        "deut": "Deuteronomy", "josh": "Joshua", "judg": "Judges", "ruth": "Ruth",
        "1sam": "1 Samuel", "2sam": "2 Samuel", "1kgs": "1 Kings", "2kgs": "2 Kings",
        "1chr": "1 Chronicles", "2chr": "2 Chronicles", "ezra": "Ezra", "neh": "Nehemiah",
        "esth": "Esther", "job": "Job", "ps": "Psalms", "prov": "Proverbs",
        "eccl": "Ecclesiastes", "song": "Song of Solomon", "isa": "Isaiah",
        "jer": "Jeremiah", "lam": "Lamentations", "ezek": "Ezekiel", "dan": "Daniel",
        "hos": "Hosea", "joel": "Joel", "amos": "Amos", "obad": "Obadiah",
        "jonah": "Jonah", "mic": "Micah", "nah": "Nahum", "hab": "Habakkuk",
        "zeph": "Zephaniah", "hag": "Haggai", "zech": "Zechariah", "mal": "Malachi",
        "matt": "Matthew", "mk": "Mark", "lk": "Luke", "jn": "John",
        "acts": "Acts", "rom": "Romans", "1cor": "1 Corinthians", "2cor": "2 Corinthians",
        "gal": "Galatians", "eph": "Ephesians", "phil": "Philippians", "col": "Colossians",
        "1thess": "1 Thessalonians", "2thess": "2 Thessalonians",
        "1tim": "1 Timothy", "2tim": "2 Timothy", "titus": "Titus", "phlm": "Philemon",
        "heb": "Hebrews", "jas": "James", "1pet": "1 Peter", "2pet": "2 Peter",
        "1jn": "1 John", "2jn": "2 John", "3jn": "3 John", "jude": "Jude", "rev": "Revelation"
    }

    # Pattern: Book Chapter:Verse(-Verse)? or just Book (defaults to ch 1)
    pattern = r'^(\d?\s*\w+)(?:\s+(\d+))?(?::(\d+)(?:-(\d+))?)?$'
    match = re.match(pattern, reference.strip(), re.IGNORECASE)

    if not match:
        return None

    # If no chapter specified, default to chapter 1
    if match.group(2) is None:
        book_raw = match.group(1)
        book_key = book_raw.lower().replace(" ", "")
        book = abbrevs.get(book_key, book_raw.title())
        return (book, 1, 1, 999, False)

    book_raw, chapter, verse_start, verse_end = match.groups()

    # Normalize book name
    book_key = book_raw.lower().replace(" ", "")
    book = abbrevs.get(book_key, book_raw.title())

    chapter = int(chapter)
    has_verse = verse_start is not None
    verse_start = int(verse_start) if verse_start else 1
    verse_end = int(verse_end) if verse_end else (verse_start if has_verse else 999)

    return (book, chapter, verse_start, verse_end, has_verse)


def get_cross_references(conn, book: str, chapter: int, verse_start: int, verse_end: int) -> list:
    """Get cross-references for a passage."""
    cursor = conn.execute("""
        SELECT target_book, target_chapter, target_verse, relationship_type
        FROM cross_references
        WHERE source_book = ? AND source_chapter = ?
              AND source_verse BETWEEN ? AND ?
        ORDER BY target_book_order, target_chapter, target_verse
    """, (book, chapter, verse_start, verse_end))

    return [dict(r) for r in cursor.fetchall()]


# Catch-all route for clean URLs (e.g., /John/3/16)
# Must be registered last to not override other routes
@app.get("/{book}/{chapter}")
@app.get("/{book}/{chapter}/{verse}")
async def serve_app_with_reference(book: str, chapter: int, verse: int = None):
    """Serve main app for clean URLs - JS handles the routing."""
    return FileResponse(frontend_path / "index.html")
