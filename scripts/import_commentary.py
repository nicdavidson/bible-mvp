#!/usr/bin/env python3
"""
Import commentaries into commentary_entries and describe them in commentary_sources.

Sources and their metadata live in scripts/commentary_registry.py. Loaders:
    helloao  HelloAO Free Use Bible API JSON (https://bible.helloao.org/api/c/...)
    sword    CrossWire SWORD module zip (OSIS or ThML), read by scripts/sword_reader.py
    tdavid   Treasury of David SWORD module, split into Spurgeon's per-verse exposition
    tyndale  Tyndale Open Study Notes XML (tyndaleopenresources.com zip)

All downloads go through scripts/source_cache.py (data/sources/), so a rebuild is offline
once the cache is warm. Each run deletes and rewrites the rows for its source, so it is
idempotent. Text is stored the same way for every source (see scripts/commentary_text.py).

Usage:
    python scripts/import_commentary.py <key> [<key> ...]
    python scripts/import_commentary.py --all
    python scripts/import_commentary.py --list
"""
from __future__ import annotations

import io
import os
import re
import sqlite3
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from commentary_registry import COMMENTARIES, CW_RAWZIP, HELLOAO, SOURCE_COLUMNS  # noqa: E402
from commentary_text import (  # noqa: E402
    RefResolver, markup_to_text, plain_to_text, render, resolve_book,
)
from source_cache import cached_fetch_bytes, cached_fetch_json, is_cached  # noqa: E402
from sword_reader import SwordModule, kjv_versification  # noqa: E402

DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", Path(__file__).parent.parent / "data" / "bible.db"))

# HelloAO 3-letter book ids
HELLOAO_BOOKS = {
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
    "2JN": "2 John", "3JN": "3 John", "JUD": "Jude", "REV": "Revelation",
}


class Stats(dict):
    def bump(self, key, n=1):
        self[key] = self.get(key, 0) + n


# ---------------------------------------------------------------------------
# Loaders: each yields (book, chapter, verse_start, verse_end, text_with_placeholders)
# ---------------------------------------------------------------------------

def load_helloao(cfg, v11n, stats):
    cid = cfg["helloao_id"]
    base = HELLOAO.format(id=cid)
    books = cached_fetch_json(f"commentary-{cid}/books.json", f"{base}/books.json")
    if not books:
        raise RuntimeError("could not fetch HelloAO book list")
    for info in books.get("books", []):
        book = HELLOAO_BOOKS.get(info["id"])
        if not book:
            stats.bump("unknown_book")
            continue
        for ch in range(1, info.get("numberOfChapters", 0) + 1):
            key = f"commentary-{cid}/{info['id']}/{ch}.json"
            fresh = not is_cached(key)
            data = cached_fetch_json(key, f"{base}/{info['id']}/{ch}.json")
            if fresh:
                time.sleep(0.3)  # be polite to the API on network fetches only
            if not data:
                stats.bump("chapter_fetch_failed")
                continue
            chapter = data.get("chapter", {})
            items = []
            for item in chapter.get("content", []):
                if item.get("type") != "verse" or not item.get("content"):
                    continue
                num = str(item.get("number"))
                parts = [p for p in item["content"] if isinstance(p, str)]
                if len(parts) != len(item["content"]):
                    stats.bump("non_text_parts_dropped")
                if "-" in num:
                    a, b = num.split("-", 1)
                    start, end = int(a), int(b)
                else:
                    start = end = int(num)
                items.append([start, end, "\n\n".join(parts)])
            # HelloAO's chapter "introduction" is either a chapter outline or, when the
            # chapter has no verse-1 item, the verse-1 note itself (JFB). Prepend it to the
            # verse-1 entry, or make it the verse-1 entry.
            intro = chapter.get("introduction")
            intro = intro if isinstance(intro, str) else ""
            intro = re.sub(r"^\s*(?:[1-3] )?[A-Z][A-Za-z ]+ \d+:\d+(?:-\d+)?\s*\n", "", intro).strip()
            if intro:
                first = min(items, key=lambda x: x[0]) if items else None
                if first and first[0] == 1:
                    first[2] = intro + "\n\n" + first[2]
                    stats.bump("chapter_intros_prepended")
                else:
                    items.append([1, 1, intro])
                    stats.bump("chapter_intros_as_verse_1")
            for start, end, text in sorted(items, key=lambda x: x[0]):
                yield book, ch, start, end, plain_to_text(text)


def _sword_module(name) -> SwordModule:
    key = f"crosswire/{name}.zip"
    if cached_fetch_bytes(key, CW_RAWZIP.format(module=name)) is None:
        raise RuntimeError(f"could not download CrossWire module {name}")
    from source_cache import SOURCES_DIR
    return SwordModule(SOURCES_DIR / key)


def load_sword(cfg, v11n, stats):
    mod = _sword_module(cfg["module"])
    for e in mod.entries(v11n):
        yield e.book, e.chapter, e.verse_start, e.verse_end, markup_to_text(e.raw)


