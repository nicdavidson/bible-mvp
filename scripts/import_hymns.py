#!/usr/bin/env python3
"""Scripture-to-hymn index from the Open Hymnal Project (build step `hymns`).

    python scripts/import_hymns.py

Source: http://openhymnal.org/OpenHymnal2026.11.abc (one ABC Plus file, cached in
data/sources/hymns/). License, checked at openhymnal.org/copying.html on 2026-11-13:
"All content produced specifically by the Open Hymnal which is not a part of a hymn is
placed into the public domain. This includes compilation, indices, web pages ... and all
other data files." Hymn words/music carry their own terms per hymn (the C: copyright
line): most are public domain; some modern words are "freely reproduced ... for Christian
worship". We store metadata and Scripture links for every hymn, and hymn text (the first
line) only when the words are public domain.

Tables (docs/HYMN_INDEX_2026-11.md):
    hymns           one row per Open Hymnal score (a text set to a tune)
    hymn_scripture  hymn -> passage links; kind:
                      reference   the hymnal's own Scripture line (%OHSCRIP); the source
                                  does not say whether a reference is quoted or alluded to
                      paraphrase  the words are a version of the passage: a metrical psalm
                                  (Watts, Tate & Brady, Scottish Psalter, by construction) or
                                  a credit line saying so ("Words: Psalm 146 ...")
                      based_on    the hymnal prints the passage as the hymn's text (Watts,
                                  Hymns and Spiritual Songs; Olney Hymns Book I)
                      quotes      computed: a line of the hymn shares a run of >= 5 words
                                  with a KJV verse that few verses contain (evidence kept)
    hymn_sources    license and credit for each dataset above
"""
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import hymn_sources  # noqa: E402
from source_cache import cached_fetch_path  # noqa: E402

from backend.core import CANONICAL_BOOKS, parse_reference  # noqa: E402
from backend.hymn_keys import title_key  # noqa: E402

DB_PATH = Path(os.environ.get("DATABASE_PATH", ROOT / "data" / "bible.db"))

OH_EDITION = "2026.11"
OH_URL = f"http://openhymnal.org/OpenHymnal{OH_EDITION}.abc"  # https cert is for another host
OH_CACHE_KEY = f"hymns/OpenHymnal{OH_EDITION}.abc"

SOURCES = [
    ("openhymnal", "The Open Hymnal Project (Brian J. Dumont, ed.), edition " + OH_EDITION,
     "Public domain (compilation, indices and data files); hymn words and music: per hymn",
     "Open Hymnal Project, openhymnal.org", "http://openhymnal.org/",
     "Hymn metadata, topics, metres, tunes and the Scripture Reference Index"),
    ("openhymnal-credit", "Open Hymnal credit lines ('Words: Psalm 146 ...')",
     "Public domain", "Open Hymnal Project, openhymnal.org", "http://openhymnal.org/",
     "Passages a hymn's own credit line says it paraphrases"),
    ("kjv-overlap", "Computed: shared word runs between public-domain hymn words and the KJV",
     "Derived from public-domain texts", "", "",
     "A line sharing >= 5 consecutive words with a KJV verse; the shared words are kept as "
     "evidence"),
]

# Open Hymnal abbreviations that core.parse_reference does not know.
BOOK_FIX = {"lv": "Leviticus", "ez": "Ezekiel", "so": "Song of Solomon", "1pt": "1 Peter",
            "2pt": "2 Peter", "1kg": "1 Kings", "2kg": "2 Kings", "1kgs": "1 Kings",
            "2kgs": "2 Kings", "1jn": "1 John", "2jn": "2 John", "3jn": "3 John",
            "1th": "1 Thessalonians", "2th": "2 Thessalonians", "est": "Esther",
            "pr": "Proverbs", "phlm": "Philemon",
            # Watts' and Newton's abbreviations
            "cant": "Song of Solomon", "psal": "Psalms", "eccles": "Ecclesiastes",
            "1pet": "1 Peter", "2pet": "2 Peter", "jud": "Judges"}

