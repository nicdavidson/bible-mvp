"""lemma_renderings: how each translation renders each Hebrew/Greek lemma.

One row per (lemma, translation, rendering) with a count. A rendering is the
English words of one verse that are linked to the same source word, in English
order, lowercased, with leading and trailing function words trimmed
('his mercy' -> 'mercy'); words that are not adjacent are joined with ' … '. Only links
the reader would be shown are counted: content words at confidence >= 0.5, function
words at >= 0.7 (backend.alignment_store.rendering_link_ok). Occurrences are listed on demand by
GET /api/word/{strong}/renderings (backend/routers/words.py), which unpacks
english_alignment_verses (backend/alignment_store.py) with the same grouping rule.
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


# Leading/trailing words dropped from a rendering so 'his mercy', 'the love',
# 'and mercy' count as 'mercy' / 'love' (kept when nothing else is left).
RENDERING_STRIP = frozenset(
    "a an the and or but of to in into on at by for from with unto upon his her its their "
    "my your our thy thine thee thou him them me us you he she it they we i is are was were "
    "be been shall will let so then also even according o".split())


def group_rendering(words) -> str:
    """[(english_position, word)] linked to one source word -> rendering text."""
    words = sorted((p, w.lower()) for p, w in words)
    while len(words) > 1 and words[0][1] in RENDERING_STRIP:
        words = words[1:]
    while len(words) > 1 and words[-1][1] in RENDERING_STRIP:
        words = words[:-1]
    out = words[0][1]
    for (p0, _), (p1, w) in zip(words, words[1:]):
        out += (" " if p1 == p0 + 1 else " … ") + w
    return out


def build_renderings(conn, min_confidence: float = 0.5) -> int:
    """`min_confidence` is kept for callers; the rule is alignment_store.rendering_link_ok."""
    from backend import alignment_store as store  # project root is on sys.path (pipeline.py)

    conn.execute(TABLE_SQL)
    conn.execute("DELETE FROM lemma_renderings")
    counts = Counter()
    strongs = {(b, c, v, p): s for b, c, v, p, s in conn.execute(
        "SELECT book, chapter, verse, word_position, strong_number FROM word_alignments "
        "WHERE strong_number IS NOT NULL")}
    cur = conn.execute(f"""
        SELECT p.translation_id, p.book, p.chapter, p.verse, p.method, p.links, v.text
        FROM {store.TABLE} p
        JOIN verses v ON v.translation_id = p.translation_id AND v.book = p.book
             AND v.chapter = p.chapter AND v.verse = p.verse
    """)
    for tr, book, ch, v, method, links, text in cur:
        words = store.tappable_words(text)
        groups = defaultdict(list)
        for epos, opos, conf, _ in store.unpack(method, links):
            strong = strongs.get((book, ch, v, opos))
            if strong is not None and store.rendering_link_ok(words[epos - 1], conf):
                groups[(strong, opos)].append((epos, words[epos - 1]))
        for (strong, _opos), ws in groups.items():
            counts[(unpad(strong), tr, group_rendering(ws))] += 1
    conn.executemany("INSERT INTO lemma_renderings VALUES (?, ?, ?, ?)",
                     [(s, tr, r, n) for (s, tr, r), n in counts.items()])
    conn.commit()
    return len(counts)
