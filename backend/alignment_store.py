"""Packed storage for English-to-source word alignments: one row per verse.

Table `english_alignment_verses` replaces the one-row-per-word
`english_word_alignments` (2.2M rows, ~88 MB with its key) with one row per
verse and translation (~93K rows). docs/ALIGNMENT_2026-11.md, "Storage".

    links    comma-separated entries, entry i = tappable word i of the verse
             (1-based, the UI positions contract in scripts/aligner/text.py);
             trailing unlinked words are omitted, an unlinked word is ''.
    entry    'O'      link to word_alignments.word_position O, confidence 1.0,
                      method = the row's `method`
             'O:C'    confidence C/1000, method = the row's `method`
             'O:C:M'  confidence C/1000, method M
    method   the most common method in the verse (0 human alignment,
             1 Strong's tag, 2 aligner)
    n_links  number of linked words (for stats without unpacking)

The English word itself is not stored: it is the tappable word at that
position in `verses.text`, which the build checks for every link. Confidence
was already stored rounded to 3 decimals, so C/1000 is the identical float.
"""
import re
from collections import Counter
from functools import lru_cache

TABLE = "english_alignment_verses"
LEGACY_TABLE = "english_word_alignments"

TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    translation_id TEXT NOT NULL,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    method INTEGER NOT NULL,     -- default method for entries that omit it
    n_links INTEGER NOT NULL,    -- linked words in this verse
    links TEXT NOT NULL,         -- see module docstring
    PRIMARY KEY (translation_id, book, chapter, verse)
) WITHOUT ROWID
"""

# Must equal scripts/aligner/text.py TAPPABLE_WORD_RE and formatVerseText() in
# frontend/static/js/app.js (tests/test_alignment_store.py checks the former).
TAPPABLE_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:['’-][A-Za-zÀ-ÖØ-öø-ÿ]+)*")


def tappable_words(text: str) -> list[str]:
    return TAPPABLE_WORD_RE.findall(text or "")


def conf_milli(conf: float) -> int:
    """Calibrated confidence -> integer thousandths (the stored precision)."""
    return round(round(conf, 3) * 1000)


def pack(links) -> tuple[int, int, str]:
    """[(english_pos, original_pos, confidence, method)] of one verse -> (method, n_links, links)."""
    links = sorted(links)
    if not links:
        return 0, 0, ""
    default = Counter(m for *_, m in links).most_common(1)[0][0]
    by_pos = {}
    for epos, opos, conf, method in links:
        if epos < 1 or epos in by_pos:
            raise ValueError(f"bad or duplicate english position {epos}")
        k = conf_milli(conf)
        if method != default:
            by_pos[epos] = f"{opos}:{k}:{method}"
        elif k != 1000:
            by_pos[epos] = f"{opos}:{k}"
        else:
            by_pos[epos] = str(opos)
    last = max(by_pos)
    return default, len(by_pos), ",".join(by_pos.get(p, "") for p in range(1, last + 1))


def unpack(method: int, links: str) -> list[tuple[int, int, float, int]]:
    """Inverse of pack: [(english_pos, original_pos, confidence, method)] in english order."""
    out = []
    if not links:
        return out
    for epos, entry in enumerate(links.split(","), 1):
        if not entry:
            continue
        parts = entry.split(":")
        out.append((epos, int(parts[0]),
                    int(parts[1]) / 1000 if len(parts) > 1 else 1.0,
                    int(parts[2]) if len(parts) > 2 else method))
    return out


def link_at(method: int, links: str, english_pos: int):
    """(original_pos, confidence, method) of one English word, or None. No full unpack."""
    if english_pos < 1 or not links:
        return None
    entries = links.split(",")
    if english_pos > len(entries) or not entries[english_pos - 1]:
        return None
    parts = entries[english_pos - 1].split(":")
    return (int(parts[0]),
            int(parts[1]) / 1000 if len(parts) > 1 else 1.0,
            int(parts[2]) if len(parts) > 2 else method)


def ensure_table(conn) -> None:
    conn.execute(TABLE_SQL)


def has_packed(conn) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                        (TABLE,)).fetchone() is not None


def write_verse_rows(conn, translation: str, verse_links) -> int:
    """Replace one translation. verse_links: {(book, chapter, verse): [(epos, opos, conf, method)]}."""
    ensure_table(conn)
    conn.execute(f"DELETE FROM {TABLE} WHERE translation_id = ?", (translation,))
    rows = []
    for (book, ch, v), links in verse_links.items():
        method, n, text = pack(links)
        if n:
            rows.append((translation, book, ch, v, method, n, text))
    conn.executemany(f"INSERT INTO {TABLE} VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    return sum(r[5] for r in rows)


# --- which links count as a rendering -------------------------------------------------
# docs/ALIGNMENT_2026-11.md, "One threshold or two?": show content-word links at >= 0.5 and
# function-word links at >= 0.7. Function words are the aligner's word classes
# (scripts/aligner/rerank.py WORD_CLASS; tests/test_alignment_store.py keeps them equal),
# tested on the aligner's normalized form ('thee' -> 'you', 'hath' -> 'have').
CONTENT_MIN_CONFIDENCE = 0.5
FUNCTION_MIN_CONFIDENCE = 0.7
FUNCTION_WORDS = frozenset(
    "the a of to and in for with from on by at that which who this not be there as so "
    "then but if when all or no what these those into upon "
    "i you he she it we they will shall may have do can would should might must let".split())


@lru_cache(maxsize=65536)
def is_function_word(word: str) -> bool:
    from scripts.aligner.text import normalize  # stdlib-only module, shipped in the image
    return normalize(word) in FUNCTION_WORDS


def rendering_link_ok(word: str, confidence: float) -> bool:
    return confidence >= (FUNCTION_MIN_CONFIDENCE if is_function_word(word)
                          else CONTENT_MIN_CONFIDENCE)
