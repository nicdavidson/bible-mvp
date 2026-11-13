"""Scripture-to-hymn index: ABC parsing, reference parsing, join keys, and the API."""
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from backend.hymn_keys import keys_for, title_key  # noqa: E402
from import_hymns import (credit_refs, first_line, hymn_rows, parse_refs,  # noqa: E402
                          quotes_for, syllables, words_public_domain)

MAXV = {("Luke", 1): 80, ("Psalms", 33): 22}

ABC = """%OHSCRIP Jn 9:25, Eph 2:4-9, 43:1
%OHTOPICS {Assurance}, {Grace [1,2]}
%OHCATEGORY CROSS AND COMFORT
%OHMETRICAL 8 6 8 6
%OHAUTHOR Newton, John (1725-1807)
%OHTRANSLATOR none
X: 219
T: Amazing Grace
T: (also known as Faith's Review and Expectation)
C: Words: John Newton, 1779.
C: Music: 'New Britain' James P. Carrell, 1831.
C: copyright: public domain.  This score is a part of the Open Hymnal Project.
[V: S1V1]  D | G2 B/G/ |
w: 1.~A- maz- ing * grace! How sweet the sound That
w: 2.~'Twas grace that * taught my heart to fear, And
[V: S1V1]  G2 B/G/ |
w: saved a * wretch like me!
w: grace my * fears re- lieved;
%OHSCRIP Ps 23
%OHMETRICAL 8 6 8 6
%OHAUTHOR Someone, Modern
X: 1
T: A Modern Text
C: Words: Psalm 23, para. A. Writer, 2009.
C: copyright: music and setting public domain.  Words: Copyright 2009, A. Writer.
[V: S1V1] D |
w: 1.~The Lord's my shep- herd, I'll not want
"""


def test_syllables_and_first_line_by_metre():
    syl = syllables("1.~A- maz- ing * grace! How sweet the sound That")
    assert syl[:3] == [("A", True), ("maz", True), ("ing", False)]
    assert first_line(syl, "8 6 8 6") == "Amazing grace! How sweet the sound"
    assert first_line(syllables("1.~Ho- ly, ho- ly, ho- ly! Lord"), "6 6 6 6") == \
        "Holy, holy, holy!"


def test_words_public_domain():
    assert words_public_domain("public domain.  This score is a part of the Open Hymnal")
    assert words_public_domain("Words and Music, public domain.  Setting: Copyright 2009 B.")
    assert not words_public_domain("music and setting public domain.  Words: Copyright 2005")
    assert not words_public_domain("Tune public domain.  Lyrics and Setting Copyright 2012")
    assert not words_public_domain("This hymn (lyrics, music, and setting) may be freely ...")


def test_parse_refs():
    refs = parse_refs("Jn 9:25, Eph 2:4-9, 43:2-5, Ps 33, Lv 25:9-10, 1Pt 2:5, 1Cor 5:7b", MAXV)
    assert [r[:4] for r in refs] == [
        ("John", 9, 25, 25), ("Ephesians", 2, 4, 9), ("Ephesians", 43, 2, 5),
        ("Psalms", 33, None, None), ("Leviticus", 25, 9, 10), ("1 Peter", 2, 5, 5),
        ("1 Corinthians", 5, 7, 7)]
    cross = parse_refs("Lk 1:67-2:10", MAXV)
    assert [r[:4] for r in cross] == [("Luke", 1, 67, 80), ("Luke", 2, 1, 10)]
    assert parse_refs("\\nMal 4:2", MAXV)[0][:4] == ("Malachi", 4, 2, 2)


def test_credit_refs():
    assert [r[:4] for r in credit_refs("Psalm 146.  Translated by ..., 1909.", MAXV)] == \
        [("Psalms", 146, None, None)]
    assert [r[:4] for r in credit_refs("Martin Luther, 1526, after Is 6:1-4.", MAXV)] == \
        [("Isaiah", 6, 1, 4)]


def test_title_keys():
    assert title_key("The Lord's My Shepherd") == "lordsmyshepherd"
    assert title_key("Holy, Holy, Holy!") == title_key("Holy Holy Holy")
    assert keys_for("Some Glad Morning (I'll Fly Away)") == {"somegladmorning", "illflyaway"}


def test_hymn_rows_from_abc():
    index = ({("i", "once", "was", "lost", "but"): {("John", 9, 25)}},
             {w: 1000 for w in ("i", "once", "was", "lost", "but")})
    hymns, links = hymn_rows(ABC, MAXV, None)
    amazing, modern = hymns
    assert amazing[0] == "oh-219" and amazing[1] == "Amazing Grace"
    assert amazing[3] == "Amazing grace! How sweet the sound"   # first line (PD words)
    assert amazing[4] == "Newton, John (1725-1807)" and amazing[6] == 1779
    assert amazing[8] == "New Britain" and amazing[10] == "8 6 8 6" and amazing[13] == 1
    assert "faithsreviewandexpectation" in amazing[16]
    assert modern[3] is None and modern[13] == 0   # copyrighted words: no text stored
    kinds = {(lk[0], lk[5]) for lk in links}
    assert ("oh-219", "reference") in kinds and ("oh-1", "paraphrase") in kinds
    assert ("Ephesians", 43, 1, 1) in [lk[1:5] for lk in links]  # book carried forward
    assert quotes_for(["I once was lost but now am found"], index) == []  # common words only