SCHEMA = """
DROP TABLE IF EXISTS hymns;
CREATE TABLE hymns (
    id TEXT PRIMARY KEY,           -- 'oh-219' (Open Hymnal X: number; 'oh-1-2' for repeats)
    title TEXT NOT NULL,
    alt_titles TEXT,               -- JSON list ("also known as")
    first_line TEXT,               -- only when the words are public domain
    author TEXT,                   -- as the source gives it: 'Newton, John (1725-1807)'
    translator TEXT,
    words_year INTEGER,            -- first year on the 'Words:' credit line
    words_credit TEXT,             -- the credit line itself
    tune TEXT,                     -- tune name(s) from the 'Music:' credit line
    composer TEXT,
    meter TEXT,                    -- '8 6 8 6', 'Irregular'
    topics TEXT,                   -- JSON list from the hymnal's topical index
    category TEXT,
    words_public_domain INTEGER NOT NULL,
    copyright TEXT,                -- the source's copyright line, verbatim
    title_key TEXT NOT NULL,       -- backend.hymn_keys.title_key(title)
    keys TEXT NOT NULL,            -- JSON: every join key (title, alternates, first line)
    text_key TEXT NOT NULL,        -- groups settings of one text (first line or title + author)
    source TEXT NOT NULL,
    source_url TEXT
);
CREATE INDEX idx_hymns_title_key ON hymns(title_key);
DROP TABLE IF EXISTS hymn_scripture;
CREATE TABLE hymn_scripture (
    hymn_id TEXT NOT NULL,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse_start INTEGER,           -- NULL: the whole chapter
    verse_end INTEGER,
    kind TEXT NOT NULL,            -- reference | paraphrase | quotes
    source TEXT NOT NULL,          -- hymn_sources.source
    ref_text TEXT NOT NULL,        -- as the source wrote it ('Ps 89:1-2')
    evidence TEXT                  -- quotes: the shared words
);
CREATE INDEX idx_hymn_scripture_passage ON hymn_scripture(book, chapter);
CREATE INDEX idx_hymn_scripture_hymn ON hymn_scripture(hymn_id);
DROP TABLE IF EXISTS hymn_sources;
CREATE TABLE hymn_sources (
    source TEXT PRIMARY KEY, name TEXT NOT NULL, license TEXT NOT NULL,
    attribution TEXT NOT NULL, url TEXT NOT NULL, note TEXT NOT NULL
);
"""


# --- ABC parsing --------------------------------------------------------------------------

def read_abc(path) -> str:
    return Path(path).read_bytes().decode("cp1252", errors="replace").replace("\r\n", "\n")


def parse_blocks(text):
    """Yield one dict per hymn: %OH metadata, X, T lines, C lines, lyric systems, W lines."""
    meta, cur = {}, None
    for line in text.split("\n"):
        if line.startswith("%OH"):
            key, _, val = line[3:].partition(" ")
            if key == "SCRIP" and cur is not None:
                yield cur
                cur = None
            meta[key] = val.strip()
        elif line.startswith("X:"):
            if cur is not None:
                yield cur
            cur = {"x": line[2:].strip(), "meta": meta, "T": [], "C": [], "systems": [],
                   "W": []}
            meta = {}
        elif cur is None:
            continue
        elif line.startswith("T:"):
            cur["T"].append(line[2:].strip())
        elif line.startswith("C:"):
            cur["C"].append(line[2:].strip())
        elif line.startswith("[V: S1V1]"):
            cur["systems"].append([])
        elif line.startswith("w:") and cur["systems"]:
            cur["systems"][-1].append(line[2:])
        elif line.startswith("W:"):
            cur["W"].append(line[2:].strip())
    if cur is not None:
        yield cur


