"""
Commentary data invariants the study view relies on (run against the built DB).
Skipped when the DB has no commentary_sources table yet.
"""
import re
import sqlite3

import pytest

from backend.database import DATABASE_PATH

SOURCE_COLUMNS = ["source", "short_name", "author", "year", "tradition", "kind", "coverage",
                  "license", "attribution", "source_url", "sort_order", "description",
                  "attribution_short", "size_bytes", "requires_attribution"]
ANCHOR = re.compile(r'<a href="#" class="commentary-ref" data-ref="[^"<>]*">|</a>')


@pytest.fixture(scope="module")
def conn():
    c = sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True)
    if not c.execute("SELECT 1 FROM sqlite_master WHERE name = 'commentary_sources'").fetchone():
        pytest.skip("commentary_sources not built")
    yield c
    c.close()


def test_columns(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(commentary_sources)")]
    assert cols == SOURCE_COLUMNS


def test_every_source_described(conn):
    entries = {r[0] for r in conn.execute("SELECT DISTINCT source FROM commentary_entries")}
    described = {r[0] for r in conn.execute("SELECT source FROM commentary_sources")}
    assert entries == described


def test_metadata_values(conn):
    for source, short, kind, year, order, lic in conn.execute(
            "SELECT source, short_name, kind, year, sort_order, license FROM commentary_sources"):
        assert short and len(short) <= 12, source
        assert kind in ("verse", "passage", "chapter", "notes"), source
        assert isinstance(year, int) and 100 < year < 2100, source
        assert isinstance(order, int), source
        assert lic, source


def test_attribution_and_size(conn):
    for source, req, short, size in conn.execute(
            "SELECT source, requires_attribution, attribution_short, size_bytes FROM commentary_sources"):
        assert req in (0, 1), source
        if req:
            assert short and len(short) <= 100 and "\n" not in short, source
        actual = conn.execute("SELECT SUM(LENGTH(CAST(content AS BLOB))) FROM commentary_entries "
                              "WHERE source = ?", (source,)).fetchone()[0]
        assert size == actual, source


def test_entries_reference_real_verses(conn):
    bad = conn.execute("""
        SELECT COUNT(*) FROM commentary_entries c
        WHERE c.book NOT IN (SELECT name FROM books)
           OR c.reference_start < 1
           OR COALESCE(c.reference_end, c.reference_start) < c.reference_start
           OR NOT EXISTS (SELECT 1 FROM verses v WHERE v.translation_id = 'KJV' AND v.book = c.book
                          AND v.chapter = c.chapter
                          AND v.verse = COALESCE(c.reference_end, c.reference_start))
    """).fetchone()[0]
    assert bad == 0


def test_content_has_only_reference_links(conn):
    for (content,) in conn.execute("SELECT content FROM commentary_entries WHERE content LIKE '%<%'"):
        assert "<" not in ANCHOR.sub("", content)
