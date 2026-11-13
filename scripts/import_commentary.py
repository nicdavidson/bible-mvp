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
from sword_reader import OSIS_BOOKS, SwordModule, kjv_versification  # noqa: E402

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

_CALVIN_HEAD = re.compile(r"^\s*(?:[1-3] )?[A-Z][A-Za-z ]+ (\d+):(\d+)(?:\s*[-–]\s*(?:(\d+):)?(\d+))?\s*$")
_CALVIN_NUM = re.compile(r"(?:^|\s)(\d{1,3})\.\s")


def clean_calvin(text: str, start: int) -> tuple[str, int | None, bool]:
    """HelloAO/CCEL Calvin section -> (commentary text, end verse from heading, text_skipped).

    A section is: "Book C:V-W" heading, the verse text (CTS English, plus Latin in the
    NT), Calvin's comments, then "Footnotes:" (translator's notes, dropped along with the
    [n] markers)."""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    end = None
    heading = paras and _CALVIN_HEAD.match(paras[0])
    if heading:
        m = heading
        end = int(m.group(4)) if m.group(4) and not m.group(3) else None
        if not m.group(4):
            end = int(m.group(2))  # single-verse heading
        paras = paras[1:]
    if "Footnotes:" in paras:
        paras = paras[:paras.index("Footnotes:")]
    lo, hi = start, end or start
    i = 0
    if heading and end:
        # Sections with a "Book C:V-W" heading print the verse text first: paragraphs
        # numbered lo..hi (English, and Latin in most volumes). Skip that leading run. The
        # commentary starts at the first unnumbered paragraph, or where the numbering
        # restarts after verse `hi` has appeared.
        seen_hi = 0
        limit = 2 * (hi - lo + 1) + 2
        for j, p in enumerate(paras):
            nums = [int(n) for n in _CALVIN_NUM.findall(" " + p[:2000])]
            lead = re.match(r"\s*(\d+)\.\s", p)
            n = int(lead.group(1)) if lead else None
            if j >= limit or n is None or not lo <= n <= hi:
                i = j
                break
            if seen_hi and (n < hi or seen_hi >= 2 or len(p) > 600):
                i = j
                break
            if n == hi or (len(nums) >= 2 and max(nums) >= hi):
                seen_hi += 1
        else:
            i = 0  # nothing but numbered paragraphs: keep everything
    body = "\n\n".join(paras[i:])
    body = re.sub(r"\s?\[\d+\]", "", body)
    return body, end, i > 0


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
                text = "\n\n".join(parts)
                if cfg.get("clean") == "calvin":
                    text, heading_end, skipped = clean_calvin(text, start)
                    if heading_end and heading_end > start:
                        end = heading_end
                    if skipped:
                        stats.bump("calvin_sections_verse_text_removed")
                items.append([start, end, text])
            # HelloAO's chapter "introduction" is either a chapter outline (Henry) or, when
            # the chapter has no verse-1 item, the verse-1 note itself (JFB). Prepend it to
            # the verse-1 entry, or make it the verse-1 entry.
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


_TITLE_OPEN = re.compile(r"<title\b")
_OSIS_ID = {name: osis for osis, name in OSIS_BOOKS}


def strip_book_intro(raw: str, book: str) -> tuple[str, int]:
    """Drop a book introduction stored in front of the first verse's commentary.

    SWORD modules have a slot for book introductions, but several (JFB, KD, Clarke,
    Barnes) put the introduction into the Gen 1:1-style first verse entry instead. Find
    where the verse commentary starts and cut at the last heading before it. Returns
    (raw, bytes_dropped). Leaves the entry alone if no start marker is found.
    """
    if len(raw) < 8000:
        return raw, 0
    osis = _OSIS_ID[book]
    markers = [
        re.compile(r'<title[^>]*>\s*CHAPTER\s+(?:1|I)\b\.?\s*</title>', re.I),
        re.compile(rf'<reference osisRef="{re.escape(osis)}\.1\.1\b'),
        re.compile(r'(?:^|<br\s*/?>|\n|>)\s*Verses?\s+1\b[.,:\s-]'),
    ]
    positions = [m.start() for rx in markers for m in [rx.search(raw)] if m]
    if not positions:
        return raw, 0
    pos = min(positions)
    titles = [m.start() for m in _TITLE_OPEN.finditer(raw, 0, pos + 1)]
    cut = titles[-1] if titles and pos - titles[-1] < 2000 else pos
    if cut < 3000:
        return raw, 0
    return raw[cut:], cut


def load_sword(cfg, v11n, stats, books: list[str] | None = None, module: str | None = None):
    mod = _sword_module(module or cfg["module"])
    for e in mod.entries(v11n):
        if books and e.book not in books:
            continue
        raw = e.raw
        if cfg.get("strip_book_intros") and e.chapter == 1 and e.verse_start == 1:
            raw, dropped = strip_book_intro(raw, e.book)
            if dropped:
                stats.bump("book_intro_bytes_dropped", dropped)
                stats.bump("book_intros_dropped")
        if cfg.get("fixup"):
            fixed = FIXUPS[cfg["fixup"]](e, raw, stats)
            if fixed is None:
                continue
            e, raw = fixed
        yield e.book, e.chapter, e.verse_start, e.verse_end, markup_to_text(raw)


