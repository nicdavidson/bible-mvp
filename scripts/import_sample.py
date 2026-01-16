#!/usr/bin/env python3
"""
Import sample Bible data for development/testing.
Uses bible-api.com for a few key passages.
"""
import json
import sqlite3
import urllib.request
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

DATABASE_PATH = Path(__file__).parent.parent / "data" / "bible.db"

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

# Sample chapters to import for development
SAMPLE_CHAPTERS = [
    "Genesis 1",
    "Psalms 23",
    "Isaiah 53",
    "Matthew 5",
    "Matthew 6",
    "Matthew 7",
    "John 1",
    "John 3",
    "Romans 3",
    "Romans 8",
    "1 Corinthians 13",
    "Ephesians 2",
    "Philippians 4",
    "Hebrews 11",
    "Revelation 21",
]


def fetch_chapter(reference: str) -> dict:
    """Fetch a chapter from bible-api.com"""
    url = f"https://bible-api.com/{reference.replace(' ', '+')}?translation=web"
    print(f"  Fetching {reference}...")

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"    Error: {e}")
        return None


def import_chapter(conn: sqlite3.Connection, data: dict):
    """Import a chapter's verses into the database."""
    if not data or 'verses' not in data:
        return 0

    cursor = conn.cursor()
    count = 0

    for verse in data['verses']:
        book = verse['book_name']
        chapter = verse['chapter']
        verse_num = verse['verse']
        text = verse['text'].strip()
        book_order = BOOK_ORDER.get(book, 0)

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO verses
                (translation_id, book, book_order, chapter, verse, text)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("WEB", book, book_order, chapter, verse_num, text))
            count += 1
        except sqlite3.Error as e:
            print(f"    DB Error: {e}")

    conn.commit()
    return count


def main():
    print("BibleMVP - Sample Data Import")
    print("=" * 40)

    # Initialize database
    from backend.database import init_db
    init_db()

    conn = sqlite3.connect(DATABASE_PATH)
    total = 0

    print("\nFetching sample chapters from bible-api.com...")

    for ref in SAMPLE_CHAPTERS:
        data = fetch_chapter(ref)
        if data:
            count = import_chapter(conn, data)
            total += count
            print(f"    Imported {count} verses")

    conn.close()

    print(f"\nImport complete! Total verses: {total}")
    print("\nSample data ready. Run the server with:")
    print("  source .venv/bin/activate")
    print("  uvicorn backend.main:app --reload")


if __name__ == "__main__":
    main()
