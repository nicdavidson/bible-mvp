#!/usr/bin/env python3
"""
Import World English Bible from open-bibles XML.
Source: https://github.com/seven1m/open-bibles

Usage:
    python scripts/import_web_xml.py
"""
import os
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
from source_cache import cached_fetch

DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", Path(__file__).parent.parent / "data" / "bible.db"))
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
    """Download WEB XML file (cached locally after first download)."""
    print(f"Loading WEB XML...")
    data = cached_fetch("web/eng-web.usfx.xml", WEB_XML_URL, timeout=120)
    if data is None:
        raise RuntimeError(f"Failed to fetch WEB XML from {WEB_XML_URL}")
    return data


# Elements whose content is never verse text: notes, cross-references, book
# headers, Psalm superscriptions (BSB and KJV rows don't carry them either),
# published verse/chapter labels.
SKIP_ELEMENTS = {"f", "x", "id", "ide", "h", "toc", "cl", "d", "vp", "cp", "rem", "fig", "s"}
# Paragraph styles that are headings or speaker labels, not verse text.
SKIP_PARAGRAPH_STYLES = {"mt", "mt1", "mt2", "mte", "ms", "ms1", "mr", "s", "s1", "s2", "sp",
                         "is", "ip", "ili", "imt", "r", "d"}


def iter_verse_text(book_elem):
    """Yield (chapter, verse, text) for every piece of verse text in document order.

    USFX keeps a verse's words in element text and tails at any depth: inside
    <q> poetry lines, <wj> words of Jesus, <add>, <qs> (Selah), and so on.
    Before 2026-11 this importer only read the tail of <v> and of a few inline
    elements, which cut most poetry verses to their first line and dropped
    every verse that opens inside <wj> or <q>.
    """
    state = {"chapter": 0, "verse": None}

    def walk(elem):
        tag = elem.tag
        if tag == "c":
            state["chapter"] = int(elem.get("id", 0))
            state["verse"] = None
        elif tag == "v":
            vid = re.match(r"\d+", elem.get("id", "0"))
            state["verse"] = int(vid.group()) if vid else None
        elif tag == "ve":
            state["verse"] = None
        skip = tag in SKIP_ELEMENTS or (tag == "p" and elem.get("sfm") in SKIP_PARAGRAPH_STYLES)
        if not skip:
            if elem.text and state["verse"]:
                yield state["chapter"], state["verse"], elem.text
            for child in elem:
                yield from walk(child)
                if child.tail and state["verse"]:
                    yield state["chapter"], state["verse"], child.tail

    for child in book_elem:
        yield from walk(child)
        if child.tail and state["verse"]:
            yield state["chapter"], state["verse"], child.tail


def parse_usfx(xml_content: str, conn: sqlite3.Connection) -> int:
    """Parse USFX XML and import verses (INSERT OR REPLACE; idempotent)."""
    cursor = conn.cursor()
    root = ET.fromstring(xml_content)

    total_verses = 0
    for book_elem in root.iter('book'):
        book_name = BOOK_ID_MAP.get(book_elem.get('id', ''))
        book_order = BOOK_ORDER.get(book_name, 0) if book_name else 0
        if not book_order:
            continue

        verses = {}
        for chapter, verse, piece in iter_verse_text(book_elem):
            if chapter > 0:
                verses.setdefault((chapter, verse), []).append(piece)

        book_verses = 0
        for (chapter, verse), pieces in verses.items():
            text = re.sub(r'\s+', ' ', ''.join(pieces)).strip()
            if text:
                # Upsert, not INSERT OR REPLACE: REPLACE deletes without firing
                # the verses_ad trigger, which leaves verses_fts corrupt.
                cursor.execute("""
                    INSERT INTO verses
                    (translation_id, book, book_order, chapter, verse, text)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(translation_id, book, chapter, verse)
                    DO UPDATE SET text = excluded.text, book_order = excluded.book_order
                """, ("WEB", book_name, book_order, chapter, verse, text))
                book_verses += 1

        conn.commit()
        total_verses += book_verses
        print(f"  {book_name}... {book_verses} verses")

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
        # Belt and braces: re-derive the external-content FTS index from verses.
        conn.execute("INSERT INTO verses_fts(verses_fts) VALUES('rebuild')")
        conn.commit()

        print(f"\n{'=' * 50}")
        print(f"WEB Import Complete: {total} verses")
        print("=" * 50)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
