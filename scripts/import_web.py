#!/usr/bin/env python3
"""
Import World English Bible (WEB) text from open-bibles repository.
Source: https://github.com/seven1m/open-bibles

Usage:
    python scripts/import_web.py

The script will download the WEB Bible JSON and import it into the SQLite database.
"""
import json
import sqlite3
import urllib.request
from pathlib import Path

# Configuration
DATABASE_PATH = Path(__file__).parent.parent / "data" / "bible.db"
WEB_URL = "https://raw.githubusercontent.com/seven1m/open-bibles/master/json/WEB.json"

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


def download_bible():
    """Download the WEB Bible JSON file."""
    print(f"Downloading WEB Bible from {WEB_URL}...")

    try:
        with urllib.request.urlopen(WEB_URL) as response:
            data = response.read().decode('utf-8')
            return json.loads(data)
    except Exception as e:
        print(f"Error downloading: {e}")
        print("Trying alternative format...")

        # Try the individual books format
        alt_url = "https://raw.githubusercontent.com/seven1m/open-bibles/master/json/eng-web_usfm.json"
        with urllib.request.urlopen(alt_url) as response:
            data = response.read().decode('utf-8')
            return json.loads(data)


def normalize_book_name(name):
    """Normalize book name to match our schema."""
    # Handle common variations
    name_map = {
        "Psalm": "Psalms",
        "Psalms": "Psalms",
        "Song of Songs": "Song of Solomon",
        "1Samuel": "1 Samuel",
        "2Samuel": "2 Samuel",
        "1Kings": "1 Kings",
        "2Kings": "2 Kings",
        "1Chronicles": "1 Chronicles",
        "2Chronicles": "2 Chronicles",
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
    }
    return name_map.get(name, name)


def import_verses(conn, bible_data):
    """Import verses into the database."""
    cursor = conn.cursor()

    # Handle different JSON formats
    if isinstance(bible_data, dict) and "books" in bible_data:
        books = bible_data["books"]
    elif isinstance(bible_data, list):
        books = bible_data
    else:
        # Try parsing as flat verse list
        books = restructure_verses(bible_data)

    verse_count = 0

    for book in books:
        book_name = normalize_book_name(book.get("name", book.get("book", "")))
        book_order = BOOK_ORDER.get(book_name, 0)

        if not book_order:
            print(f"  Warning: Unknown book '{book_name}', skipping...")
            continue

        chapters = book.get("chapters", [])

        for chapter in chapters:
            chapter_num = chapter.get("number", chapter.get("chapter", 0))
            verses = chapter.get("verses", [])

            for verse in verses:
                verse_num = verse.get("number", verse.get("verse", 0))
                text = verse.get("text", "")

                if not text:
                    continue

                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO verses
                        (translation_id, book, book_order, chapter, verse, text)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, ("WEB", book_name, book_order, chapter_num, verse_num, text))
                    verse_count += 1
                except sqlite3.IntegrityError as e:
                    print(f"  Skipping duplicate: {book_name} {chapter_num}:{verse_num}")

        print(f"  Imported {book_name}")

    conn.commit()
    return verse_count


def restructure_verses(data):
    """Restructure flat verse data into books/chapters format."""
    books = {}

    for verse in data:
        book = verse.get("book", "")
        chapter = verse.get("chapter", 0)
        verse_num = verse.get("verse", 0)
        text = verse.get("text", "")

        if book not in books:
            books[book] = {"name": book, "chapters": {}}

        if chapter not in books[book]["chapters"]:
            books[book]["chapters"][chapter] = {"number": chapter, "verses": []}

        books[book]["chapters"][chapter]["verses"].append({
            "number": verse_num,
            "text": text
        })

    # Convert to list format
    result = []
    for book_name, book_data in books.items():
        result.append({
            "name": book_name,
            "chapters": list(book_data["chapters"].values())
        })

    return result


def main():
    """Main entry point."""
    print("BibleMVP - WEB Bible Import")
    print("=" * 40)

    # Ensure data directory exists
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Download Bible data
    bible_data = download_bible()
    print(f"Downloaded Bible data")

    # Connect to database
    conn = sqlite3.connect(DATABASE_PATH)

    # Initialize schema if needed
    from backend.database import init_db
    init_db()

    # Import verses
    print("\nImporting verses...")
    verse_count = import_verses(conn, bible_data)

    print(f"\nImport complete!")
    print(f"Total verses imported: {verse_count}")

    conn.close()


if __name__ == "__main__":
    main()
