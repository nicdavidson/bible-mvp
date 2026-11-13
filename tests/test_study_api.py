"""Study view API: sources with per-selection availability, and per-source entries.

Most tests run against a small throwaway SQLite DB (built here) so they can cover
both states of the data contract: without `commentary_sources` (today) and with it
(after the commentary import lands). One test runs against the real DB.
"""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.routers import study
from tests.fixtures import study_seed


def _make_db(path, with_sources: bool):
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE verses (id INTEGER PRIMARY KEY, translation_id TEXT, book TEXT,
            book_order INTEGER, chapter INTEGER, verse INTEGER, text TEXT);
        CREATE TABLE commentary_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT,
            book TEXT, chapter INTEGER, reference_start INTEGER, reference_end INTEGER,
            content TEXT, searchable_text TEXT);
    """)
    for v in range(1, 37):
        conn.execute("INSERT INTO verses (translation_id, book, book_order, chapter, verse, text)"
                     " VALUES ('BSB', 'John', 43, 3, ?, ?)", (v, f"John three {v}"))
    for v in range(1, 22):
        conn.execute("INSERT INTO verses (translation_id, book, book_order, chapter, verse, text)"
                     " VALUES ('BSB', 'Jude', 65, 1, ?, ?)", (v, f"Jude {v}"))
    # Passage rows stored with start only (as old imports did); Gill-style verse rows
    rows = [("Hale's Exposition", 1, None, "hale one"), ("Hale's Exposition", 22, None, "hale two")]
    rows += [("John Gill", v, v, f"gill {v}") for v in range(1, 37)]
    for src, s, e, c in rows:
        conn.execute("INSERT INTO commentary_entries (source, book, chapter, reference_start,"
                     " reference_end, content) VALUES (?, 'John', 3, ?, ?, ?)", (src, s, e, c))
    conn.execute("INSERT INTO commentary_entries (source, book, chapter, reference_start,"
                 " reference_end, content) VALUES ('John Gill', 'Jude', 1, 3, 3, 'gill jude 3')")
    if with_sources:
        study_seed.seed(conn, chapters=(("John", 3),))
        conn.execute("INSERT INTO commentary_sources (source, sort_order) VALUES (?, 20)",
                     ("Hale's Exposition",))
    conn.commit()
    conn.close()


@pytest.fixture(params=[False, True], ids=["no-sources-table", "with-sources-table"])
def tmp_client(request, tmp_path, monkeypatch):
    db = tmp_path / "study.db"
    _make_db(db, with_sources=request.param)

    def conn_factory():
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(study, "get_db_connection", conn_factory)
    monkeypatch.setattr(study, "DATABASE_PATH", db)
    study._cache.update(key=None, sources=None)
    yield TestClient(app), request.param
    study._cache.update(key=None, sources=None)


def _by_name(data):
    return {s["source"]: s for s in data["sources"]}


class TestStudyEndpoint:
    def test_selection_text_and_canonical_reference(self, tmp_client):
        client, _ = tmp_client
        r = client.get("/api/passage/jn 3:16-18/study")
        assert r.status_code == 200
        d = r.json()
        assert d["reference"] == "John 3:16-18"
        assert (d["verse_start"], d["verse_end"], d["chapter_verses"]) == (16, 18, 36)
        assert [v["verse"] for v in d["verses"]] == [16, 17, 18]

    def test_passage_entry_stored_with_start_only_covers_its_passage(self, tmp_client):
        client, _ = tmp_client
        hale = _by_name(client.get("/api/passage/John 3:16/study").json())["Hale's Exposition"]
        assert hale["kind"] == "passage"
        assert hale["selection_entries"] == 1
        assert hale["ranges"] == [{"start": 1, "end": 21}]

    def test_verse_source_counts_each_selected_verse(self, tmp_client):
        client, _ = tmp_client
        gill = _by_name(client.get("/api/passage/John 3:16-18/study").json())["John Gill"]
        assert gill["kind"] == "verse"
        assert gill["short_name"] == "Gill"          # fallback metadata (_KNOWN)
        assert gill["author"] == "John Gill"
        assert gill["selection_entries"] == 3
        assert gill["chapter_entries"] == 36

    def test_every_source_listed_even_without_entries(self, tmp_client):
        client, with_sources = tmp_client
        srcs = _by_name(client.get("/api/passage/John 3:16/study").json())
        if not with_sources:
            assert set(srcs) == {"John Gill", "Hale's Exposition"}
            return
        assert len(srcs) >= 11
        pell = srcs["Pell's Expositor"]           # passage that stops at v12
        assert pell["selection_entries"] == 0
        assert pell["nearest"] == {"start": 1, "end": 12}
        cal = srcs["Calloway Word Notes"]          # verse source with a gap 11-24
        assert cal["selection_entries"] == 0 and cal["nearest"]["start"] in (10, 25)
        assert srcs["Lindqvist Chapter Studies"]["ranges"] == [{"start": 1, "end": 36}]
        assert srcs["Okafor Study Notes"]["license"] == "CC BY 4.0"
        assert srcs["Okafor Study Notes"]["attribution"]

    def test_table_sort_order_wins(self, tmp_client):
        client, with_sources = tmp_client
        names = [s["source"] for s in client.get("/api/passage/John 3:16/study").json()["sources"]]
        if with_sources:
            assert names[:3] == ["John Gill", "Hale's Exposition", "Whitcombe's Verse Notes"]
        else:
            assert names == sorted(names, key=str.lower)

    def test_whole_chapter_selection(self, tmp_client):
        client, _ = tmp_client
        d = client.get("/api/passage/John 3/study").json()
        assert d["reference"] == "John 3"
        assert (d["verse_start"], d["verse_end"]) == (1, 36)
        assert _by_name(d)["Hale's Exposition"]["selection_entries"] == 2

    def test_range_past_chapter_end_is_clamped(self, tmp_client):
        client, _ = tmp_client
        d = client.get("/api/passage/John 3:35-50/study").json()
        assert d["verse_end"] == 36

    def test_bad_reference(self, tmp_client):
        client, _ = tmp_client
        assert client.get("/api/passage/John 99:1/study").status_code == 404
        assert client.get("/api/passage/John 3:80/study").status_code == 404

    def test_single_chapter_book(self, tmp_client):
        client, _ = tmp_client
        d = client.get("/api/passage/Jude 3/study").json()
        assert (d["chapter"], d["verse_start"]) == (1, 3)
        assert _by_name(d)["John Gill"]["selection_entries"] == 1


class TestCommentaryEntries:
    def test_source_filter_by_slug_and_effective_range(self, tmp_client):
        client, _ = tmp_client
        d = client.get("/api/passage/John 3:16/commentary?source=hale-s-exposition").json()
        assert len(d["entries"]) == 1
        e = d["entries"][0]
        assert (e["source"], e["range_start"], e["range_end"]) == ("Hale's Exposition", 1, 21)
        assert e["content"] == "hale one"

    def test_source_filter_by_name(self, tmp_client):
        client, _ = tmp_client
        d = client.get("/api/passage/John 3:16-17/commentary", params={"source": "John Gill"}).json()
        assert [e["range_start"] for e in d["entries"]] == [16, 17]

    def test_whole_chapter_all_sources(self, tmp_client):
        client, _ = tmp_client
        d = client.get("/api/passage/John 3/commentary").json()
        srcs = {e["source"] for e in d["entries"]}
        assert {"John Gill", "Hale's Exposition"} <= srcs
        assert all("range_start" in e and "range_end" in e for e in d["entries"])

    def test_unknown_source_is_empty_not_error(self, tmp_client):
        client, _ = tmp_client
        r = client.get("/api/passage/John 3:16/commentary?source=nobody")
        assert r.status_code == 200 and r.json()["entries"] == []


class TestSourcesEndpoint:
    def test_lists_sources_with_metadata(self, tmp_client):
        client, with_sources = tmp_client
        r = client.get("/api/commentary/sources")
        assert r.status_code == 200
        srcs = {s["slug"]: s for s in r.json()["sources"]}
        assert srcs["john-gill"]["kind"] == "verse"
        assert srcs["hale-s-exposition"]["kind"] == "passage"
        if with_sources:
            assert srcs["lindqvist-chapter-studies"]["kind"] == "chapter"
            assert srcs["okafor-study-notes"]["kind"] == "notes"
        assert "cache-control" in {k.lower() for k in r.headers}


def test_effective_ranges_rules():
    rows = [{"reference_start": 1, "reference_end": None},
            {"reference_start": 5, "reference_end": 9},
            {"reference_start": 12, "reference_end": 12},
            {"reference_start": 14, "reference_end": None}]
    # A filled end is trusted even when it is a single verse; only a missing end is inferred
    assert study.effective_ranges(rows, "passage", 20) == [(1, 4), (5, 9), (12, 12), (14, 20)]
    assert study.effective_ranges(rows, "verse", 20) == [(1, 1), (5, 9), (12, 12), (14, 14)]
    assert study.effective_ranges(rows, "chapter", 20) == [(1, 20)] * 4


# The owner's library (2026-11-13), in this order: the five kept after the trim plus the
# dispensational sources added the same day. The other eight were removed.
LIBRARY = [("scofield-notes-1917", "Scofield Notes (1917)"), ("john-gill", "John Gill"),
           ("jamieson-fausset-brown", "Jamieson-Fausset-Brown"),
           ("tyndale-study-notes", "Tyndale Study Notes"),
           ("gaebelein-annotated-bible", "Gaebelein Annotated Bible"),
           ("ironside-expositions", "Ironside Expositions"), ("darby-synopsis", "Darby Synopsis"),
           ("brooks-summarized-bible", "Brooks Summarized Bible"),
           ("mackintosh-notes-on-the-pentateuch", "Mackintosh Notes on the Pentateuch"),
           ("larkin-on-revelation", "Larkin on Revelation"), ("treasury-of-david", "Treasury of David")]
REMOVED = ["matthew-henry", "keil-delitzsch", "barnes-notes", "john-calvin", "john-wesley",
           "adam-clarke", "people-s-new-testament", "catena-aurea"]


def test_real_db_has_exactly_the_library_in_order():
    study._cache.update(key=None, sources=None)
    client = TestClient(app)
    srcs = client.get("/api/commentary/sources").json()["sources"]
    assert [(s["slug"], s["source"]) for s in srcs] == LIBRARY
    study_srcs = client.get("/api/passage/John 3:16/study").json()["sources"]
    assert [s["slug"] for s in study_srcs] == [slug for slug, _ in LIBRARY]
    for slug in REMOVED:   # old deep links ask for these: nothing, not an error
        r = client.get(f"/api/passage/John 3:16/commentary?source={slug}")
        assert r.status_code == 200 and r.json()["entries"] == []


# ---------- round two: real library (items 1, 6, 7) ----------

def test_requires_attribution_comes_from_license(tmp_client):
    client, with_sources = tmp_client
    srcs = {s["source"]: s for s in client.get("/api/commentary/sources").json()["sources"]}
    assert srcs["John Gill"]["requires_attribution"] is False          # public domain
    if with_sources:
        assert srcs["Okafor Study Notes"]["requires_attribution"] is True    # CC BY 4.0
        assert srcs["Ferreira Greek Notes"]["requires_attribution"] is True  # CC BY-SA 4.0


@pytest.mark.parametrize("lic,expected", [
    ("Public domain", False), ("Public Domain (US)", False), ("CC0", False), (None, False),
    ("CC BY 4.0", True), ("CC BY-SA 4.0", True), ("Some custom license", True),
])
def test_requires_attribution_rules(lic, expected):
    assert study.requires_attribution(lic) is expected


def _real_client():
    study._cache.update(key=None, sources=None)
    return TestClient(app)


def _real_has_library(client):
    return any(s["slug"] == "treasury-of-david" for s in client.get("/api/commentary/sources").json()["sources"])


def test_real_overview_and_verse_entries_both_listed_tightest_first():
    """Treasury of David on Ps 23:1-3: verse entries 1, 2, 3 plus the whole-psalm overview."""
    client = _real_client()
    if not _real_has_library(client):
        pytest.skip("DB without the commentary library")
    td = _by_name(client.get("/api/passage/Psalms 23:1-3/study").json())["Treasury of David"]
    spans = sorted((r["start"], r["end"]) for r in td["ranges"])
    assert {(1, 1), (2, 2), (3, 3), (1, 6)} <= set(spans)
    entries = client.get("/api/passage/Psalms 23:1-3/commentary?source=treasury-of-david").json()["entries"]
    order = [(e["range_start"], e["range_end"]) for e in entries]
    assert order.index((1, 1)) < order.index((1, 6))       # same start: shortest first
    tyn = _by_name(client.get("/api/passage/John 3:16/study").json())["Tyndale Study Notes"]
    assert tyn["requires_attribution"] is True and "CC BY-SA" in tyn["attribution"]


class TestOfflineSources:
    """Offline downloads take a source list (item 7)."""

    def test_chapter_sources_filter(self):
        client = _real_client()
        all_ = client.get("/api/offline/chapter?book=John&chapter=3").json()["commentary"]
        none = client.get("/api/offline/chapter?book=John&chapter=3&sources=").json()["commentary"]
        gill = client.get("/api/offline/chapter?book=John&chapter=3&sources=john-gill").json()["commentary"]
        assert none == []
        assert gill and {e["source"] for e in gill} == {"John Gill"}
        assert len(all_) > len(gill)

    def test_book_commentary_sources_by_name_or_slug(self):
        client = _real_client()
        r = client.get("/api/offline/commentary", params={"book": "Jude", "sources": "Jamieson-Fausset-Brown,john-gill"})
        assert r.status_code == 200
        assert {e["source"] for e in r.json()["entries"]} == {"Jamieson-Fausset-Brown", "John Gill"}
        unknown = client.get("/api/offline/commentary?book=Jude&sources=nobody").json()["entries"]
        assert unknown == []
        removed = client.get("/api/offline/commentary?book=Jude&sources=matthew-henry").json()["entries"]
        assert removed == []
        old = client.get("/api/offline/commentary?book=Jude").json()["entries"]   # old callers: all
        assert len({e["source"] for e in old}) >= 2

    def test_book_endpoint_sources(self):
        client = _real_client()
        d = client.get("/api/offline/book?book=Jude&sources=john-gill").json()
        comm = [e for ch in d["chapters"].values() for e in ch.get("commentary", [])]
        assert comm and {e["source"] for e in comm} == {"John Gill"}

    def test_sources_with_sizes_and_defaults(self):
        client = _real_client()
        if not _real_has_library(client):
            pytest.skip("DB without the commentary library")
        srcs = client.get("/api/offline/commentary/sources").json()["sources"]
        by = {s["slug"]: s for s in srcs}
        assert by["john-gill"]["bytes"] > 1_000_000
        assert all(s["bytes"] >= 0 and "default" in s for s in srcs)
        assert 1 <= sum(s["default"] for s in srcs) <= 3


# ---------- cross-references with text (study view pane) ----------

def test_real_crossrefs_carry_text_and_votes():
    client = _real_client()
    r = client.get("/api/passage/john 3:16-18/study/crossrefs")
    assert r.status_code == 200
    d = r.json()
    assert d["reference"] == "John 3:16-18" and "OpenBible.info" in d["credit"]
    refs = d["cross_references"]
    assert len(refs) > 40
    assert {x["source_verse"] for x in refs} <= {16, 17, 18}
    rom = next(x for x in refs if (x["target_book"], x["target_chapter"], x["target_verse"]) == ("Romans", 5, 8))
    assert rom["votes"] > 500 and rom["text"].startswith("But God proves His love")
    assert all(x["text"] for x in refs)
    # Translation follows the reader
    kjv = client.get("/api/passage/John 3:16/study/crossrefs?translation=KJV").json()["cross_references"]
    assert any("commendeth" in (x["text"] or "") for x in kjv)


def test_crossrefs_bad_reference_is_an_error():
    client = _real_client()
    assert client.get("/api/passage/Nothing 99/study/crossrefs").status_code in (400, 404)
    assert client.get("/api/passage/John 3:99/study/crossrefs").status_code == 404
