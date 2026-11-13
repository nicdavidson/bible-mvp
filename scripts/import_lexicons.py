#!/usr/bin/env python3
"""Import Dodson, Abbott-Smith and Brown-Driver-Briggs, each kept as its own lexicon.

    python scripts/import_lexicons.py          (build step `lexicons`)

Tables (docs/WORD_STUDY_2026-11.md):
    lexicon_entries    one row per (Strong's number, lexicon, entry); definitions are
                       plain text converted from each source's XML, never merged
    lexicon_relations  lemma-to-lemma links that a lexicon states: Strong's own
                       derivation lines ("from G25"), Abbott-Smith derivations
                       ("< ἀγαπάω"), BDB root families (OpenScriptures LexicalIndex)
    word_study_sources the license and credit line for every dataset a word study shows

Sources (licenses checked at the source on 2026-11-13; files pinned by commit):
    Dodson Greek lexicon, biblicalhumanities/Dodson-Greek-Lexicon: CC0 1.0 (LICENSE) and
        "released by the copyright holder into the public domain" (README-ulrikp.txt)
    Abbott-Smith, translatable-exegetical-tools/Abbott-Smith: "The lexicon
        (abbott-smith.tei.xml), including the marked up version in this repository, is in
        the public domain" (README). Its archive.org PDF has restrictions: not used.
    OpenScriptures HebrewLexicon (BDB + LexicalIndex): CC BY 4.0, "credit the Open
        Scriptures Hebrew Bible Project"; BDB and Strong's text public domain (readme.md)
Not used: STEPBible TBESH/TBESG/TFLSJ (docs/RESOURCE_LICENSES_2026-10.md, Traps 1).
"""
import json
import os
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from source_cache import cached_fetch_path  # noqa: E402

DB_PATH = Path(os.environ.get("DATABASE_PATH", Path(__file__).parent.parent / "data" / "bible.db"))

DODSON_SHA = "74f70358d4acfaf2f980bf2feb58ab7115cbbcbc"
ABBOTT_SMITH_SHA = "8c00cb244761aa23659421a8cbbbf7a3b27b7d59"
OSHB_LEXICON_SHA = "21c9add13bc727d3a951361778e97e3ff7afd1ce"
RAW = "https://raw.githubusercontent.com"
FILES = {
    "dodson": (f"lexicons/dodson-{DODSON_SHA[:7]}.xml",
               f"{RAW}/biblicalhumanities/Dodson-Greek-Lexicon/{DODSON_SHA}/dodson.xml"),
    "abbott-smith": (f"lexicons/abbott-smith-{ABBOTT_SMITH_SHA[:7]}.tei.xml",
                     f"{RAW}/translatable-exegetical-tools/Abbott-Smith/{ABBOTT_SMITH_SHA}/"
                     "abbott-smith.tei.xml"),
    "bdb": (f"lexicons/oshb-{OSHB_LEXICON_SHA[:7]}/BrownDriverBriggs.xml",
            f"{RAW}/openscriptures/HebrewLexicon/{OSHB_LEXICON_SHA}/BrownDriverBriggs.xml"),
    "lexical-index": (f"lexicons/oshb-{OSHB_LEXICON_SHA[:7]}/LexicalIndex.xml",
                      f"{RAW}/openscriptures/HebrewLexicon/{OSHB_LEXICON_SHA}/LexicalIndex.xml"),
}

# Every dataset a word study draws on, with what its license asks of us.
SOURCES = [
    ("strongs", "Strong's Exhaustive Concordance, Hebrew and Greek dictionaries (1890)",
     "Public domain", "", "https://github.com/openscriptures/strongs",
     "Brief definitions, KJV usage list, derivation lines"),
    ("dodson", "Dodson, Greek Lexicon of the New Testament (2010)", "CC0 1.0 / public domain",
     "", "https://github.com/biblicalhumanities/Dodson-Greek-Lexicon",
     "Brief glosses compiled from Abbott-Smith, Berry, Souter and Strong"),
    ("abbott-smith", "Abbott-Smith, A Manual Greek Lexicon of the New Testament (1922)",
     "Public domain", "", "https://github.com/translatable-exegetical-tools/Abbott-Smith",
     "TEI markup by the Abbott-Smith project contributors"),
    ("bdb", "Brown, Driver, Briggs, Hebrew and English Lexicon (1906), OpenScriptures edition",
     "CC BY 4.0 (markup); BDB text public domain", "Open Scriptures Hebrew Bible Project",
     "https://github.com/openscriptures/HebrewLexicon",
     "Abridged: many entries carry the sense outline without references"),
    ("stepbible", "STEPBible TAHOT / TAGNT (Tyndale House, Cambridge)", "CC BY 4.0",
     "STEP Bible (STEPBible.org)", "https://github.com/STEPBible/STEPBible-Data",
     "Source words, lemmas (Strong's), parsing codes, editions: occurrence counts"),
    ("alignments", "Bible MVP word alignments (from Clear-Bible alignments + STEPBible)",
     "CC BY 4.0", "Clear Bible / Biblica; STEP Bible", "https://github.com/Clear-Bible/Alignments",
     "How BSB, KJV and WEB render each lemma; see docs/ALIGNMENT_2026-11.md"),
    ("naves", "Nave's Topical Bible (1896)", "Public domain", "", "",
     "Topic verse lists"),
    ("openbible-xrefs", "OpenBible.info cross-references", "CC BY 4.0", "OpenBible.info",
     "https://www.openbible.info/labs/cross-references/", "Cross-references with votes"),
]

