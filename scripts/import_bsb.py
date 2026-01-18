#!/usr/bin/env python3
"""
Import Berean Standard Bible (BSB) text and word alignments from Clear-Bible data.

Data source: https://github.com/Clear-Bible/Alignments
License: CC-BY 4.0
"""

import sqlite3
import json
import csv
from pathlib import Path
from collections import defaultdict

# Paths
DATA_DIR = Path(__file__).parent.parent / "data" / "clear-bible"
DB_PATH = Path(__file__).parent.parent / "data" / "bible.db"

# Book ID to name mapping (Clear-Bible uses 2-digit book codes)
BOOK_ID_TO_NAME = {
    # Old Testament
    '01': 'Genesis', '02': 'Exodus', '03': 'Leviticus', '04': 'Numbers', '05': 'Deuteronomy',
    '06': 'Joshua', '07': 'Judges', '08': 'Ruth', '09': '1 Samuel', '10': '2 Samuel',
    '11': '1 Kings', '12': '2 Kings', '13': '1 Chronicles', '14': '2 Chronicles',
    '15': 'Ezra', '16': 'Nehemiah', '17': 'Esther', '18': 'Job', '19': 'Psalms',
    '20': 'Proverbs', '21': 'Ecclesiastes', '22': 'Song of Solomon', '23': 'Isaiah',
    '24': 'Jeremiah', '25': 'Lamentations', '26': 'Ezekiel', '27': 'Daniel',
    '28': 'Hosea', '29': 'Joel', '30': 'Amos', '31': 'Obadiah', '32': 'Jonah',
    '33': 'Micah', '34': 'Nahum', '35': 'Habakkuk', '36': 'Zephaniah', '37': 'Haggai',
    '38': 'Zechariah', '39': 'Malachi',
    # New Testament
    '40': 'Matthew', '41': 'Mark', '42': 'Luke', '43': 'John', '44': 'Acts',
    '45': 'Romans', '46': '1 Corinthians', '47': '2 Corinthians', '48': 'Galatians',
    '49': 'Ephesians', '50': 'Philippians', '51': 'Colossians', '52': '1 Thessalonians',
    '53': '2 Thessalonians', '54': '1 Timothy', '55': '2 Timothy', '56': 'Titus',
    '57': 'Philemon', '58': 'Hebrews', '59': 'James', '60': '1 Peter', '61': '2 Peter',
    '62': '1 John', '63': '2 John', '64': '3 John', '65': 'Jude', '66': 'Revelation'
}


def parse_word_id(word_id: str) -> tuple:
    """
    Parse Clear-Bible word ID to (book, chapter, verse, word_pos).

    Format: BBCCCVVVWWW where:
    - BB: book (01-66)
    - CCC: chapter (001-150)
    - VVV: verse (001-176)
    - WWW: word position (001-999)

    Prefixes:
    - 'o' for OT Hebrew source IDs
    - 'n' for NT Greek source IDs
    - No prefix for target (English) IDs

    Example: 01001001001 -> Genesis 1:1 word 1
    Example: n40001001001 -> Matthew 1:1 word 1
    """
    # Remove 'o' or 'n' prefix if present (source text IDs)
    if word_id.startswith('o') or word_id.startswith('n'):
        word_id = word_id[1:]

    book_id = word_id[0:2]
    chapter = int(word_id[2:5])
    verse = int(word_id[5:8])
    word_pos = int(word_id[8:11])

    book_name = BOOK_ID_TO_NAME.get(book_id)
    return book_name, chapter, verse, word_pos


def load_source_data():
    """Load Hebrew (WLCM) and Greek (SBLGNT) source data with Strong's numbers."""
    source_data = {}

    # Load Hebrew (OT)
    wlcm_path = DATA_DIR / "WLCM.tsv"
    if wlcm_path.exists():
        print(f"Loading Hebrew source data from {wlcm_path}...")
        with open(wlcm_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                word_id = row['id']
                source_data[word_id] = {
                    'text': row.get('text', ''),
                    'strongs': row.get('strongs', ''),
                    'gloss': row.get('gloss', ''),
                    'pos': row.get('pos', ''),
                    'morph': row.get('morph', ''),
                    'language': 'hebrew'
                }
        print(f"  Loaded {len(source_data)} Hebrew words")

    # Load Greek (NT)
    sblgnt_path = DATA_DIR / "SBLGNT.tsv"
    if sblgnt_path.exists():
        print(f"Loading Greek source data from {sblgnt_path}...")
        greek_count = 0
        with open(sblgnt_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                word_id = row['id']
                source_data[word_id] = {
                    'text': row.get('text', ''),
                    'strongs': row.get('strongs', ''),
                    'gloss': row.get('gloss', ''),
                    'pos': row.get('pos', ''),
                    'morph': row.get('morph', ''),
                    'language': 'greek'
                }
                greek_count += 1
        print(f"  Loaded {greek_count} Greek words")

    return source_data


def load_bsb_text():
    """Load BSB text from TSV files."""
    verses = defaultdict(list)  # (book, chapter, verse) -> [(word_pos, word, skip_space, exclude, is_punct)]

    for filename in ['ot_BSB.tsv', 'nt_BSB.tsv']:
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"Warning: {filepath} not found")
            continue

        print(f"Loading BSB text from {filepath}...")
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                word_id = row['id']
                text = row.get('text', '')
                skip_space = row.get('skip_space_after', '') == 'y'
                exclude = row.get('exclude', '') == 'y'

                # Check if this is punctuation (exclude=y means it's punctuation that shouldn't be aligned)
                is_punct = exclude

                if not text:
                    continue

                book, chapter, verse, word_pos = parse_word_id(word_id)
                if book:
                    verses[(book, chapter, verse)].append({
                        'word_id': word_id,
                        'position': word_pos,
                        'text': text,
                        'skip_space': skip_space,
                        'is_punct': is_punct
                    })

    return verses


def load_alignments():
    """Load alignment data linking source (Hebrew/Greek) to target (BSB) words."""
    alignments = {}  # target_word_id -> [source_word_ids]

    for filename in ['WLCM-BSB-manual.json', 'SBLGNT-BSB-manual.json']:
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"Warning: {filepath} not found")
            continue

        print(f"Loading alignments from {filepath}...")
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        count = 0
        for record in data.get('records', []):
            source_ids = record.get('source', [])
            target_ids = record.get('target', [])

            # Map each target word to its source words
            for target_id in target_ids:
                if target_id not in alignments:
                    alignments[target_id] = []
                alignments[target_id].extend(source_ids)
                count += 1

        print(f"  Loaded {count} alignment records")

    return alignments