def syllables(wline: str):
    """ABC 'w:' line -> [(syllable, joins_next)]; '*' and '_' hold notes, '~' is a space."""
    out = []
    for tok in wline.split():
        tok = re.sub(r"^\d+\.~?", "", tok)
        if tok in ("*", "_", "|", ""):
            continue
        parts = tok.replace("\\-", "\x00").split("-")
        for i, p in enumerate(parts):
            p = p.replace("\x00", "-").replace("~", " ").replace("_", "").strip("*")
            if p:
                out.append((p, i < len(parts) - 1))
    return out


def join_syllables(syls) -> str:
    s = ""
    for syl, joins in syls:
        s += syl + ("" if joins else " ")
    return re.sub(r"\s+", " ", s).strip()


def verses_of(block):
    """Verse texts: w: lines by their order within each system, then the W: verses."""
    by_index = defaultdict(list)
    for system in block["systems"]:
        for i, wl in enumerate(system):
            by_index[i].extend(syllables(wl))
    verses = [by_index[i] for i in sorted(by_index)]
    w_text, cur = [], []
    for line in block["W"]:
        if not line.strip():
            if cur:
                w_text.append(" ".join(cur))
            cur = []
        else:
            cur.append(re.sub(r"^\d+\.\s*", "", line))
    if cur:
        w_text.append(" ".join(cur))
    return verses, w_text


def first_line(verse1, meter: str):
    """The first poetic line: as many syllables as the metre's first number."""
    if not verse1:
        return None
    m = re.match(r"\s*(\d+)", meter or "")
    if m:
        n = int(m.group(1))
        text = join_syllables(verse1[:n])
    else:
        text = join_syllables(verse1[:12])
        cut = re.search(r"[,;:.!?]", text[10:])
        text = text[:10 + cut.start()] if cut else text
    return text.rstrip(" ,;:")


def first_line_key(first: str | None) -> str:
    """Letters and digits of a first line, lowercased: the key that merges one text across
    sources ('Amazing grace! (how sweet the sound)' = 'Amazing grace! How sweet the sound')."""
    return "".join(ch for ch in (first or "").lower().replace("’", "'") if ch.isalnum())


def words_public_domain(copyright: str) -> bool:
    c = copyright or ""
    if re.search(r"\b(Words|Lyrics)\b[^.]{0,30}Copyright|This hymn \(lyrics", c, re.I):
        return False
    return "public domain" in c.lower()


def credit(block, label):
    for c in block["C"]:
        m = re.match(rf"^{label}\b[^:]*:\s*(.*)$", c)
        if m:
            return m.group(1).strip()
    return None


def copyright_text(block):
    out, on = [], False
    for c in block["C"]:
        if c.lower().startswith("copyright:"):
            on = True
            out.append(c.split(":", 1)[1].strip())
        elif on and not re.match(r"^(Words|Music|Setting|Tune)\b", c):
            out.append(c)
        else:
            on = False
    return " ".join(out) or None


# --- references ---------------------------------------------------------------------------

def resolve_book(token: str):
    key = token.lower().replace(" ", "").rstrip(".")
    if key in BOOK_FIX:
        return BOOK_FIX[key]
    parsed = parse_reference(f"{token} 1")
    return parsed[0] if parsed and parsed[0] in CANONICAL_BOOKS else None


def parse_refs(text: str, max_verse):
    """'Jn 9:25, Eph 2:4-9, 43:2-5, Ps 33' -> [(book, ch, v1, v2, as written)].

    A reference without a book takes the previous one's ('Is 41:10, 43:2-5').
    Cross-chapter ranges ('Lk 1:67-2:10') become one row per chapter.
    """
    out, book = [], None
    for raw in (text or "").replace("\\n", " ").split(","):
        part = raw.strip()
        if not part:
            continue
        m = re.match(r"^(\d?\s?[A-Za-z]+\.?)?\s*(\d+)(?::(\d+)[a-z]?)?"
                     r"(?:-(\d+)(?::(\d+))?[a-z]?)?$", part)
        if not m:
            continue
        if m.group(1):
            book = resolve_book(m.group(1))
        if not book:
            continue
        ch, v1, x, y = int(m.group(2)), m.group(3), m.group(4), m.group(5)
        if v1 is None:  # 'Ps 33' or 'Ps 33-34'
            for c in range(ch, (int(x) if x else ch) + 1):
                out.append((book, c, None, None, part))
        elif y is not None:  # 'Lk 1:67-2:10'
            out.append((book, ch, int(v1), max_verse.get((book, ch), 999), part))
            for c in range(ch + 1, int(x)):
                out.append((book, c, None, None, part))
            out.append((book, int(x), 1, int(y), part))
        else:
            out.append((book, ch, int(v1), int(x) if x else int(v1), part))
    return out


