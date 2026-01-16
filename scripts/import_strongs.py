#!/usr/bin/env python3
"""
Import Strong's Concordance definitions.
Source: Various public domain sources

Usage:
    python scripts/import_strongs.py

This creates the lexicon entries for Greek (G) and Hebrew (H) Strong's numbers.
"""
import json
import sqlite3
import urllib.request
from pathlib import Path

DATABASE_PATH = Path(__file__).parent.parent / "data" / "bible.db"

# Public domain Strong's data sources
STRONGS_GREEK_URL = "https://raw.githubusercontent.com/openscriptures/strongs/master/greek/strongs-greek-dictionary.json"
STRONGS_HEBREW_URL = "https://raw.githubusercontent.com/openscriptures/strongs/master/hebrew/strongs-hebrew-dictionary.json"


def download_json(url):
    """Download and parse JSON from URL."""
    print(f"Downloading from {url}...")
    with urllib.request.urlopen(url) as response:
        data = response.read().decode('utf-8')
        return json.loads(data)


def import_lexicon(conn, data, language):
    """Import lexicon entries into the database."""
    cursor = conn.cursor()
    count = 0

    for strong_num, entry in data.items():
        # Normalize Strong's number format
        if not strong_num.startswith(('G', 'H')):
            prefix = 'G' if language == 'greek' else 'H'
            strong_num = f"{prefix}{strong_num}"

        # Extract fields (format varies by source)
        if isinstance(entry, dict):
            original = entry.get('lemma', entry.get('word', ''))
            transliteration = entry.get('translit', entry.get('transliteration', ''))
            pronunciation = entry.get('pronunciation', '')
            definition = entry.get('strongs_def', entry.get('definition', ''))
            extended = entry.get('kjv_def', entry.get('extended_definition', ''))
            derivation = entry.get('derivation', '')
        else:
            # Simple string format
            original = ''
            transliteration = ''
            pronunciation = ''
            definition = str(entry)
            extended = ''
            derivation = ''

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO lexicon
                (strong_number, language, original, transliteration, pronunciation,
                 definition, extended_definition, derivation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (strong_num, language, original, transliteration, pronunciation,
                  definition, extended, derivation))
            count += 1
        except sqlite3.Error as e:
            print(f"  Error importing {strong_num}: {e}")

    conn.commit()
    return count


def main():
    """Main entry point."""
    print("BibleMVP - Strong's Concordance Import")
    print("=" * 40)

    # Ensure data directory exists
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Connect to database
    conn = sqlite3.connect(DATABASE_PATH)

    try:
        # Download and import Greek
        print("\nImporting Greek lexicon...")
        greek_data = download_json(STRONGS_GREEK_URL)
        greek_count = import_lexicon(conn, greek_data, 'greek')
        print(f"  Imported {greek_count} Greek entries")

        # Download and import Hebrew
        print("\nImporting Hebrew lexicon...")
        hebrew_data = download_json(STRONGS_HEBREW_URL)
        hebrew_count = import_lexicon(conn, hebrew_data, 'hebrew')
        print(f"  Imported {hebrew_count} Hebrew entries")

        print(f"\nTotal lexicon entries: {greek_count + hebrew_count}")

    except Exception as e:
        print(f"Error during import: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
