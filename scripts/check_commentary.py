#!/usr/bin/env python3
"""
Quality checks for commentary data. Prints a per-source report and exits non-zero if an
invariant fails.

Checks:
  - the library is exactly the sources in scripts/commentary_registry.py (no removed ones)
  - every commentary_entries.source has a commentary_sources row and vice versa
  - book names match the books table; chapter/verse ranges exist (KJV versification)
  - every data-ref link target exists
  - content holds no markup except the generated commentary-ref anchors
  - FTS search returns hits from every source
Reports per source: entries, books, verse coverage, entries over 20 KB, payload bytes and
an estimate of DB bytes (payload share of the pages used by commentary tables + FTS).

Usage:
    python scripts/check_commentary.py [--samples N]   # N random entries per source
"""
import argparse
import os
import random
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from commentary_registry import COMMENTARIES  # noqa: E402
from sword_reader import kjv_versification  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import commentary_search  # noqa: E402
from backend.commentary_search import SEARCH_TEXT_SQL  # noqa: E402

DB = Path(os.environ.get("DATABASE_PATH", Path(__file__).parent.parent / "data" / "bible.db"))
ANCHOR = re.compile(r'<a href="#" class="commentary-ref" data-ref="([^"]*)">')
ANY_TAG = re.compile(r"<[^>]*>")
REF = re.compile(r"^(.+?) (\d+)(?::(\d+)(?:-(\d+))?)?$")
FTS_PROBES = ["god", "lord", "faith", "christ", "israel", "grace"]

# Verse-alignment ("shift") checks. "lemma": the entry opens by quoting KJV words, which
# must appear in its own verse range (or be found in the next/previous verse = shifted).
# "marker": the entry prints its own verse number ("Verse 16.", "3:16", "16.").
SHIFT_CHECKS = {
    "John Gill": ("lemma", r"\s*(.{6,80}?),\.\.\.\."),
    "Jamieson-Fausset-Brown": ("lemma", r"\s*(?:[A-Z][A-Z ,.;'()\d:-]+\n+)?(?:\d+(?:-\d+)?\.\s*)?([^\n]{4,60}?)--"),
    "Treasury of David": ("marker", r"\s*Verses?\s+(\d+)"),
    "Tyndale Study Notes": ("marker", r"\s*\d+:(\d+)"),
    "Scofield Notes (1917)": ("lemma1", r"\s*([A-Za-z][^\n]{2,40})\n"),
}
WORD = re.compile(r"[a-z]+")

# Truncation. Every source ends >97% of entries with . ! ? ) " ' etc. An entry that ends on a
# lowercase letter or a comma stopped mid-sentence; when it is also near 32K characters it
# was cut by a length cap (HelloAO cuts long entries at 32,767). Entries we could not
# complete end with a visible " […]" and are reported, not failed.
INCOMPLETE_MARK = "[\u2026]"
CAP_SIGNATURE = 30000
MID_SENTENCE_FAIL = 0.02   # fail a source if more than 2% of its entries end mid-sentence
DEBRIS = re.compile(r"(?m)^\s*(?:Next: .{1,60}(?:Chapter \d+|Introduction)|Unabridged|End of Barnes)")


def ends_mid_sentence(text):
    t = (text or "").rstrip()
    return bool(t) and (t[-1].islower() or t[-1] == ",")


