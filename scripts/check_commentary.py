#!/usr/bin/env python3
"""
Quality checks for commentary data. Prints a per-source report and exits non-zero if an
invariant fails.

Checks:
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
from sword_reader import kjv_versification  # noqa: E402

DB = Path(os.environ.get("DATABASE_PATH", Path(__file__).parent.parent / "data" / "bible.db"))
ANCHOR = re.compile(r'<a href="#" class="commentary-ref" data-ref="([^"]*)">')
ANY_TAG = re.compile(r"<[^>]*>")
REF = re.compile(r"^(.+?) (\d+)(?::(\d+)(?:-(\d+))?)?$")
FTS_PROBES = ["god", "lord", "faith", "christ", "israel", "grace"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=0)
    args = ap.parse_args()

    conn = sqlite3.connect(DB)
    v11n = kjv_versification(conn)
    book_names = {r[0] for r in conn.execute("SELECT name FROM books")}
    total_verses = sum(sum(c) for c in v11n.values())
    failures = []

    meta = {r[0]: r for r in conn.execute("SELECT source, short_name, kind, coverage FROM commentary_sources")}
    sources = [r[0] for r in conn.execute(
        "SELECT source FROM commentary_entries GROUP BY source "
        "ORDER BY (SELECT sort_order FROM commentary_sources s WHERE s.source = commentary_entries.source)")]
    for s in sources:
        if s not in meta:
            failures.append(f"{s}: no commentary_sources row")
    for s in meta:
        if s not in sources:
            failures.append(f"{s}: commentary_sources row without entries")

    # DB bytes used by commentary tables (needs dbstat; fall back to payload only)
    try:
        commentary_pages = conn.execute(
            "SELECT SUM(pgsize) FROM dbstat WHERE name IN ('commentary_entries', 'idx_commentary_lookup') "
            "OR name LIKE 'commentary_fts%'").fetchone()[0]
    except sqlite3.OperationalError:
        commentary_pages = None
    total_payload = conn.execute(
        "SELECT SUM(LENGTH(content) + LENGTH(COALESCE(searchable_text, ''))) FROM commentary_entries"
    ).fetchone()[0]

    hdr = f"{'source':26} {'chip':9} {'kind':7} {'entries':>7} {'books':>5} {'cover':>6} {'scope':>6} " \
          f"{'>20KB':>5} {'payloadMB':>9} {'estDB_MB':>8}"
    print(hdr)
    print("-" * len(hdr))
    rnd = random.Random(42)
    for src in sources:
        rows = conn.execute(
            "SELECT id, book, chapter, reference_start, reference_end, content, "
            "LENGTH(content) + LENGTH(COALESCE(searchable_text, '')) FROM commentary_entries "
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