_TD_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.S)
_TD_VERSE = re.compile(
    r'<hi type="bold">\s*(?:Verses?|Ver\.)\s*(\d+)(?:\s*(?:-|–|,|to|and)\s*(\d+))*\.?\s*</hi>'
)


def load_tdavid(cfg, v11n, stats):
    """Treasury of David: one SWORD entry per psalm. Keep Spurgeon's overview and his
    EXPOSITION split at its "Verse N." markers; drop the collected quotations
    ("Explanatory Notes and Quaint Sayings") and "Hints to Preachers"."""
    mod = _sword_module(cfg["module"])
    for e in mod.entries(v11n):
        psalm = e.chapter
        nverses = v11n["Psalms"][psalm - 1]
        titles = list(_TD_TITLE.finditer(e.raw))
        # segments: (title, body)
        segs = []
        prev_end, prev_title = 0, ""
        for m in titles:
            segs.append((prev_title, e.raw[prev_end:m.start()]))
            prev_title, prev_end = re.sub(r"<[^>]+>", "", m.group(1)).strip(), m.end()
        segs.append((prev_title, e.raw[prev_end:]))

        overview, expositions, dropped = [], [], 0
        seen_expo = False
        for title, body in segs:
            t = title.upper()
            if t.startswith("EXPOSITION"):
                seen_expo = True
                expositions.append(body)
            elif "NOTES" in t or "HINTS" in t or "QUAINT" in t:
                dropped += len(body)
            elif not seen_expo:
                overview.append(body)
            else:
                dropped += len(body)
        stats.bump("quotations_and_hints_bytes_dropped", dropped)

        ov = markup_to_text(" <p/> ".join(overview))
        if ov:
            yield "Psalms", psalm, 1, nverses, ov
        for body in expositions:
            marks = list(_TD_VERSE.finditer(body))
            if not marks:
                txt = markup_to_text(body)
                if txt:
                    stats.bump("expositions_without_verse_marks")
                    yield "Psalms", psalm, 1, nverses, txt
                continue
            lead = markup_to_text(body[:marks[0].start()])
            for i, m in enumerate(marks):
                start = int(m.group(1))
                nums = [int(n) for n in re.findall(r"\d+", m.group(0))]
                end = max(nums)
                chunk = body[m.start():marks[i + 1].start() if i + 1 < len(marks) else len(body)]
                txt = markup_to_text(chunk)
                if i == 0 and lead:
                    txt = lead + "\n\n" + txt
                yield "Psalms", psalm, start, end, txt


_TY_ITEM = re.compile(r'<item name="([^"]*)" typename="StudyNote"[^>]*>.*?<refs>(.*?)</refs>\s*<body>(.*?)</body>', re.S)
_TY_LINK = re.compile(r'<a href="\?bref=([^"]*)">(.*?)</a>', re.S)
_TY_REF = re.compile(r"^([1-3]?[A-Za-z]+)\.(\d+)(?:\.(\d+))?(?:-(?:(\d+)\.)?(\d+))?$")


def load_tyndale(cfg, v11n, stats):
    data = cached_fetch_bytes("tyndale/tyndale_open-studynotes.zip", cfg["url"])
    if data is None:
        raise RuntimeError("could not download Tyndale Open Study Notes")
    zf = zipfile.ZipFile(io.BytesIO(data))
    name = next(n for n in zf.namelist() if n.endswith("StudyNotes.xml"))
    xml = zf.read(name).decode("utf-8")
    for m in _TY_ITEM.finditer(xml):
        ref = m.group(2).strip().split(";")[0].split(",")[0]
        rm = _TY_REF.match(ref)
        book = resolve_book(rm.group(1)) if rm else None
        if not book:
            stats.bump("unparsed_refs")
            continue
        ch = int(rm.group(2))
        start = int(rm.group(3) or 1)
        ch2 = int(rm.group(4)) if rm.group(4) else ch
        v2 = rm.group(5)
        chapters = v11n[book]
        if rm.group(3) is None:  # chapter-only note
            spans = [(ch, 1, chapters[ch - 1] if ch <= len(chapters) else 1)]
        elif v2 is None:
            spans = [(ch, start, start)]
        elif ch2 == ch:
            spans = [(ch, start, int(v2))]
        else:
            # A note on a group of chapters ("Pss 23-28"): attach it to every chapter it
            # covers, with the verses covered in each, instead of only the first chapter.
            ch2 = min(ch2, len(chapters))
            spans = [(c, start if c == ch else 1, int(v2) if c == ch2 else chapters[c - 1])
                     for c in range(ch, ch2 + 1)]
            stats.bump("multi_chapter_notes")
            stats.bump("multi_chapter_note_rows_added", len(spans) - 1)
        body = _TY_LINK.sub(r'<reference osisRef="\1">\2</reference>', m.group(3))
        text = markup_to_text(body)
        for c, a, b in spans:
            yield book, c, a, b, text


LOADERS = {"helloao": load_helloao, "sword": load_sword, "tdavid": load_tdavid,
           "tyndale": load_tyndale}


# ---------------------------------------------------------------------------
# Post-processing, validation and writing
# ---------------------------------------------------------------------------