TEI = "{http://www.crosswire.org/2008/TEIOSIS/namespace}"
TEI13 = "{http://www.crosswire.org/2013/TEIOSIS/namespace}"
OSHB = "{http://openscriptures.github.com/morphhb/namespace}"


def fetch(name) -> Path:
    key, url = FILES[name]
    path = cached_fetch_path(key, url)
    if path is None:
        sys.exit(f"Could not download {url}")
    return path


def clean(s: str) -> str:
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    s = re.sub(r"\n{2,}", "\n", s)
    s = re.sub(r" ([,.;:)\]])", r"\1", s)
    return s.strip()


def tag(el) -> str:
    return el.tag.rsplit("}", 1)[-1]


def sense_text(el, skip=()) -> str:
    """Render an entry's senses with depth = nesting level of <sense>."""
    def walk(e, depth):
        parts = []
        name = tag(e)
        if name in skip:
            return e.tail or ""
        if name == "sense":
            n = e.get("n")
            parts.append("\n" + "  " * depth + (n + " " if n else ""))
            depth += 1
        if name not in ("pb", "lb", "status"):
            parts.append(e.text or "")
        for c in e:
            parts.append(walk(c, depth))
        parts.append(e.tail or "")
        return "".join(parts)
    body = (el.text or "") + "".join(walk(c, 0) for c in el)
    lines = [clean(x) for x in body.split("\n")]
    indent = [len(x) - len(x.lstrip(" ")) for x in body.split("\n")]
    return "\n".join(" " * i + x for i, x in zip(indent, lines) if x).strip()


def strong_key(prefix: str, num: str) -> str | None:
    """'G', '0026' -> 'G26'. None for OSHB's letter codes for prefixes (strong="b")."""
    num = (num or "").strip()
    return f"{prefix}{int(num)}" if num.isdigit() else None


# --- Dodson ------------------------------------------------------------------------------

def dodson_rows(path):
    root = ET.parse(path).getroot()
    seq = defaultdict(int)
    for e in root.iter(f"{TEI}entry"):
        head, _, num = (e.get("n") or "").partition("|")
        if not num.strip().isdigit():
            continue
        s = strong_key("G", num.strip())
        defs = {d.get("role"): clean("".join(d.itertext())) for d in e.findall(f"{TEI}def")}
        orth = e.find(f"{TEI}orth")
        seq[s] += 1
        yield (s, "dodson", seq[s], num.strip(), clean("".join(orth.itertext())) if orth is not None
               else head.strip(), defs.get("brief"), defs.get("full"), None, None)


# --- Abbott-Smith ------------------------------------------------------------------------

def derivation_words(seg) -> list[str]:
    """Greek words Abbott-Smith derives this entry from: those right after '<',
    separated only by ',' or '+' ('(< τέλος, ὠνέομαι)'). Stops at any other text, so
    glosses and pointers such as 'v.s. ἀγάπη' (see under) are not read as sources."""
    stream = []

    def walk(e):
        if tag(e) == "foreign":
            stream.append(("w", clean("".join(e.itertext()))))
        else:
            stream.append(("t", e.text or ""))
            for c in e:
                walk(c)
        if e is not seg:
            stream.append(("t", e.tail or ""))
    walk(seg)
    words, started = [], False
    for kind, val in stream:
        if kind == "t":
            if not started:
                if "<" in val:
                    started = True
                    if val.split("<", 1)[1].strip(" ,+"):
                        break
            elif val.strip(" ,+\n\t"):
                break
        elif started:
            words.append(val)
    return words


