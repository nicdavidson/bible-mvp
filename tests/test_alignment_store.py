"""Packed alignment storage (backend/alignment_store.py) and its migration.

Unit tests run on synthetic data. The checks at the bottom run against the
built database when it is in the packed layout.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from aligner import text as aligner_text  # noqa: E402
from aligner.pipeline import ensure_table, write_rows  # noqa: E402
from aligner.renderings import build_renderings  # noqa: E402
from backend import alignment_store as store  # noqa: E402


def test_tokenizer_regex_matches_the_aligner():
    assert store.TAPPABLE_WORD_RE.pattern == aligner_text.TAPPABLE_WORD_RE.pattern
    assert store.tappable_words("“Let there be light,” God’s—word") == \
        ["Let", "there", "be", "light", "God’s", "word"]


def test_pack_unpack_round_trip_and_defaults():
    links = [(1, 3, 1.0, 0), (2, 3, 1.0, 0), (4, 7, 0.953, 0), (5, 9, 0.5, 2), (6, 1, 1.0, 2)]
    method, n, text = store.pack(links)
    assert (method, n) == (0, 5)
    assert text == "3,3,,7:953,9:500:2,1:1000:2"
    assert store.unpack(method, text) == links
    assert store.link_at(method, text, 4) == (7, 0.953, 0)
    assert store.link_at(method, text, 3) is None
    assert store.link_at(method, text, 0) is None
    assert store.link_at(method, text, 99) is None
    assert store.pack([]) == (0, 0, "")


def test_confidence_survives_exactly():
    # the per-word table stored round(conf, 3); C/1000 must be the identical float
    for conf in (0.1234, 0.9995, 0.0005, 0.5, 0.7004999, 1 / 3, 0.0):
        _, _, text = store.pack([(1, 1, conf, 2)])
        assert store.unpack(2, text)[0][2] == round(conf, 3)


def test_pack_rejects_duplicate_positions():
    with pytest.raises(ValueError):
        store.pack([(1, 1, 1.0, 0), (1, 2, 1.0, 0)])


def _tiny_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE verses (translation_id TEXT, book TEXT, chapter INT, verse INT, text TEXT);
        CREATE TABLE word_alignments (book TEXT, chapter INT, verse INT, word_position INT,
                                      strong_number TEXT);
        INSERT INTO verses VALUES ('KJV', 'John', 3, 16, 'For God so loved the world');
        INSERT INTO word_alignments VALUES ('John', 3, 16, 1, 'G1063'), ('John', 3, 16, 3, 'G2316'),
            ('John', 3, 16, 4, 'G3779'), ('John', 3, 16, 5, 'G0025'), ('John', 3, 16, 7, 'G2889');
        CREATE TABLE english_word_alignments (
            translation_id TEXT, book TEXT, chapter INT, verse INT,
            english_word_position INT, english_word TEXT, original_word_position INT,
            confidence REAL, method INT);
        INSERT INTO english_word_alignments VALUES
            ('KJV', 'John', 3, 16, 1, 'For', 1, 0.871, 2),
            ('KJV', 'John', 3, 16, 2, 'God', 3, 1.0, 1),
            ('KJV', 'John', 3, 16, 4, 'loved', 5, 1.0, 1),
            ('KJV', 'John', 3, 16, 6, 'world', 7, 0.9, 1);
    """)
    return conn


def test_legacy_table_is_converted_and_dropped():
    conn = _tiny_db()
    ensure_table(conn)
    assert conn.execute("SELECT name FROM sqlite_master WHERE name='english_word_alignments'"
                        ).fetchone() is None
    method, n, links = conn.execute(
        "SELECT method, n_links, links FROM english_alignment_verses").fetchone()
    assert (method, n, links) == (1, 4, "1:871:2,3,,5,,7:900")
    ensure_table(conn)  # idempotent
    assert conn.execute("SELECT COUNT(*) FROM english_alignment_verses").fetchone()[0] == 1
    build_renderings(conn, 0.5)
    assert ("G25", "KJV", "loved", 1) in conn.execute("SELECT * FROM lemma_renderings").fetchall()