# Lines that are page navigation or edition labels from the digitizers, not commentary:
# HelloAO JFB "Next: Genesis Chapter 2", "See Chapter Introduction". ("Unabridged" and
# "End of Barnes Notes on ..." came from sources removed in 2026-11; harmless to keep.)
_DEBRIS_LINE = re.compile(
    r"(?m)^[ \t]*(?:Next: [^\n]{1,60}?(?:Chapter \d+|Introduction)|Previous: [^\n]{1,60}"
    r"|Unabridged|End of Barnes(?:'|’)? Notes on [^\n]{1,40}|See Chapter Introduction)[ \t]*\.?[ \t]*$\n?")


def strip_debris(rows, stats):
    out = []
    for b, c, s, e, t in rows:
        t2 = _DEBRIS_LINE.sub("", t)
        if t2 != t:
            stats.bump("navigation_lines_removed", len(_DEBRIS_LINE.findall(t)))
            t2 = re.sub(r"\n{3,}", "\n\n", t2).strip()
        out.append((b, c, s, e, t2))
    return out


def validate(rows, v11n, stats):
    out = []
    for book, ch, s, e, t in rows:
        if not t or len(t.strip()) < 2:
            stats.bump("empty_dropped")
            continue
        chapters = v11n.get(book)
        if not chapters or ch < 1 or ch > len(chapters):
            stats.bump("bad_chapter_dropped")
            continue
        maxv = chapters[ch - 1]
        if s < 1 or s > maxv:
            stats.bump("bad_verse_dropped")
            continue
        if e is None or e < s:
            e = s
        if e > maxv:
            stats.bump("end_clamped")
            e = maxv
        out.append((book, ch, s, e, t))
    return out


def write_source_row(conn, cfg):
    """Metadata row from the registry, plus size_bytes measured from the rows just written."""
    size = conn.execute(
        "SELECT COALESCE(SUM(LENGTH(CAST(content AS BLOB))), 0) FROM commentary_entries "
        "WHERE source = ?", (cfg["source"],)).fetchone()[0]
    values = {**cfg, "size_bytes": size}
    cols = ", ".join(SOURCE_COLUMNS)
    marks = ", ".join("?" for _ in SOURCE_COLUMNS)
    conn.execute(f"INSERT OR REPLACE INTO commentary_sources ({cols}) VALUES ({marks})",
                 [values[c] for c in SOURCE_COLUMNS])


def ensure_schema(conn):
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from backend import commentary_search
    from backend.database import _migrate_commentary_sources
    commentary_search.register(conn)   # the FTS triggers derive the indexed text
    _migrate_commentary_sources(conn)


def import_commentary(key: str):
    cfg = COMMENTARIES[key]
    source = cfg["source"]
    print(f"\n{'=' * 60}\nImporting {source} ({key}, loader={cfg['loader']})\n{'=' * 60}")
    conn = sqlite3.connect(DATABASE_PATH)
    ensure_schema(conn)
    v11n = kjv_versification(conn)
    resolver = RefResolver(v11n)
    stats = Stats()
    t0 = time.time()

    rows = list(LOADERS[cfg["loader"]](cfg, v11n, stats))
    rows = strip_debris(rows, stats)
    rows = validate(rows, v11n, stats)
    if not rows:
        raise RuntimeError(f"{source}: no entries produced")

    from backend.commentary_search import override_for
    conn.execute("DELETE FROM commentary_entries WHERE source = ?", (source,))
    links = 0
    for book, ch, s, e, text in rows:
        content, searchable, n = render(text, resolver)
        links += n
        # The search text is derived from content (backend/commentary_search.py); store
        # it only where the derivation would differ, so FTS indexes the same text.
        conn.execute(
            "INSERT INTO commentary_entries (source, book, chapter, reference_start, "
            "reference_end, content, search_override) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (source, book, ch, s, e, content, override_for(content, searchable)),
        )
    write_source_row(conn, cfg)
    conn.commit()
    # Merge FTS segments and drop delete markers left by the DELETE/INSERT above; without
    # this, repeated rebuilds bloated commentary_fts_data to 3x its size (309 MB vs 93 MB).
    conn.execute("INSERT INTO commentary_fts(commentary_fts) VALUES('optimize')")
    conn.commit()
    books = len({r[0] for r in rows})
    conn.close()
    print(f"  books: {books}  links: {links}  time: {time.time() - t0:.0f}s")
    for k, v in sorted(stats.items()):
        if not k.startswith("_"):
            print(f"  {k}: {v}")
    print(f"Imported {len(rows)} entries")
    return len(rows)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 1
    if argv[0] == "--list":
        for k, c in COMMENTARIES.items():
            print(f"  {k:24} {c['source']:26} {c['loader']:8} {c['coverage']}")
        return 0
    keys = list(COMMENTARIES) if argv[0] == "--all" else argv
    for k in keys:
        if k not in COMMENTARIES:
            print(f"Unknown commentary '{k}'. Use --list.")
            return 1
    for k in keys:
        import_commentary(k)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
