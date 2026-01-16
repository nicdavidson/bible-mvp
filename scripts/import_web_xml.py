#!/usr/bin/env python3
"""
Import World English Bible from open-bibles XML.
Source: https://github.com/seven1m/open-bibles

Usage:
    python scripts/import_web_xml.py
"""
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DATABASE_PATH = Path(__file__).parent.parent / "data" / "bible.db"
WEB_XML_URL = "https://raw.githubusercontent.com/seven1m/open-bibles/master/eng-web.usfx.xml"

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

# Map USFX book IDs to canonical names
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


def download_xml():
    """Download WEB XML file."""
    print(f"Downloading WEB XML from GitHub...")
    print(f"URL: {WEB_XML_URL}")

    req = urllib.request.Request(WEB_XML_URL, headers={'User-Agent': 'BibleMVP/1.0'})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read().decode('utf-8')


def get_text_content(element):
    """Get all text content from an element, including nested elements."""
    text_parts = []
    if element.text:
        text_parts.append(element.text)
    for child in element:
        text_parts.append(get_text_content(child))
        if child.tail:
            text_parts.append(child.tail)
    return ''.join(text_parts)


def parse_usfx(xml_content: str, conn: sqlite3.Connection) -> int:
    """Parse USFX XML and import verses."""
    cursor = conn.cursor()

    # Parse XML
    root = ET.fromstring(xml_content)

    total_verses = 0
    current_book = None
    current_chapter = 0
    book_name = None
    book_order = 0

    # Find all book elements
    for book_elem in root.iter('book'):
        book_id = book_elem.get('id', '')
        book_name = BOOK_ID_MAP.get(book_id)

        if not book_name:
            continue

        book_order = BOOK_ORDER.get(book_name, 0)
        if not book_order:
            continue

        book_verses = 0
        print(f"  {book_name}...", end=" ", flush=True)

        # Process chapters within this book
        for chapter_elem in book_elem.iter('c'):
            current_chapter = int(chapter_elem.get('id', 0))

        # The USFX format has verses as <v> elements
        # We need to collect text between verse markers
        current_chapter = 0
        verses_in_chapter = {}

        for elem in book_elem.iter():
            if elem.tag == 'c':
                # Save previous chapter's verses
                if verses_in_chapter and current_chapter > 0:
                    for v_num, v_text in verses_in_chapter.items():
                        text = ' '.join(v_text).strip()
                        text = re.sub(r'\s+', ' ', text)
                        if text:
                            cursor.execute("""
                                INSERT OR REPLACE INTO verses
                                (translation_id, book, book_order, chapter, verse, text)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, ("WEB", book_name, book_order, current_chapter, v_num, text))
                            book_verses += 1

                current_chapter = int(elem.get('id', 0))
                verses_in_chapter = {}

            elif elem.tag == 'v':
                verse_num = int(elem.get('id', 0))
                if verse_num > 0:
                    verses_in_chapter[verse_num] = []
                    # Get text that follows this verse marker
                    if elem.tail:
                        verses_in_chapter[verse_num].append(elem.tail.strip())

            elif elem.tag in ('ve', 'f', 'x', 'wj', 'add', 'nd', 'qt'):
                # Verse end, footnote, cross-ref, words of Jesus, added text, etc.
                # Get tail text and add to current verse
                if elem.tail and verses_in_chapter:
                    last_verse = max(verses_in_chapter.keys())
                    verses_in_chapter[last_verse].append(elem.tail.strip())

        # Save last chapter
        if verses_in_chapter and current_chapter > 0:
            for v_num, v_text in verses_in_chapter.items():
                text = ' '.join(v_text).strip()
                text = re.sub(r'\s+', ' ', text)
                if text:
                    cursor.execute("""
                        INSERT OR REPLACE INTO verses
                        (translation_id, book, book_order, chapter, verse, text)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, ("WEB", book_name, book_order, current_chapter, v_num, text))
                    book_verses += 1

        conn.commit()
        total_verses += book_verses
        print(f"{book_verses} verses")

    return total_verses


def main():
    print("BibleMVP - WEB Bible Import (XML)")
    print("=" * 50)

    from backend.database import init_db
    init_db()

    conn = sqlite3.connect(DATABASE_PATH)

    try:
        xml_content = download_xml()
        print(f"Downloaded {len(xml_content):,} bytes\n")

        total = parse_usfx(xml_content, conn)

        print(f"\n{'=' * 50}")
        print(f"WEB Import Complete: {total} verses")
        print("=" * 50)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
