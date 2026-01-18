#!/usr/bin/env python3
"""
Import STEPBible TAHOT/TAGNT word alignment data.

This creates word-level alignments between Hebrew/Greek original words and their
English translations, enabling deterministic lookup instead of fuzzy matching.

Data source: STEPBible-Data (CC BY 4.0)
https://github.com/STEPBible/STEPBible-Data
"""

import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "bible.db"
DATA_DIR = Path(__file__).parent.parent / "data" / "alignment"

# Map STEPBible book abbreviations to our book names
BOOK_MAP = {
    # Old Testament
    'Gen': 'Genesis', 'Exo': 'Exodus', 'Lev': 'Leviticus', 'Num': 'Numbers', 'Deu': 'Deuteronomy',
    'Jos': 'Joshua', 'Jdg': 'Judges', 'Rut': 'Ruth', '1Sa': '1 Samuel', '2Sa': '2 Samuel',
    '1Ki': '1 Kings', '2Ki': '2 Kings', '1Ch': '1 Chronicles', '2Ch': '2 Chronicles',
    'Ezr': 'Ezra', 'Neh': 'Nehemiah', 'Est': 'Esther', 'Job': 'Job', 'Psa': 'Psalms',
    'Pro': 'Proverbs', 'Ecc': 'Ecclesiastes', 'Sng': 'Song of Solomon', 'Isa': 'Isaiah',
    'Jer': 'Jeremiah', 'Lam': 'Lamentations', 'Ezk': 'Ezekiel', 'Dan': 'Daniel',
    'Hos': 'Hosea', 'Joe': 'Joel', 'Jol': 'Joel', 'Amo': 'Amos', 'Oba': 'Obadiah', 'Jon': 'Jonah',
    'Mic': 'Micah', 'Nah': 'Nahum', 'Nam': 'Nahum', 'Hab': 'Habakkuk', 'Zep': 'Zephaniah',
    'Hag': 'Haggai', 'Zec': 'Zechariah', 'Mal': 'Malachi',
    # New Testament
    'Mat': 'Matthew', 'Mrk': 'Mark', 'Luk': 'Luke', 'Jhn': 'John', 'Act': 'Acts',
    'Rom': 'Romans', '1Co': '1 Corinthians', '2Co': '2 Corinthians',
    'Gal': 'Galatians', 'Eph': 'Ephesians', 'Php': 'Philippians', 'Col': 'Colossians',
    '1Th': '1 Thessalonians', '2Th': '2 Thessalonians',
    '1Ti': '1 Timothy', '2Ti': '2 Timothy', 'Tit': 'Titus', 'Phm': 'Philemon',
    'Heb': 'Hebrews', 'Jas': 'James', '1Pe': '1 Peter', '2Pe': '2 Peter',
    '1Jn': '1 John', '2Jn': '2 John', '3Jn': '3 John', 'Jud': 'Jude', 'Rev': 'Revelation'
}


