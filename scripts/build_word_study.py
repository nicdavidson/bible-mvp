#!/usr/bin/env python3
"""Precompute the parts of a word study that are too slow to compute per request.

    python scripts/build_word_study.py        (build step `word_study`)

Needs: word_alignments (interlinear), english_alignment_verses + verses (BSB
renderings of each occurrence), lexicon (Strong's), naves_topic_refs,
cross_references. Writes (docs/WORD_STUDY_2026-11.md has the method and why):

    lemma_profile     part of speech (majority over occurrences), counts, function flag
    lemma_collocates  content lemmas that share verses with it far more than chance:
                      verse-level co-occurrence within one testament; kept when
                      together >= 3 verses, observed > expected and Dunning's
                      log-likelihood G2 >= 15.13 (p < 0.0001, 1 df); ranked by logDice;
                      top 15. Function words are excluded on both sides.
    lemma_topics      Nave's topics whose verse lists hold the lemma far more than
                      chance (same G2 test over all verses, >= 3 shared verses); top 8 by G2
    lemma_xrefs       OpenBible cross-references whose both ends contain the lemma;
                      top 8 pairs by votes
    lemma_samples     up to 12 representative occurrences (lemmas with more than 12):
                      one per frequent BSB rendering (>= 5%, at most 6), then one per
                      canonical section not yet covered, then one per book not yet
                      covered (largest first); within a choice: least-covered section,
                      then most cross-reference votes (a data proxy for well-known
                      verses); section/book picks prefer an occurrence with a frequent
                      rendering
Deterministic, no model.
"""
import math
import os
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from aligner.renderings import group_rendering  # noqa: E402
from backend import alignment_store as store  # noqa: E402
from backend.word_study import (PRIMARY_TEXT_SQL, is_function_lemma, pos_code,  # noqa: E402
                                section_of, unpad)

DB_PATH = Path(os.environ.get("DATABASE_PATH", ROOT / "data" / "bible.db"))

G2_MIN = 15.13          # chi-square 1 df, p < 0.0001
TOGETHER_MIN = 3        # verses
TOP_COLLOCATES = 15
TOP_TOPICS = 8
TOP_XREFS = 8
SAMPLE_MAX = 12
SAMPLE_RENDERING_SHARE = 0.05
SAMPLE_RENDERINGS_MAX = 6
RENDERING_MIN_CONFIDENCE = 0.5   # as lemma_renderings

SCHEMA = """
DROP TABLE IF EXISTS lemma_profile;
CREATE TABLE lemma_profile (
    strong_number TEXT PRIMARY KEY,  -- 'G26'
    pos TEXT NOT NULL,               -- majority part-of-speech code over its occurrences
    occurrences INTEGER NOT NULL,    -- primary text (see backend/word_study.py)
    verses INTEGER NOT NULL,
    function_word INTEGER NOT NULL   -- 1: no collocates computed for it, never one itself
) WITHOUT ROWID;
DROP TABLE IF EXISTS lemma_collocates;
CREATE TABLE lemma_collocates (
    strong_number TEXT NOT NULL, rank INTEGER NOT NULL, other TEXT NOT NULL,
    together INTEGER NOT NULL, expected REAL NOT NULL, g2 REAL NOT NULL, log_dice REAL NOT NULL,
    PRIMARY KEY (strong_number, rank)
) WITHOUT ROWID;
DROP TABLE IF EXISTS lemma_topics;
CREATE TABLE lemma_topics (
    strong_number TEXT NOT NULL, rank INTEGER NOT NULL, topic_id INTEGER NOT NULL,
    hits INTEGER NOT NULL, topic_verses INTEGER NOT NULL, g2 REAL NOT NULL,
    PRIMARY KEY (strong_number, rank)
) WITHOUT ROWID;
DROP TABLE IF EXISTS lemma_xrefs;
CREATE TABLE lemma_xrefs (
    strong_number TEXT NOT NULL, rank INTEGER NOT NULL,
    from_book TEXT NOT NULL, from_chapter INTEGER NOT NULL, from_verse INTEGER NOT NULL,
    to_book TEXT NOT NULL, to_chapter INTEGER NOT NULL, to_verse INTEGER NOT NULL,
    votes INTEGER NOT NULL,
    PRIMARY KEY (strong_number, rank)
) WITHOUT ROWID;
DROP TABLE IF EXISTS lemma_samples;
CREATE TABLE lemma_samples (
    strong_number TEXT NOT NULL, rank INTEGER NOT NULL,
    book TEXT NOT NULL, chapter INTEGER NOT NULL, verse INTEGER NOT NULL,
    word_position INTEGER NOT NULL, rendering TEXT, reason TEXT NOT NULL,
    PRIMARY KEY (strong_number, rank)
) WITHOUT ROWID;
"""


def g2(o11, r1, c1, n):
    """Dunning's log-likelihood ratio for a 2x2 table (o11 together, r1/c1 margins, n total)."""
    cells = ((o11, r1 * c1 / n), (r1 - o11, r1 * (n - c1) / n),
             (c1 - o11, (n - r1) * c1 / n), (n - r1 - c1 + o11, (n - r1) * (n - c1) / n))
    return 2 * sum(o * math.log(o / e) for o, e in cells if o > 0)


