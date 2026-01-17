#!/usr/bin/env python3
"""
Import interlinear (original language) data for the Old Testament (Hebrew) and Matthew (Greek).

Sources:
- Hebrew: Open Scriptures Hebrew Bible (morphhb) - CC-BY 4.0
- Greek: Open Greek New Testament (OpenGNT) - CC-BY-SA 4.0

Usage:
    python scripts/import_interlinear.py
"""
import csv
import re
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

DATABASE_PATH = Path(__file__).parent.parent / "data" / "bible.db"
DATA_DIR = Path(__file__).parent.parent / "data"

# OSIS namespace for Hebrew XML
OSIS_NS = {'osis': 'http://www.bibletechnologies.net/2003/OSIS/namespace'}

# OSIS abbreviation to database book name mapping
OSIS_TO_BOOK = {
    'Gen': 'Genesis',
    'Exod': 'Exodus',
    'Lev': 'Leviticus',
    'Num': 'Numbers',
    'Deut': 'Deuteronomy',
    'Josh': 'Joshua',
    'Judg': 'Judges',
    'Ruth': 'Ruth',
    '1Sam': '1 Samuel',
    '2Sam': '2 Samuel',
    '1Kgs': '1 Kings',
    '2Kgs': '2 Kings',
    '1Chr': '1 Chronicles',
    '2Chr': '2 Chronicles',
    'Ezra': 'Ezra',
    'Neh': 'Nehemiah',
    'Esth': 'Esther',
    'Job': 'Job',
    'Ps': 'Psalms',
    'Prov': 'Proverbs',
    'Eccl': 'Ecclesiastes',
    'Song': 'Song of Solomon',
    'Isa': 'Isaiah',
    'Jer': 'Jeremiah',
    'Lam': 'Lamentations',
    'Ezek': 'Ezekiel',
    'Dan': 'Daniel',
    'Hos': 'Hosea',
    'Joel': 'Joel',
    'Amos': 'Amos',
    'Obad': 'Obadiah',
    'Jonah': 'Jonah',
    'Mic': 'Micah',
    'Nah': 'Nahum',
    'Hab': 'Habakkuk',
    'Zeph': 'Zephaniah',
    'Hag': 'Haggai',
    'Zech': 'Zechariah',
    'Mal': 'Malachi',
}

# Hebrew XML files from Open Scriptures
HEBREW_BASE_URL = "https://raw.githubusercontent.com/openscriptures/morphhb/master/wlc/"
HEBREW_FILES = [
    'Gen.xml', 'Exod.xml', 'Lev.xml', 'Num.xml', 'Deut.xml',
    'Josh.xml', 'Judg.xml', 'Ruth.xml', '1Sam.xml', '2Sam.xml',
    '1Kgs.xml', '2Kgs.xml', '1Chr.xml', '2Chr.xml', 'Ezra.xml',
    'Neh.xml', 'Esth.xml', 'Job.xml', 'Ps.xml', 'Prov.xml',
    'Eccl.xml', 'Song.xml', 'Isa.xml', 'Jer.xml', 'Lam.xml',
    'Ezek.xml', 'Dan.xml', 'Hos.xml', 'Joel.xml', 'Amos.xml',
    'Obad.xml', 'Jonah.xml', 'Mic.xml', 'Nah.xml', 'Hab.xml',
    'Zeph.xml', 'Hag.xml', 'Zech.xml', 'Mal.xml'
]


def download_file(url, dest_path):
    """Download a file from URL to destination path."""
    print(f"    Downloading {url}...")
    urllib.request.urlretrieve(url, dest_path)


def get_verse_id(conn, book, chapter, verse, translation='WEB'):
    """Get the verse ID from the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM verses
        WHERE book = ? AND chapter = ? AND verse = ? AND translation_id = ?
    """, (book, chapter, verse, translation))
    result = cursor.fetchone()
    return result[0] if result else None


