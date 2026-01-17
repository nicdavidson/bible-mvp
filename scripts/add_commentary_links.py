#!/usr/bin/env python3
"""
Add clickable Bible reference links to commentary entries.
This is a one-time migration that processes all commentary and embeds links.
"""

import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "bible.db"

# Book abbreviation mappings (Matthew Henry style -> full name)
# Includes both abbreviations and full names for comprehensive matching
BOOK_ABBREVS = {
    # Old Testament - abbreviations
    'Gen': 'Genesis', 'Ge': 'Genesis', 'Exod': 'Exodus', 'Exo': 'Exodus', 'Ex': 'Exodus',
    'Lev': 'Leviticus', 'Le': 'Leviticus',
    'Num': 'Numbers', 'Nu': 'Numbers', 'Deut': 'Deuteronomy', 'Deu': 'Deuteronomy', 'De': 'Deuteronomy',
    'Josh': 'Joshua', 'Jos': 'Joshua', 'Judg': 'Judges', 'Jdg': 'Judges',
    'Rth': 'Ruth', 'Ru': 'Ruth',
    '1Sam': '1 Samuel', '1Sa': '1 Samuel', 'Sa1': '1 Samuel',
    '2Sam': '2 Samuel', '2Sa': '2 Samuel', 'Sa2': '2 Samuel',
    '1Kgs': '1 Kings', '1Ki': '1 Kings', 'Kg1': '1 Kings', '1Kg': '1 Kings',
    '2Kgs': '2 Kings', '2Ki': '2 Kings', 'Kg2': '2 Kings', '2Kg': '2 Kings',
    '1Chr': '1 Chronicles', '1Ch': '1 Chronicles', 'Ch1': '1 Chronicles',
    '2Chr': '2 Chronicles', '2Ch': '2 Chronicles', 'Ch2': '2 Chronicles',
    'Ezr': 'Ezra', 'Ne': 'Nehemiah',
    'Esth': 'Esther', 'Est': 'Esther', 'Es': 'Esther',
    'Psa': 'Psalms', 'Ps': 'Psalms',
    'Prov': 'Proverbs', 'Pro': 'Proverbs', 'Pr': 'Proverbs',
    'Eccl': 'Ecclesiastes', 'Ecc': 'Ecclesiastes', 'Ec': 'Ecclesiastes',
    'Song': 'Song of Solomon', 'Sol': 'Song of Solomon', 'So': 'Song of Solomon', 'Ca': 'Song of Solomon',
    'Isa': 'Isaiah', 'Is': 'Isaiah', 'Je': 'Jeremiah',
    'Lam': 'Lamentations', 'La': 'Lamentations',
    'Ezek': 'Ezekiel', 'Eze': 'Ezekiel', 'Da': 'Daniel',
    'Ho': 'Hosea', 'Joe': 'Joel',
    'Am': 'Amos', 'Obad': 'Obadiah', 'Oba': 'Obadiah', 'Ob': 'Obadiah',
    'Jon': 'Jonah', 'Mi': 'Micah',
    'Na': 'Nahum',
    'Zeph': 'Zephaniah', 'Zep': 'Zephaniah',
    'Zech': 'Zechariah', 'Zec': 'Zechariah', 'Zac': 'Zechariah',
    # Old Testament - full names
    'Genesis': 'Genesis', 'Exodus': 'Exodus', 'Leviticus': 'Leviticus', 'Numbers': 'Numbers',
    'Deuteronomy': 'Deuteronomy', 'Joshua': 'Joshua', 'Judges': 'Judges', 'Ruth': 'Ruth',
    'Ezra': 'Ezra', 'Nehemiah': 'Nehemiah', 'Esther': 'Esther', 'Job': 'Job',
    'Psalms': 'Psalms', 'Proverbs': 'Proverbs', 'Ecclesiastes': 'Ecclesiastes',
    'Isaiah': 'Isaiah', 'Jeremiah': 'Jeremiah', 'Lamentations': 'Lamentations',
    'Ezekiel': 'Ezekiel', 'Daniel': 'Daniel', 'Hosea': 'Hosea', 'Joel': 'Joel',
    'Amos': 'Amos', 'Obadiah': 'Obadiah', 'Jonah': 'Jonah', 'Micah': 'Micah',
    'Nahum': 'Nahum', 'Habakkuk': 'Habakkuk', 'Hab': 'Habakkuk',
    'Zephaniah': 'Zephaniah', 'Haggai': 'Haggai', 'Hag': 'Haggai',
    'Zechariah': 'Zechariah', 'Malachi': 'Malachi', 'Mal': 'Malachi',
    # New Testament - abbreviations
    'Mat': 'Matthew', 'Matt': 'Matthew', 'Mt': 'Matthew',
    'Mar': 'Mark', 'Mk': 'Mark', 'Lk': 'Luke', 'Lu': 'Luke',
    'Joh': 'John', 'Jn': 'John', 'Act': 'Acts', 'Ac': 'Acts',
    'Rom': 'Romans', 'Ro': 'Romans',
    '1Cor': '1 Corinthians', '1Co': '1 Corinthians', 'Co1': '1 Corinthians',
    '2Cor': '2 Corinthians', '2Co': '2 Corinthians', 'Co2': '2 Corinthians',
    'Gal': 'Galatians', 'Ga': 'Galatians',
    'Eph': 'Ephesians', 'Phil': 'Philippians', 'Php': 'Philippians',
    'Col': 'Colossians',
    '1Thes': '1 Thessalonians', '1Th': '1 Thessalonians', 'Th1': '1 Thessalonians',
    '2Thes': '2 Thessalonians', '2Th': '2 Thessalonians', 'Th2': '2 Thessalonians',
    '1Tim': '1 Timothy', '1Ti': '1 Timothy', 'Ti1': '1 Timothy',
    '2Tim': '2 Timothy', '2Ti': '2 Timothy', 'Ti2': '2 Timothy',
    'Tit': 'Titus', 'Phm': 'Philemon', 'Philem': 'Philemon',
    'Jam': 'James', 'Jas': 'James',
    '1Pet': '1 Peter', '1Pe': '1 Peter', 'Pe1': '1 Peter',
    '2Pet': '2 Peter', '2Pe': '2 Peter', 'Pe2': '2 Peter',
    '1Joh': '1 John', '1Jn': '1 John', 'Jo1': '1 John',
    '2Joh': '2 John', '2Jn': '2 John', 'Jo2': '2 John',
    '3Joh': '3 John', '3Jn': '3 John', 'Jo3': '3 John',
    'Jud': 'Jude',
    'Rev': 'Revelation', 'Re': 'Revelation',
    # New Testament - full names
    'Matthew': 'Matthew', 'Mark': 'Mark', 'Luke': 'Luke', 'John': 'John', 'Acts': 'Acts',
    'Romans': 'Romans', 'Galatians': 'Galatians', 'Ephesians': 'Ephesians',
    'Philippians': 'Philippians', 'Colossians': 'Colossians',
    'Titus': 'Titus', 'Hebrews': 'Hebrews', 'Heb': 'Hebrews',
    'James': 'James', 'Jude': 'Jude', 'Revelation': 'Revelation',
    # Standalone "Peter" (used as "Peter 2:5" meaning 1 Peter)
    'Peter': '1 Peter', 'Luk': 'Luke',
}

