#!/usr/bin/env python3
"""
Import commentaries from the HelloAO Bible API.

Source: https://bible.helloao.org/api
Available commentaries (all public domain or CC):
- matthew-henry: Matthew Henry Bible Commentary
- john-gill: John Gill Bible Commentary
- adam-clarke: Adam Clarke Bible Commentary
- jamieson-fausset-brown: Jamieson-Fausset-Brown Bible Commentary
- keil-delitzsch: Keil and Delitzsch Old Testament Commentary
- tyndale: Tyndale Open Study Notes

Usage:
    python scripts/import_commentary.py [commentary_id]

Example:
    python scripts/import_commentary.py matthew-henry
"""
import json
import sqlite3
import urllib.request
import sys
import time
from pathlib import Path

DATABASE_PATH = Path(__file__).parent.parent / "data" / "bible.db"
API_BASE = "https://bible.helloao.org/api/c"

# Book ID to name mapping (HelloAO uses 3-letter codes)
BOOK_ID_MAP = {
    "GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus", "NUM": "Numbers",
    "DEU": "Deuteronomy", "JOS": "Joshua", "JDG": "Judges", "RUT": "Ruth",
    "1SA": "1 Samuel", "2SA": "2 Samuel", "1KI": "1 Kings", "2KI": "2 Kings",
    "1CH": "1 Chronicles", "2CH": "2 Chronicles", "EZR": "Ezra", "NEH": "Nehemiah",
    "EST": "Esther", "JOB": "Job", "PSA": "Psalms", "PRO": "Proverbs",
    "ECC": "Ecclesiastes", "SNG": "Song of Solomon", "ISA": "Isaiah",
    "JER": "Jeremiah", "LAM": "Lamentations", "EZK": "Ezekiel", "DAN": "Daniel",
    "HOS": "Hosea", "JOL": "Joel", "AMO": "Amos", "OBA": "Obadiah",
    "JON": "Jonah", "MIC": "Micah", "NAM": "Nahum", "HAB": "Habakkuk",
    "ZEP": "Zephaniah", "HAG": "Haggai", "ZEC": "Zechariah", "MAL": "Malachi",
    "MAT": "Matthew", "MRK": "Mark", "LUK": "Luke", "JHN": "John",
    "ACT": "Acts", "ROM": "Romans", "1CO": "1 Corinthians", "2CO": "2 Corinthians",
    "GAL": "Galatians", "EPH": "Ephesians", "PHP": "Philippians", "COL": "Colossians",
    "1TH": "1 Thessalonians", "2TH": "2 Thessalonians", "1TI": "1 Timothy",
    "2TI": "2 Timothy", "TIT": "Titus", "PHM": "Philemon", "HEB": "Hebrews",
    "JAS": "James", "1PE": "1 Peter", "2PE": "2 Peter", "1JN": "1 John",
    "2JN": "2 John", "3JN": "3 John", "JUD": "Jude", "REV": "Revelation"
}


def fetch_json(url: str, timeout: int = 30) -> dict | None:
    """Fetch and parse JSON from URL."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'BibleMVP/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"    Error fetching {url}: {e}")
        return None


def get_source_name(commentary_id: str) -> str:
    """Get human-readable source name from commentary ID."""
    names = {
        "matthew-henry": "Matthew Henry",
        "john-gill": "John Gill",
        "adam-clarke": "Adam Clarke",
        "jamieson-fausset-brown": "Jamieson-Fausset-Brown",
        "keil-delitzsch": "Keil & Delitzsch",
        "tyndale": "Tyndale Study Notes"
    }
    return names.get(commentary_id, commentary_id)


def import_commentary(commentary_id: str, limit_books: int | None = None):
    """Import a commentary from HelloAO API."""
    print(f"\n{'=' * 60}")
    print(f"Importing {get_source_name(commentary_id)} Commentary")
    print(f"{'=' * 60}")

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get list of books
    books_url = f"{API_BASE}/{commentary_id}/books.json"
    print(f"\nFetching book list from {books_url}")
    books_data = fetch_json(books_url)

    if not books_data:
        print("ERROR: Failed to fetch books list")
        return

    books = books_data.get("books", [])
    print(f"Found {len(books)} books with commentary")

    if limit_books:
        books = books[:limit_books]
        print(f"(Limiting to first {limit_books} books)")

    source_name = get_source_name(commentary_id)
    total_entries = 0

    for book_info in books:
        book_id = book_info["id"]
        book_name = BOOK_ID_MAP.get(book_id, book_info.get("commonName", book_id))
        num_chapters = book_info.get("numberOfChapters", 0)

        print(f"\n  {book_name} ({num_chapters} chapters)...")
        book_entries = 0

        # Fetch each chapter
        for chapter_num in range(1, num_chapters + 1):
            chapter_url = f"{API_BASE}/{commentary_id}/{book_id}/{chapter_num}.json"
            chapter_data = fetch_json(chapter_url)

            if not chapter_data:
                continue

            chapter_info = chapter_data.get("chapter", {})
            content_items = chapter_info.get("content", [])

            for item in content_items:
                if item.get("type") == "verse":
                    verse_num = item.get("number")
                    content_parts = item.get("content", [])

                    if content_parts and verse_num:
                        # Join all content parts
                        content_text = "\n\n".join(content_parts)

                        # Parse verse range if present (e.g., "1-5" or just "1")
                        if isinstance(verse_num, str) and "-" in verse_num:
                            parts = verse_num.split("-")
                            ref_start = int(parts[0])
                            ref_end = int(parts[1])
                        else:
                            ref_start = int(verse_num)
                            ref_end = ref_start

                        # Insert into database
                        cursor.execute("""
                            INSERT INTO commentary_entries
                            (source, book, chapter, reference_start, reference_end, content, searchable_text)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            source_name,
                            book_name,
                            chapter_num,
                            ref_start,
                            ref_end,
                            content_text,
                            content_text.lower()
                        ))
                        book_entries += 1

            # Small delay to be nice to the API
            time.sleep(0.1)

        print(f"    Added {book_entries} entries")
        total_entries += book_entries
        conn.commit()

    conn.close()

    print(f"\n{'=' * 60}")
    print(f"Import complete!")
    print(f"Total entries added: {total_entries}")
    print(f"{'=' * 60}")


def list_commentaries():
    """List available commentaries from the API."""
    url = "https://bible.helloao.org/api/available_commentaries.json"
    data = fetch_json(url)

    if not data:
        print("Failed to fetch commentaries list")
        return

    print("\nAvailable Commentaries:")
    print("-" * 50)
    for c in data.get("commentaries", []):
        print(f"  {c['id']:25} - {c['name']}")
        print(f"                            ({c['numberOfBooks']} books, {c['totalNumberOfVerses']} verses)")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_commentary.py <commentary_id> [limit_books]")
        list_commentaries()
        sys.exit(1)

    commentary_id = sys.argv[1]
    limit_books = int(sys.argv[2]) if len(sys.argv) > 2 else None

    if commentary_id == "--list":
        list_commentaries()
    else:
        import_commentary(commentary_id, limit_books)