CREDIT_REF = re.compile(
    r"\b(?:Psalm|Ps\.?)\s+(\d+)|\bafter\s+((?:\d\s?)?[A-Z][a-z]+\.?\s+\d+(?::\d+(?:-\d+)?)?)")


def credit_refs(words_credit: str, max_verse):
    """Passages a 'Words:' credit line names as the source of the text."""
    out = []
    for m in CREDIT_REF.finditer(words_credit or ""):
        if m.group(1):
            out.append(("Psalms", int(m.group(1)), None, None, m.group(0)))
        else:
            out += parse_refs(m.group(2), max_verse)
    return out


# --- quotations (shared word runs with the KJV) -------------------------------------------

NGRAM = 5
NGRAM_MAX_VERSES = 1
STOP = set("""a an and are as at be but by for from he her his i in is it me my of on or our
shall so that the thee their them they this thou thy to unto us was we were which who will
with ye you your all not no o oh lord god him hath have be his its""".split())
WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")


def norm_words(text: str):
    return WORD_RE.findall(text.lower().replace("’", "'"))


RARE_WORD_VERSES = 100   # the shared words must include one found in fewer KJV verses
LONG_MATCH = 6           # ... and be at least this many words long


def kjv_ngrams(conn):
    """(n-gram index, verse frequency of each word) over the KJV."""
    index, freq = defaultdict(set), defaultdict(int)
    for b, c, v, text in conn.execute(
            "SELECT book, chapter, verse, text FROM verses WHERE translation_id = 'KJV'"):
        ws = norm_words(text)
        for w in set(ws):
            freq[w] += 1
        for i in range(len(ws) - NGRAM + 1):
            index[tuple(ws[i:i + NGRAM])].add((b, c, v))
    index = {g: vs for g, vs in index.items()
             if len(vs) <= NGRAM_MAX_VERSES and sum(w not in STOP for w in g) >= 2}
    return index, freq


def quotes_for(verse_texts, kjv):
    """[((book, ch, v), shared phrase)] for one hymn's words: a run of >= 6 words shared
    with exactly one KJV verse (every 5-word window of it found in that verse only, with
    >= 2 non-function words) that holds a word found in fewer than 100 KJV verses.
    Chosen to make chance matches rare (docs/HYMN_INDEX_2026-11.md, 'Quotations')."""
    index, freq = kjv
    out = []
    for text in verse_texts:
        ws = norm_words(text)
        hits = defaultdict(list)
        for i in range(len(ws) - NGRAM + 1):
            for key in index.get(tuple(ws[i:i + NGRAM]), ()):
                hits[key].append(i)
        for key, starts in hits.items():
            # the longest contiguous run of matching n-grams = the shared phrase
            runs, run = [], [starts[0]]
            for s in starts[1:]:
                if s == run[-1] + 1:
                    run.append(s)
                else:
                    runs.append(run)
                    run = [s]
            runs.append(run)
            best = max(runs, key=len)
            phrase = ws[best[0]:best[-1] + NGRAM]
            if len(phrase) >= LONG_MATCH and any(
                    w not in STOP and freq.get(w, 0) < RARE_WORD_VERSES for w in phrase):
                out.append((key, " ".join(phrase)))
    return out


