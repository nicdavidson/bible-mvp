"""Build steps that change an existing DB in place: pruning commentary sources that left
the library, and the release version stamped into data/db-manifest.json."""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_db  # noqa: E402
import migrate_commentary_search  # noqa: E402
from backend import commentary_search  # noqa: E402
from backend.database import SCHEMA  # noqa: E402


def _old_library_db(path):
    """A DB as the 13-source library left it: a removed source next to a kept one."""
    conn = sqlite3.connect(path, isolation_level=None)
    commentary_search.register(conn)
    conn.executescript(SCHEMA)
    rows = [("Matthew Henry", 1, 21, "Henry on the new birth"),
            ("John Gill", 16, 16, "Gill on so loved the world"),
            ("John Gill", 17, 17, "Gill on not to condemn")]
    for src, s, e, text in rows:
        conn.execute("INSERT INTO commentary_entries (source, book, chapter, reference_start, "
                     "reference_end, content) VALUES (?, 'John', 3, ?, ?, ?)", (src, s, e, text))
    for src, order in (("Matthew Henry", 20), ("John Gill", 90)):
        conn.execute("INSERT INTO commentary_sources (source, sort_order) VALUES (?, ?)", (src, order))
    return conn


def test_prune_drops_removed_sources_and_converges(tmp_path):
    conn = _old_library_db(tmp_path / "old.db")
    out = migrate_commentary_search.prune_sources(conn)
    assert out["removed_sources"] == ["Matthew Henry"] and out["removed_entries"] == 1
    assert {r[0] for r in conn.execute("SELECT source FROM commentary_entries")} == {"John Gill"}
    gill = conn.execute("SELECT short_name, sort_order, size_bytes FROM commentary_sources").fetchall()
    assert gill == [("Gill", 20, len("Gill on so loved the world") + len("Gill on not to condemn"))]
    # The search index lost Henry's text with his rows, and kept Gill's
    match = "SELECT COUNT(*) FROM commentary_fts WHERE commentary_fts MATCH ?"
    assert conn.execute(match, ("birth",)).fetchone()[0] == 0
    assert conn.execute(match, ("condemn",)).fetchone()[0] == 1
    # Idempotent: a second run removes nothing
    again = migrate_commentary_search.prune_sources(conn)
    assert again["removed_sources"] == [] and again["removed_entries"] == 0


def test_manifest_version_changes_with_the_file():
    today = "2026.11.13"
    assert build_db.manifest_version(None, "a", today) == today
    assert build_db.manifest_version({"version": "2026.11.12", "sha256": "a"}, "b", today) == today
    # Same date, different file: releases are immutable, so a suffix
    assert build_db.manifest_version({"version": today, "sha256": "a"}, "b", today) == "2026.11.13.1"
    assert build_db.manifest_version({"version": "2026.11.13.1", "sha256": "b"}, "c", today) == "2026.11.13.2"
    # Same file: same version
    assert build_db.manifest_version({"version": "2026.11.13.1", "sha256": "b"}, "b", today) == "2026.11.13.1"


def test_build_does_not_import_removed_sources():
    steps = {s["name"]: s for s in build_db.IMPORT_STEPS}
    imported = [s["args"][0] for s in steps.values() if s.get("script") == "import_commentary.py"]
    assert sorted(imported) == sorted(["john-gill", "jamieson-fausset-brown", "scofield",
                                       "tyndale", "treasury-of-david", "gaebelein", "ironside",
                                       "darby", "brooks", "mackintosh", "larkin"])