def test_quotes_need_a_long_run_or_a_rare_word():
    index = {("holy", "holy", "holy", "lord", "god"): {("Revelation", 4, 8)},
             ("holy", "holy", "lord", "god", "almighty"): {("Revelation", 4, 8)},
             ("that", "we", "may", "live", "and"): {("Genesis", 42, 2)}}
    freq = {"almighty": 57, "holy": 500, "live": 600, "may": 900}
    found = quotes_for(["Holy, holy, holy! Lord God Almighty!", "that we may live and die"],
                       (index, freq))
    assert found == [(("Revelation", 4, 8), "holy holy holy lord god almighty")]


# --- API on the built database --------------------------------------------------------------

DB = ROOT / "data" / "bible.db"


def _built():
    if not DB.exists():
        return False
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        return conn.execute("SELECT 1 FROM sqlite_master WHERE name='hymn_scripture'"
                            ).fetchone() is not None
    finally:
        conn.close()


needs_db = pytest.mark.skipif(not _built(), reason="hymn index not built")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from backend.main import app
    return TestClient(app)


@needs_db
def test_for_passage_ranks_paraphrase_first(client):
    d = client.get("/api/hymns/for-passage", params={"ref": "Psalm 23"}).json()
    assert d["hymns"][0]["title"] == "The Lord's My Shepherd"
    assert d["hymns"][0]["links"][0]["kind"] == "paraphrase"
    assert all(h["match"] in ("passage", "chapter") for h in d["hymns"])
    for h in d["hymns"]:
        for lk in h["links"]:
            assert lk["source"] in d["sources"]


@needs_db
def test_for_passage_quote_and_groups_tunes(client):
    d = client.get("/api/hymns/for-passage", params={"ref": "Revelation 4:8"}).json()
    top = d["hymns"][0]
    assert top["title"] == "Holy, Holy, Holy" and top["links"][0]["kind"] == "quotes"
    assert "holy holy holy" in top["links"][0]["evidence"]
    fortress = client.get("/api/hymns/for-passage",
                          params={"book": "Romans", "chapter": 8, "verse_start": 37,
                                  "verse_end": 39}).json()
    f = next(h for h in fortress["hymns"] if h["title"] == "A Mighty Fortress Is Our God")
    assert len(f["settings"]) == 2


@needs_db
def test_chapter_only_matches_can_be_excluded(client):
    d = client.get("/api/hymns/for-passage",
                   params={"ref": "Lamentations 3:22-23", "include_chapter": "false"}).json()
    assert {h["match"] for h in d["hymns"]} == {"passage"}
    assert "Great Is Thy Faithfulness" in [h["title"] for h in d["hymns"]]


@needs_db
def test_hymn_detail_lookup_and_errors(client):
    h = client.get("/api/hymns/oh-219").json()
    assert h["title"] == "Amazing Grace" and h["words_public_domain"] is True
    assert any(p["reference"] == "John 9:25" for p in h["passages"])
    found = client.get("/api/hymns", params={"key": "Amazing Grace!"}).json()
    assert {x["id"] for x in found["hymns"]} == {"oh-219", "olney-book-1-hymn-41"}
    assert client.get("/api/hymns", params={"q": "wondrous cross"}).json()["total"] >= 3
    assert client.get("/api/hymns/nope").status_code == 404
    assert client.get("/api/hymns/for-passage").status_code == 400
    assert client.get("/api/hymns/for-passage", params={"ref": "Psalm 999"}).status_code == 404


# --- psalters and hymnals with their own Scripture structure ---------------------------

import hymn_sources as hs  # noqa: E402

PG_PSALMS = """header
*** START OF THE PROJECT GUTENBERG EBOOK THE PSALMS OF DAVID ***
Psalm 90:2. 1-5. First Part. C. M.
Man frail, and God eternal.

1 Our God, our help in ages past,
Our hope for years to come,

Psalm 100:1. 1st M. A plain translation.
Praise to our Creator.

1 Ye nations round the earth, rejoice
Before the Lord, your sovereign King;

Psalm 148:1. As the 148th Psalm.
Universal praise.

[1 Ye tribes of Adam, join
*** END OF THE PROJECT GUTENBERG EBOOK THE PSALMS OF DAVID ***
"""