# --- main -------------------------------------------------------------------------------

def hymn_rows(text, max_verse, kjv_index):
    hymns, links, seen_ids = [], [], {}
    for block in parse_blocks(text):
        meta = block["meta"]
        titles = [t for t in block["T"] if t]
        title = titles[0] if titles else f"Hymn {block['x']}"
        alts = []
        for t in titles[1:]:
            t = re.sub(r"^\(?also known as\s*", "", t.strip(), flags=re.I).rstrip(")")
            alts += [a.strip(" ()") for a in re.split(r"\bor\b", t) if a.strip(" ()")]
        words_credit = credit(block, "Words") or credit(block, "Lyrics")
        music = credit(block, "Music") or credit(block, "Tune") or ""
        tune = ", ".join(re.findall(r"'([^']+)'", music)) or None
        year = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", words_credit or "")
        cp = copyright_text(block)
        pd = words_public_domain(cp)
        verses, w_text = verses_of(block)
        first = first_line(verses[0] if verses else None, meta.get("METRICAL")) if pd else None
        topics = re.findall(r"\{([^}\[]+?)\s*(?:\[[^\]]*\])?\}", meta.get("TOPICS", ""))
        # X: numbers are unique except a few scores all numbered 'X:1': suffix repeats
        hid = f"oh-{block['x']}"
        seen_ids[hid] = seen_ids.get(hid, 0) + 1
        if seen_ids[hid] > 1:
            hid = f"{hid}-{seen_ids[hid]}"
        keys = sorted({k for k in [title_key(title), *map(title_key, alts),
                                   title_key(first) if first else ""] if k})
        hymns.append((
            hid, title, json.dumps(alts, ensure_ascii=False) if alts else None, first,
            meta.get("AUTHOR") or None,
            None if meta.get("TRANSLATOR", "none") in ("none", "") else meta["TRANSLATOR"],
            int(year.group(1)) if year else None, words_credit, tune,
            meta.get("COMPOSER") or None, meta.get("METRICAL") or None,
            json.dumps(topics, ensure_ascii=False) if topics else None,
            meta.get("CATEGORY") or None, int(pd), cp, title_key(title),
            json.dumps(keys), first_line_key(first) or (
                title_key(title) + "|" + title_key((meta.get("AUTHOR") or "").split(",")[0])),
            "openhymnal", "http://openhymnal.org/"))
        seen = set()
        for b, c, v1, v2, raw in parse_refs(meta.get("SCRIP", ""), max_verse):
            if (b, c, v1, v2) not in seen:
                seen.add((b, c, v1, v2))
                links.append((hid, b, c, v1, v2, "reference", "openhymnal", raw, None))
        for b, c, v1, v2, raw in credit_refs(words_credit, max_verse):
            links.append((hid, b, c, v1, v2, "paraphrase", "openhymnal-credit", raw,
                          words_credit))
        if pd and kjv_index is not None:
            texts = [join_syllables(v) for v in verses] + w_text
            for (b, c, v), phrase in sorted(set(quotes_for(texts, kjv_index))):
                links.append((hid, b, c, v, v, "quotes", "kjv-overlap", f"{b} {c}:{v}",
                              phrase))
    return hymns, links


SOURCE_PREFIX = {"pg-watts-psalms": "wps", "pg-watts-hss": "whss", "tcp-tate-brady": "tb",
                 "ccel-scottish-psalter": "sp", "ccel-olney": "olney"}
QUOTE_TEXT_SOURCES = {"pg-watts-psalms", "pg-watts-hss", "tcp-tate-brady"}


