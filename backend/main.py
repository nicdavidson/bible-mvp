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
async def get_devotional(
    date: Optional[str] = None,
    time_of_day: Optional[str] = None
):
    """
    Get today's devotional or specified date.

    Parameters:
    - date: MM-DD format (e.g., "01-15" for January 15). Defaults to today.
    - time_of_day: "morning" or "evening". If omitted, returns both.
    """
    from datetime import datetime

    if date is None:
        now = datetime.now()
        month = now.month
        day = now.day
    else:
        parts = date.split("-")
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Date must be in MM-DD format")
        month = int(parts[0])
        day = int(parts[1])

    conn = get_db_connection()
    try:
        if time_of_day:
            cursor = conn.execute("""
                SELECT source, month, day, time_of_day, title, verse_ref, content
                FROM devotionals
                WHERE month = ? AND day = ? AND time_of_day = ?
                ORDER BY source
            """, (month, day, time_of_day))
        else:
            cursor = conn.execute("""
                SELECT source, month, day, time_of_day, title, verse_ref, content
                FROM devotionals
                WHERE month = ? AND day = ?
                ORDER BY time_of_day DESC, source
            """, (month, day))

        entries = cursor.fetchall()
        if not entries:
            raise HTTPException(status_code=404, detail=f"No devotional for: {month:02d}-{day:02d}")

        return {
            "date": f"{month:02d}-{day:02d}",
            "month": month,
            "day": day,
            "entries": [dict(e) for e in entries]
        }
    finally:
        conn.close()


@app.get("/api/devotional/sources")
async def get_devotional_sources():
    """Get available devotional sources and their entry counts."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            SELECT source, COUNT(*) as entry_count
            FROM devotionals
            GROUP BY source
            ORDER BY source
        """)
        sources = [dict(row) for row in cursor.fetchall()]
        return {"sources": sources}
    finally:
        conn.close()


# ========== READING PLAN ENDPOINTS ==========

@app.get("/api/reading-plans")
async def get_reading_plans():
    """Get list of available reading plans."""
    import json
    data_path = Path(__file__).parent.parent / "data"
    plans = []

    for plan_file in data_path.glob("reading-plan-*.json"):
        with open(plan_file) as f:
            plan = json.load(f)
            plans.append({
                "id": plan["id"],
                "name": plan["name"],
                "description": plan["description"],
                "duration_days": plan["duration_days"],
                "tracks": plan.get("tracks", [])
            })

    return {"plans": plans}


@app.get("/api/reading-plans/{plan_id}")
async def get_reading_plan(plan_id: str):
    """Get full reading plan with all days."""
    import json
    data_path = Path(__file__).parent.parent / "data"
    plan_file = data_path / f"reading-plan-{plan_id.replace('chronological-year', 'chronological')}.json"

    if not plan_file.exists():
        raise HTTPException(status_code=404, detail=f"Reading plan not found: {plan_id}")

    with open(plan_file) as f:
        return json.load(f)


@app.get("/api/reading-plans/{plan_id}/day/{day}")
async def get_reading_plan_day(plan_id: str, day: int):
    """Get a specific day's reading from a plan."""
    import json
    data_path = Path(__file__).parent.parent / "data"
    plan_file = data_path / f"reading-plan-{plan_id.replace('chronological-year', 'chronological')}.json"

    if not plan_file.exists():
        raise HTTPException(status_code=404, detail=f"Reading plan not found: {plan_id}")

    with open(plan_file) as f:
        plan = json.load(f)

    # Find the day
    for d in plan["days"]:
        if d["day"] == day:
            return {
                "plan_id": plan_id,
                "plan_name": plan["name"],
                "day": day,
                "total_days": plan["duration_days"],
                "readings": d
            }

    raise HTTPException(status_code=404, detail=f"Day {day} not found in plan")


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


# ========== OFFLINE DATA EXPORT ENDPOINTS ==========

@app.get("/api/offline/chapter")
async def get_chapter_offline_data(
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


@app.get("/api/offline/lexicon")
async def get_lexicon_offline():
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


@app.get("/api/offline/book")
async def get_book_offline_data(
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

        # Get all chapters for this book
        cursor = conn.execute("""
            SELECT DISTINCT chapter FROM verses
            WHERE book = ? AND translation_id = ?
            ORDER BY chapter
        """, (book, translation))
        chapters = [row['chapter'] for row in cursor.fetchall()]

        for chapter in chapters:
            chapter_data = {"verses": []}

            # Verses (always included)
            cursor = conn.execute("""
                SELECT verse, text FROM verses
                WHERE book = ? AND chapter = ? AND translation_id = ?
                ORDER BY verse
            """, (book, chapter, translation))
            chapter_data["verses"] = [dict(v) for v in cursor.fetchall()]

            if include_alignments:
                cursor = conn.execute("""
                    SELECT e.verse, e.english_word_position as position,
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
                    WHERE e.translation_id = ? AND e.book = ? AND e.chapter = ?
                    ORDER BY e.verse, e.english_word_position
                """, (translation, book, chapter))
                chapter_data["alignments"] = [dict(a) for a in cursor.fetchall()]

            if include_interlinear:
                cursor = conn.execute("""
                    SELECT verse, word_position as position, hebrew_text as original_text,
                           transliteration, english_gloss as gloss, strong_number
                    FROM word_alignments
                    WHERE book = ? AND chapter = ?
                    ORDER BY verse, word_position
                """, (book, chapter))
                chapter_data["interlinear"] = [dict(i) for i in cursor.fetchall()]

            if include_crossrefs:
                cursor = conn.execute("""
                    SELECT source_verse, target_book, target_chapter, target_verse
                    FROM cross_references
                    WHERE source_book = ? AND source_chapter = ?
                """, (book, chapter))
                chapter_data["crossRefs"] = [dict(c) for c in cursor.fetchall()]

            if include_commentary:
                cursor = conn.execute("""
                    SELECT source, reference_start, reference_end, content
                    FROM commentary_entries
                    WHERE book = ? AND chapter = ?
                """, (book, chapter))
                chapter_data["commentary"] = [dict(c) for c in cursor.fetchall()]

            result["chapters"][chapter] = chapter_data

        return result
    finally:
        conn.close()


@app.get("/api/offline/commentary")
async def get_commentary_offline_data(book: str):
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


@app.get("/api/offline/crossrefs")
async def get_crossrefs_offline_data(book: str):
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


@app.get("/api/offline/stats")
async def get_offline_stats():
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


@app.get("/api/offline/devotionals")
async def get_devotionals_offline(source: Optional[str] = None):
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


# Catch-all route for clean URLs (e.g., /John/3/16)
# Must be registered last to not override other routes
@app.get("/{book}/{chapter}")
@app.get("/{book}/{chapter}/{verse}")
async def serve_app_with_reference(book: str, chapter: int, verse: int = None):
    """Serve main app for clean URLs - JS handles the routing."""
    return FileResponse(frontend_path / "index.html")
