"""Shared reference parsing, cross-reference and speaker helpers + rate limiter."""
import re
import sqlite3
from typing import Optional

from fastapi import Request
from slowapi import Limiter

# Canonical book names in order
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
CANONICAL_BOOKS = OT_BOOKS + NT_BOOKS

def _get_client_ip(request: Request) -> str:
    """Extract real client IP from X-Forwarded-For (set by Fly.io proxy)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Last entry is appended by Fly's proxy; leftmost entries are client-controlled
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


# Rate limiter, keyed by real client IP behind reverse proxy
limiter = Limiter(key_func=_get_client_ip)

def parse_reference(reference: str) -> Optional[tuple]:
    """
    Parse a Bible reference into (book, chapter, verse_start, verse_end, has_verse).
    Returns None if invalid.
    has_verse indicates whether a specific verse was requested (for highlighting).
    """
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
    canonical_map = {b.lower(): b for b in CANONICAL_BOOKS}
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


