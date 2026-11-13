"""Commentary search reads its text through a view (backend/commentary_search.py)."""
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from backend import commentary_search as cs  # noqa: E402
from backend.database import SCHEMA  # noqa: E402

ANCHOR = '<a href="#" class="commentary-ref" data-ref="John 3:16">Joh 3:16</a>'


def test_plain_text_matches_the_importer_rule():
    from commentary_text import render

    class Resolver:  # resolves nothing, so render() adds no anchors of its own
        def parse(self, s):
            return None
    text = "Brackets <x> and &amp;c. stay; a bare & too."
    content, searchable, _ = render(text, Resolver())
    assert cs.plain_text(content) == searchable
    assert cs.plain_text(f"God so loved, {ANCHOR} &lt;n&gt; &amp;amp;") == \
        "God so loved, Joh 3:16  n  &amp;"


def _db():
    conn = sqlite3.connect(":memory:")
    cs.register(conn)
    conn.executescript(SCHEMA)
    return conn


def _hits(conn, q):
    return conn.execute("SELECT COUNT(*) FROM commentary_fts WHERE commentary_fts MATCH ?",
                        (f"searchable_text: ({q})",)).fetchone()[0]


def test_new_schema_indexes_updates_and_deletes():
    conn = _db()
    conn.execute("INSERT INTO commentary_entries (source, book, chapter, content) "
                 "VALUES ('X', 'John', 3, ?)", (f"God so loved, {ANCHOR}",))
    snip = conn.execute("SELECT snippet(commentary_fts, 0, '[', ']', '…', 8) FROM commentary_fts "
                        "WHERE commentary_fts MATCH 'searchable_text: (joh)'").fetchone()[0]
    assert snip == "God so loved, [Joh] 3:16"
    conn.execute("UPDATE commentary_entries SET content = 'about grace'")
    assert _hits(conn, "grace") == 1 and _hits(conn, "loved") == 0
    conn.execute("UPDATE commentary_entries SET search_override = 'that a override'")
    assert _hits(conn, "override") == 1 and _hits(conn, "grace") == 0
    conn.execute("DELETE FROM commentary_entries")
    assert _hits(conn, "override") == 0
    conn.execute("INSERT INTO commentary_fts(commentary_fts, rank) VALUES('integrity-check', 1)")


def test_migration_keeps_the_indexed_text(tmp_path):
    from migrate_commentary_search import migrate
    db = tmp_path / "old.db"
    conn = sqlite3.connect(db, isolation_level=None)
    conn.executescript("""
        CREATE TABLE commentary_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT,
            book TEXT, chapter INTEGER, reference_start INTEGER DEFAULT 1, reference_end INTEGER,
            content TEXT NOT NULL, searchable_text TEXT);
        CREATE VIRTUAL TABLE commentary_fts USING fts5(searchable_text, source, book, chapter,
            content='commentary_entries', content_rowid='id');
        CREATE TRIGGER commentary_ai AFTER INSERT ON commentary_entries BEGIN
            INSERT INTO commentary_fts(rowid, searchable_text, source, book, chapter)
            VALUES (new.id, new.searchable_text, new.source, new.book, new.chapter);
        END;""")
    conn.execute("INSERT INTO commentary_entries (source, book, chapter, content, searchable_text)"
                 " VALUES ('X', 'John', 3, ?, 'God so loved, Joh 3:16')", (f"God so loved, {ANCHOR}",))
    # the HTML lost a space: the stored text must win
    conn.execute("INSERT INTO commentary_entries (source, book, chapter, content, searchable_text)"
                 " VALUES ('X', 'Acts', 6, 'the result thata great', 'the result that a great')")
    out = migrate(conn)
    assert out["status"] == "migrated" and out["overrides"] == 1
    cols = {r[1] for r in conn.execute("PRAGMA table_info(commentary_entries)")}
    assert "searchable_text" not in cols and "search_override" in cols
    assert _hits(conn, "that") == 1 and _hits(conn, "thata") == 0 and _hits(conn, "joh") == 1
    assert migrate(conn)["status"] == "already migrated"


DB = ROOT / "data" / "bible.db"


def _migrated():
    if not DB.exists():
        return False
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        return conn.execute("SELECT 1 FROM sqlite_master WHERE name='commentary_search'"
                            ).fetchone() is not None
    finally:
        conn.close()


@pytest.mark.skipif(not _migrated(), reason="commentary search not migrated")
def test_built_db_search_returns_snippets():
    from fastapi.testclient import TestClient

    from backend.main import app
    r = TestClient(app).get("/api/search", params={"q": "lovingkindness", "scope": "commentary"})
    res = r.json()["results"]
    assert res and all("<mark>" in x["snippet"] for x in res)
