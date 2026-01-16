#!/usr/bin/env python3
"""
Import cross-references from OpenBible.info data.

Source: https://www.openbible.info/labs/cross-references/
License: CC-BY (Creative Commons Attribution)

The data format is tab-separated:
    From Verse    To Verse    Votes
    Gen.1.1       Isa.65.17   51

Usage:
    python scripts/import_cross_refs.py
"""
import sqlite3
import re
from pathlib import Path

DATABASE_PATH = Path(__file__).parent.parent / "data" / "bible.db"
CROSS_REFS_FILE = Path(__file__).parent.parent / "data" / "cross_references.txt"

# Book abbreviation mapping (OpenBible uses different abbreviations)
BOOK_MAP = {
    "Gen": "Genesis", "Exod": "Exodus", "Lev": "Leviticus", "Num": "Numbers",
    "Deut": "Deuteronomy", "Josh": "Joshua", "Judg": "Judges", "Ruth": "Ruth",
    "1Sam": "1 Samuel", "2Sam": "2 Samuel", "1Kgs": "1 Kings", "2Kgs": "2 Kings",
    "1Chr": "1 Chronicles", "2Chr": "2 Chronicles", "Ezra": "Ezra", "Neh": "Nehemiah",
    "Esth": "Esther", "Job": "Job", "Ps": "Psalms", "Prov": "Proverbs",
    "Eccl": "Ecclesiastes", "Song": "Song of Solomon", "Isa": "Isaiah",
    "Jer": "Jeremiah", "Lam": "Lamentations", "Ezek": "Ezekiel", "Dan": "Daniel",
    "Hos": "Hosea", "Joel": "Joel", "Amos": "Amos", "Obad": "Obadiah",
    "Jonah": "Jonah", "Mic": "Micah", "Nah": "Nahum", "Hab": "Habakkuk",
    "Zeph": "Zephaniah", "Hag": "Haggai", "Zech": "Zechariah", "Mal": "Malachi",
    "Matt": "Matthew", "Mark": "Mark", "Luke": "Luke", "John": "John",
    "Acts": "Acts", "Rom": "Romans", "1Cor": "1 Corinthians", "2Cor": "2 Corinthians",
    "Gal": "Galatians", "Eph": "Ephesians", "Phil": "Philippians", "Col": "Colossians",
    "1Thess": "1 Thessalonians", "2Thess": "2 Thessalonians",
    "1Tim": "1 Timothy", "2Tim": "2 Timothy", "Titus": "Titus", "Phlm": "Philemon",
    "Heb": "Hebrews", "Jas": "James", "1Pet": "1 Peter", "2Pet": "2 Peter",
    "1John": "1 John", "2John": "2 John", "3John": "3 John", "Jude": "Jude", "Rev": "Revelation"
}

# Book order for sorting
BOOK_ORDER = {name: i for i, name in enumerate([
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
])}


def parse_reference(ref: str) -> tuple | None:
    """
    Parse a reference like 'Gen.1.1' or 'Ps.148.4-Ps.148.5' into (book, chapter, verse).
    For ranges, returns the start verse.
    """
    # Handle ranges - take the first part
    if '-' in ref:
        ref = ref.split('-')[0]

    # Parse Book.Chapter.Verse
    match = re.match(r'^(\d?\w+)\.(\d+)\.(\d+)$', ref)
    if not match:
        return None

    book_abbr, chapter, verse = match.groups()
    book = BOOK_MAP.get(book_abbr)
    if not book:
        return None

    return (book, int(chapter), int(verse))


def import_cross_refs(min_votes: int = 10):
    """Import cross-references with at least min_votes."""
    print(f"\n{'=' * 60}")
    print(f"Importing Cross-References from OpenBible.info")
    print(f"{'=' * 60}")
    print(f"Minimum votes threshold: {min_votes}")

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Clear existing cross-references
    cursor.execute("DELETE FROM cross_references")
    conn.commit()

    imported = 0
    skipped = 0
    errors = 0

    with open(CROSS_REFS_FILE, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip header and comments
            if not line or line.startswith('#') or line.startswith('From'):
                continue

            parts = line.split('\t')
            if len(parts) < 3:
                errors += 1
                continue

            from_ref, to_ref, votes_str = parts[0], parts[1], parts[2]

            try:
                votes = int(votes_str)
            except ValueError:
                errors += 1
                continue

            # Filter by vote threshold
            if votes < min_votes:
                skipped += 1
                continue

            # Parse references
            source = parse_reference(from_ref)
            target = parse_reference(to_ref)

            if not source or not target:
                errors += 1
                continue

            source_book, source_chapter, source_verse = source
            target_book, target_chapter, target_verse = target

            # Insert cross-reference
            cursor.execute("""
                INSERT INTO cross_references
                (source_book, source_chapter, source_verse,
                 target_book, target_chapter, target_verse,
                 target_book_order, relationship_type, votes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                source_book, source_chapter, source_verse,
                target_book, target_chapter, target_verse,
                BOOK_ORDER.get(target_book, 99),
                'cross-reference',
                votes
            ))
            imported += 1

            # Progress every 50k
            if imported % 50000 == 0:
                print(f"  Imported {imported:,} cross-references...")
                conn.commit()

    conn.commit()
    conn.close()

    print(f"\n{'=' * 60}")
    print(f"Import complete!")
    print(f"  Imported: {imported:,}")
    print(f"  Skipped (low votes): {skipped:,}")
    print(f"  Errors: {errors:,}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    import sys
    min_votes = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    import_cross_refs(min_votes)
