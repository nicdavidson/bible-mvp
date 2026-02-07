#!/usr/bin/env python3
"""
Import Nave's Topical Bible data into SQLite.

Data source: BradyStephenson/bible-data (GitHub) - NavesTopicalDictionary.csv
Original compiler: Orville James Nave (1896, public domain)

Usage:
    python scripts/import_naves.py
"""

import csv
import json
import os
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("DATABASE_PATH", Path(__file__).parent.parent / "data" / "bible.db"))
CSV_PATH = Path(__file__).parent.parent / "data" / "naves" / "NavesTopicalDictionary.csv"

# Map Nave's abbreviations to our book names
NAVES_BOOK_MAP = {
    'GEN': 'Genesis', 'EXO': 'Exodus', 'LEV': 'Leviticus', 'NUM': 'Numbers',
    'DEU': 'Deuteronomy', 'JOS': 'Joshua', 'JDG': 'Judges', 'RUT': 'Ruth',
    '1SA': '1 Samuel', '2SA': '2 Samuel', '1KI': '1 Kings', '2KI': '2 Kings',
    '1CH': '1 Chronicles', '2CH': '2 Chronicles', 'EZR': 'Ezra', 'NEH': 'Nehemiah',
    'EST': 'Esther', 'JOB': 'Job', 'PSA': 'Psalms', 'PRO': 'Proverbs',
    'ECC': 'Ecclesiastes', 'SOS': 'Song of Solomon', 'SON': 'Song of Solomon',
    'ISA': 'Isaiah', 'JER': 'Jeremiah', 'LAM': 'Lamentations', 'EZK': 'Ezekiel',
    'DAN': 'Daniel', 'HOS': 'Hosea', 'JOL': 'Joel', 'AMO': 'Amos',
    'OBA': 'Obadiah', 'JON': 'Jonah', 'MIC': 'Micah', 'NAM': 'Nahum',
    'NAH': 'Nahum', 'HAB': 'Habakkuk', 'ZEP': 'Zephaniah', 'HAG': 'Haggai',
    'ZEC': 'Zechariah', 'MAL': 'Malachi',
    'MAT': 'Matthew', 'MRK': 'Mark', 'LUK': 'Luke', 'JHN': 'John',
    'ACT': 'Acts', 'ROM': 'Romans', '1CO': '1 Corinthians', '2CO': '2 Corinthians',
    'GAL': 'Galatians', 'EPH': 'Ephesians', 'PHP': 'Philippians', 'COL': 'Colossians',
    '1TH': '1 Thessalonians', '2TH': '2 Thessalonians', '1TI': '1 Timothy',
    '2TI': '2 Timothy', 'TIT': 'Titus', 'PHM': 'Philemon', 'HEB': 'Hebrews',
    'JAS': 'James', '1PE': '1 Peter', '2PE': '2 Peter', '1JN': '1 John',
    '2JN': '2 John', '3JN': '3 John', 'JDE': 'Jude', 'JUD': 'Jude', 'REV': 'Revelation',
    # Edge cases
    '1JHN': '1 John',
}


def create_tables(conn):
    """Create topics tables."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS naves_topics (
            id INTEGER PRIMARY KEY,
            topic TEXT NOT NULL,
            section TEXT NOT NULL,
            entry_text TEXT NOT NULL,
            refs_json TEXT
        );

        CREATE TABLE IF NOT EXISTS naves_topic_refs (
            id INTEGER PRIMARY KEY,
            topic_id INTEGER NOT NULL,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse_start INTEGER NOT NULL,
            verse_end INTEGER,
            FOREIGN KEY (topic_id) REFERENCES naves_topics(id)
        );

        CREATE INDEX IF NOT EXISTS idx_naves_topic ON naves_topics(topic);
        CREATE INDEX IF NOT EXISTS idx_naves_section ON naves_topics(section);
        CREATE INDEX IF NOT EXISTS idx_naves_refs_book ON naves_topic_refs(book, chapter, verse_start);
        CREATE INDEX IF NOT EXISTS idx_naves_refs_topic ON naves_topic_refs(topic_id);

        CREATE VIRTUAL TABLE IF NOT EXISTS naves_topics_fts USING fts5(
            topic, entry_text, content=naves_topics, content_rowid=id
        );
    """)
    conn.commit()


def parse_references(text):
    """Extract Bible references from entry text.

    Handles patterns like:
    - GEN 1:1
    - GEN 1:1,2,3
    - GEN 1:1-5
    - GEN 1:1; 2:3
    - GEN 1:1-5,7,9-11
    - GEN 1 (whole chapter)
    """
    refs = []
    # Find all book abbreviation + reference patterns
    # Pattern: BOOK CHAPTER:VERSE[-VERSE][,VERSE[-VERSE]]* or BOOK CHAPTER
    pattern = re.compile(
        r'([A-Z1-3][A-Z]{1,4})\s+'
        r'(\d+)'
        r'(?::(\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*))?'
    )

    for match in pattern.finditer(text):
        book_abbr = match.group(1)
        chapter = int(match.group(2))
        verse_part = match.group(3)

        book = NAVES_BOOK_MAP.get(book_abbr)
        if not book:
            continue

        if not verse_part:
            # Whole chapter reference
            refs.append({
                'book': book, 'chapter': chapter,
                'verse_start': 1, 'verse_end': None
            })
        else:
            # Parse comma-separated verse ranges
            for segment in verse_part.split(','):
                segment = segment.strip()
                if '-' in segment:
                    parts = segment.split('-')
                    try:
                        vs = int(parts[0])
                        ve = int(parts[1])
                        refs.append({
                            'book': book, 'chapter': chapter,
                            'verse_start': vs, 'verse_end': ve
                        })
                    except ValueError:
                        continue
                else:
                    try:
                        v = int(segment)
                        refs.append({
                            'book': book, 'chapter': chapter,
                            'verse_start': v, 'verse_end': v
                        })
                    except ValueError:
                        continue

    return refs


