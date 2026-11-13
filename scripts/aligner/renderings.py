"""lemma_renderings: how each translation renders each Hebrew/Greek lemma.

One row per (lemma, translation, rendering) with a count. A rendering is the
English words of one verse that are linked to the same source word, in English
order, lowercased ('in the beginning', 'beginning'); words that are not
adjacent are joined with ' … '. Only links at or above a confidence threshold
are counted. Occurrences are listed on demand by
GET /api/word/{strong}/renderings (backend/routers/words.py), which joins
english_word_alignments to word_alignments with the same grouping rule.
"""
from collections import Counter, defaultdict

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS lemma_renderings (
    strong_number TEXT NOT NULL,     -- lexicon format: 'H430', 'G26'
    translation_id TEXT NOT NULL,
    rendering TEXT NOT NULL,
    count INTEGER NOT NULL,
    PRIMARY KEY (strong_number, translation_id, rendering)
) WITHOUT ROWID
"""


def unpad(strong: str) -> str:
    """'H0430' -> 'H430' (lexicon format)."""
    if strong and strong[1:].isdigit():
        return strong[0] + str(int(strong[1:]))
    return strong


def group_rendering(words) -> str:
    """[(english_position, word)] linked to one source word -> rendering text."""
    words = sorted(words)
    out = words[0][1]
    for (p0, _), (p1, w) in zip(words, words[1:]):
        out += (" " if p1 == p0 + 1 else " … ") + w
    return out.lower()


def build_renderings(conn, min_confidence: float) -> int:
    conn.execute(TABLE_SQL)
    conn.execute("DELETE FROM lemma_renderings")
    counts = Counter()
    cur = conn.execute("""
        SELECT e.translation_id, e.book, e.chapter, e.verse, e.original_word_position,
               e.english_word_position, e.english_word, w.strong_number
        FROM english_word_alignments e
        JOIN word_alignments w ON w.book = e.book AND w.chapter = e.chapter
             AND w.verse = e.verse AND w.word_position = e.original_word_position
        WHERE e.confidence >= ? AND w.strong_number IS NOT NULL
        ORDER BY e.translation_id, e.book, e.chapter, e.verse
    """, (min_confidence,))
    verse_key, groups = None, defaultdict(list)

    def flush():
        for (strong, _opos, tr), ws in groups.items():
            counts[(unpad(strong), tr, group_rendering(ws))] += 1
        groups.clear()

    for tr, book, ch, v, opos, epos, word, strong in cur:
        if (tr, book, ch, v) != verse_key:
            flush()
            verse_key = (tr, book, ch, v)
        groups[(strong, opos, tr)].append((epos, word))
    flush()
    conn.executemany("INSERT INTO lemma_renderings VALUES (?, ?, ?, ?)",
                     [(s, tr, r, n) for (s, tr, r), n in counts.items()])
    conn.commit()
    return len(counts)