_BARNES_FILLER = re.compile(
    r"(?:No specific Barnes text on this verse|No entry from BARNES for this verse)\.?", re.I)


def fixup_barnes(e, raw, stats):
    """CrossWire Barnes e-text quirks.

    - Matthew 1:1 and 1:2 hold the general preface and introduction to the Gospels, and
      the genealogy note ("Verses 2-16") sits in the 1:3 slot. Drop the first two and
      re-key the third to 1:2-16, as its own heading says.
    - "No specific Barnes text on this verse" placeholder slots: remove the placeholder,
      and drop the entry when only a lemma or bare references are left.
    """
    if e.book == "Matthew" and e.chapter == 1 and e.verse_start in (1, 2):
        stats.bump("barnes_gospel_preface_entries_dropped")
        return None
    if e.book == "Matthew" and e.chapter == 1 and e.verse_start == 3:
        e.verse_start, e.verse_end = 2, 16
        stats.bump("barnes_rekeyed")
    if _BARNES_FILLER.search(raw):
        raw = _BARNES_FILLER.sub("", raw)
        rest = re.sub(r"<[^>]+>|\bVer(?:se)?s?\b\.?\s*[\d:,\- ]*|\([a-z0-9+]\)|\"[^\"]*\"|"
                      r"\b[1-3]?[A-Z][a-z]{0,4}\.? ?\d+:\d+(?:[-,]\d+)*", "", raw)
        if len(re.sub(r"[^A-Za-z]", "", rest)) < 40:
            stats.bump("barnes_placeholder_entries_dropped")
            return None
        stats.bump("barnes_placeholders_removed")
    return e, raw


def fixup_wesley(e, raw, stats):
    """CrossWire Wesley: 1 Kings is empty and its first notes ("In the way", "His father")
    sit in the 2 Samuel 24 slots; the one 2 Samuel 22 entry is the note on 21:22. Drop
    those three misplaced entries."""
    if e.book == "2 Samuel" and (e.chapter == 24 or (e.chapter == 22 and e.verse_start == 1)):
        stats.bump("wesley_misplaced_entries_dropped")
        return None
    return e, raw


FIXUPS = {"barnes": fixup_barnes, "wesley": fixup_wesley}


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
        if rm.group(3) is None:  # chapter-only note
            end = v11n[book][ch - 1] if ch <= len(v11n[book]) else start
        elif v2 is None:
            end = start
        elif ch2 != ch:
            stats.bump("cross_chapter_notes_truncated_to_first_chapter")
            end = v11n[book][ch - 1] if ch <= len(v11n[book]) else start
        else:
            end = int(v2)
        body = _TY_LINK.sub(r'<reference osisRef="\1">\2</reference>', m.group(3))
        yield book, ch, start, end, markup_to_text(body)


LOADERS = {"helloao": load_helloao, "sword": load_sword, "tdavid": load_tdavid,
           "tyndale": load_tyndale}


# ---------------------------------------------------------------------------
# Post-processing, validation and writing
# ---------------------------------------------------------------------------

def infer_ranges(rows, v11n, stats):
    """Passage commentaries stored only at their first verse: extend each entry to the
    verse before the next entry in the chapter (or the chapter end)."""
    by_ch: dict[tuple, list] = {}
    for r in rows:
        by_ch.setdefault((r[0], r[1]), []).append(r)
    out = []
    for (book, ch), items in by_ch.items():
        items.sort(key=lambda r: r[2])
        last = v11n[book][ch - 1] if ch <= len(v11n[book]) else items[-1][3]
        for i, (b, c, s, e, t) in enumerate(items):
            if e == s:
                nxt = next((x[2] for x in items[i + 1:] if x[2] > s), None)
                new_e = (nxt - 1) if nxt else last
                if new_e != e:
                    stats.bump("ranges_inferred")
                e = max(s, new_e)
            out.append((b, c, s, e, t))
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
    cols = ", ".join(SOURCE_COLUMNS)
    marks = ", ".join("?" for _ in SOURCE_COLUMNS)
    conn.execute(f"INSERT OR REPLACE INTO commentary_sources ({cols}) VALUES ({marks})",
                 [cfg[c] for c in SOURCE_COLUMNS])


def ensure_schema(conn):
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from backend.database import COMMENTARY_SOURCES_DDL
    conn.executescript(COMMENTARY_SOURCES_DDL)


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
    sup = cfg.get("supplement")
    if sup:
        have = {r[0] for r in rows}
        need = [b for b in sup["books"] if b not in have]
        if need:
            sup_cfg = {**cfg, "fixup": None, **sup}  # supplement options override the source's
            extra = list(load_sword(sup_cfg, v11n, stats, books=need, module=sup["module"]))
            stats.bump(f"supplement_{sup['module']}_entries", len(extra))
            rows.extend(extra)
    if cfg.get("infer_ranges"):
        rows = infer_ranges(rows, v11n, stats)
    rows = validate(rows, v11n, stats)
    if not rows:
        raise RuntimeError(f"{source}: no entries produced")

    conn.execute("DELETE FROM commentary_entries WHERE source = ?", (source,))
    links = 0
    for book, ch, s, e, text in rows:
        content, searchable, n = render(text, resolver)
        links += n
        conn.execute(
            "INSERT INTO commentary_entries (source, book, chapter, reference_start, "
            "reference_end, content, searchable_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (source, book, ch, s, e, content, searchable),
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
