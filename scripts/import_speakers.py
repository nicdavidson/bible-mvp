#!/usr/bin/env python3
"""
Import speaker/quotation data from Clear-Bible speaker-quotations repository.

Data source: https://github.com/Clear-Bible/speaker-quotations
License: CC-BY 4.0

This creates a verse-level mapping of which verses contain spoken words
from God (OT) or Jesus (NT), for red-letter Bible display.
"""

import sqlite3
import json
from pathlib import Path
from collections import defaultdict

# Paths
DATA_DIR = Path(__file__).parent.parent / "data" / "speaker-quotations"
DB_PATH = Path(__file__).parent.parent / "data" / "bible.db"

# Book name normalization (Clear-Bible uses abbreviated names)
BOOK_ABBREV_TO_NAME = {
    # Old Testament
    'GEN': 'Genesis', 'EXO': 'Exodus', 'LEV': 'Leviticus', 'NUM': 'Numbers', 'DEU': 'Deuteronomy',
    'JOS': 'Joshua', 'JDG': 'Judges', 'RUT': 'Ruth', '1SA': '1 Samuel', '2SA': '2 Samuel',
    '1KI': '1 Kings', '2KI': '2 Kings', '1CH': '1 Chronicles', '2CH': '2 Chronicles',
    'EZR': 'Ezra', 'NEH': 'Nehemiah', 'EST': 'Esther', 'JOB': 'Job', 'PSA': 'Psalms',
    'PRO': 'Proverbs', 'ECC': 'Ecclesiastes', 'SNG': 'Song of Solomon', 'ISA': 'Isaiah',
    'JER': 'Jeremiah', 'LAM': 'Lamentations', 'EZK': 'Ezekiel', 'DAN': 'Daniel',
    'HOS': 'Hosea', 'JOL': 'Joel', 'AMO': 'Amos', 'OBA': 'Obadiah', 'JON': 'Jonah',
    'MIC': 'Micah', 'NAM': 'Nahum', 'HAB': 'Habakkuk', 'ZEP': 'Zephaniah', 'HAG': 'Haggai',
    'ZEC': 'Zechariah', 'MAL': 'Malachi',
    # New Testament
    'MAT': 'Matthew', 'MRK': 'Mark', 'LUK': 'Luke', 'JHN': 'John', 'ACT': 'Acts',
    'ROM': 'Romans', '1CO': '1 Corinthians', '2CO': '2 Corinthians', 'GAL': 'Galatians',
    'EPH': 'Ephesians', 'PHP': 'Philippians', 'COL': 'Colossians', '1TH': '1 Thessalonians',
    '2TH': '2 Thessalonians', '1TI': '1 Timothy', '2TI': '2 Timothy', 'TIT': 'Titus',
    'PHM': 'Philemon', 'HEB': 'Hebrews', 'JAS': 'James', '1PE': '1 Peter', '2PE': '2 Peter',
    '1JN': '1 John', '2JN': '2 John', '3JN': '3 John', 'JUD': 'Jude', 'REV': 'Revelation'
}

# Speakers we care about for red-letter display
# God in OT, Jesus in NT - treating them the same for styling
RED_LETTER_SPEAKERS = {'God', 'Jesus'}


def parse_verse_ref(ref: str) -> tuple:
    """
    Parse verse reference like 'GEN 1:3' to (book, chapter, verse).
    Returns (book_name, chapter, verse) or None if invalid.
    """
    try:
        parts = ref.split()
        if len(parts) != 2:
            return None
        book_abbrev = parts[0]
        chapter_verse = parts[1].split(':')
        if len(chapter_verse) != 2:
            return None

        book_name = BOOK_ABBREV_TO_NAME.get(book_abbrev)
        if not book_name:
            return None

        chapter = int(chapter_verse[0])
        verse = int(chapter_verse[1])
        return (book_name, chapter, verse)
    except (ValueError, IndexError):
        return None


def create_table(conn):
    """Create the speaker_verses table if it doesn't exist."""
    cursor = conn.cursor()

    # Drop existing table to rebuild
    cursor.execute("DROP TABLE IF EXISTS speaker_verses")

    # Create new table - simple verse-level speaker attribution
    cursor.execute("""
        CREATE TABLE speaker_verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            speaker TEXT NOT NULL,
            is_divine BOOLEAN DEFAULT 0,
            UNIQUE(book, chapter, verse, speaker)
        )
    """)

    # Create indexes for fast lookup
    cursor.execute("CREATE INDEX idx_speaker_verses_ref ON speaker_verses(book, chapter, verse)")
    cursor.execute("CREATE INDEX idx_speaker_verses_divine ON speaker_verses(is_divine)")

    conn.commit()
    print("Created speaker_verses table")