def shift_check(conn, src, mode, rx, kjv):
    """Returns Counter of ok / next / prev / unclear (entries without a usable lemma skipped)."""
    import collections
    pat = re.compile(rx) if rx else None
    out = collections.Counter()
    col = "content" if mode == "selfref" else SEARCH_TEXT_SQL
    for b, ch, s, e, t in conn.execute(
            "SELECT book, chapter, reference_start, COALESCE(reference_end, reference_start), "
            f"{col} FROM commentary_entries WHERE source = ?", (src,)):
        if mode == "selfref":
            # first link to a verse in the same chapter should fall inside the entry's range
            m = re.search(rf'data-ref="{re.escape(b)} {ch}:(\d+)', t or "")
            if m:
                n = int(m.group(1))
                out["ok" if s <= n <= e else "next" if n == e + 1 else "prev" if n == s - 1
                    else "unclear"] += 1
            continue
        m = pat.match(t or "")
        if not m:
            continue
        if mode == "marker":
            n = int(m.group(1))
            out["ok" if s <= n <= e else "next" if n == e + 1 else "prev" if n == s - 1 else "unclear"] += 1
            continue
        words = [w for w in WORD.findall(m.group(1).lower()) if len(w) > 2][:6]
        if len(words) < (1 if mode == "lemma1" else 2):
            continue

        def score(v):
            vt = kjv.get((b, ch, v), ())
            return sum(w in vt for w in words) / len(words)
        if max(score(v) for v in range(s, e + 1)) >= 0.6:
            out["ok"] += 1
        elif score(e + 1) >= 0.6:
            out["next"] += 1
        elif score(s - 1) >= 0.6:
            out["prev"] += 1
        else:
            out["unclear"] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=0)
    args = ap.parse_args()

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    commentary_search.register(conn)
    v11n = kjv_versification(conn)
    book_names = {r[0] for r in conn.execute("SELECT name FROM books")}
    total_verses = sum(sum(c) for c in v11n.values())
    failures = []

    try:
        meta = {r[0]: r for r in conn.execute(
            "SELECT source, short_name, kind, coverage, size_bytes FROM commentary_sources")}
    except sqlite3.OperationalError:
        meta = {}
        failures.append("commentary_sources table missing")
    order = {s: i for i, s in enumerate(meta)}
    if meta:
        order = {r[0]: r[1] for r in conn.execute("SELECT source, sort_order FROM commentary_sources")}
    sources = sorted((r[0] for r in conn.execute("SELECT DISTINCT source FROM commentary_entries")),
                     key=lambda s: (order.get(s, 0), s))
    for s in sources:
        if s not in meta:
            failures.append(f"{s}: no commentary_sources row")
    for s in meta:
        if s not in sources:
            failures.append(f"{s}: commentary_sources row without entries")
    registry = {c["source"] for c in COMMENTARIES.values()}
    for s in sorted((set(sources) | set(meta)) - registry):
        failures.append(f"{s}: not in scripts/commentary_registry.py (removed source left in the DB)")
    for s in sorted(registry - set(sources)):
        failures.append(f"{s}: in the registry but has no entries")

    # DB bytes used by commentary tables (needs dbstat; fall back to payload only)
    try:
        commentary_pages = conn.execute(
            "SELECT SUM(pgsize) FROM dbstat WHERE name IN ('commentary_entries', 'idx_commentary_lookup') "
            "OR name LIKE 'commentary_fts%'").fetchone()[0]
    except sqlite3.OperationalError:
        commentary_pages = None
    total_payload = conn.execute(
        "SELECT SUM(LENGTH(content) + LENGTH(COALESCE(search_override, ''))) FROM commentary_entries"
    ).fetchone()[0]

    hdr = f"{'source':26} {'chip':9} {'kind':7} {'entries':>7} {'books':>5} {'cover':>6} {'scope':>6} " \
          f"{'>20KB':>5} {'payloadMB':>9} {'estDB_MB':>8}"
    print(hdr)
    print("-" * len(hdr))
    rnd = random.Random(42)
    for src in sources:
        rows = conn.execute(
            "SELECT id, book, chapter, reference_start, reference_end, content, "
            "LENGTH(content) + LENGTH(COALESCE(search_override, '')) FROM commentary_entries "
            "WHERE source = ?", (src,)).fetchall()
        covered = set()
        books = set()
        big = 0
        payload = 0
        bad_rows = bad_links = bad_tags = 0
        for _id, book, ch, s, e, content, size in rows:
            payload += size
            if len(content) > 20000:
                big += 1
            if book not in book_names or book not in v11n or not (1 <= ch <= len(v11n[book])):
                bad_rows += 1
                continue
            maxv = v11n[book][ch - 1]
            e = e or s
            if not (1 <= s <= e <= maxv):
                bad_rows += 1
                continue
            books.add(book)
            for v in range(s, e + 1):
                covered.add((book, ch, v))
            for target in ANCHOR.findall(content):
                m = REF.match(target)
                ok = False
                if m and m.group(1) in v11n:
                    tb, tc = m.group(1), int(m.group(2))
                    if 1 <= tc <= len(v11n[tb]):
                        mv = v11n[tb][tc - 1]
                        tv = int(m.group(3)) if m.group(3) else 1
                        tv2 = int(m.group(4)) if m.group(4) else tv
                        ok = 1 <= tv <= tv2 <= mv
                if not ok:
                    bad_links += 1
            stripped = ANCHOR.sub("", content).replace("</a>", "")
            if ANY_TAG.search(stripped):
                bad_tags += 1
        scope_total = sum(sum(v11n[b]) for b in books) or 1
        est = payload / total_payload * commentary_pages if commentary_pages else payload
        chip = meta[src][1] if src in meta else "?"
        kind = meta[src][2] if src in meta else "?"
        print(f"{src[:26]:26} {chip:9} {kind:7} {len(rows):7} {len(books):5} "
              f"{len(covered) / total_verses:6.1%} {len(covered) / scope_total:6.1%} {big:5} "
              f"{payload / 1e6:9.1f} {est / 1e6:8.1f}")
        for label, n in (("rows with invalid book/chapter/verse", bad_rows),
                         ("links to verses that do not exist", bad_links),
                         ("rows with markup other than reference links", bad_tags)):
            if n:
                failures.append(f"{src}: {n} {label}")
        hit = None
        for probe in FTS_PROBES:
            hit = conn.execute(
                "SELECT COUNT(*) FROM (SELECT rowid FROM commentary_fts WHERE commentary_fts MATCH ? "
                "AND source = ? LIMIT 1)", (f"searchable_text: {probe}", src)).fetchone()[0]
            if hit:
                break
        if not hit:
            failures.append(f"{src}: FTS returned no hits for {FTS_PROBES}")
        if args.samples:
            for r in rnd.sample(rows, min(args.samples, len(rows))):
                text = ANY_TAG.sub("", r[5]).replace("\n", " ")
                print(f"    sample {r[1]} {r[2]}:{r[3]}-{r[4]}  {text[:160]}")

    print("\nVerse alignment (shift) check: entries whose lemma/verse marker matches their own "
          "range (ok), the next verse, or the previous verse")
    kjv = {(b, ch, v): set(WORD.findall(t.lower())) for b, ch, v, t in conn.execute(
        "SELECT book, chapter, verse, text FROM verses WHERE translation_id = 'KJV'")}
    for src in sources:
        if src not in SHIFT_CHECKS:
            print(f"  {src:26} (no lemma or verse marker to check)")
            continue
        mode, rx = SHIFT_CHECKS[src]
        r = shift_check(conn, src, mode, rx, kjv)
        decided = r["ok"] + r["next"] + r["prev"]
        shifted = (r["next"] + r["prev"]) / decided if decided else 0
        print(f"  {src:26} {mode:6} ok={r['ok']:6} next={r['next']:5} prev={r['prev']:5} "
              f"unclear={r['unclear']:5} shifted={shifted:.1%}")
        if decided >= 50 and shifted > 0.03:
            failures.append(f"{src}: {shifted:.1%} of checked entries look shifted by one verse")

    print("\nTruncation check: entries ending mid-sentence (lowercase letter or comma), those "
          f"over {CAP_SIGNATURE:,} chars (cap signature), marked incomplete, leftover navigation")
    for src in sources:
        mid = capped = marked = debris = n = 0
        for (t,) in conn.execute(f"SELECT {SEARCH_TEXT_SQL} FROM commentary_entries "
                                 "WHERE source = ?", (src,)):
            n += 1
            if (t or "").rstrip().endswith(INCOMPLETE_MARK):
                marked += 1
            elif ends_mid_sentence(t):
                mid += 1
                if len(t) >= CAP_SIGNATURE:
                    capped += 1
            if DEBRIS.search(t or ""):
                debris += 1
        print(f"  {src:26} mid-sentence={mid:4} ({mid / n:.2%})  cap-truncated={capped:3}  "
              f"marked-incomplete={marked:3}  navigation-debris={debris:3}")
        if capped:
            failures.append(f"{src}: {capped} entries cut at a length cap")
        if mid / n > MID_SENTENCE_FAIL:
            failures.append(f"{src}: {mid / n:.1%} of entries end mid-sentence")
        if debris:
            failures.append(f"{src}: {debris} entries contain page-navigation lines")

    print(f"\ncoverage = share of all 31,102 KJV verses with at least one entry; "
          f"scope = share of verses in the books the source covers")
    if commentary_pages:
        print(f"commentary tables + FTS use {commentary_pages / 1e6:.1f} MB; estDB_MB splits that "
              f"by each source's share of text bytes")
    print(f"database file: {DB.stat().st_size / 1e6:.1f} MB")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  " + f)
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
