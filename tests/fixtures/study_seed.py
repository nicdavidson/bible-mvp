"""DEV/TEST ONLY: synthetic commentary sources for the study view.

Never run this against a production database. It adds a `commentary_sources`
table (the schema the commentary-import agent is adding) and ten fictional
sources with entries on one chapter, covering every `kind`, very long entries,
sources with nothing on John 3:16, and a source with nothing in the chapter.
All synthetic rows are marked "(dev sample)" in their description.

    # seed your own *copy* of the DB (refuses paths outside the worktree data dir)
    .venv/bin/python -m tests.fixtures.study_seed data/bible.db

    # undo
    .venv/bin/python -m tests.fixtures.study_seed data/bible.db --remove
"""
import sqlite3
import sys
from pathlib import Path

DEV_TAG = "(dev sample)"

SOURCES_DDL = """
CREATE TABLE IF NOT EXISTS commentary_sources (
    source TEXT PRIMARY KEY,
    short_name TEXT,
    author TEXT,
    year TEXT,
    tradition TEXT,
    kind TEXT,
    coverage TEXT,
    license TEXT,
    attribution TEXT,
    source_url TEXT,
    sort_order INTEGER,
    description TEXT
)
"""

# (source, short, author, year, tradition, kind, coverage, license, attribution, url, sort)
SYNTHETIC = [
    ("Whitcombe's Verse Notes", "Whitcombe", "Elias Whitcombe", "1789", "Methodist", "verse",
     "Whole Bible", "Public domain", None, None, 30),
    ("Harrow Passage Commentary", "Harrow", "Margaret Harrow", "1872", "Anglican", "passage",
     "New Testament", "Public domain", None, None, 40),
    ("Lindqvist Chapter Studies", "Lindqvist", "Anders Lindqvist", "1931", "Lutheran", "chapter",
     "Gospels", "Public domain", None, None, 50),
    ("Okafor Study Notes", "Okafor", "Grace Okafor", "2004", "Evangelical", "notes",
     "Whole Bible", "CC BY 4.0", "Okafor Study Notes by Grace Okafor, CC BY 4.0",
     "https://example.org/okafor-notes", 60),
    ("Pell's Expositor", "Pell", "Josiah Pell", "1850", "Reformed", "passage",
     "John 1-3 only", "Public domain", None, None, 70),
    ("Marrow Sermon Outlines", "Marrow", "Thomas Marrow", "1698", "Puritan", "passage",
     "Selected chapters", "Public domain", None, None, 80),
    ("Calloway Word Notes", "Calloway", "Ruth Calloway", "1911", "Holiness", "verse",
     "New Testament", "Public domain", None, None, 90),
    ("Dunmore Devotional Readings", "Dunmore", "Isaac Dunmore", "1902", "Baptist", "chapter",
     "Whole Bible", "Public domain", None, None, 100),
    ("Ferreira Greek Notes", "Ferreira", "Paulo Ferreira", "2015", "Catholic", "verse",
     "New Testament", "CC BY-SA 4.0", "Ferreira Greek Notes, CC BY-SA 4.0, via example.org",
     "https://example.org/ferreira", 110),
    ("Thistle Bible Handbook", "Thistle", "Anne Thistle", "1960", "Presbyterian", "chapter",
     "Whole Bible", "Public domain", None, None, 120),
]

REAL = [
    ("John Gill", 10), ("Matthew Henry", 20),
]

SENTENCES = [
    "The words are plain, yet they reward slow reading.",
    "Observe how the clause turns on a single verb.",
    "Here the evangelist gathers up what was said before.",
    "Some have pressed this too far; the context restrains them.",
    "It is the same word used of the wind a few verses earlier.",
    "The reader should not hurry past the small connecting word.",
    "This is love not in sentiment but in a gift given.",
    "The older interpreters saw in this a summary of the whole gospel.",
]


def _para(i: int, n: int = 4) -> str:
    return " ".join(SENTENCES[(i + k) % len(SENTENCES)] for k in range(n))


def _ref(book, ch, v):
    abbr = book[:3]
    return f'<a href="#" class="commentary-ref" data-ref="{book} {ch}:{v}">{abbr} {ch}:{v}</a>'


def _outline_entry(book, ch, start, end, paras_per_verse=2, mention_every=1):
    """A long outline-style entry (I. / 1. / (1.) / [1.]) citing verses in turn."""
    out = [f"An exposition of {book} {ch}:{start}-{end}. {_para(start, 3)}"]
    roman = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
    head = 0
    for v in range(start, end + 1):
        if (v - start) % 4 == 0 and head < len(roman):
            out.append(f"{roman[head]}. Concerning verses {v} and following. {_para(v, 2)}")
            head += 1
        cite = f" ({_ref(book, ch, v)})" if (v - start) % mention_every == 0 else ""
        out.append(f"{(v - start) % 4 + 1}. On verse {v}{cite}. {_para(v, 5)}")
        for k in range(paras_per_verse - 1):
            out.append(f"({k + 1}.) {_para(v + k + 1, 6)}")
        if v % 3 == 0:
            out.append(f"[1.] A further note: {_para(v + 3, 7)}")
    return "\n".join(out)


