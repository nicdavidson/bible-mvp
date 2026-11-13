#!/usr/bin/env python3
"""Stop storing commentary text twice (build step `commentary_search`). Idempotent.

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
