#!/usr/bin/env python3
"""
Import full Bible translations from GitHub sources.

Sources:
- KJV: https://github.com/aruljohn/Bible-kjv (public domain)
- WEB: https://github.com/bibleapi/bibleapi-bibles-json (public domain)

Usage:
    python scripts/import_full_bibles.py
"""
import json
import sqlite3
import urllib.request
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))

DATABASE_PATH = Path(__file__).parent.parent / "data" / "bible.db"

# Book order mapping
BOOK_ORDER = {
    "Genesis": 1, "Exodus": 2, "Leviticus": 3, "Numbers": 4, "Deuteronomy": 5,
    "Joshua": 6, "Judges": 7, "Ruth": 8, "1 Samuel": 9, "2 Samuel": 10,
    "1 Kings": 11, "2 Kings": 12, "1 Chronicles": 13, "2 Chronicles": 14,
    "Ezra": 15, "Nehemiah": 16, "Esther": 17, "Job": 18, "Psalms": 19,
    "Proverbs": 20, "Ecclesiastes": 21, "Song of Solomon": 22, "Isaiah": 23,
    "Jeremiah": 24, "Lamentations": 25, "Ezekiel": 26, "Daniel": 27,
    "Hosea": 28, "Joel": 29, "Amos": 30, "Obadiah": 31, "Jonah": 32,
    "Micah": 33, "Nahum": 34, "Habakkuk": 35, "Zephaniah": 36, "Haggai": 37,
    "Zechariah": 38, "Malachi": 39, "Matthew": 40, "Mark": 41, "Luke": 42,
    "John": 43, "Acts": 44, "Romans": 45, "1 Corinthians": 46, "2 Corinthians": 47,
    "Galatians": 48, "Ephesians": 49, "Philippians": 50, "Colossians": 51,
    "1 Thessalonians": 52, "2 Thessalonians": 53, "1 Timothy": 54, "2 Timothy": 55,
    "Titus": 56, "Philemon": 57, "Hebrews": 58, "James": 59, "1 Peter": 60,
    "2 Peter": 61, "1 John": 62, "2 John": 63, "3 John": 64, "Jude": 65,
    "Revelation": 66
}

# All 66 books
BOOKS = list(BOOK_ORDER.keys())

# URL patterns
KJV_BASE_URL = "https://raw.githubusercontent.com/aruljohn/Bible-kjv/master"
WEB_BIBLE_URL = "https://raw.githubusercontent.com/bibleapi/bibleapi-bibles-json/main/Bibles/en-web.json"


def fetch_json(url: str, timeout: int = 30) -> dict | list | None:
    """Fetch and parse JSON from URL."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'BibleMVP/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"    Error fetching {url}: {e}")
        return None


def fetch_kjv_book(book_name: str) -> dict | None:
    """Fetch a single KJV book."""
    # The repo uses no spaces in filenames: "1Samuel.json", "SongofSolomon.json"
    url_name = book_name.replace(" ", "")
    url = f"{KJV_BASE_URL}/{url_name}.json"
    return fetch_json(url)


def import_kjv(conn: sqlite3.Connection) -> int:
    """Import KJV Bible from aruljohn/Bible-kjv repo."""
    print("\n" + "=" * 50)
    print("Importing KJV (King James Version)")
    print("=" * 50)

    cursor = conn.cursor()
    total_verses = 0

    for book_name in BOOKS:
        print(f"  Fetching {book_name}...", end=" ", flush=True)
        data = fetch_kjv_book(book_name)

        if not data:
            print("FAILED")
            continue

        book_order = BOOK_ORDER[book_name]
        book_verses = 0

        for chapter in data.get("chapters", []):
            chapter_num = int(chapter.get("chapter", 0))

            for verse in chapter.get("verses", []):
                verse_num = int(verse.get("verse", 0))
                text = verse.get("text", "").strip()

                if text:
                    cursor.execute("""
                        INSERT OR REPLACE INTO verses
                        (translation_id, book, book_order, chapter, verse, text)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, ("KJV", book_name, book_order, chapter_num, verse_num, text))
                    book_verses += 1

        conn.commit()
        total_verses += book_verses
        print(f"{book_verses} verses")

    return total_verses