def parse_hebrew_xml(xml_path, osis_abbrev):
    """Parse Hebrew XML from Open Scriptures Hebrew Bible."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    book_name = OSIS_TO_BOOK.get(osis_abbrev, osis_abbrev)
    words_data = []

    # Find all chapters
    for chapter_elem in root.findall('.//osis:chapter', OSIS_NS):
        chapter_id = chapter_elem.get('osisID', '')
        # Format: Gen.1, Ps.119, etc.
        match = re.match(rf'{re.escape(osis_abbrev)}\.(\d+)', chapter_id)
        if not match:
            continue
        chapter = int(match.group(1))

        # Find all verses in this chapter
        for verse_elem in chapter_elem.findall('.//osis:verse', OSIS_NS):
            verse_id = verse_elem.get('osisID', '')
            # Format: Gen.1.1, Ps.119.176, etc.
            vmatch = re.match(rf'{re.escape(osis_abbrev)}\.(\d+)\.(\d+)', verse_id)
            if not vmatch:
                continue
            verse = int(vmatch.group(2))

            # Get all words in this verse
            position = 0
            for w_elem in verse_elem.findall('.//osis:w', OSIS_NS):
                position += 1

                # Get Hebrew text
                hebrew_text = w_elem.text or ''

                # Get lemma (Strong's number)
                lemma = w_elem.get('lemma', '')
                # Clean up lemma: "b/7225" -> "H7225", "1254 a" -> "H1254"
                strong_number = None
                if lemma:
                    # Remove prefixes like "b/", "c/", "d/"
                    lemma_clean = re.sub(r'^[a-z]/+', '', lemma)
                    # Remove letter suffixes like "a", "b"
                    lemma_clean = re.sub(r'\s*[a-z]$', '', lemma_clean)
                    # Handle multiple lemmas (take first)
                    lemma_clean = lemma_clean.split('/')[0].strip()
                    if lemma_clean and lemma_clean.isdigit():
                        strong_number = f"H{lemma_clean}"

                # Get morphology
                morph = w_elem.get('morph', '')

                words_data.append({
                    'book': book_name,
                    'chapter': chapter,
                    'verse': verse,
                    'position': position,
                    'text': hebrew_text,
                    'strong_number': strong_number,
                    'parsing': morph
                })

    return words_data


# NT book number to name mapping (OpenGNT uses numbers 40-66)
NT_BOOK_NUM_MAP = {
    40: 'Matthew', 41: 'Mark', 42: 'Luke', 43: 'John', 44: 'Acts',
    45: 'Romans', 46: '1 Corinthians', 47: '2 Corinthians', 48: 'Galatians',
    49: 'Ephesians', 50: 'Philippians', 51: 'Colossians', 52: '1 Thessalonians',
    53: '2 Thessalonians', 54: '1 Timothy', 55: '2 Timothy', 56: 'Titus',
    57: 'Philemon', 58: 'Hebrews', 59: 'James', 60: '1 Peter', 61: '2 Peter',
    62: '1 John', 63: '2 John', 64: '3 John', 65: 'Jude', 66: 'Revelation'
}


def parse_greek_nt(csv_path, book_filter=None):
    """Parse Greek NT data from OpenGNT for all books or specific ones.

    Args:
        csv_path: Path to OpenGNT CSV file
        book_filter: Optional list of book numbers to import (e.g., [40, 43] for Matthew and John)
                     If None, imports all NT books.
    """
    print(f"  Parsing {csv_path}...")
    words_data = []
    books_found = set()

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        header = next(reader)  # Skip header

        current_verse_key = None
        position = 0

        for row in reader:
            if len(row) < 11:
                continue

            # Column 7: 〔Book｜Chapter｜Verse〕
            # Format: 〔40｜1｜1〕
            ref_col = row[6] if len(row) > 6 else ''
            ref_match = re.match(r'〔(\d+)｜(\d+)｜(\d+)〕', ref_col)
            if not ref_match:
                continue

            book_num = int(ref_match.group(1))
            chapter = int(ref_match.group(2))
            verse = int(ref_match.group(3))

            # Filter books if specified
            if book_filter and book_num not in book_filter:
                continue

            # Skip if not a valid NT book
            if book_num not in NT_BOOK_NUM_MAP:
                continue

            book_name = NT_BOOK_NUM_MAP[book_num]
            books_found.add(book_name)

            verse_key = (book_num, chapter, verse)
            if verse_key != current_verse_key:
                current_verse_key = verse_key
                position = 0
            position += 1

            # Column 8: 〔OGNTk｜OGNTu｜OGNTa｜lexeme｜rmac｜sn〕
            word_col = row[7] if len(row) > 7 else ''
            word_match = re.match(r'〔([^｜]*)｜([^｜]*)｜([^｜]*)｜([^｜]*)｜([^｜]*)｜([^〕]*)〕', word_col)
            if not word_match:
                continue

            greek_text = word_match.group(3)  # OGNTa - accented Greek
            lexeme = word_match.group(4)
            morph = word_match.group(5)  # rmac
            strong_raw = word_match.group(6)  # sn - e.g., "G976"

            # Clean up Strong's number
            strong_number = None
            if strong_raw and strong_raw.startswith('G'):
                strong_number = strong_raw

            # Column 11: 〔TBESG｜IT｜LT｜ST｜Español〕
            trans_col = row[10] if len(row) > 10 else ''
            trans_match = re.match(r'〔([^｜]*)｜([^｜]*)｜([^｜]*)｜([^｜]*)｜([^〕]*)〕', trans_col)
            translation = ''
            if trans_match:
                translation = trans_match.group(2)  # IT - Interlinear Translation

            words_data.append({
                'book': book_name,
                'chapter': chapter,
                'verse': verse,
                'position': position,
                'text': greek_text,
                'strong_number': strong_number,
                'parsing': morph,
                'translation': translation
            })

    print(f"    Found words for books: {', '.join(sorted(books_found))}")
    return words_data


def import_words(conn, words_data, clear_existing=True):
    """Import words into the database."""
    cursor = conn.cursor()

    if clear_existing:
        # Clear existing words for these books
        books = set(w['book'] for w in words_data)
        for book in books:
            cursor.execute("""
                DELETE FROM words WHERE verse_id IN (
                    SELECT id FROM verses WHERE book = ? AND translation_id = 'WEB'
                )
            """, (book,))

    imported = 0
    skipped = 0

    for word in words_data:
        verse_id = get_verse_id(conn, word['book'], word['chapter'], word['verse'], 'WEB')
        if not verse_id:
            skipped += 1
            continue

        cursor.execute("""
            INSERT INTO words (verse_id, position, text, strong_number, parsing, translation)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            verse_id,
            word['position'],
            word['text'],
            word['strong_number'],
            word['parsing'],
            word.get('translation', '')
        ))
        imported += 1

    conn.commit()
    return imported, skipped