def parse_cross_refs(text):
    """Extract cross-references to other Nave's topics (e.g., 'See PRIEST, HIGH')."""
    cross_refs = []
    for match in re.finditer(r'See\s+(?:sub-topic\s+)?(?:\w+\s+)?(?:under\s+)?(?:\[\d+\])?([A-Z][A-Z, \'-]+)', text):
        topic = match.group(1).strip().rstrip(',')
        if len(topic) > 2:
            cross_refs.append(topic)
    return cross_refs


def import_naves(conn):
    """Import Nave's Topical Dictionary CSV into SQLite."""
    print(f"Importing from {CSV_PATH}...")

    topics = []
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header

        for row in reader:
            if len(row) < 3:
                continue
            section, subject, entry = row[0], row[1], row[2]
            topics.append((section, subject, entry))

    print(f"  Parsed {len(topics)} topics")

    # Insert topics
    topic_count = 0
    ref_count = 0

    for section, subject, entry_text in topics:
        refs = parse_references(entry_text)
        refs_json = json.dumps(refs) if refs else None

        cursor = conn.execute(
            "INSERT INTO naves_topics (topic, section, entry_text, refs_json) VALUES (?, ?, ?, ?)",
            (subject, section, entry_text, refs_json)
        )
        topic_id = cursor.lastrowid
        topic_count += 1

        # Insert individual references for lookup
        for ref in refs:
            conn.execute(
                "INSERT INTO naves_topic_refs (topic_id, book, chapter, verse_start, verse_end) "
                "VALUES (?, ?, ?, ?, ?)",
                (topic_id, ref['book'], ref['chapter'], ref['verse_start'], ref['verse_end'])
            )
            ref_count += 1

    conn.commit()

    # Populate FTS index
    conn.execute("""
        INSERT INTO naves_topics_fts(rowid, topic, entry_text)
        SELECT id, topic, entry_text FROM naves_topics
    """)
    conn.commit()

    print(f"  Imported {topic_count} topics with {ref_count} verse references")
    return topic_count, ref_count


def main():
    print("Nave's Topical Bible Import")
    print("=" * 50)
    print(f"Credit: Orville James Nave (1896, public domain)")
    print()

    if not CSV_PATH.exists():
        print(f"ERROR: {CSV_PATH} not found!")
        print("Download from: https://github.com/BradyStephenson/bible-data")
        return

    conn = sqlite3.connect(DB_PATH)

    # Drop existing data for clean re-import
    conn.executescript("""
        DROP TABLE IF EXISTS naves_topic_refs;
        DROP TABLE IF EXISTS naves_topics_fts;
        DROP TABLE IF EXISTS naves_topics;
    """)

    create_tables(conn)
    topic_count, ref_count = import_naves(conn)

    # Show sample
    print("\nSample topics:")
    cursor = conn.execute(
        "SELECT topic, section FROM naves_topics ORDER BY topic LIMIT 10"
    )
    for row in cursor:
        print(f"  [{row[1]}] {row[0]}")

    # Show a topic with references
    print("\nSample topic with refs (FAITH):")
    cursor = conn.execute(
        "SELECT id, topic, entry_text FROM naves_topics WHERE topic = 'FAITH'"
    )
    row = cursor.fetchone()
    if row:
        text = row[2][:200] + "..." if len(row[2]) > 200 else row[2]
        print(f"  {text}")
        ref_cursor = conn.execute(
            "SELECT book, chapter, verse_start, verse_end FROM naves_topic_refs "
            "WHERE topic_id = ? LIMIT 5", (row[0],)
        )
        for ref in ref_cursor:
            ve = f"-{ref[3]}" if ref[3] and ref[3] != ref[2] else ""
            print(f"    {ref[0]} {ref[1]}:{ref[2]}{ve}")

    # Show topics for a verse
    print("\nTopics referencing John 3:16:")
    cursor = conn.execute("""
        SELECT DISTINCT t.topic FROM naves_topics t
        JOIN naves_topic_refs r ON t.id = r.topic_id
        WHERE r.book = 'John' AND r.chapter = 3
          AND r.verse_start <= 16 AND (r.verse_end >= 16 OR r.verse_end IS NULL)
        LIMIT 10
    """)
    for row in cursor:
        print(f"  {row[0]}")

    # FTS search test
    print("\nFTS search for 'salvation':")
    cursor = conn.execute("""
        SELECT topic FROM naves_topics_fts WHERE naves_topics_fts MATCH 'salvation'
        LIMIT 5
    """)
    for row in cursor:
        print(f"  {row[0]}")

    print(f"\nTotal: {topic_count} topics, {ref_count} references")
    conn.close()


if __name__ == '__main__':
    main()