# Build regex pattern for book abbreviations
abbrev_pattern = '|'.join(re.escape(k) for k in sorted(BOOK_ABBREVS.keys(), key=len, reverse=True))

# Pattern: Book Ch:V or Book Ch:V-V (e.g., "Joh 3:16" or "Psa 119:1-8")
REF_PATTERN = re.compile(
    rf'\b({abbrev_pattern})\s+(\d+):(\d+)(?:-(\d+))?\b',
    re.IGNORECASE
)


def normalize_book(abbrev):
    """Convert abbreviation to full book name."""
    # Try exact match first
    if abbrev in BOOK_ABBREVS:
        return BOOK_ABBREVS[abbrev]
    # Try case-insensitive
    for key, val in BOOK_ABBREVS.items():
        if key.lower() == abbrev.lower():
            return val
    return None


def strip_existing_links(content):
    """Remove existing commentary-ref links to allow re-processing."""
    # Pattern matches: <a href="#" class="commentary-ref" data-ref="...">TEXT</a>
    return re.sub(r'<a href="#" class="commentary-ref" data-ref="[^"]*">([^<]*)</a>', r'\1', content)


def add_links(content):
    """Replace Bible references with clickable links."""
    # First strip any existing links so we can re-process
    content = strip_existing_links(content)

    def replace_ref(match):
        abbrev = match.group(1)
        chapter = match.group(2)
        verse_start = match.group(3)
        verse_end = match.group(4)  # May be None

        book = normalize_book(abbrev)
        if not book:
            return match.group(0)  # Return unchanged if unknown

        # Build reference string
        if verse_end:
            ref = f"{book} {chapter}:{verse_start}-{verse_end}"
            display = f"{abbrev} {chapter}:{verse_start}-{verse_end}"
        else:
            ref = f"{book} {chapter}:{verse_start}"
            display = f"{abbrev} {chapter}:{verse_start}"

        # Return clickable link (uses data attribute for Alpine.js to handle)
        return f'<a href="#" class="commentary-ref" data-ref="{ref}">{display}</a>'

    return REF_PATTERN.sub(replace_ref, content)


def main():
    print(f"Opening database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all commentary entries
    cursor.execute("SELECT id, content FROM commentary_entries")
    entries = cursor.fetchall()
    print(f"Found {len(entries)} commentary entries")

    updated = 0
    links_added = 0

    for entry_id, content in entries:
        if not content:
            continue

        # Count existing refs
        original_refs = len(REF_PATTERN.findall(content))

        # Add links
        new_content = add_links(content)

        if new_content != content:
            cursor.execute(
                "UPDATE commentary_entries SET content = ? WHERE id = ?",
                (new_content, entry_id)
            )
            updated += 1
            links_added += original_refs

    conn.commit()
    conn.close()

    print(f"\nUpdated {updated} entries")
    print(f"Added {links_added} clickable links")
    print("Done!")


if __name__ == "__main__":
    main()