def abbott_smith_rows(path, relations):
    root = ET.parse(path).getroot()
    entries = list(root.iter(f"{TEI13}entry"))
    by_word = {}
    for e in entries:
        word, _, rest = (e.get("n") or "").partition("|")
        nums = re.findall(r"G(\d+)", rest)
        if nums:
            by_word.setdefault(word.strip(), [strong_key("G", n) for n in nums])
    seq = defaultdict(int)
    for e in entries:
        word, _, rest = (e.get("n") or "").partition("|")
        nums = [strong_key("G", n) for n in re.findall(r"G(\d+)", rest)]
        if not nums:
            continue
        form = e.find(f"{TEI13}form")
        head = clean("".join(form.itertext())).lstrip("† ").strip() if form is not None else word
        glosses = []
        for s in e.findall(f"{TEI13}sense"):
            glosses += [clean("".join(g.itertext())) for g in s.findall(f"{TEI13}gloss")]
        definition = "\n".join(sense_text(s) for s in e.findall(f"{TEI13}sense"))
        etym = e.find(f"{TEI13}etym")
        notes = [clean("".join(r.itertext())) for r in e.findall(f"{TEI13}re")]
        meta = {}
        occ = e.find(f"{TEI13}note[@type='occurrencesNT']")
        if occ is not None and (occ.text or "").strip().isdigit():
            meta["nt_occurrences"] = int(occ.text.strip())
        if etym is not None:
            meta["etymology"] = clean("".join(etym.itertext()))
            for seg in etym.findall(f"{TEI13}seg[@type='derivation']"):
                for word in derivation_words(seg):
                    for other in by_word.get(word, []):
                        for s in nums:
                            if other != s:
                                relations.add((s, other, "derived_from", "abbott-smith", ""))
                                relations.add((other, s, "source_of", "abbott-smith", ""))
        for s in nums:
            seq[s] += 1
            yield (s, "abbott-smith", seq[s], e.get("n"), head, "; ".join(glosses[:6]) or None,
                   definition or None, "\n".join(notes) or None,
                   json.dumps(meta, ensure_ascii=False) if meta else None)


# --- BDB ---------------------------------------------------------------------------------

def bdb_rows(bdb_path, index_path, relations):
    bdb = {e.get("id"): e for e in ET.parse(bdb_path).getroot().iter(f"{OSHB}entry")}
    index = list(ET.parse(index_path).getroot().iter(f"{OSHB}entry"))
    by_id = {e.get("id"): e for e in index}
    parent = {}
    for e in index:
        et = e.find(f"{OSHB}etym")
        if et is not None and et.get("type") == "sub" and (et.text or "").strip():
            parent[e.get("id")] = et.text.strip()

    def strongs_of(ix):
        x = by_id[ix].find(f"{OSHB}xref") if ix in by_id else None
        return strong_key("H", x.get("strong")) if x is not None else None

    # Root families: index entries sharing a parent root (and the root itself)
    family = defaultdict(set)
    for ix, p in parent.items():
        family[p].add(ix)
    for p, kids in family.items():
        root_el = by_id.get(p)
        root_w = root_el.find(f"{OSHB}w") if root_el is not None else None
        root_label = (root_w.text or "").strip() if root_w is not None else ""
        members = {s for s in (strongs_of(k) for k in kids | {p}) if s}
        for a in members:
            for b in members:
                if a != b:
                    relations.add((a, b, "same_root", "bdb", root_label))

    found = defaultdict(list)
    for e in index:
        x = e.find(f"{OSHB}xref")
        if x is None or not strong_key("H", x.get("strong")) or x.get("bdb") not in bdb:
            continue
        w = e.find(f"{OSHB}w")
        found[strong_key("H", x.get("strong"))].append(
            (x.get("bdb"), x.get("aug") or "", w.get("xlit") if w is not None else None))
    for s, items in found.items():
        rows = []
        seen = set()
        for bid, aug, xlit in items:
            if bid in seen:
                continue
            seen.add(bid)
            e = bdb[bid]
            status = e.find(f"{OSHB}status")
            w = e.find(f"{OSHB}w")
            text_head = clean((e.text or "") + (w.text if w is not None else "") +
                              (w.tail if w is not None else ""))
            m = re.match(r"^\S*\s+(\d+)\b", text_head)
            count = int(m.group(1)) if m else None
            pos = e.find(f"{OSHB}pos")
            gloss = ", ".join(clean("".join(d.itertext())) for d in e.findall(f"{OSHB}def"))
            definition = sense_text(e)
            meta = {k: v for k, v in (("bdb_id", bid), ("aug", aug or None), ("xlit", xlit),
                                      ("homograph", e.get("mod")), ("count", count),
                                      ("pos", clean(pos.text) if pos is not None else None),
                                      ("status", status.text if status is not None else None))
                    if v}
            rows.append((-(count or 0), aug, bid, w.text.strip() if w is not None else None,
                         gloss or None, definition or None, meta))
        for i, (_, _, bid, head, gloss, definition, meta) in enumerate(sorted(rows, key=lambda r: r[:3]), 1):
            yield (s, "bdb", i, bid, head, gloss, definition, None,
                   json.dumps(meta, ensure_ascii=False))


