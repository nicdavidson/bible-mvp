#!/usr/bin/env python3
"""
Build English word alignments from STEPBible gloss data.

This creates a mapping from English translation word positions to Hebrew/Greek
original word positions, enabling deterministic lookup when clicking English words.

The approach:
1. Get the STEPBible glosses (English translations of each Hebrew/Greek word)
2. Get the English translation text (KJV, WEB)
3. Match English words to glosses to create position mappings
"""

import sqlite3
import re
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent.parent / "data" / "bible.db"


def create_english_alignments_table(conn):
    """Create the english_word_alignments table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS english_word_alignments (
            id INTEGER PRIMARY KEY,
            translation_id TEXT NOT NULL,     -- KJV, WEB, etc.
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            english_word_position INTEGER NOT NULL,  -- 1-based position in English text
            english_word TEXT NOT NULL,              -- The actual English word
            original_word_position INTEGER NOT NULL, -- Position in Hebrew/Greek (word_alignments)
            confidence REAL DEFAULT 1.0,             -- Match confidence (1.0 = exact, <1.0 = inferred)
            UNIQUE(translation_id, book, chapter, verse, english_word_position)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_eng_align_ref
        ON english_word_alignments(translation_id, book, chapter, verse)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_eng_align_lookup
        ON english_word_alignments(translation_id, book, chapter, verse, english_word_position)
    """)
    conn.commit()
    print("Created english_word_alignments table")


def tokenize_text(text):
    """Tokenize text into words, preserving position info."""
    # Remove punctuation but keep word positions
    words = []
    for match in re.finditer(r"[A-Za-z]+(?:'[A-Za-z]+)?", text):
        words.append({
            'word': match.group().lower(),
            'original': match.group(),
            'start': match.start(),
            'end': match.end()
        })
    return words


def normalize_word(word):
    """Normalize a word for matching (lowercase, stem common suffixes)."""
    word = word.lower()
    # Basic stemming for common patterns
    if word.endswith('ness') and len(word) > 5:
        return word[:-4]  # emptiness -> empti
    if word.endswith('less') and len(word) > 5:
        return word[:-4]
    if word.endswith('ful') and len(word) > 4:
        return word[:-3]
    if word.endswith('ing') and len(word) > 4:
        return word[:-3]
    if word.endswith('ed') and len(word) > 3:
        return word[:-2]
    if word.endswith('ly') and len(word) > 3:
        return word[:-2]
    if word.endswith('er') and len(word) > 3:
        return word[:-2]
    if word.endswith('est') and len(word) > 4:
        return word[:-3]
    if word.endswith('s') and len(word) > 2:
        return word[:-1]
    return word


def build_gloss_index(glosses):
    """Build an index of gloss words to original word positions.

    Returns dict: normalized_word -> list of (original_position, full_gloss)
    """
    index = defaultdict(list)

    for orig_pos, gloss in glosses:
        if not gloss:
            continue
        # Tokenize the gloss
        for word_info in tokenize_text(gloss):
            normalized = normalize_word(word_info['word'])
            if len(normalized) >= 2:  # Skip single letters
                index[normalized].append((orig_pos, gloss, word_info['word']))

    return index


