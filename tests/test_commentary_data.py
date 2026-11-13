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


LIBRARY = ["Scofield Notes (1917)", "John Gill", "Jamieson-Fausset-Brown", "Tyndale Study Notes",
           "Gaebelein Annotated Bible", "Ironside Expositions", "Darby Synopsis", "Brooks Summarized Bible",
           "Mackintosh Notes on the Pentateuch", "Larkin on Revelation", "Treasury of David"]


def _registry():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    import commentary_registry
    return commentary_registry


def test_library_is_exactly_these_sources_in_order(conn):
    """The owner's library: the five kept on 2026-11-13 plus the dispensational sources
    added the same day. Matthew Henry, Keil & Delitzsch, Barnes, Calvin, Wesley, Clarke,
    People's New Testament and Catena Aurea were removed and must not come back through a
    build. Registry, commentary_sources and entries all agree."""
    reg = _registry()
    assert [reg.COMMENTARIES[k]["source"] for k in reg.DEFAULT_ORDER] == LIBRARY
    assert [r[0] for r in conn.execute(
        "SELECT source FROM commentary_sources ORDER BY sort_order")] == LIBRARY
    assert {r[0] for r in conn.execute("SELECT DISTINCT source FROM commentary_entries")} == set(LIBRARY)


def test_frontend_default_order_matches_registry():
    import re
    from pathlib import Path
    reg = _registry()
    js = (Path(__file__).parent.parent / "frontend/static/js/modules/study.js").read_text()
    block = re.search(r"const DEFAULT_ORDER = \[(.*?)\];", js, re.S).group(1)
    slugs = re.findall(r"'([a-z0-9-]+)'", block)
    slug = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")  # noqa: E731
    assert slugs == [slug(reg.COMMENTARIES[k]["source"]) for k in reg.DEFAULT_ORDER]


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


def test_scripts_have_no_shadowed_functions():
    """Two branches each added source_cache.cached_fetch_bytes with different return types;
    the later definition silently shadowed the earlier one and broke the Tyndale import."""
    import ast
    from pathlib import Path

    for path in (Path(__file__).parent.parent / "scripts").glob("*.py"):
        names = [n.name for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef)]
        dupes = {n for n in names if names.count(n) > 1}
        assert not dupes, f"{path.name} defines {sorted(dupes)} more than once"


# ---------------------------------------------------------------------------
# Dispensational sources (2026-11-13)
# ---------------------------------------------------------------------------

def _notes_on(conn, source, book, chapter, verse):
    return [t for (t,) in conn.execute(
        "SELECT content FROM commentary_entries WHERE source = ? AND book = ? AND chapter = ? "
        "AND reference_start <= ? AND reference_end >= ?", (source, book, chapter, verse, verse))]


@pytest.mark.parametrize("source,book,chapter,verse,needle", [
    # Gaebelein's section on Gen 2:4-25 ("Man in Innocency"), not the chapter-1 section
    ("Gaebelein Annotated Bible", "Genesis", 2, 7, "Man in Innocency before the Fall"),
    ("Darby Synopsis", "Romans", 8, 1, "no condemnation"),
    ("Brooks Summarized Bible", "Daniel", 9, 25, "Vision of the seventy weeks"),
    ("Mackintosh Notes on the Pentateuch", "Exodus", 12, 13, "blood"),
    # Lev 6:8-7:38 has no heading of its own: the essay on 5:14-6:7 runs on to chapter 8
    ("Mackintosh Notes on the Pentateuch", "Leviticus", 7, 11, "trespass-offering"),
    # A section that runs on: Mackintosh's Joseph essay (Gen 39-45) covers to the end of Genesis
    ("Mackintosh Notes on the Pentateuch", "Genesis", 50, 20, "In perusing these interesting sections"),
    ("Larkin on Revelation", "Revelation", 20, 4, "THE MILLENNIUM"),
    ("Ironside Expositions", "Romans", 8, 1, "The Triumph of Grace"),
    ("Ironside Expositions", "Esther", 4, 14, "Sackcloth"),
])
def test_known_verse_lands_in_the_right_note(conn, source, book, chapter, verse, needle):
    notes = _notes_on(conn, source, book, chapter, verse)
    assert notes and any(needle in n for n in notes), (source, book, chapter, verse)