# --- Strong's own derivation lines -------------------------------------------------------

def strongs_relations(conn, relations):
    known = {r[0] for r in conn.execute("SELECT strong_number FROM lexicon")}
    for s, derivation in conn.execute(
            "SELECT strong_number, derivation FROM lexicon WHERE derivation IS NOT NULL"):
        # "from G25 (ἀγαπάω)": derived. "from G303 (ἀνά) (in the sense of ...) and G2572":
        # both outside parentheses after 'from': derived. Numbers inside parentheses
        # ("in the sense of G833", "like H1254") or after compare/see: a weaker pointer.
        for m in re.finditer(r"([HG])0*(\d+)", derivation):
            other = f"{m.group(1)}{int(m.group(2))}"
            if other == s or other not in known:
                continue
            before = derivation[:m.start()]
            depth = before.count("(") - before.count(")")
            low = before.lower()
            after_from = low[low.rfind("from"):] if "from" in low else None
            derived = (depth == 0 and after_from is not None and
                       not re.search(r"\b(compare|comp\.|see|like)\b", after_from))
            kind = "derived_from" if derived else "compare"
            relations.add((s, other, kind, "strongs", ""))
            if kind == "derived_from":
                relations.add((other, s, "source_of", "strongs", ""))


SCHEMA = """
DROP TABLE IF EXISTS lexicon_entries;
CREATE TABLE lexicon_entries (
    strong_number TEXT NOT NULL,   -- lexicon format: 'G26', 'H2617'
    source TEXT NOT NULL,          -- word_study_sources.source: dodson | abbott-smith | bdb
    seq INTEGER NOT NULL,          -- order when one source has several entries (BDB homographs)
    source_key TEXT,               -- the source's own id (BDB 'h.ed.ab', Dodson '0026', ...)
    headword TEXT,
    gloss TEXT,                    -- the source's short gloss(es)
    definition TEXT,               -- full entry, plain text; one sense per line, indented
    notes TEXT,                    -- Abbott-Smith synonym/usage notes
    meta TEXT,                     -- JSON: pos, count, homograph, status, etymology...
    PRIMARY KEY (strong_number, source, seq)
) WITHOUT ROWID;
DROP TABLE IF EXISTS lexicon_relations;
CREATE TABLE lexicon_relations (
    strong_number TEXT NOT NULL,
    related TEXT NOT NULL,
    relation TEXT NOT NULL,        -- derived_from | source_of | compare | same_root
    source TEXT NOT NULL,          -- strongs | abbott-smith | bdb
    detail TEXT NOT NULL DEFAULT '',  -- e.g. the BDB root letters
    PRIMARY KEY (strong_number, related, relation, source)
) WITHOUT ROWID;
DROP TABLE IF EXISTS word_study_sources;
CREATE TABLE word_study_sources (
    source TEXT PRIMARY KEY, name TEXT NOT NULL, license TEXT NOT NULL,
    attribution TEXT NOT NULL, url TEXT NOT NULL, note TEXT NOT NULL
);
"""


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    relations = set()
    rows = list(dodson_rows(fetch("dodson")))
    rows += list(abbott_smith_rows(fetch("abbott-smith"), relations))
    rows += list(bdb_rows(fetch("bdb"), fetch("lexical-index"), relations))
    strongs_relations(conn, relations)
    conn.executemany("INSERT INTO lexicon_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    conn.executemany("INSERT OR IGNORE INTO lexicon_relations VALUES (?, ?, ?, ?, ?)",
                     sorted(relations))
    conn.executemany("INSERT INTO word_study_sources VALUES (?, ?, ?, ?, ?, ?)", SOURCES)
    conn.commit()
    for src, n, lemmas in conn.execute("SELECT source, COUNT(*), COUNT(DISTINCT strong_number) "
                                       "FROM lexicon_entries GROUP BY source"):
        print(f"  {src}: {n} entries for {lemmas} Strong's numbers")
    for src, rel, n in conn.execute("SELECT source, relation, COUNT(*) FROM lexicon_relations "
                                    "GROUP BY 1, 2"):
        print(f"  relations {src} {rel}: {n}")
    print(f"Imported {len(rows)} lexicon entries, {len(relations)} relations")


if __name__ == "__main__":
    main()