def create_alignment_table(conn):
    """Create the word_alignments table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS word_alignments (
            id INTEGER PRIMARY KEY,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            word_position INTEGER NOT NULL,  -- Position in Hebrew text (1-based)
            hebrew_text TEXT,                -- Original Hebrew with prefixes
            transliteration TEXT,
            english_gloss TEXT,              -- English translation/gloss
            strong_number TEXT,              -- Primary Strong's number (e.g., H0430)
            grammar TEXT,                    -- Morphology code
            UNIQUE(book, chapter, verse, word_position)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alignment_ref ON word_alignments(book, chapter, verse)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alignment_strongs ON word_alignments(strong_number)")
    conn.commit()
    print("Created word_alignments table")


def parse_reference(ref_str):
    """Parse reference like 'Gen.1.1#01=L' into (book, chapter, verse, word_pos)."""
    # Pattern: Book.Chapter.Verse#Position=Type
    match = re.match(r'([A-Za-z0-9]+)\.(\d+)\.(\d+)#(\d+)', ref_str)
    if not match:
        return None

    book_abbr = match.group(1)
    chapter = int(match.group(2))
    verse = int(match.group(3))
    word_pos = int(match.group(4))

    book = BOOK_MAP.get(book_abbr)
    if not book:
        return None

    return (book, chapter, verse, word_pos)


def extract_primary_strong(dstrongs, is_greek=False):
    """Extract primary Strong's number from dStrongs field.

    Hebrew examples:
    - 'H9003/{H7225G}' -> 'H7225'
    - '{H1254A}' -> 'H1254'
    - 'H9002/H9009/{H0776G}' -> 'H0776'

    Greek examples:
    - 'G0976=N-NSF' -> 'G0976'
    - 'G2424G=N-GSM-P' -> 'G2424'
    """
    if not dstrongs:
        return None

    prefix = 'G' if is_greek else 'H'

    if is_greek:
        # Greek format: G####[suffix]=morphology
        match = re.match(rf'{prefix}(\d+)[A-Z]?(?:=|$)', dstrongs)
        if match:
            return f"{prefix}{match.group(1)}"
    else:
        # Hebrew format: may have curly braces for main word
        # Find the main Strong's number (in curly braces)
        match = re.search(rf'\{{{prefix}(\d+)[A-Z]?\}}', dstrongs)
        if match:
            return f"{prefix}{match.group(1)}"

        # Fallback: find any H#### pattern
        match = re.search(rf'{prefix}(\d+)', dstrongs)
        if match:
            num = match.group(1)
            # Skip H9xxx (grammatical markers)
            if not num.startswith('9'):
                return f"{prefix}{num}"

    return None


def clean_gloss(gloss):
    """Clean up the English gloss.

    - Remove brackets: <obj.> -> obj., [was] -> was
    - Join prefix/suffix translations: 'in/ beginning' -> 'in beginning'
    """
    if not gloss:
        return None

    # Remove angle brackets (words that could be omitted)
    gloss = re.sub(r'<([^>]+)>', r'\1', gloss)
    # Remove square brackets (implied words)
    gloss = re.sub(r'\[([^\]]+)\]', r'\1', gloss)
    # Clean up forward slashes with spaces
    gloss = re.sub(r'\s*/\s*', ' ', gloss)
    # Clean up extra whitespace
    gloss = ' '.join(gloss.split())

    return gloss if gloss else None


def extract_transliteration_from_greek(greek_field):
    """Extract transliteration from Greek field like 'Βίβλος (Biblos)'."""
    if not greek_field:
        return None
    match = re.search(r'\(([^)]+)\)', greek_field)
    return match.group(1) if match else None


def import_alignment_file(conn, filepath, book_filter=None):
    """Import a TAHOT (Hebrew) or TAGNT (Greek) file into the database.

    Args:
        conn: Database connection
        filepath: Path to alignment TSV file
        book_filter: Optional book name to filter (e.g., 'Genesis')
    """
    print(f"Importing {filepath}...")

    # Detect if this is a Greek NT file
    filename = filepath.name if hasattr(filepath, 'name') else str(filepath)
    is_greek = 'TAGNT' in filename

    alignments = []
    skipped = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Skip header/comment lines
            if line.startswith('#') or line.startswith('=') or line.startswith('TAHOT') or line.startswith('TAGNT'):
                continue
            if line.startswith('Eng') or line.startswith('Ref') or line.startswith('('):
                continue
            if 'Translation' in line or 'Grammar' in line or 'Spreadsheet' in line:
                continue
            if 'STEPBible' in line or 'licence' in line or 'TinyURL' in line:
                continue

            # Split by tabs
            parts = line.split('\t')
            if len(parts) < 4:
                continue

            # Parse reference
            ref = parse_reference(parts[0])
            if not ref:
                continue

            book, chapter, verse, word_pos = ref

            # Apply book filter if specified
            if book_filter and book != book_filter:
                continue

            if is_greek:
                # Greek TAGNT format:
                # 0: Reference (Mat.1.1#01=NKO)
                # 1: Greek text with transliteration (Βίβλος (Biblos))
                # 2: English gloss ([The] book)
                # 3: Strong's + morphology (G0976=N-NSF)
                # 4: Lexeme info (βίβλος=book)
                original_text = parts[1].split('(')[0].strip() if len(parts) > 1 else None
                transliteration = extract_transliteration_from_greek(parts[1]) if len(parts) > 1 else None
                english_gloss = clean_gloss(parts[2]) if len(parts) > 2 else None
                dstrongs = parts[3] if len(parts) > 3 else None
                grammar = dstrongs.split('=')[1] if dstrongs and '=' in dstrongs else None
            else:
                # Hebrew TAHOT format:
                # 0: Reference (Gen.1.1#01=L)
                # 1: Hebrew text (בְּ/רֵאשִׁ֖ית)
                # 2: Transliteration (be./re.Shit)
                # 3: English gloss (in/ beginning)
                # 4: dStrongs (H9003/{H7225G})
                # 5: Grammar (HR/Ncfsa)
                original_text = parts[1] if len(parts) > 1 else None
                transliteration = parts[2] if len(parts) > 2 else None
                english_gloss = clean_gloss(parts[3]) if len(parts) > 3 else None
                dstrongs = parts[4] if len(parts) > 4 else None
                grammar = parts[5] if len(parts) > 5 else None

            strong_number = extract_primary_strong(dstrongs, is_greek=is_greek)

            # Skip if no useful data
            if not english_gloss and not strong_number:
                skipped += 1
                continue

            alignments.append((
                book, chapter, verse, word_pos,
                original_text, transliteration, english_gloss,
                strong_number, grammar
            ))

    # Insert into database
    if alignments:
        conn.executemany("""
            INSERT OR REPLACE INTO word_alignments
            (book, chapter, verse, word_position, hebrew_text, transliteration,
             english_gloss, strong_number, grammar)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, alignments)
        conn.commit()

    print(f"  Imported {len(alignments)} word alignments (skipped {skipped})")
    return len(alignments)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Import STEPBible alignment data')
    parser.add_argument('--book', help='Import only this book (e.g., Genesis)')
    parser.add_argument('--file', help='Specific alignment file to import')
    parser.add_argument('--ot-only', action='store_true', help='Only import OT (TAHOT) files')
    parser.add_argument('--nt-only', action='store_true', help='Only import NT (TAGNT) files')
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)

    # Create table
    create_alignment_table(conn)

    total = 0

    if args.file:
        # Import specific file
        total = import_alignment_file(conn, args.file, args.book)
    else:
        # Import all alignment files in data/alignment directory
        if not args.nt_only:
            for tahot_file in sorted(DATA_DIR.glob("TAHOT*.txt")):
                if tahot_file.stat().st_size > 100:  # Skip tiny placeholder files
                    count = import_alignment_file(conn, tahot_file, args.book)
                    total += count

        if not args.ot_only:
            for tagnt_file in sorted(DATA_DIR.glob("TAGNT*.txt")):
                count = import_alignment_file(conn, tagnt_file, args.book)
                total += count

    print(f"\nTotal: {total} word alignments imported")

    # Show sample for OT
    cursor = conn.execute("""
        SELECT book, chapter, verse, word_position, hebrew_text, english_gloss, strong_number
        FROM word_alignments
        WHERE book = 'Genesis' AND chapter = 1 AND verse = 1
        ORDER BY word_position
        LIMIT 7
    """)

    print("\nSample OT data (Genesis 1:1):")
    for row in cursor:
        text = row[4] or ''
        gloss = row[5] or ''
        strong = row[6] or ''
        print(f"  {row[3]:2d}: {text:15s} -> {gloss:20s} [{strong}]")

    # Show sample for NT
    cursor = conn.execute("""
        SELECT book, chapter, verse, word_position, hebrew_text, english_gloss, strong_number
        FROM word_alignments
        WHERE book = 'Matthew' AND chapter = 1 AND verse = 1
        ORDER BY word_position
        LIMIT 8
    """)

    print("\nSample NT data (Matthew 1:1):")
    for row in cursor:
        text = row[4] or ''
        gloss = row[5] or ''
        strong = row[6] or ''
        print(f"  {row[3]:2d}: {text:15s} -> {gloss:20s} [{strong}]")

    conn.close()


if __name__ == '__main__':
    main()