def test_chapter_sources_have_one_note_per_chapter(conn):
    for source in ("Brooks Summarized Bible", "Darby Synopsis"):
        dupes = conn.execute(
            "SELECT book, chapter, COUNT(*) FROM commentary_entries WHERE source = ? "
            "GROUP BY book, chapter HAVING COUNT(*) > 1", (source,)).fetchall()
        assert not dupes, (source, dupes[:5])
    # Brooks covers every chapter of the Bible
    assert conn.execute("SELECT COUNT(*) FROM commentary_entries WHERE source = "
                        "'Brooks Summarized Bible'").fetchone()[0] == 1189


def _sermonindex_sources():
    reg = _registry()
    return [c for c in reg.COMMENTARIES.values() if c["loader"] == "sermonindex"]


def test_sermonindex_text_repaired(conn):
    """No entry ends mid-sentence beyond the library's 2% rule, no SermonIndex "entry is
    longer than a module" note is left, no "Isaiah N" that should read "is N" (the rule in
    scripts/commentary_repair.py), and the deleted ALL-CAPS words were put back in Larkin."""
    from backend.commentary_search import SEARCH_TEXT_SQL, register
    from commentary_repair import is_isaiah_leftovers
    register(conn)
    for cfg in _sermonindex_sources():
        texts = [t for (t,) in conn.execute(
            f"SELECT {SEARCH_TEXT_SQL} FROM commentary_entries WHERE source = ?", (cfg["source"],))]
        assert texts, cfg["source"]
        mid = sum(1 for t in texts if t.rstrip()[-1:].islower() or t.rstrip()[-1:] == ",")
        assert mid / len(texts) <= 0.02, cfg["source"]
        assert not any("longer than a Bible module" in t for t in texts), cfg["source"]
        assert sum(is_isaiah_leftovers(t) for t in texts) == 0, cfg["source"]
    brooks = _notes_on(conn, "Brooks Summarized Bible", "Daniel", 9, 25)[0]
    assert "is 476 years" in brooks and "Isaiah 476" not in brooks
    larkin = " ".join(_notes_on(conn, "Larkin on Revelation", "Revelation", 1, 1))
    assert "THE REVELATION OF JESUS CHRIST" in larkin


def test_book_allow_lists_hold(conn):
    """Sources imported by an explicit book list (Ironside) have no rows for other books."""
    reg = _registry()
    for cfg in reg.COMMENTARIES.values():
        if cfg.get("books") is None:
            continue
        books = {r[0] for r in conn.execute(
            "SELECT DISTINCT book FROM commentary_entries WHERE source = ?", (cfg["source"],))}
        assert books and books <= set(cfg["books"]), (cfg["source"], books - set(cfg["books"]))


def test_ironside_left_out_material_stays_out(conn):
    """Later works SermonIndex appended inside allowed books are not imported."""
    texts = " ".join(t for (t,) in conn.execute(
        "SELECT content FROM commentary_entries WHERE source = 'Ironside Expositions'"))
    assert "NOT WRATH BUT RAPTURE" not in texts and "Olive Tree" not in texts
    assert not conn.execute(
        "SELECT COUNT(*) FROM commentary_entries WHERE source = 'Ironside Expositions' AND "
        "((book = 'Romans' AND chapter = 11 AND reference_end >= 25) OR "
        "(book = 'Hosea' AND chapter = 3 AND reference_end >= 4))").fetchone()[0]
    for book in ("Daniel", "Proverbs", "Revelation", "Philippians", "Isaiah"):
        assert not conn.execute("SELECT 1 FROM commentary_entries WHERE source = "
                                "'Ironside Expositions' AND book = ?", (book,)).fetchone(), book