def match_verse_words(english_text, glosses):
    """Match English translation words to Hebrew/Greek positions.

    Args:
        english_text: The English translation text
        glosses: List of (original_position, english_gloss) tuples

    Returns:
        List of (english_pos, english_word, original_pos, confidence) tuples
    """
    alignments = []
    english_words = tokenize_text(english_text)
    gloss_index = build_gloss_index(glosses)

    # Track which original positions have been used
    used_positions = set()

    for eng_pos, word_info in enumerate(english_words, 1):
        eng_word = word_info['word']
        normalized = normalize_word(eng_word)

        # Skip very common words that match many glosses
        if eng_word in ('the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'for', 'is', 'was', 'be'):
            continue

        # Look for exact match first
        if normalized in gloss_index:
            candidates = gloss_index[normalized]
            # Prefer unused positions
            for orig_pos, full_gloss, matched_word in candidates:
                if orig_pos not in used_positions:
                    alignments.append((eng_pos, word_info['original'], orig_pos, 1.0))
                    used_positions.add(orig_pos)
                    break
            else:
                # All positions used, take first match
                if candidates:
                    orig_pos, full_gloss, matched_word = candidates[0]
                    alignments.append((eng_pos, word_info['original'], orig_pos, 0.8))

    return alignments


def build_alignments_for_translation(conn, translation_id, book_filter=None, limit=None):
    """Build English word alignments for a specific translation."""
    print(f"\nBuilding alignments for {translation_id}...")

    # Get all verses with their glosses
    query = """
        SELECT DISTINCT v.book, v.chapter, v.verse, v.text
        FROM verses v
        WHERE v.translation_id = ?
        AND EXISTS (
            SELECT 1 FROM word_alignments wa
            WHERE wa.book = v.book AND wa.chapter = v.chapter AND wa.verse = v.verse
        )
    """
    params = [translation_id]

    if book_filter:
        query += " AND v.book = ?"
        params.append(book_filter)

    query += " ORDER BY v.book, v.chapter, v.verse"

    if limit:
        query += f" LIMIT {limit}"

    verses = conn.execute(query, params).fetchall()
    print(f"  Processing {len(verses)} verses...")

    total_alignments = 0
    batch = []

    for book, chapter, verse, text in verses:
        # Get glosses for this verse
        glosses = conn.execute("""
            SELECT word_position, english_gloss
            FROM word_alignments
            WHERE book = ? AND chapter = ? AND verse = ?
            ORDER BY word_position
        """, (book, chapter, verse)).fetchall()

        if not glosses:
            continue

        # Match English words to glosses
        alignments = match_verse_words(text, glosses)

        for eng_pos, eng_word, orig_pos, confidence in alignments:
            batch.append((
                translation_id, book, chapter, verse,
                eng_pos, eng_word, orig_pos, confidence
            ))

        total_alignments += len(alignments)

        # Batch insert
        if len(batch) >= 1000:
            conn.executemany("""
                INSERT OR REPLACE INTO english_word_alignments
                (translation_id, book, chapter, verse, english_word_position,
                 english_word, original_word_position, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()
            batch = []

    # Final batch
    if batch:
        conn.executemany("""
            INSERT OR REPLACE INTO english_word_alignments
            (translation_id, book, chapter, verse, english_word_position,
             english_word, original_word_position, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()

    print(f"  Imported {total_alignments} word alignments for {translation_id}")
    return total_alignments


def show_sample(conn, book, chapter, verse, translation_id):
    """Show sample alignment data for debugging."""
    print(f"\n=== Sample: {book} {chapter}:{verse} ({translation_id}) ===")

    # Get the verse text
    text = conn.execute("""
        SELECT text FROM verses
        WHERE book = ? AND chapter = ? AND verse = ? AND translation_id = ?
    """, (book, chapter, verse, translation_id)).fetchone()

    if text:
        print(f"Text: {text[0]}")

    # Get alignments
    alignments = conn.execute("""
        SELECT ea.english_word_position, ea.english_word,
               wa.word_position, wa.hebrew_text, wa.english_gloss, wa.strong_number
        FROM english_word_alignments ea
        JOIN word_alignments wa ON (
            wa.book = ea.book AND wa.chapter = ea.chapter
            AND wa.verse = ea.verse AND wa.word_position = ea.original_word_position
        )
        WHERE ea.book = ? AND ea.chapter = ? AND ea.verse = ? AND ea.translation_id = ?
        ORDER BY ea.english_word_position
    """, (book, chapter, verse, translation_id)).fetchall()

    print(f"\nAlignments ({len(alignments)} words):")
    for eng_pos, eng_word, orig_pos, orig_text, gloss, strong in alignments:
        print(f"  {eng_pos:2d}: '{eng_word:12s}' -> #{orig_pos} {orig_text or ''} ({gloss or ''}) [{strong or ''}]")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Build English word alignments')
    parser.add_argument('--translation', default='KJV', help='Translation to process')
    parser.add_argument('--book', help='Process only this book')
    parser.add_argument('--limit', type=int, help='Limit number of verses (for testing)')
    parser.add_argument('--all', action='store_true', help='Process all translations')
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)

    # Create table
    create_english_alignments_table(conn)

    if args.all:
        # Get all translations
        translations = conn.execute("SELECT id FROM translations").fetchall()
        for (trans_id,) in translations:
            build_alignments_for_translation(conn, trans_id, args.book, args.limit)
    else:
        build_alignments_for_translation(conn, args.translation, args.book, args.limit)

    # Show sample
    show_sample(conn, 'Genesis', 1, 1, args.translation)
    show_sample(conn, 'Genesis', 1, 2, args.translation)

    # Show stats
    stats = conn.execute("""
        SELECT translation_id, COUNT(*)
        FROM english_word_alignments
        GROUP BY translation_id
    """).fetchall()

    print("\n=== Statistics ===")
    for trans_id, count in stats:
        print(f"  {trans_id}: {count:,} word alignments")

    conn.close()


if __name__ == '__main__':
    main()