def import_web(conn: sqlite3.Connection) -> int:
    """Import WEB Bible from bibleapi-bibles-json repo."""
    print("\n" + "=" * 50)
    print("Importing WEB (World English Bible)")
    print("=" * 50)

    # First, try the consolidated JSON file
    print("  Fetching complete WEB Bible...", flush=True)
    data = fetch_json(WEB_BIBLE_URL, timeout=60)

    if not data:
        # Fallback: try bible-api.com chapter by chapter
        print("  Primary source failed, using bible-api.com fallback...")
        return import_web_via_api(conn)

    cursor = conn.cursor()
    total_verses = 0

    # Parse the bibleapi format
    # Format: array of books, each with chapters array containing verse arrays
    for book_data in data:
        book_name = book_data.get("book", "")

        # Normalize book name
        book_name = normalize_book_name(book_name)
        book_order = BOOK_ORDER.get(book_name, 0)

        if not book_order:
            print(f"  Skipping unknown book: {book_name}")
            continue

        chapters = book_data.get("chapters", [])
        book_verses = 0

        for chapter_idx, verses in enumerate(chapters):
            chapter_num = chapter_idx + 1

            for verse_idx, text in enumerate(verses):
                verse_num = verse_idx + 1
                text = text.strip() if isinstance(text, str) else ""

                if text:
                    cursor.execute("""
                        INSERT OR REPLACE INTO verses
                        (translation_id, book, book_order, chapter, verse, text)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, ("WEB", book_name, book_order, chapter_num, verse_num, text))
                    book_verses += 1

        conn.commit()
        total_verses += book_verses
        print(f"  {book_name}: {book_verses} verses")

    return total_verses


def import_web_via_api(conn: sqlite3.Connection) -> int:
    """Fallback: Import WEB via bible-api.com chapter by chapter."""
    cursor = conn.cursor()
    total_verses = 0

    # Chapter counts for each book
    chapter_counts = {
        "Genesis": 50, "Exodus": 40, "Leviticus": 27, "Numbers": 36, "Deuteronomy": 34,
        "Joshua": 24, "Judges": 21, "Ruth": 4, "1 Samuel": 31, "2 Samuel": 24,
        "1 Kings": 22, "2 Kings": 25, "1 Chronicles": 29, "2 Chronicles": 36,
        "Ezra": 10, "Nehemiah": 13, "Esther": 10, "Job": 42, "Psalms": 150,
        "Proverbs": 31, "Ecclesiastes": 12, "Song of Solomon": 8, "Isaiah": 66,
        "Jeremiah": 52, "Lamentations": 5, "Ezekiel": 48, "Daniel": 12,
        "Hosea": 14, "Joel": 3, "Amos": 9, "Obadiah": 1, "Jonah": 4,
        "Micah": 7, "Nahum": 3, "Habakkuk": 3, "Zephaniah": 3, "Haggai": 2,
        "Zechariah": 14, "Malachi": 4, "Matthew": 28, "Mark": 16, "Luke": 24,
        "John": 21, "Acts": 28, "Romans": 16, "1 Corinthians": 16, "2 Corinthians": 13,
        "Galatians": 6, "Ephesians": 6, "Philippians": 4, "Colossians": 4,
        "1 Thessalonians": 5, "2 Thessalonians": 3, "1 Timothy": 6, "2 Timothy": 4,
        "Titus": 3, "Philemon": 1, "Hebrews": 13, "James": 5, "1 Peter": 5,
        "2 Peter": 3, "1 John": 5, "2 John": 1, "3 John": 1, "Jude": 1, "Revelation": 22
    }

    for book_name, num_chapters in chapter_counts.items():
        book_order = BOOK_ORDER[book_name]
        book_verses = 0
        print(f"  {book_name} ", end="", flush=True)

        for chapter in range(1, num_chapters + 1):
            ref = f"{book_name} {chapter}".replace(" ", "+")
            url = f"https://bible-api.com/{ref}?translation=web"
            data = fetch_json(url)

            if data and "verses" in data:
                for verse in data["verses"]:
                    verse_num = verse.get("verse", 0)
                    text = verse.get("text", "").strip()

                    if text:
                        cursor.execute("""
                            INSERT OR REPLACE INTO verses
                            (translation_id, book, book_order, chapter, verse, text)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, ("WEB", book_name, book_order, chapter, verse_num, text))
                        book_verses += 1

            print(".", end="", flush=True)

        conn.commit()
        total_verses += book_verses
        print(f" {book_verses} verses")

    return total_verses


def normalize_book_name(name: str) -> str:
    """Normalize book name to match our schema."""
    name_map = {
        "Psalm": "Psalms",
        "Song of Songs": "Song of Solomon",
        "Wisdom of Solomon": None,  # Apocrypha - skip
        "Sirach": None,  # Apocrypha - skip
        "1Corinthians": "1 Corinthians",
        "2Corinthians": "2 Corinthians",
        "1Thessalonians": "1 Thessalonians",
        "2Thessalonians": "2 Thessalonians",
        "1Timothy": "1 Timothy",
        "2Timothy": "2 Timothy",
        "1Peter": "1 Peter",
        "2Peter": "2 Peter",
        "1John": "1 John",
        "2John": "2 John",
        "3John": "3 John",
        "1Samuel": "1 Samuel",
        "2Samuel": "2 Samuel",
        "1Kings": "1 Kings",
        "2Kings": "2 Kings",
        "1Chronicles": "1 Chronicles",
        "2Chronicles": "2 Chronicles",
    }

    # Check exact matches first
    if name in name_map:
        return name_map[name]

    # Check if it's already valid
    if name in BOOK_ORDER:
        return name

    # Try removing spaces and matching
    no_space = name.replace(" ", "")
    for canonical in BOOK_ORDER:
        if canonical.replace(" ", "") == no_space:
            return canonical

    return name


def main():
    print("BibleMVP - Full Bible Import")
    print("=" * 50)

    # Initialize database
    from backend.database import init_db
    init_db()

    conn = sqlite3.connect(DATABASE_PATH)

    try:
        # Import KJV
        kjv_count = import_kjv(conn)
        print(f"\nKJV Total: {kjv_count} verses")

        # Import WEB
        web_count = import_web(conn)
        print(f"\nWEB Total: {web_count} verses")

        print("\n" + "=" * 50)
        print(f"IMPORT COMPLETE")
        print(f"  KJV: {kjv_count} verses")
        print(f"  WEB: {web_count} verses")
        print(f"  Total: {kjv_count + web_count} verses")
        print("=" * 50)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