def main():
    print("BibleMVP - Full Interlinear Data Import")
    print("=" * 50)

    conn = sqlite3.connect(DATABASE_PATH)

    try:
        # Import all Hebrew OT books
        print("\n1. Importing Hebrew Old Testament...")
        total_hebrew_words = 0
        total_skipped = 0

        for i, xml_file in enumerate(HEBREW_FILES, 1):
            osis_abbrev = xml_file.replace('.xml', '')
            book_name = OSIS_TO_BOOK.get(osis_abbrev, osis_abbrev)
            xml_path = DATA_DIR / xml_file

            # Download if not exists
            if not xml_path.exists():
                url = HEBREW_BASE_URL + xml_file
                download_file(url, xml_path)

            print(f"  [{i}/{len(HEBREW_FILES)}] {book_name}...", end=" ", flush=True)
            hebrew_words = parse_hebrew_xml(xml_path, osis_abbrev)
            imported, skipped = import_words(conn, hebrew_words)
            total_hebrew_words += imported
            total_skipped += skipped
            print(f"{imported} words")

        print(f"\n  Total Hebrew words imported: {total_hebrew_words}")
        if total_skipped:
            print(f"  Skipped (verse not found): {total_skipped}")

        # Import Greek NT (all books)
        print("\n2. Importing Greek New Testament (all books)...")
        nt_csv = DATA_DIR / "OpenGNT_version3_3.csv"
        if not nt_csv.exists():
            print(f"   ERROR: {nt_csv} not found!")
            print("   Download from: https://github.com/eliranwong/OpenGNT/raw/master/OpenGNT_BASE_TEXT.zip")
        else:
            greek_words = parse_greek_nt(nt_csv)
            imported, skipped = import_words(conn, greek_words)
            print(f"   Imported {imported} Greek words, skipped {skipped}")

        # Show stats
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM words")
        total = cursor.fetchone()[0]
        print(f"\n" + "=" * 50)
        print(f"Total words in database: {total:,}")

        # Sample data
        print("\nSample Hebrew (Genesis 1:1):")
        cursor.execute("""
            SELECT w.text, w.strong_number, w.parsing, l.transliteration, l.definition
            FROM words w
            JOIN verses v ON w.verse_id = v.id
            LEFT JOIN lexicon l ON w.strong_number = l.strong_number
            WHERE v.book = 'Genesis' AND v.chapter = 1 AND v.verse = 1
            ORDER BY w.position
            LIMIT 3
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]} | {row[1]} | {(row[4] or 'N/A')[:40]}...")

        print("\nSample Hebrew (Psalms 23:1):")
        cursor.execute("""
            SELECT w.text, w.strong_number, l.definition
            FROM words w
            JOIN verses v ON w.verse_id = v.id
            LEFT JOIN lexicon l ON w.strong_number = l.strong_number
            WHERE v.book = 'Psalms' AND v.chapter = 23 AND v.verse = 1
            ORDER BY w.position
            LIMIT 3
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]} | {row[1]} | {(row[2] or 'N/A')[:40]}...")

    finally:
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