def other_source_rows(records, kjv_index):
    """hymns/hymn_scripture rows for the psalters and hymnals in scripts/hymn_sources.py."""
    hymns, links = [], []
    for r in records:
        hid = SOURCE_PREFIX[r["source"]] + "-" + re.sub(r"[^A-Za-z0-9]+", "-",
                                                       r["source_ref"]).strip("-").lower()
        first = r["first_line"]
        keys = sorted({k for k in (title_key(first), first_line_key(first)) if k})
        hymns.append((
            hid, r["title"], None, first, r["author"], None, r["words_year"], None, r["tune"],
            None, r["meter"], None, None, int(r["words_public_domain"]), r["copyright"],
            title_key(r["title"]), json.dumps(keys), first_line_key(first), r["source"],
            dict((x[0], x[4]) for x in hymn_sources.SOURCES)[r["source"]]))
        seen = set()
        for b, c, v1, v2, raw, kind in r["refs"]:
            if (b, c, v1, v2, kind) not in seen:
                seen.add((b, c, v1, v2, kind))
                links.append((hid, b, c, v1, v2, kind, r["source"], raw, None))
        if r["text"] and r["source"] in QUOTE_TEXT_SOURCES and kjv_index is not None:
            for (b, c, v), phrase in sorted(set(quotes_for(r["text"], kjv_index))):
                links.append((hid, b, c, v, v, "quotes", "kjv-overlap", f"{b} {c}:{v}", phrase))
    return hymns, links


def load_other_sources(max_verse):
    def fetch(spec):
        path = cached_fetch_path(*spec)
        if path is None:
            sys.exit(f"Could not download {spec[1]}")
        return path
    recs = list(hymn_sources.watts_psalms(fetch(hymn_sources.PG_WATTS_PSALMS), max_verse))
    recs += hymn_sources.watts_hss(fetch(hymn_sources.PG_WATTS_HSS), max_verse, resolve_book)
    recs += hymn_sources.tate_brady(fetch(hymn_sources.TCP_TATE_BRADY))
    if hymn_sources.ENABLE_CCEL:
        recs += hymn_sources.scottish_psalter(fetch(hymn_sources.CCEL_SCOTTISH),
                                              hymn_sources.OSIS_BOOKS.get, max_verse)
        recs += hymn_sources.olney(fetch(hymn_sources.CCEL_OLNEY),
                                   hymn_sources.OSIS_BOOKS.get, max_verse)
    return recs


def main():
    path = cached_fetch_path(OH_CACHE_KEY, OH_URL)
    if path is None:
        sys.exit(f"Could not download {OH_URL}")
    conn = sqlite3.connect(DB_PATH)
    max_verse = {(b, c): v for b, c, v in conn.execute(
        "SELECT book, chapter, MAX(verse) FROM verses WHERE translation_id = 'KJV' "
        "GROUP BY 1, 2")}
    kjv = kjv_ngrams(conn)
    hymns, links = hymn_rows(read_abc(path), max_verse, kjv)
    more_hymns, more_links = other_source_rows(load_other_sources(max_verse), kjv)
    hymns += more_hymns
    links += more_links
    conn.executescript(SCHEMA)
    conn.executemany(f"INSERT INTO hymns VALUES ({','.join('?' * 20)})", hymns)
    conn.executemany("INSERT INTO hymn_scripture VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", links)
    conn.executemany("INSERT INTO hymn_sources VALUES (?, ?, ?, ?, ?, ?)",
                     SOURCES + [x for x in hymn_sources.SOURCES
                                if hymn_sources.ENABLE_CCEL or not x[0].startswith("ccel")])
    conn.commit()
    for kind, n, h in conn.execute("SELECT kind, COUNT(*), COUNT(DISTINCT hymn_id) "
                                   "FROM hymn_scripture GROUP BY kind"):
        print(f"  {kind}: {n} links, {h} hymns")
    for src, n in conn.execute("SELECT source, COUNT(*) FROM hymns GROUP BY 1"):
        print(f"  {src}: {n} items")
    print(f"  {conn.execute('SELECT COUNT(DISTINCT text_key) FROM hymns').fetchone()[0]} "
          "distinct texts")
    print(f"Imported {len(hymns)} hymns, {len(links)} scripture links")


if __name__ == "__main__":
    main()
