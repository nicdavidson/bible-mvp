#!/usr/bin/env python3
"""
Import interlinear (original language) data for Genesis (Hebrew) and Matthew (Greek).

Sources:
- Hebrew: Open Scriptures Hebrew Bible (morphhb) - CC-BY 4.0
- Greek: Open Greek New Testament (OpenGNT) - CC-BY-SA 4.0

Usage:
    python scripts/import_interlinear.py
"""
import csv
import re
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

DATABASE_PATH = Path(__file__).parent.parent / "data" / "bible.db"
DATA_DIR = Path(__file__).parent.parent / "data"

# OSIS namespace for Hebrew XML
OSIS_NS = {'osis': 'http://www.bibletechnologies.net/2003/OSIS/namespace'}


def get_verse_id(conn, book, chapter, verse, translation='WEB'):
    """Get the verse ID from the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM verses
        WHERE book = ? AND chapter = ? AND verse = ? AND translation_id = ?
    """, (book, chapter, verse, translation))
    result = cursor.fetchone()
    return result[0] if result else None


def parse_hebrew_genesis(xml_path):
    """Parse Genesis Hebrew XML from Open Scriptures Hebrew Bible."""
    print(f"  Parsing {xml_path}...")
    tree = ET.parse(xml_path)
    root = tree.getroot()

    words_data = []

    # Find all chapters
    for chapter_elem in root.findall('.//osis:chapter', OSIS_NS):
        chapter_id = chapter_elem.get('osisID', '')
        # Format: Gen.1
        match = re.match(r'Gen\.(\d+)', chapter_id)
        if not match:
            continue
        chapter = int(match.group(1))

        # Find all verses in this chapter
        for verse_elem in chapter_elem.findall('.//osis:verse', OSIS_NS):
            verse_id = verse_elem.get('osisID', '')
            # Format: Gen.1.1
            vmatch = re.match(r'Gen\.(\d+)\.(\d+)', verse_id)
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
                    'book': 'Genesis',
                    'chapter': chapter,
                    'verse': verse,
                    'position': position,
                    'text': hebrew_text,
                    'strong_number': strong_number,
                    'parsing': morph
                })

    return words_data


def parse_greek_matthew(csv_path):
    """Parse Matthew Greek data from OpenGNT."""
    print(f"  Parsing {csv_path}...")
    words_data = []

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

            # Only process Matthew (book 40)
            if book_num != 40:
                continue

            verse_key = (chapter, verse)
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
                'book': 'Matthew',
                'chapter': chapter,
                'verse': verse,
                'position': position,
                'text': greek_text,
                'strong_number': strong_number,
                'parsing': morph,
                'translation': translation
            })

    return words_data


def import_words(conn, words_data):
    """Import words into the database."""
    cursor = conn.cursor()

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
    print("BibleMVP - Interlinear Data Import")
    print("=" * 40)

    conn = sqlite3.connect(DATABASE_PATH)

    try:
        # Import Hebrew Genesis
        print("\n1. Importing Hebrew Genesis...")
        genesis_xml = DATA_DIR / "Gen.xml"
        if not genesis_xml.exists():
            print(f"   ERROR: {genesis_xml} not found!")
            print("   Download from: https://raw.githubusercontent.com/openscriptures/morphhb/master/wlc/Gen.xml")
        else:
            hebrew_words = parse_hebrew_genesis(genesis_xml)
            imported, skipped = import_words(conn, hebrew_words)
            print(f"   Imported {imported} Hebrew words, skipped {skipped}")

        # Import Greek Matthew
        print("\n2. Importing Greek Matthew...")
        matthew_csv = DATA_DIR / "OpenGNT_version3_3.csv"
        if not matthew_csv.exists():
            print(f"   ERROR: {matthew_csv} not found!")
            print("   Download from: https://github.com/eliranwong/OpenGNT/raw/master/OpenGNT_BASE_TEXT.zip")
        else:
            greek_words = parse_greek_matthew(matthew_csv)
            imported, skipped = import_words(conn, greek_words)
            print(f"   Imported {imported} Greek words, skipped {skipped}")

        # Show stats
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM words")
        total = cursor.fetchone()[0]
        print(f"\nTotal words in database: {total}")

        # Sample data
        print("\nSample Hebrew (Genesis 1:1):")
        cursor.execute("""
            SELECT w.text, w.strong_number, w.parsing, l.transliteration, l.definition
            FROM words w
            JOIN verses v ON w.verse_id = v.id
            LEFT JOIN lexicon l ON w.strong_number = l.strong_number
            WHERE v.book = 'Genesis' AND v.chapter = 1 AND v.verse = 1
            ORDER BY w.position
            LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]} | {row[1]} | {row[3]} | {row[4][:50] if row[4] else 'N/A'}...")

        print("\nSample Greek (Matthew 1:1):")
        cursor.execute("""
            SELECT w.text, w.strong_number, w.parsing, w.translation, l.transliteration
            FROM words w
            JOIN verses v ON w.verse_id = v.id
            LEFT JOIN lexicon l ON w.strong_number = l.strong_number
            WHERE v.book = 'Matthew' AND v.chapter = 1 AND v.verse = 1
            ORDER BY w.position
            LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]} | {row[1]} | {row[3]} | {row[4]}")

    finally:
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
