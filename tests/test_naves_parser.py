"""Nave's reference parser (scripts/import_naves.py) on real lines from the CSV."""
import csv
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from import_naves import CSV_PATH, parse_references  # noqa: E402

from backend.database import DATABASE_PATH  # noqa: E402
from backend.main import app  # noqa: E402


def refs(text):
    return [(r["book"], r["chapter"], r["verse_start"], r["verse_end"])
            for r in parse_references(text)]


def test_same_book_verse_continuation():
    # CARE, "REMEDY FOR": 55:22 used to be dropped
    got = refs("-REMEDY FOR PSA 37:5; 55:22; PRO 16:3; JER 17:7,8")
    assert got == [("Psalms", 37, 5, 5), ("Psalms", 55, 22, 22), ("Proverbs", 16, 3, 3),
                   ("Jeremiah", 17, 7, 7), ("Jeremiah", 17, 8, 8)]


def test_same_book_whole_chapter_continuation():
    got = refs("-Consecration of, to the priesthood EXO 28; 29; LEV 8")
    assert got == [("Exodus", 28, 1, None), ("Exodus", 29, 1, None), ("Leviticus", 8, 1, None)]


def test_numbered_book_after_semicolon_is_a_new_book():
    # "; 1CH" must not be read as chapter 1 of Joshua
    got = refs("-Lineage of EXO 6:16-20; JOS 21:4,10; 1CH 6:2,3; 23:13")
    assert got == [("Exodus", 6, 16, 20), ("Joshua", 21, 4, 4), ("Joshua", 21, 10, 10),
                   ("1 Chronicles", 6, 2, 2), ("1 Chronicles", 6, 3, 3),
                   ("1 Chronicles", 23, 13, 13)]


def test_ranges_lists_and_comma_space():
    assert refs("1CH 6:3-15,50-53; 24") == [("1 Chronicles", 6, 3, 15),
                                            ("1 Chronicles", 6, 50, 53),
                                            ("1 Chronicles", 24, 1, None)]
    assert refs("PSA 119:82,84, 107") == [("Psalms", 119, 82, 82), ("Psalms", 119, 84, 84),
                                          ("Psalms", 119, 107, 107)]


def test_non_book_capitals_are_ignored():
    assert refs("-See PRIEST, HIGH") == []
    assert refs("-OF GOD 1 time") == []


def test_continuation_does_not_cross_lines():
    assert refs("-A EXO 3:1\n-12 tribes") == [("Exodus", 3, 1, 1)]


@pytest.mark.skipif(not CSV_PATH.exists(), reason="Nave's CSV not present")
def test_whole_csv_count():
    """Pins the 2026-11 counts: 49,399 before the fix, 75,878 after, none lost."""
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))[1:]
    assert sum(len(parse_references(r[2])) for r in rows if len(r) > 2) == 75878


def _db_has_rebuilt_naves():
    try:
        conn = sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True)
        n = conn.execute("SELECT COUNT(*) FROM naves_topic_refs").fetchone()[0]
        conn.close()
        return n == 75878
    except sqlite3.Error:
        return False


@pytest.mark.skipif(not _db_has_rebuilt_naves(), reason="run: build_db.py --step naves")
def test_topics_for_verse_only_matches_covering_refs():
    client = TestClient(app)
    topics = {t["topic"] for t in client.get(
        "/api/topics/for-verse", params={"book": "John", "chapter": 3, "verse": 36}
    ).json()["topics"]}
    # COWARDICE cites John 3:1-2 only; it used to match every later verse in the chapter.
    assert "COWARDICE" not in topics
    care = {t["topic"] for t in client.get(
        "/api/topics/for-verse", params={"book": "Psalms", "chapter": 55, "verse": 22}
    ).json()["topics"]}
    assert "CARE" in care  # recovered continuation ref