def build_verse_text(words):
    """Build verse text from word list."""
    parts = []
    for word in sorted(words, key=lambda w: w['position']):
        parts.append(word['text'])
        if not word['skip_space']:
            parts.append(' ')
    return ''.join(parts).strip()


def import_bsb():
    """Main import function."""
    print("=" * 60)
    print("Importing Berean Standard Bible (BSB)")
    print("=" * 60)

    # Load all data
    source_data = load_source_data()
    bsb_verses = load_bsb_text()
    alignments = load_alignments()

    print(f"\nTotal verses to import: {len(bsb_verses)}")
    print(f"Total alignment mappings: {len(alignments)}")

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Add BSB translation
    cursor.execute("""
        INSERT OR REPLACE INTO translations (id, name, language, is_public_domain, license_info)
        VALUES ('BSB', 'Berean Standard Bible', 'en', 1, 'CC-BY 4.0 - berean.bible')
    """)

    # Get book order mapping
    cursor.execute("SELECT name, book_order FROM books")
    book_orders = {row['name']: row['book_order'] for row in cursor.fetchall()}

    # Clear existing BSB data
    print("\nClearing existing BSB data...")
    cursor.execute("DELETE FROM verses WHERE translation_id = 'BSB'")
    cursor.execute("DELETE FROM english_word_alignments WHERE translation_id = 'BSB'")

    # Import verses
    print("Importing BSB verses...")
    verse_count = 0
    for (book, chapter, verse), words in sorted(bsb_verses.items()):
        if book not in book_orders:
            continue

        text = build_verse_text(words)
        book_order = book_orders[book]

        cursor.execute("""
            INSERT INTO verses (translation_id, book, book_order, chapter, verse, text)
            VALUES ('BSB', ?, ?, ?, ?, ?)
        """, (book, book_order, chapter, verse, text))

        verse_count += 1
        if verse_count % 5000 == 0:
            print(f"  Imported {verse_count} verses...")

    print(f"  Total verses imported: {verse_count}")

    # Import word alignments
    print("\nImporting BSB word alignments...")
    alignment_count = 0

    for (book, chapter, verse), words in bsb_verses.items():
        if book not in book_orders:
            continue

        # Build word position map (1-indexed, only real words not punctuation)
        real_word_pos = 0
        for word in sorted(words, key=lambda w: w['position']):
            text = word['text']
            # Skip pure punctuation
            if not any(c.isalpha() for c in text):
                continue

            real_word_pos += 1
            word_id = word['word_id']

            # Get alignment for this word
            source_ids = alignments.get(word_id, [])

            if source_ids:
                # Get the first source word's info (primary alignment)
                source_id = source_ids[0]
                source_info = source_data.get(source_id, {})

                # Parse source word position
                source_book, source_chapter, source_verse, source_word_pos = parse_word_id(source_id)

                if source_book:
                    # Clean the word text
                    clean_word = ''.join(c for c in text if c.isalpha() or c == "'")

                    cursor.execute("""
                        INSERT OR REPLACE INTO english_word_alignments
                        (translation_id, book, chapter, verse, english_word_position,
                         english_word, original_word_position, confidence)
                        VALUES ('BSB', ?, ?, ?, ?, ?, ?, 1.0)
                    """, (book, chapter, verse, real_word_pos, clean_word, source_word_pos))

                    alignment_count += 1

        if alignment_count % 50000 == 0 and alignment_count > 0:
            print(f"  Imported {alignment_count} alignments...")

    print(f"  Total alignments imported: {alignment_count}")

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("BSB import complete!")
    print("=" * 60)


if __name__ == "__main__":
    import_bsb()
