#!/usr/bin/env python3
"""Commentary search storage and library pruning (build step `commentary_search`). Idempotent.

1. prune_sources: drop every commentary_entries / commentary_sources row whose source is
   not in scripts/commentary_registry.py (the FTS delete trigger keeps commentary_fts in
   step), and rewrite the kept sources' commentary_sources rows from the registry
   (sort_order, metadata; size_bytes re-measured). This is how a DB built with the
   13-source library converges on the five kept on 2026-11-13 without a rebuild.

2. migrate: stop storing commentary text twice (below).

Before: commentary_entries.searchable_text (plain copy of content, ~208 MB) feeds an
external-content FTS5 table. After: FTS5 reads the text through the view
commentary_search, derived from content by backend.commentary_search.plain_text, with
search_override holding the old text for the few entries where derivation differs.

Steps (one transaction): check every entry; drop the FTS triggers; add search_override
and fill it where needed; recreate commentary_fts over the view and rebuild it; drop
searchable_text; create the new triggers. Then 'optimize' and FTS5's own
'integrity-check' (index vs. view). VACUUM afterwards (build_db does it) to reclaim the
space.
"""
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend import commentary_search as cs  # noqa: E402

DB_PATH = Path(os.environ.get("DATABASE_PATH", ROOT / "data" / "bible.db"))


def migrate(conn) -> dict:
    cs.register(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(commentary_entries)")}
    if not cols:
        return {"status": "no commentary_entries table"}
    if "searchable_text" not in cols:
        return {"status": "already migrated"}
    t0 = time.time()
    overrides, rows = [], 0
    for i, content, searchable in conn.execute(
            "SELECT id, content, searchable_text FROM commentary_entries"):
        rows += 1
        o = cs.override_for(content, searchable or "")
        if o is not None:
            overrides.append((o, i))
    conn.execute("BEGIN")
    for t in ("commentary_ai", "commentary_ad", "commentary_au"):
        conn.execute(f"DROP TRIGGER IF EXISTS {t}")
    if "search_override" not in cols:
        conn.execute("ALTER TABLE commentary_entries ADD COLUMN search_override TEXT")
    conn.executemany("UPDATE commentary_entries SET search_override = ? WHERE id = ?", overrides)
    conn.execute("DROP TABLE IF EXISTS commentary_fts")
    conn.execute(cs.VIEW_SQL)
    conn.execute(cs.FTS_SQL)
    conn.execute("INSERT INTO commentary_fts(commentary_fts) VALUES('rebuild')")
    conn.execute("ALTER TABLE commentary_entries DROP COLUMN searchable_text")
    for stmt in _statements(cs.TRIGGERS_SQL):
        conn.execute(stmt)
    conn.execute("COMMIT")
    conn.execute("INSERT INTO commentary_fts(commentary_fts) VALUES('optimize')")
    conn.execute("INSERT INTO commentary_fts(commentary_fts, rank) VALUES('integrity-check', 1)")
    conn.commit()
    return {"status": "migrated", "entries": rows, "overrides": len(overrides),
            "seconds": round(time.time() - t0)}


def prune_sources(conn) -> dict:
    """Remove sources that are not in the registry; refresh the kept sources' metadata."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from commentary_registry import COMMENTARIES
    from import_commentary import write_source_row

    cs.register(conn)   # the delete trigger derives the text it removes from the index
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "commentary_entries" not in tables:
        return {"status": "no commentary_entries table"}
    kept = {c["source"]: c for c in COMMENTARIES.values()}
    present = {r[0] for r in conn.execute("SELECT DISTINCT source FROM commentary_entries")}
    if "commentary_sources" in tables:
        present |= {r[0] for r in conn.execute("SELECT source FROM commentary_sources")}
    removed = sorted(present - set(kept))
    rows = 0
    conn.execute("BEGIN")
    for name in removed:
        rows += conn.execute("DELETE FROM commentary_entries WHERE source = ?", (name,)).rowcount
        if "commentary_sources" in tables:
            conn.execute("DELETE FROM commentary_sources WHERE source = ?", (name,))
    refreshed = []
    if "commentary_sources" in tables:
        for name, cfg in kept.items():
            if name in present:   # only sources that were imported; never invent a row
                write_source_row(conn, cfg)
                refreshed.append(name)
    conn.execute("COMMIT")
    if rows:
        conn.execute("INSERT INTO commentary_fts(commentary_fts) VALUES('optimize')")
        conn.execute("INSERT INTO commentary_fts(commentary_fts, rank) VALUES('integrity-check', 1)")
    return {"removed_sources": removed, "removed_entries": rows, "refreshed": refreshed}


def _statements(sql: str):
    """Split the trigger script into CREATE TRIGGER ... END statements."""
    out, cur = [], []
    for line in sql.strip().splitlines():
        cur.append(line)
        if line.strip() == "END;":
            out.append("\n".join(cur)[:-1])
            cur = []
    return out


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    print(migrate(conn))
    print(prune_sources(conn))