PG_HSS = """*** START OF THE PROJECT GUTENBERG EBOOK HYMNS ***
Hymn 3:7.
Crucifixion to the world by the cross of Christ, Gal. 6. 14.

1 When I survey the wondrous cross
On which the Prince of glory died,

Hymn 1:2.
The deity of Christ, John 1. 1-3 14.
Col. 9. 16.

1 Ere the blue heavens were stretch'd abroad,
*** END OF THE PROJECT GUTENBERG EBOOK HYMNS ***
"""

MV = {("Psalms", 90): 17, ("Psalms", 100): 5, ("Psalms", 148): 14, ("Galatians", 6): 18,
      ("John", 1): 51, ("Colossians", 1): 29}


def test_watts_psalm_headings(tmp_path):
    f = tmp_path / "p.txt"
    f.write_text(PG_PSALMS)
    rows = {r["source_ref"]: r for r in hs.watts_psalms(f, MV)}
    assert rows["Psalm 90:2"]["first_line"] == "Our God, our help in ages past"
    assert [x[:4] for x in rows["Psalm 90:2"]["refs"]] == [("Psalms", 90, 1, 5)]
    # '1st M.' is the metre, not verse 1; 'As the 148th Psalm.' is a tune note
    assert [x[:4] for x in rows["Psalm 100:1"]["refs"]] == [("Psalms", 100, None, None)]
    assert rows["Psalm 148:1"]["first_line"] == "Ye tribes of Adam, join"


def test_watts_hss_text_headings(tmp_path):
    from import_hymns import resolve_book
    f = tmp_path / "h.txt"
    f.write_text(PG_HSS)
    rows = {r["source_ref"]: r for r in hs.watts_hss(f, MV, resolve_book)}
    assert [x[:4] for x in rows["Hymn 3:7"]["refs"]] == [("Galatians", 6, 14, 14)]
    # 'Col. 9. 16' is a misprint (Colossians has 4 chapters): dropped, not guessed
    assert [x[:4] for x in rows["Hymn 1:2"]["refs"]] == [("John", 1, 1, 3), ("John", 1, 14, 14)]


def test_osis_refs_drop_impossible_verses():
    mv = {("Isaiah", 33): 24, ("1 Chronicles", 17): 27}
    get = hs.OSIS_BOOKS.get
    assert hs._osis_refs("Bible:Isa.33.27-Isa.33.28", get, mv) == []
    assert hs._osis_refs("Bible:1Chr.17.16-1Chr.17.17", get, mv) == [("1 Chronicles", 17, 16, 17)]


@needs_db
def test_psalm_100_finds_old_hundredth_and_texts_merge(client):
    d = client.get("/api/hymns/for-passage", params={"ref": "Psalm 100"}).json()
    old100 = next(h for h in d["hymns"] if h["first_line"] == "All people that on earth do dwell")
    assert set(old100["sources_for_text"]) == {"ccel-scottish-psalter", "openhymnal"}
    grace = client.get("/api/hymns/for-passage", params={"ref": "1 Chronicles 17:16"}).json()
    top = grace["hymns"][0]
    assert top["links"][0]["kind"] == "based_on" and top["links"][0]["source"] == "ccel-olney"
    assert {"ccel-olney", "openhymnal"} <= set(top["sources_for_text"])
    joy = client.get("/api/hymns", params={"key": "Joy to the World"}).json()
    assert joy["total"] >= 2   # title matches the start of the first line


@needs_db
def test_familiar_hymn_first_within_the_same_link_strength(client):
    """Psalm 100: "All People That On Earth Do Dwell" (Open Hymnal + Scottish Psalter)
    before the metrical versions found only in one psalter; plain references stay after
    every paraphrase, however familiar."""
    d = client.get("/api/hymns/for-passage", params={"ref": "Psalm 100"}).json()
    assert "familiar" in d["ranking"]
    hymns = d["hymns"]
    assert hymns[0]["first_line"] == "All people that on earth do dwell"
    kinds = [h["links"][0]["kind"] for h in hymns if h["match"] == "passage"]
    assert kinds == sorted(kinds, key=lambda k: k == "reference")   # strength still leads
    # Isaiah 6: among plain references, a hymnal text with a tune before one without
    isa = [h["title"] for h in client.get("/api/hymns/for-passage",
                                          params={"ref": "Isaiah 6"}).json()["hymns"]]
    assert isa.index("Holy, Holy, Holy") < isa.index("For The Beauty Of The Earth")


@needs_db
def test_hymn_topics_and_tunes_read_cleanly(client):
    d = client.get("/api/hymns/oh-28").json()
    assert "God, Majesty & Power of" in d["topics"]
    ps23 = client.get("/api/hymns/for-passage", params={"ref": "Psalm 23"}).json()["hymns"][0]
    assert "`" not in ps23["tune"] and "James’ Air" in ps23["tune"]
    assert all("`" not in (s["tune"] or "") for s in ps23["settings"])