def synthetic_entries(book: str, ch: int, last: int):
    """Yield (source, start, end, content) rows for one chapter."""
    # verse-by-verse, every verse
    for v in range(1, last + 1):
        yield ("Whitcombe's Verse Notes", v, v, f"{_para(v, 3)}\n{_para(v + 2, 2)}")
    # passage with explicit ranges, three sections (long)
    thirds = [(1, last // 3), (last // 3 + 1, 2 * last // 3), (2 * last // 3 + 1, last)]
    for s, e in thirds:
        yield ("Harrow Passage Commentary", s, e, _outline_entry(book, ch, s, e, 2, 2))
    # one very long chapter entry (~60k chars)
    yield ("Lindqvist Chapter Studies", 1, last, _outline_entry(book, ch, 1, last, 6, 3))
    # sparse notes
    for v in (3, 5, max(1, last // 2 - 2), last - 6):
        yield ("Okafor Study Notes", v, v, f"<em>Note.</em> {_para(v, 2)}")
    # passage source that stops early: nothing on the second half
    yield ("Pell's Expositor", 1, min(12, last), _outline_entry(book, ch, 1, min(12, last), 1, 1))
    # Marrow: only Romans, so it has nothing at all in John
    if book == "Romans":
        yield ("Marrow Sermon Outlines", 1, None, _outline_entry(book, ch, 1, last, 1, 4))
    # verse source with a gap in the middle
    for v in list(range(1, 11)) + list(range(25, last + 1)):
        if v <= last:
            yield ("Calloway Word Notes", v, v, _para(v, 2))
    yield ("Dunmore Devotional Readings", 1, last,
           "\n".join(_para(i, 5) for i in range(14)))
    for v in range(max(1, last // 2 - 3), min(last, last // 2 + 1) + 1):
        yield ("Ferreira Greek Notes", v, v,
               f"The Greek here repays attention. {_para(v, 3)} Compare {_ref(book, ch, max(1, v - 1))}.")
    yield ("Thistle Bible Handbook", 1, last,
           f"{book} {ch} at a glance. {_para(1, 3)}\nKey verse: {_ref(book, ch, last // 2 - 2)}. {_para(2, 2)}")


def seed(conn: sqlite3.Connection, chapters=(("John", 3), ("Romans", 8))) -> None:
    conn.execute(SOURCES_DDL)
    for src, short, author, year, trad, kind, cov, lic, attr, url, sort in SYNTHETIC:
        conn.execute(
            "INSERT OR REPLACE INTO commentary_sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (src, short, author, year, trad, kind, cov, lic, attr, url, sort,
             f"A fictional {kind}-level commentary for testing the study view {DEV_TAG}."))
    for src, sort in REAL:
        conn.execute("INSERT OR IGNORE INTO commentary_sources (source, sort_order) VALUES (?, ?)",
                     (src, sort))
    names = [s[0] for s in SYNTHETIC]
    conn.execute(f"DELETE FROM commentary_entries WHERE source IN ({','.join('?' * len(names))})", names)
    for book, ch in chapters:
        last = conn.execute("SELECT MAX(verse) FROM verses WHERE book=? AND chapter=?",
                            (book, ch)).fetchone()[0]
        if not last:
            continue
        for src, s, e, content in synthetic_entries(book, ch, last):
            plain = content.replace("<", " <")
            conn.execute(
                "INSERT INTO commentary_entries (source, book, chapter, reference_start, reference_end,"
                " content, searchable_text) VALUES (?,?,?,?,?,?,?)",
                (src, book, ch, s, e, content, plain))
    conn.commit()


def remove(conn: sqlite3.Connection) -> None:
    names = [s[0] for s in SYNTHETIC]
    conn.execute(f"DELETE FROM commentary_entries WHERE source IN ({','.join('?' * len(names))})", names)
    conn.execute("DROP TABLE IF EXISTS commentary_sources")
    conn.commit()


if __name__ == "__main__":
    db = Path(sys.argv[1]).resolve()
    worktree_data = (Path(__file__).resolve().parents[2] / "data").resolve()
    if db.parent != worktree_data:
        sys.exit(f"refusing: {db} is not this worktree's data/ copy")
    c = sqlite3.connect(db)
    if "--remove" in sys.argv:
        remove(c)
        print("removed synthetic sources")
    else:
        seed(c)
        print("seeded", len(SYNTHETIC), "synthetic sources")