def log_dice(o11, r1, c1):
    return 14 + math.log2(2 * o11 / (r1 + c1))


def load_tokens(conn):
    """Primary-text tokens: [(strong, book, chapter, verse, position, testament, book_order, grammar)]."""
    return [(unpad(s), b, c, v, p, t, o, g) for s, b, c, v, p, t, o, g in conn.execute(f"""
        SELECT w.strong_number, w.book, w.chapter, w.verse, w.word_position, b.testament,
               b.book_order, w.grammar
        FROM word_alignments w JOIN books b ON b.name = w.book
        WHERE w.strong_number IS NOT NULL AND {PRIMARY_TEXT_SQL}""")]


def profiles(tokens):
    pos = defaultdict(Counter)
    verses = defaultdict(set)
    for s, b, c, v, _p, _t, _o, g in tokens:
        pos[s][pos_code(g, s[0] == "H")] += 1
        verses[s].add((b, c, v))
    out = {}
    for s, cnt in pos.items():
        code = cnt.most_common(1)[0][0]
        out[s] = (code, sum(cnt.values()), len(verses[s]), int(is_function_lemma(s, code)))
    return out, verses


def collocates(tokens, prof):
    verse_lemmas = defaultdict(set)
    for s, b, c, v, _p, t, _o, _g in tokens:
        if not prof[s][3]:
            verse_lemmas[(t, b, c, v)].add(s)
    n = Counter()
    df = Counter()
    pairs = Counter()
    for (t, *_), lemmas in verse_lemmas.items():
        n[t] += 1
        ls = sorted(lemmas)
        df.update(ls)
        for i, a in enumerate(ls):
            for b in ls[i + 1:]:
                pairs[(a, b)] += 1
    cands = defaultdict(list)
    for (a, b), o in pairs.items():
        if o < TOGETHER_MIN:
            continue
        t = "NT" if a[0] == "G" else "OT"
        e = df[a] * df[b] / n[t]
        if o <= e:
            continue
        score = g2(o, df[a], df[b], n[t])
        if score < G2_MIN:
            continue
        ld = log_dice(o, df[a], df[b])
        cands[a].append((ld, score, o, e, b))
        cands[b].append((ld, score, o, e, a))
    rows = []
    for s, items in cands.items():
        items.sort(key=lambda x: (-x[0], -x[1], x[4]))
        for rank, (ld, score, o, e, other) in enumerate(items[:TOP_COLLOCATES], 1):
            rows.append((s, rank, other, o, round(e, 2), round(score, 1), round(ld, 2)))
    return rows


def topics(conn, lemma_verses):
    maxv = {(b, c): m for b, c, m in conn.execute(
        "SELECT book, chapter, MAX(verse) FROM verses WHERE translation_id='KJV' GROUP BY 1, 2")}
    n = sum(1 for _ in conn.execute("SELECT 1 FROM verses WHERE translation_id='KJV'"))
    topic_verses = defaultdict(set)
    for tid, b, c, vs, ve in conn.execute(
            "SELECT topic_id, book, chapter, verse_start, verse_end FROM naves_topic_refs"):
        for v in range(vs, min(ve or vs, maxv.get((b, c), vs)) + 1):
            topic_verses[tid].add((b, c, v))
    by_verse = defaultdict(list)
    for tid, vs in topic_verses.items():
        for key in vs:
            by_verse[key].append(tid)
    rows = []
    for s, vs in lemma_verses.items():
        hits = Counter(tid for key in vs for tid in by_verse.get(key, ()))
        items = []
        for tid, h in hits.items():
            if h < TOGETHER_MIN:
                continue
            size = len(topic_verses[tid])
            if h * n <= len(vs) * size:
                continue
            score = g2(h, len(vs), size, n)
            if score >= G2_MIN:
                items.append((-score, tid, h, size))
        items.sort()
        for rank, (neg, tid, h, size) in enumerate(items[:TOP_TOPICS], 1):
            rows.append((s, rank, tid, h, size, round(-neg, 1)))
    return rows


def xref_pairs(conn, lemma_verses):
    xr = defaultdict(list)
    for sb, sc, sv, tb, tc, tv, votes in conn.execute(
            "SELECT source_book, source_chapter, source_verse, target_book, target_chapter, "
            "target_verse, votes FROM cross_references"):
        xr[(sb, sc, sv)].append(((tb, tc, tv), votes or 0))
    rows = []
    for s, vs in lemma_verses.items():
        best = {}
        for a in vs:
            for b, votes in xr.get(a, ()):
                if b in vs and b != a and votes > 0:
                    key = tuple(sorted((a, b)))
                    if votes > best.get(key, (0,))[0]:
                        best[key] = (votes, a, b)
        items = sorted(best.values(), key=lambda x: (-x[0], x[1], x[2]))[:TOP_XREFS]
        for rank, (votes, a, b) in enumerate(items, 1):
            rows.append((s, rank, *a, *b, votes))
    return rows


