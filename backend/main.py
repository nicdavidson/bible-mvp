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
    # Create indexes needed for bidirectional cross-reference lookups
    conn = get_db_connection()
    try:
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_crossref_target
            ON cross_references(target_book, target_chapter, target_verse)
        """)
        conn.commit()
    finally:
        conn.close()


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


@app.get("/api/passage/{reference}/parallel")
async def get_parallel_passage(
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
        # Sanitize FTS5 special characters to prevent OperationalError
        fts_query = q
        if '"' in q:
            # FTS5 handles quoted phrases natively, but ensure balanced quotes
            if q.count('"') % 2 != 0:
                fts_query = q.replace('"', '')
        else:
            # Strip FTS5 special operators that could cause syntax errors
            import re as _re
            sanitized = _re.sub(r'[*(){}^~]', '', q)
            # Add wildcard for partial matching on last word
            words = sanitized.split()
            if words:
                words[-1] = words[-1] + '*'
                fts_query = ' '.join(words)

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
        except sqlite3.OperationalError:
            # Malformed FTS query - return empty results rather than 500
            pass

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
        NT_BOOKS = [
            "Matthew", "Mark", "Luke", "John", "Acts", "Romans",
            "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
            "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
            "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews",
            "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John",
            "Jude", "Revelation"
        ]
        if not language and verses_data:
            language = 'hebrew' if book in OT_BOOKS else 'greek' if book in NT_BOOKS else None

        # Determine source text based on language
        source_text = None
        if language == 'hebrew':
            source_text = 'Westminster Leningrad Codex'
        elif language == 'greek':
            source_text = 'SBL Greek New Testament'

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
        try:
            month = int(parts[0])
            day = int(parts[1])
        except ValueError:
            raise HTTPException(status_code=400, detail="Date must be in MM-DD format with numeric values")
        if not (1 <= month <= 12 and 1 <= day <= 31):
            raise HTTPException(status_code=400, detail="Invalid month or day")

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
    import re as _re
    # Sanitize plan_id to prevent path traversal
    if not _re.match(r'^[a-zA-Z0-9_-]+$', plan_id):
        raise HTTPException(status_code=400, detail="Invalid plan ID")
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
    import re as _re
    # Sanitize plan_id to prevent path traversal
    if not _re.match(r'^[a-zA-Z0-9_-]+$', plan_id):
        raise HTTPException(status_code=400, detail="Invalid plan ID")
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
        "gen": "Genesis", "ge": "Genesis", "ex": "Exodus", "exod": "Exodus",
        "lev": "Leviticus", "le": "Leviticus",
        "num": "Numbers", "nu": "Numbers",
        "deut": "Deuteronomy", "de": "Deuteronomy", "dt": "Deuteronomy",
        "josh": "Joshua", "jos": "Joshua",
        "judg": "Judges", "jdg": "Judges",
        "ruth": "Ruth", "ru": "Ruth",
        "1sam": "1 Samuel", "1sa": "1 Samuel", "2sam": "2 Samuel", "2sa": "2 Samuel",
        "1kgs": "1 Kings", "1ki": "1 Kings", "2kgs": "2 Kings", "2ki": "2 Kings",
        "1chr": "1 Chronicles", "1ch": "1 Chronicles", "2chr": "2 Chronicles", "2ch": "2 Chronicles",
        "ezra": "Ezra", "ezr": "Ezra",
        "neh": "Nehemiah", "ne": "Nehemiah",
        "esth": "Esther", "est": "Esther",
        "job": "Job",
        "ps": "Psalms", "psa": "Psalms", "psalm": "Psalms", "psalms": "Psalms",
        "prov": "Proverbs", "pro": "Proverbs", "pr": "Proverbs",
        "eccl": "Ecclesiastes", "ecc": "Ecclesiastes", "eccles": "Ecclesiastes",
        "song": "Song of Solomon", "songofsolomon": "Song of Solomon",
        "songofsongs": "Song of Solomon", "sos": "Song of Solomon", "ss": "Song of Solomon",
        "isa": "Isaiah", "is": "Isaiah",
        "jer": "Jeremiah", "je": "Jeremiah",
        "lam": "Lamentations", "la": "Lamentations",
        "ezek": "Ezekiel", "eze": "Ezekiel",
        "dan": "Daniel", "da": "Daniel",
        "hos": "Hosea", "ho": "Hosea",
        "joel": "Joel", "joe": "Joel",
        "amos": "Amos", "am": "Amos",
        "obad": "Obadiah", "ob": "Obadiah",
        "jonah": "Jonah", "jon": "Jonah",
        "mic": "Micah", "mi": "Micah",
        "nah": "Nahum", "na": "Nahum",
        "hab": "Habakkuk",
        "zeph": "Zephaniah", "zep": "Zephaniah",
        "hag": "Haggai",
        "zech": "Zechariah", "zec": "Zechariah",
        "mal": "Malachi",
        "matt": "Matthew", "mat": "Matthew", "mt": "Matthew",
        "mk": "Mark", "mar": "Mark",
        "lk": "Luke", "lu": "Luke", "luk": "Luke",
        "jn": "John", "joh": "John",
        "acts": "Acts", "act": "Acts", "ac": "Acts",
        "rom": "Romans", "ro": "Romans",
        "1cor": "1 Corinthians", "1co": "1 Corinthians",
        "2cor": "2 Corinthians", "2co": "2 Corinthians",
        "gal": "Galatians", "ga": "Galatians",
        "eph": "Ephesians",
        "phil": "Philippians", "php": "Philippians",
        "col": "Colossians",
        "1thess": "1 Thessalonians", "1thes": "1 Thessalonians", "1th": "1 Thessalonians",
        "2thess": "2 Thessalonians", "2thes": "2 Thessalonians", "2th": "2 Thessalonians",
        "1tim": "1 Timothy", "1ti": "1 Timothy",
        "2tim": "2 Timothy", "2ti": "2 Timothy",
        "titus": "Titus", "tit": "Titus",
        "phlm": "Philemon", "phm": "Philemon", "philem": "Philemon",
        "heb": "Hebrews",
        "jas": "James", "jam": "James",
        "1pet": "1 Peter", "1pe": "1 Peter",
        "2pet": "2 Peter", "2pe": "2 Peter",
        "1jn": "1 John", "1joh": "1 John", "1jo": "1 John",
        "2jn": "2 John", "2joh": "2 John", "2jo": "2 John",
        "3jn": "3 John", "3joh": "3 John", "3jo": "3 John",
        "jude": "Jude", "jud": "Jude",
        "rev": "Revelation", "re": "Revelation",
    }

    # Also map full canonical book names (case-insensitive) for direct lookup
    canonical_books = [
        "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
        "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
        "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles",
        "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
        "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah",
        "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
        "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
        "Haggai", "Zechariah", "Malachi",
        "Matthew", "Mark", "Luke", "John", "Acts", "Romans",
        "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
        "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
        "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews",
        "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John",
        "Jude", "Revelation"
    ]
    canonical_map = {b.lower(): b for b in canonical_books}
    # Add common alternative names
    canonical_map["song of songs"] = "Song of Solomon"
    canonical_map["psalm"] = "Psalms"

    # Pattern: supports multi-word book names (e.g., "Song of Solomon 8:1")
    # Splits on the last occurrence of a number sequence that looks like chapter
    pattern = r'^(.+?)\s+(\d+)(?::(\d+)(?:-(\d+))?)?$'
    match = re.match(pattern, reference.strip(), re.IGNORECASE)

    if not match:
        # No chapter - try as book name only (defaults to ch 1)
        book_raw = reference.strip()
        book_key = book_raw.lower().replace(" ", "")
        book = abbrevs.get(book_key) or canonical_map.get(book_raw.lower()) or book_raw.title()
        return (book, 1, 1, 999, False)

    book_raw, chapter, verse_start, verse_end = match.groups()

    # Normalize book name: try abbreviation, then canonical name, then title case
    book_key = book_raw.lower().replace(" ", "")
    book = abbrevs.get(book_key) or canonical_map.get(book_raw.lower()) or book_raw.title()

    chapter = int(chapter)
    has_verse = verse_start is not None
    verse_start = int(verse_start) if verse_start else 1
    verse_end = int(verse_end) if verse_end else (verse_start if has_verse else 999)

    return (book, chapter, verse_start, verse_end, has_verse)


def get_cross_references(conn, book: str, chapter: int, verse_start: int, verse_end: int) -> list:
    """Get cross-references for a passage (bidirectional)."""

    cursor = conn.execute("""
        SELECT source_verse, target_book, target_chapter, target_verse,
               MAX(book_order) as target_book_order, MAX(votes) as votes,
               relationship_type
        FROM (
            SELECT source_verse, target_book, target_chapter, target_verse,
                   b.book_order, votes, relationship_type
            FROM cross_references cr
            JOIN books b ON b.name = cr.target_book
            WHERE source_book = ? AND source_chapter = ?
                  AND source_verse BETWEEN ? AND ?
            UNION ALL
            SELECT target_verse, source_book, source_chapter, source_verse,
                   b.book_order, votes, relationship_type
            FROM cross_references cr
            JOIN books b ON b.name = cr.source_book
            WHERE cr.target_book = ? AND cr.target_chapter = ?
                  AND cr.target_verse BETWEEN ? AND ?
        )
        GROUP BY source_verse, target_book, target_chapter, target_verse
        ORDER BY target_book_order, target_chapter, target_verse
    """, (book, chapter, verse_start, verse_end,
          book, chapter, verse_start, verse_end))

    return [dict(r) for r in cursor.fetchall()]


def get_speaker_verses(conn, book: str, chapter: int) -> list:
    """Get verses with divine speech (God in OT, Jesus in NT) for red-letter display."""
    try:
        cursor = conn.execute("""
            SELECT verse, speaker
            FROM speaker_verses
            WHERE book = ? AND chapter = ? AND is_divine = 1
            ORDER BY verse
        """, (book, chapter))
        return [row[0] for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        return []


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


# ============================================================
# Christological seed verses for "Points to Jesus" mode
# ============================================================
CHRISTOLOGICAL_SEEDS = {
    "gospel-peaks": [
        ("John", 1, 1), ("John", 14, 6), ("Matthew", 1, 23),
        ("Mark", 10, 45), ("Luke", 2, 11), ("Isaiah", 53, 5),
    ],
    "messianic": [
        ("Genesis", 3, 15), ("Psalms", 22, 1), ("Psalms", 110, 1),
        ("Isaiah", 7, 14), ("Isaiah", 9, 6), ("Isaiah", 53, 5),
        ("Isaiah", 53, 7), ("Isaiah", 61, 1), ("Micah", 5, 2),
        ("Zechariah", 9, 9), ("Daniel", 7, 13), ("Malachi", 3, 1),
        ("Jeremiah", 23, 5), ("Jeremiah", 31, 31), ("Hosea", 11, 1),
        ("Zechariah", 12, 10), ("Deuteronomy", 18, 15),
        ("Psalms", 16, 10), ("Psalms", 118, 22), ("Isaiah", 40, 3),
    ],
}


def _enrich_nodes(conn, nodes: dict):
    """Add verse text preview and book metadata (testament, book_order) to nodes."""
    for key, node in nodes.items():
        if node.get("isChrist"):
            continue
        cursor = conn.execute("""
            SELECT text FROM verses
            WHERE book = ? AND chapter = ? AND verse = ? AND translation_id = 'BSB'
            LIMIT 1
        """, (node["book"], node["chapter"], node["verse"]))
        row = cursor.fetchone()
        if row:
            text = row[0]
            node["text"] = text[:120] + "..." if len(text) > 120 else text
        else:
            node["text"] = ""

    book_meta_cache = {}
    for key, node in nodes.items():
        if node.get("isChrist"):
            continue
        b = node["book"]
        if b not in book_meta_cache:
            cursor = conn.execute(
                "SELECT book_order, testament FROM books WHERE name = ?", (b,)
            )
            row = cursor.fetchone()
            if row:
                book_meta_cache[b] = {"book_order": row[0], "testament": row[1]}
            else:
                book_meta_cache[b] = {"book_order": 0, "testament": "OT"}
        meta = book_meta_cache[b]
        node["testament"] = meta["testament"]
        node["book_order"] = meta["book_order"]


@app.get("/api/crossref-map/christological")
async def get_crossref_map_christological(
    method: str = Query(default="gospel-peaks", description="Calculation method"),
    verse: str = Query(default=None, description="Verse for find-path mode"),
    depth: int = Query(default=2, ge=1, le=5, description="BFS depth from seeds"),
    per_verse: int = Query(default=5, ge=1, le=30, description="Top N connections per verse"),
    limit: int = Query(default=200, ge=20, le=500, description="Max nodes to return"),
):
    """
    Generate a christological cross-reference graph.
    Center is a synthetic CHRIST node; seeds are christological verses connected to it.
    """
    conn = get_db_connection()
    try:
        # Determine seed verses
        if method == "red-letter":
            # Top cross-referenced Jesus-spoken verses
            cursor = conn.execute("""
                SELECT sv.book, sv.chapter, sv.verse,
                       COUNT(cr.source_book) as xref_count
                FROM speaker_verses sv
                LEFT JOIN cross_references cr
                    ON (cr.source_book = sv.book AND cr.source_chapter = sv.chapter
                        AND cr.source_verse = sv.verse)
                    OR (cr.target_book = sv.book AND cr.target_chapter = sv.chapter
                        AND cr.target_verse = sv.verse)
                WHERE sv.speaker = 'Jesus'
                GROUP BY sv.book, sv.chapter, sv.verse
                ORDER BY xref_count DESC
                LIMIT 20
            """)
            seeds = [(row[0], row[1], row[2]) for row in cursor.fetchall()]
        elif method == "messianic":
            seeds = CHRISTOLOGICAL_SEEDS["messianic"]
        else:
            # Default: gospel-peaks
            seeds = CHRISTOLOGICAL_SEEDS["gospel-peaks"]

        # --- Find-path mode: BFS from user's verse to any seed ---
        if method == "find-path":
            if not verse:
                raise HTTPException(status_code=400, detail="Verse required for find-path mode")
            parsed = parse_reference(verse)
            if not parsed:
                raise HTTPException(status_code=400, detail=f"Invalid reference: {verse}")
            book, chapter, verse_start, verse_end, has_verse = parsed
            if not has_verse:
                raise HTTPException(status_code=400, detail="A specific verse is required")

            # All seed IDs we're trying to reach
            all_seeds = (
                CHRISTOLOGICAL_SEEDS["gospel-peaks"]
                + CHRISTOLOGICAL_SEEDS["messianic"]
            )
            seed_ids = {f"{s[0]}.{s[1]}.{s[2]}" for s in all_seeds}

            start_key = f"{book}.{chapter}.{verse_start}"
            nodes = {}
            edges = []
            edge_set = set()
            visited = set()
            parent = {}  # for path reconstruction
            queue = [(book, chapter, verse_start, 0)]
            nodes[start_key] = {
                "id": start_key, "book": book, "chapter": chapter,
                "verse": verse_start, "depth": 0
            }

            found_seed = None
            max_search_depth = 6

            while queue and not found_seed:
                src_book, src_chapter, src_verse, current_depth = queue.pop(0)
                src_key = f"{src_book}.{src_chapter}.{src_verse}"
                if src_key in visited:
                    continue
                visited.add(src_key)

                if src_key in seed_ids and src_key != start_key:
                    found_seed = src_key
                    break

                if current_depth >= max_search_depth:
                    continue

                cursor = conn.execute("""
                    SELECT target_book, target_chapter, target_verse, votes
                    FROM (
                        SELECT target_book, target_chapter, target_verse, votes
                        FROM cross_references
                        WHERE source_book = ? AND source_chapter = ? AND source_verse = ?
                        UNION ALL
                        SELECT source_book, source_chapter, source_verse, votes
                        FROM cross_references
                        WHERE target_book = ? AND target_chapter = ? AND target_verse = ?
                    )
                    GROUP BY target_book, target_chapter, target_verse
                    ORDER BY MAX(votes) DESC
                    LIMIT ?
                """, (src_book, src_chapter, src_verse,
                      src_book, src_chapter, src_verse, 15))

                for row in cursor.fetchall():
                    tgt_book, tgt_chapter, tgt_verse, votes = row
                    tgt_key = f"{tgt_book}.{tgt_chapter}.{tgt_verse}"

                    edge_key = (min(src_key, tgt_key), max(src_key, tgt_key))
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        edges.append({
                            "source": src_key, "target": tgt_key, "votes": votes
                        })

                    if tgt_key not in nodes:
                        nodes[tgt_key] = {
                            "id": tgt_key, "book": tgt_book,
                            "chapter": tgt_chapter, "verse": tgt_verse,
                            "depth": current_depth + 1,
                            "isSeed": tgt_key in seed_ids,
                        }
                        parent[tgt_key] = src_key

                    if tgt_key in seed_ids:
                        found_seed = tgt_key
                        break

                    if tgt_key not in visited:
                        queue.append((tgt_book, tgt_chapter, tgt_verse, current_depth + 1))

            # Reconstruct path
            path_to_christ = []
            if found_seed:
                curr = found_seed
                while curr and curr != start_key:
                    path_to_christ.append(curr)
                    curr = parent.get(curr)
                path_to_christ.append(start_key)
                path_to_christ.reverse()

            # Filter to only path + immediate neighbors for clarity
            path_set = set(path_to_christ) if path_to_christ else set(nodes.keys())
            filtered_nodes = {}
            filtered_edges = []
            for key in path_set:
                if key in nodes:
                    filtered_nodes[key] = nodes[key]
            # Also include one hop around the path for context
            for e in edges:
                if e["source"] in path_set or e["target"] in path_set:
                    if e["source"] in nodes:
                        filtered_nodes[e["source"]] = nodes[e["source"]]
                    if e["target"] in nodes:
                        filtered_nodes[e["target"]] = nodes[e["target"]]
                    filtered_edges.append(e)

            nodes = filtered_nodes
            edges = filtered_edges

            # Add Christ node at the end of the path
            christ_node = {
                "id": "__CHRIST__", "book": "", "chapter": 0, "verse": 0,
                "depth": 0, "isChrist": True, "text": "",
                "testament": "", "book_order": 0,
            }
            nodes["__CHRIST__"] = christ_node
            # Connect Christ to the found seed
            if found_seed:
                edges.append({
                    "source": "__CHRIST__", "target": found_seed, "votes": 9999
                })
                if found_seed in nodes:
                    nodes[found_seed]["isSeed"] = True

            _enrich_nodes(conn, nodes)

            return {
                "center": start_key,
                "nodes": list(nodes.values()),
                "edges": edges,
                "seedIds": list(seed_ids & set(nodes.keys())),
                "method": "find-path",
                "pathToChrist": path_to_christ if found_seed else None,
                "christNodeId": "__CHRIST__",
                "foundSeed": found_seed,
            }

        # --- Standard christological BFS (gospel-peaks, messianic, red-letter) ---
        nodes = {}
        edges = []
        edge_set = set()
        queue = []

        # Create synthetic Christ center node
        christ_node = {
            "id": "__CHRIST__", "book": "", "chapter": 0, "verse": 0,
            "depth": 0, "isChrist": True, "text": "",
            "testament": "", "book_order": 0,
        }
        nodes["__CHRIST__"] = christ_node
        seed_ids = []

        # Add seed verses at depth 1 with synthetic edges to Christ
        for s_book, s_chapter, s_verse in seeds:
            key = f"{s_book}.{s_chapter}.{s_verse}"
            # Verify this verse exists
            cursor = conn.execute(
                "SELECT 1 FROM verses WHERE book = ? AND chapter = ? AND verse = ? LIMIT 1",
                (s_book, s_chapter, s_verse)
            )
            if not cursor.fetchone():
                continue
            nodes[key] = {
                "id": key, "book": s_book, "chapter": s_chapter,
                "verse": s_verse, "depth": 1, "isSeed": True,
            }
            seed_ids.append(key)
            edges.append({"source": "__CHRIST__", "target": key, "votes": 9999})
            edge_set.add(("__CHRIST__", key))
            queue.append((s_book, s_chapter, s_verse, 1))

        # BFS outward from seeds
        visited = set(n for n in nodes if n != "__CHRIST__")
        while queue and len(nodes) < limit:
            src_book, src_chapter, src_verse, current_depth = queue.pop(0)
            src_key = f"{src_book}.{src_chapter}.{src_verse}"

            hop_limit = per_verse
            if current_depth >= depth:
                continue

            cursor = conn.execute("""
                SELECT target_book, target_chapter, target_verse, votes
                FROM (
                    SELECT target_book, target_chapter, target_verse, votes
                    FROM cross_references
                    WHERE source_book = ? AND source_chapter = ? AND source_verse = ?
                    UNION ALL
                    SELECT source_book, source_chapter, source_verse, votes
                    FROM cross_references
                    WHERE target_book = ? AND target_chapter = ? AND target_verse = ?
                )
                GROUP BY target_book, target_chapter, target_verse
                ORDER BY MAX(votes) DESC
                LIMIT ?
            """, (src_book, src_chapter, src_verse,
                  src_book, src_chapter, src_verse, hop_limit))

            for row in cursor.fetchall():
                tgt_book, tgt_chapter, tgt_verse, votes = row
                tgt_key = f"{tgt_book}.{tgt_chapter}.{tgt_verse}"

                edge_key = (min(src_key, tgt_key), max(src_key, tgt_key))
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        "source": src_key, "target": tgt_key, "votes": votes
                    })

                if tgt_key not in nodes and len(nodes) < limit:
                    nodes[tgt_key] = {
                        "id": tgt_key, "book": tgt_book,
                        "chapter": tgt_chapter, "verse": tgt_verse,
                        "depth": current_depth + 1,
                    }
                    if current_depth + 1 < depth:
                        queue.append((tgt_book, tgt_chapter, tgt_verse, current_depth + 1))

        _enrich_nodes(conn, nodes)

        return {
            "center": "__CHRIST__",
            "nodes": list(nodes.values()),
            "edges": edges,
            "seedIds": seed_ids,
            "method": method,
            "pathToChrist": None,
        }
    finally:
        conn.close()


@app.get("/api/path-to-christ/{reference}")
async def get_path_to_christ(
    reference: str,
    translation: str = Query(default="BSB", description="Translation for verse text"),
):
    """Find shortest cross-reference path from a verse to a christological seed."""
    conn = get_db_connection()
    try:
        parsed = parse_reference(reference)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")
        book, chapter, verse_start, verse_end, has_verse = parsed
        if not has_verse:
            raise HTTPException(status_code=400, detail="A specific verse is required")

        all_seeds = CHRISTOLOGICAL_SEEDS["gospel-peaks"] + CHRISTOLOGICAL_SEEDS["messianic"]
        seed_ids = set()
        seed_info = {}  # key -> (book, chapter, verse)
        for s in all_seeds:
            key = f"{s[0]}.{s[1]}.{s[2]}"
            seed_ids.add(key)
            seed_info[key] = s

        start_key = f"{book}.{chapter}.{verse_start}"

        # If the start verse IS a seed, return immediately
        if start_key in seed_ids:
            cursor = conn.execute(
                "SELECT text FROM verses WHERE book = ? AND chapter = ? AND verse = ? AND translation_id = ?",
                (book, chapter, verse_start, translation)
            )
            row = cursor.fetchone()
            # Get testament
            bcur = conn.execute("SELECT testament FROM books WHERE name = ?", (book,))
            brow = bcur.fetchone()
            testament = brow[0] if brow else "NT"
            return {
                "found": True,
                "start": start_key,
                "seed": start_key,
                "path": [{
                    "key": start_key,
                    "book": book,
                    "chapter": chapter,
                    "verse": verse_start,
                    "text": row[0] if row else "",
                    "reference": f"{book} {chapter}:{verse_start}",
                    "isSeed": True,
                    "testament": testament,
                }],
                "hops": 0,
            }

        # BFS
        visited = set()
        parent = {}
        verse_lookup = {}  # key -> (book, chapter, verse)
        verse_lookup[start_key] = (book, chapter, verse_start)
        queue = [(book, chapter, verse_start, 0)]
        found_seed = None
        max_search_depth = 6

        while queue and not found_seed:
            src_book, src_chapter, src_verse, current_depth = queue.pop(0)
            src_key = f"{src_book}.{src_chapter}.{src_verse}"
            if src_key in visited:
                continue
            visited.add(src_key)

            if src_key in seed_ids and src_key != start_key:
                found_seed = src_key
                break

            if current_depth >= max_search_depth:
                continue

            cursor = conn.execute("""
                SELECT target_book, target_chapter, target_verse, votes
                FROM (
                    SELECT target_book, target_chapter, target_verse, votes
                    FROM cross_references
                    WHERE source_book = ? AND source_chapter = ? AND source_verse = ?
                    UNION ALL
                    SELECT source_book, source_chapter, source_verse, votes
                    FROM cross_references
                    WHERE target_book = ? AND target_chapter = ? AND target_verse = ?
                )
                GROUP BY target_book, target_chapter, target_verse
                ORDER BY MAX(votes) DESC
                LIMIT ?
            """, (src_book, src_chapter, src_verse,
                  src_book, src_chapter, src_verse, 15))

            for row in cursor.fetchall():
                tgt_book, tgt_chapter, tgt_verse, votes = row
                tgt_key = f"{tgt_book}.{tgt_chapter}.{tgt_verse}"

                if tgt_key not in verse_lookup:
                    verse_lookup[tgt_key] = (tgt_book, tgt_chapter, tgt_verse)

                if tgt_key not in parent and tgt_key != start_key:
                    parent[tgt_key] = src_key

                if tgt_key in seed_ids:
                    found_seed = tgt_key
                    break

                if tgt_key not in visited:
                    queue.append((tgt_book, tgt_chapter, tgt_verse, current_depth + 1))

        if not found_seed:
            return {"found": False, "start": start_key, "seed": None, "path": [], "hops": 0}

        # Reconstruct path
        path_keys = []
        curr = found_seed
        while curr and curr != start_key:
            path_keys.append(curr)
            curr = parent.get(curr)
        path_keys.append(start_key)
        path_keys.reverse()

        # Enrich with full verse text
        # Cache testament lookups
        testament_cache = {}
        path = []
        for key in path_keys:
            v_book, v_chapter, v_verse = verse_lookup[key]
            cursor = conn.execute(
                "SELECT text FROM verses WHERE book = ? AND chapter = ? AND verse = ? AND translation_id = ?",
                (v_book, v_chapter, v_verse, translation)
            )
            row = cursor.fetchone()
            # Testament
            if v_book not in testament_cache:
                bcur = conn.execute("SELECT testament FROM books WHERE name = ?", (v_book,))
                brow = bcur.fetchone()
                testament_cache[v_book] = brow[0] if brow else "NT"
            path.append({
                "key": key,
                "book": v_book,
                "chapter": v_chapter,
                "verse": v_verse,
                "text": row[0] if row else "",
                "reference": f"{v_book} {v_chapter}:{v_verse}",
                "isSeed": key in seed_ids,
                "testament": testament_cache[v_book],
            })

        return {
            "found": True,
            "start": start_key,
            "seed": found_seed,
            "path": path,
            "hops": len(path) - 1,
        }
    finally:
        conn.close()


@app.get("/api/crossref-map/{reference}")
async def get_crossref_map(
    reference: str,
    depth: int = Query(default=1, ge=1, le=7, description="How many hops to follow"),
    per_verse: int = Query(default=5, ge=1, le=50, description="Top N connections per verse"),
    diminish: bool = Query(default=False, description="Reduce connections at each hop depth"),
    limit: int = Query(default=150, ge=10, le=500, description="Max nodes to return"),
    focus_books: str = Query(default=None, description="Comma-separated book names to prioritize in BFS")
):
    """
    Get cross-reference graph data for visualization.
    Uses per-verse top-N selection so every verse gets its best connections
    regardless of absolute vote count.
    """
    conn = get_db_connection()
    try:
        parsed = parse_reference(reference)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")

        book, chapter, verse_start, verse_end, has_verse = parsed

        # Parse focus books and auto-boost depth/limit when focusing
        focus_list = []
        if focus_books:
            focus_list = [b.strip() for b in focus_books.split(",") if b.strip()]
        if focus_list:
            depth = max(depth, 3)
            limit = max(limit, 250)

        # Build graph by BFS traversal of cross-references
        nodes = {}  # key -> node dict
        edges = []  # list of edge dicts
        edge_set = set()  # for O(1) dedup
        visited = set()
        queue = []

        # Seed with the requested verses
        if has_verse:
            for v in range(verse_start, verse_end + 1):
                key = f"{book}.{chapter}.{v}"
                nodes[key] = {"id": key, "book": book, "chapter": chapter, "verse": v, "depth": 0}
                queue.append((book, chapter, v, 0))
        else:
            # For whole chapter, get the top cross-referenced verses
            cursor = conn.execute("""
                SELECT source_verse, COUNT(*) as cnt
                FROM cross_references
                WHERE source_book = ? AND source_chapter = ?
                GROUP BY source_verse ORDER BY cnt DESC LIMIT 5
            """, (book, chapter))
            seed_verses = [row[0] for row in cursor.fetchall()]
            if not seed_verses:
                seed_verses = [1]
            for v in seed_verses:
                key = f"{book}.{chapter}.{v}"
                nodes[key] = {"id": key, "book": book, "chapter": chapter, "verse": v, "depth": 0}
                queue.append((book, chapter, v, 0))

        # BFS to collect graph
        # per_verse controls how many connections each verse contributes (top N by votes).
        # diminish mode: each hop gets fewer connections (tapers outward)
        # normal mode: deeper hops get slightly more connections
        while queue and len(nodes) < limit:
            src_book, src_chapter, src_verse, current_depth = queue.pop(0)
            src_key = f"{src_book}.{src_chapter}.{src_verse}"

            if src_key in visited:
                continue
            visited.add(src_key)

            if diminish:
                # Each hop gets ~60% of the previous hop's connections (min 2)
                hop_limit = max(2, round(per_verse * (0.6 ** current_depth)))
            else:
                hop_limit = per_verse + min(per_verse, current_depth * 2)

            # Get top cross-refs for this verse (bidirectional), ordered by votes
            # When focus_books is set, prioritize those books in the sort order
            if focus_list:
                placeholders = ",".join(["?" for _ in focus_list])
                sql = f"""
                    SELECT target_book, target_chapter, target_verse, votes
                    FROM (
                        SELECT target_book, target_chapter, target_verse, votes
                        FROM cross_references
                        WHERE source_book = ? AND source_chapter = ? AND source_verse = ?
                        UNION ALL
                        SELECT source_book, source_chapter, source_verse, votes
                        FROM cross_references
                        WHERE target_book = ? AND target_chapter = ? AND target_verse = ?
                    )
                    GROUP BY target_book, target_chapter, target_verse
                    ORDER BY CASE WHEN target_book IN ({placeholders})
                             THEN 0 ELSE 1 END, MAX(votes) DESC
                    LIMIT ?
                """
                params = (
                    src_book, src_chapter, src_verse,
                    src_book, src_chapter, src_verse,
                    *focus_list, hop_limit,
                )
                cursor = conn.execute(sql, params)
            else:
                cursor = conn.execute("""
                    SELECT target_book, target_chapter, target_verse, votes
                    FROM (
                        SELECT target_book, target_chapter, target_verse, votes
                        FROM cross_references
                        WHERE source_book = ? AND source_chapter = ? AND source_verse = ?
                        UNION ALL
                        SELECT source_book, source_chapter, source_verse, votes
                        FROM cross_references
                        WHERE target_book = ? AND target_chapter = ? AND target_verse = ?
                    )
                    GROUP BY target_book, target_chapter, target_verse
                    ORDER BY MAX(votes) DESC
                    LIMIT ?
                """, (src_book, src_chapter, src_verse,
                      src_book, src_chapter, src_verse,
                      hop_limit))

            for row in cursor.fetchall():
                tgt_book, tgt_chapter, tgt_verse, votes = row
                tgt_key = f"{tgt_book}.{tgt_chapter}.{tgt_verse}"

                # Add edge (deduplicate with set)
                edge_key = (min(src_key, tgt_key), max(src_key, tgt_key))
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        "source": src_key,
                        "target": tgt_key,
                        "votes": votes
                    })

                # Add node if new
                if tgt_key not in nodes and len(nodes) < limit:
                    nodes[tgt_key] = {
                        "id": tgt_key,
                        "book": tgt_book,
                        "chapter": tgt_chapter,
                        "verse": tgt_verse,
                        "depth": current_depth + 1
                    }

                    # Queue for next depth level
                    if current_depth + 1 < depth:
                        queue.append((tgt_book, tgt_chapter, tgt_verse, current_depth + 1))

        _enrich_nodes(conn, nodes)

        return {
            "center": f"{book}.{chapter}.{verse_start}" if has_verse else f"{book}.{chapter}.1",
            "nodes": list(nodes.values()),
            "edges": edges,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "depth": depth,
                "per_verse": per_verse,
                "focus_books": focus_list or None
            }
        }
    finally:
        conn.close()


@app.get("/map")
async def serve_map():
    """Serve the cross-reference mapper visualization page."""
    return FileResponse(frontend_path / "map.html")


# Route for reading plan URLs (e.g., /plan/chronological-year/45)
# Must be registered before the catch-all book/chapter routes
@app.get("/plan/{plan_id}/{day}")
async def serve_app_with_plan(plan_id: str, day: int):
    """Serve main app for reading plan URLs - JS handles the routing."""
    return FileResponse(frontend_path / "index.html")


# Catch-all route for clean URLs (e.g., /John/3/16)
# Must be registered last to not override other routes
@app.get("/{book}/{chapter}")
@app.get("/{book}/{chapter}/{verse}")
async def serve_app_with_reference(book: str, chapter: int, verse: int = None):
    """Serve main app for clean URLs - JS handles the routing."""
    return FileResponse(frontend_path / "index.html")