def import_speakers(conn):
    """Import speaker data from the Clear-Bible JSON file."""
    json_path = DATA_DIR / "SpeakerProjections-clear.json"

    if not json_path.exists():
        print(f"Error: {json_path} not found")
        print("Download from: https://github.com/Clear-Bible/speaker-quotations/blob/main/json/SpeakerProjections-clear.json")
        return 0

    print(f"Loading {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cursor = conn.cursor()

    # Track unique verse-speaker combinations
    verse_speakers = set()

    for key, entry in data.items():
        speaker_instance = entry.get('SpeakerInstance', {})
        character_id = speaker_instance.get('DefaultCharacterId', '')

        # Only include God and Jesus for red-letter
        if character_id not in RED_LETTER_SPEAKERS:
            continue

        # Get all verses in this quotation
        verses = speaker_instance.get('Verses', [])

        for verse_ref in verses:
            parsed = parse_verse_ref(verse_ref)
            if not parsed:
                continue

            book, chapter, verse = parsed
            verse_speakers.add((book, chapter, verse, character_id))

    # Insert unique verse-speaker combinations
    inserted = 0
    for book, chapter, verse, speaker in verse_speakers:
        is_divine = speaker in RED_LETTER_SPEAKERS
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO speaker_verses (book, chapter, verse, speaker, is_divine)
                VALUES (?, ?, ?, ?, ?)
            """, (book, chapter, verse, speaker, is_divine))
            if cursor.rowcount > 0:
                inserted += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    return inserted


def print_stats(conn):
    """Print statistics about the imported data."""
    cursor = conn.cursor()

    # Total verses with speakers
    cursor.execute("SELECT COUNT(DISTINCT book || chapter || verse) FROM speaker_verses")
    total_verses = cursor.fetchone()[0]

    # By speaker
    cursor.execute("""
        SELECT speaker, COUNT(DISTINCT book || chapter || verse)
        FROM speaker_verses
        GROUP BY speaker
        ORDER BY COUNT(*) DESC
    """)
    by_speaker = cursor.fetchall()

    # OT vs NT
    ot_books = {'Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy',
                'Joshua', 'Judges', 'Ruth', '1 Samuel', '2 Samuel',
                '1 Kings', '2 Kings', '1 Chronicles', '2 Chronicles',
                'Ezra', 'Nehemiah', 'Esther', 'Job', 'Psalms', 'Proverbs',
                'Ecclesiastes', 'Song of Solomon', 'Isaiah', 'Jeremiah',
                'Lamentations', 'Ezekiel', 'Daniel', 'Hosea', 'Joel', 'Amos',
                'Obadiah', 'Jonah', 'Micah', 'Nahum', 'Habakkuk', 'Zephaniah',
                'Haggai', 'Zechariah', 'Malachi'}

    cursor.execute("SELECT book, COUNT(*) FROM speaker_verses WHERE speaker = 'God' GROUP BY book")
    god_by_book = {row[0]: row[1] for row in cursor.fetchall()}
    ot_god = sum(v for k, v in god_by_book.items() if k in ot_books)

    cursor.execute("SELECT book, COUNT(*) FROM speaker_verses WHERE speaker = 'Jesus' GROUP BY book")
    jesus_by_book = {row[0]: row[1] for row in cursor.fetchall()}
    nt_jesus = sum(v for k, v in jesus_by_book.items() if k not in ot_books)

    print(f"\n=== Speaker Import Statistics ===")
    print(f"Total verses with divine speech: {total_verses}")
    print(f"\nBy speaker:")
    for speaker, count in by_speaker:
        print(f"  {speaker}: {count} verses")
    print(f"\nOT 'God' verses: {ot_god}")
    print(f"NT 'Jesus' verses: {nt_jesus}")


def main():
    print("=== Importing Speaker/Quotation Data ===\n")

    conn = sqlite3.connect(DB_PATH)

    # Create table
    create_table(conn)

    # Import data
    inserted = import_speakers(conn)
    print(f"\nInserted {inserted} verse-speaker records")

    # Print stats
    print_stats(conn)

    conn.close()
    print("\nDone!")


if __name__ == '__main__':
    main()