def verse_prominence(conn):
    """Sum of positive OpenBible votes on cross-references from or to each verse."""
    prom = Counter()
    for sb, sc, sv, tb, tc, tv, votes in conn.execute(
            "SELECT source_book, source_chapter, source_verse, target_book, target_chapter, "
            "target_verse, votes FROM cross_references WHERE votes > 0"):
        prom[(sb, sc, sv)] += votes
        prom[(tb, tc, tv)] += votes
    return prom


def bsb_renderings(conn):
    """(book, chapter, verse, source position) -> BSB rendering (conf >= 0.5)."""
    out = {}
    for b, c, v, method, links, text in conn.execute(f"""
            SELECT p.book, p.chapter, p.verse, p.method, p.links, v.text
            FROM {store.TABLE} p JOIN verses v ON v.translation_id = p.translation_id
                 AND v.book = p.book AND v.chapter = p.chapter AND v.verse = p.verse
            WHERE p.translation_id = 'BSB'"""):
        words = store.tappable_words(text)
        groups = defaultdict(list)
        for epos, opos, conf, _ in store.unpack(method, links):
            if conf >= RENDERING_MIN_CONFIDENCE:
                groups[opos].append((epos, words[epos - 1]))
        for opos, ws in groups.items():
            out[(b, c, v, opos)] = group_rendering(ws)
    return out


def samples(tokens, prof, rendering_of, prominence):
    occ = defaultdict(list)
    for s, b, c, v, p, _t, order, _g in tokens:
        occ[s].append((order, c, v, p, b))
    rows = []
    for s, items in occ.items():
        if len(items) <= SAMPLE_MAX:
            continue
        items.sort()
        rend = {it: rendering_of.get((it[4], it[1], it[2], it[3])) for it in items}
        counts = Counter(r for r in rend.values() if r)
        chosen, used_verses = [], set()
        covered = Counter()

        frequent = [r for r, n in counts.most_common(SAMPLE_RENDERINGS_MAX)
                    if n / len(items) >= SAMPLE_RENDERING_SHARE]

        def pick(cands, reason, prefer_frequent=True):
            cands = [it for it in cands if (it[4], it[1], it[2]) not in used_verses]
            if prefer_frequent:
                # an occurrence rendered in one of the usual ways, so a stray
                # alignment ('so' for nephesh) does not become the example
                cands = [it for it in cands if rend[it] in frequent] or cands
            if not cands:
                return
            best = min(cands, key=lambda it: (covered[section_of(it[0])],
                                              -prominence[(it[4], it[1], it[2])], it))
            chosen.append((best, reason))
            used_verses.add((best[4], best[1], best[2]))
            covered[section_of(best[0])] += 1
            covered_books.add(best[4])

        covered_books = set()
        for r in frequent:
            pick([it for it in items if rend[it] == r], f"rendering: {r}", False)
        for name, key in (("section", lambda it: section_of(it[0])), ("book", lambda it: it[4])):
            groups = defaultdict(list)
            for it in items:
                groups[key(it)].append(it)
            for g, its in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[1][0])):
                if len(chosen) >= SAMPLE_MAX:
                    break
                done = covered[g] if name == "section" else g in covered_books
                if not done:
                    pick(its, f"{name}: {g}")
        chosen.sort()
        for rank, (it, reason) in enumerate(chosen, 1):
            order, c, v, p, b = it
            rows.append((s, rank, b, c, v, p, rend[it], reason))
    return rows


def main():
    t0 = time.time()
    conn = sqlite3.connect(DB_PATH)
    tokens = load_tokens(conn)
    prof, lemma_verses = profiles(tokens)
    print(f"{len(tokens)} primary-text tokens, {len(prof)} lemmas ({time.time() - t0:.0f}s)")
    col = collocates(tokens, prof)
    print(f"collocates: {len(col)} rows ({time.time() - t0:.0f}s)")
    top = topics(conn, lemma_verses)
    print(f"topics: {len(top)} rows ({time.time() - t0:.0f}s)")
    xrs = xref_pairs(conn, lemma_verses)
    print(f"xrefs: {len(xrs)} rows ({time.time() - t0:.0f}s)")
    smp = samples(tokens, prof, bsb_renderings(conn), verse_prominence(conn))
    print(f"samples: {len(smp)} rows ({time.time() - t0:.0f}s)")
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO lemma_profile VALUES (?, ?, ?, ?, ?)",
                     [(s, *p) for s, p in sorted(prof.items())])
    conn.executemany("INSERT INTO lemma_collocates VALUES (?, ?, ?, ?, ?, ?, ?)", col)
    conn.executemany("INSERT INTO lemma_topics VALUES (?, ?, ?, ?, ?, ?)", top)
    conn.executemany("INSERT INTO lemma_xrefs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", xrs)
    conn.executemany("INSERT INTO lemma_samples VALUES (?, ?, ?, ?, ?, ?, ?, ?)", smp)
    conn.commit()
    print(f"Built word study tables for {len(prof)} lemmas in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
