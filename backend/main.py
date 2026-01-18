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
    scope: str = Query(default="all", description="Search scope: bible, ot, nt, book:BookName, commentary, all")
):
    """Full-text search across Bible text, notes, and commentaries."""
    import re

    # OT/NT book lists for filtering
    OT_BOOKS = [
        "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
        "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
        "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles",
        "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
        "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah",
        "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
        "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
        "Haggai", "Zechariah", "Malachi"
    ]
    NT_BOOKS = [
        "Matthew", "Mark", "Luke", "John", "Acts", "Romans",
        "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
        "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
        "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews",
        "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John",
        "Jude", "Revelation"
    ]

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

            # Search for verses with this Strong's number, including the original word
            cursor = conn.execute("""
                SELECT 'verse' as type, v.book, v.chapter, v.verse,
                       v.text as snippet, w.text as original_word,
                       w.translation as gloss
                FROM words w
                JOIN verses v ON w.verse_id = v.id
                WHERE w.strong_number = ?
                ORDER BY v.book_order, v.chapter, v.verse
                LIMIT 50
            """, (strongs_num,))

            for row in cursor.fetchall():
                result = dict(row)
                # Highlight the translated word in the snippet if we have a gloss
                if result.get("gloss"):
                    gloss = result["gloss"]
                    snippet = result["snippet"]
                    # Try to highlight the gloss word in the verse text
                    import re as regex
                    pattern = regex.compile(r'\b(' + regex.escape(gloss) + r')\b', regex.IGNORECASE)
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
        fts_query = q
        if '"' in q:
            # FTS5 handles quoted phrases natively
            pass
        else:
            # Add wildcard for partial matching on last word
            words = q.split()
            if words:
                words[-1] = words[-1] + '*'
                fts_query = ' '.join(words)

        if scope in ("all", "bible"):
            if book_filter:
                cursor = conn.execute("""
                    SELECT 'verse' as type, book, chapter, verse,
                           snippet(verses_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
                    FROM verses_fts
                    WHERE verses_fts MATCH ? AND book = ?
                    ORDER BY rank
                    LIMIT 50
                """, (fts_query, book_filter))
            elif testament_filter:
                placeholders = ','.join('?' * len(testament_filter))
                cursor = conn.execute(f"""
                    SELECT 'verse' as type, book, chapter, verse,
                           snippet(verses_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
                    FROM verses_fts
                    WHERE verses_fts MATCH ? AND book IN ({placeholders})
                    ORDER BY rank
                    LIMIT 50
                """, (fts_query, *testament_filter))
            else:
                cursor = conn.execute("""
                    SELECT 'verse' as type, book, chapter, verse,
                           snippet(verses_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
                    FROM verses_fts
                    WHERE verses_fts MATCH ?
                    ORDER BY rank
                    LIMIT 50
                """, (fts_query,))
            results.extend([dict(r) for r in cursor.fetchall()])

        if scope in ("all", "commentary"):
            cursor = conn.execute("""
                SELECT 'commentary' as type, source, book, chapter,
                       snippet(commentary_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
                FROM commentary_fts
                WHERE commentary_fts MATCH ?
                ORDER BY rank
                LIMIT 50
            """, (fts_query,))
            results.extend([dict(r) for r in cursor.fetchall()])

        return {"query": q, "scope": scope, "results": results}
    finally:
        conn.close()


@app.get("/api/word-alignment")
async def get_word_alignment(
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


@app.get("/api/word/{strong_number}")
async def get_word(strong_number: str):
    """Get lexicon entry and all occurrences for a Strong's number."""
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
            "word": word_dict,
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
    """Get interlinear (original language) data for an entire chapter.

    The interlinear data comes from word_alignments which contains the original
    Hebrew/Greek text with English glosses. This is translation-independent since
    the original language text is the same regardless of which English translation
    is being viewed.
    """
    conn = get_db_connection()
    try:
        parsed = parse_reference(reference)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")

        book, chapter, _, _, _ = parsed

        # Query alignment data directly - this works for any translation since
        # the Hebrew/Greek text is the same. Normalize Strong's numbers for lexicon lookup.
        # Include word_id for deterministic English word alignment.
        cursor = conn.execute("""
            SELECT a.verse, a.word_position as position, a.hebrew_text as original_text,
                   a.book || '.' || a.chapter || '.' || a.verse || '.' || a.word_position as word_id,
                   CASE WHEN a.strong_number LIKE 'H0%' THEN 'H' || CAST(CAST(SUBSTR(a.strong_number, 2) AS INTEGER) AS TEXT)
                        WHEN a.strong_number LIKE 'G0%' THEN 'G' || CAST(CAST(SUBSTR(a.strong_number, 2) AS INTEGER) AS TEXT)
                        ELSE a.strong_number END as strong_number,
                   a.grammar as parsing,
                   a.english_gloss as translation,
                   l.original as lexeme,
                   COALESCE(NULLIF(a.transliteration, ''), l.transliteration) as transliteration,
                   l.pronunciation,
                   l.definition,
                   l.extended_definition,
                   l.language
            FROM word_alignments a
            LEFT JOIN lexicon l ON l.strong_number = CASE
                WHEN a.strong_number LIKE 'H0%' THEN 'H' || CAST(CAST(SUBSTR(a.strong_number, 2) AS INTEGER) AS TEXT)
                WHEN a.strong_number LIKE 'G0%' THEN 'G' || CAST(CAST(SUBSTR(a.strong_number, 2) AS INTEGER) AS TEXT)
                ELSE a.strong_number END
            WHERE a.book = ? AND a.chapter = ?
            ORDER BY a.verse, a.word_position
        """, (book, chapter))

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
        OT_BOOKS = [
            "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
            "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
            "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles",
            "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
            "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah",
            "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
            "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
            "Haggai", "Zechariah", "Malachi"
        ]
        if not language and verses_data:
            language = 'hebrew' if book in OT_BOOKS else 'greek' if book == 'Matthew' else None

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