def test_conversion_refuses_a_word_that_is_not_the_verse_word():
    conn = _tiny_db()
    conn.execute("UPDATE english_word_alignments SET english_word='Lord' "
                 "WHERE english_word_position=2")
    with pytest.raises(ValueError):
        ensure_table(conn)
    # nothing dropped when the check fails
    assert conn.execute("SELECT COUNT(*) FROM english_word_alignments").fetchone()[0] == 4


def test_write_rows_replaces_one_translation():
    conn = _tiny_db()
    write_rows(conn, "KJV", [(("John", 3, 16), 3, "so", 4, 0.61234, 2)])
    assert conn.execute("SELECT method, n_links, links FROM english_alignment_verses"
                        ).fetchone() == (2, 1, ",,4:612")


# --- against the built database -------------------------------------------------------

DB = ROOT / "data" / "bible.db"


def _packed_db():
    if not DB.exists():
        return False
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        return store.has_packed(conn) and conn.execute(
            "SELECT COUNT(*) FROM english_alignment_verses").fetchone()[0] > 0
    finally:
        conn.close()


needs_db = pytest.mark.skipif(not _packed_db(), reason="packed alignment table not built")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from backend.core import limiter
    from backend.main import app
    limiter.enabled = False
    yield TestClient(app)
    limiter.enabled = True


@needs_db
def test_db_has_no_per_word_table_and_all_words_resolve():
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        assert conn.execute("SELECT 1 FROM sqlite_master WHERE name='english_word_alignments'"
                            ).fetchone() is None
        bad = 0
        for method, links, text in conn.execute("""
                SELECT p.method, p.links, v.text FROM english_alignment_verses p
                JOIN verses v USING (translation_id, book, chapter, verse)
                WHERE p.book IN ('Ruth', 'John')"""):
            n = len(store.tappable_words(text))
            bad += sum(1 for epos, *_ in store.unpack(method, links) if epos > n)
        assert bad == 0
    finally:
        conn.close()


@needs_db
def test_offline_chapter_and_book_agree(client):
    ch = client.get("/api/offline/chapter", params={"book": "Ruth", "chapter": 1,
                                                    "translation": "KJV", "sources": ""}).json()
    bk = client.get("/api/offline/book", params={"book": "Ruth", "translation": "KJV",
                                                 "include_commentary": "false"}).json()
    a, b = ch["alignments"], bk["chapters"]["1"]["alignments"]
    assert len(a) == len(b) > 300
    assert [(x["verse"], x["position"], x["word"]) for x in a] == \
        [(x["verse"], x["position"], x["word"]) for x in b]
    assert list(a[0]) == ["verse", "position", "word", "original_word_position", "original_text",
                          "transliteration", "gloss", "strong_number", "grammar", "definition",
                          "extended_definition", "language"]


@needs_db
def test_stats_counts_linked_words(client):
    stats = client.get("/api/offline/stats").json()["alignments"]
    assert set(stats) >= {"BSB", "KJV", "WEB"} and stats["BSB"]["count"] > 700_000


def test_tidy_drops_redundant_indexes_and_lookups_keep_an_index():
    from tidy_db import tidy
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE word_alignments (id INTEGER PRIMARY KEY, book TEXT, chapter INT, verse INT,
            word_position INT, strong_number TEXT, word_type TEXT,
            UNIQUE(book, chapter, verse, word_position));
        CREATE INDEX idx_alignment_ref ON word_alignments(book, chapter, verse);
        CREATE INDEX idx_alignment_word_type ON word_alignments(word_type);
    """)
    assert tidy(conn) == ["idx_alignment_ref", "idx_alignment_word_type"]
    assert tidy(conn) == []
    for where in ("book='John' AND chapter=3", "book='John' AND chapter=3 AND verse=16",
                  "book='Ruth'"):
        plan = " ".join(r[3] for r in conn.execute(
            f"EXPLAIN QUERY PLAN SELECT * FROM word_alignments WHERE {where}"))
        assert "sqlite_autoindex_word_alignments_1" in plan, plan


def test_function_words_match_the_aligner_and_thresholds():
    from aligner.rerank import WORD_CLASS
    assert store.FUNCTION_WORDS == frozenset(WORD_CLASS)
    assert store.is_function_word("thee") and store.is_function_word("hath")
    assert store.is_function_word("A") and not store.is_function_word("love")
    assert store.rendering_link_ok("love", 0.55) and not store.rendering_link_ok("a", 0.55)
    assert store.rendering_link_ok("a", 0.7)
