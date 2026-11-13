"""Computed word studies: parsing rules, lexicon import rules, and the API on a built DB."""
import sqlite3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from backend.word_study import (editions_of, form_of, is_function_lemma,  # noqa: E402
                                main_segment, pos_code, section_of)
from build_word_study import g2, log_dice  # noqa: E402
from import_lexicons import derivation_words, sense_text, strongs_relations  # noqa: E402


# --- parsing codes -------------------------------------------------------------------------

@pytest.mark.parametrize("code,main,pos", [
    ("HR/Ncfsa", "Ncfsa", "N"), ("HC/Vqw3ms", "Vqw3ms", "V"), ("Hc/Vqw3ms", "Vqw3ms", "V"),
    ("HTd/Ncmpa", "Ncmpa", "N"), ("ANcbsd/Ta", "Ncbsd", "N"), ("HR/Sp3ms", "R", "R"),
    ("HTo", "To", "T"), ("HC/To", "To", "T"), ("HNcmpc/Sp2ms", "Ncmpc", "N"),
])
def test_hebrew_main_segment(code, main, pos):
    assert main_segment(code) == main
    assert pos_code(code, hebrew=True) == pos


def test_greek_pos_uses_language_not_first_letter():
    # ADV / HEB start with A / H but are Greek codes
    assert pos_code("ADV", hebrew=False) == "ADV"
    assert pos_code("HEB", hebrew=False) == "HEB"
    assert pos_code("CONJ + G1565", hebrew=False) == "CONJ"


@pytest.mark.parametrize("code,hebrew,key,label", [
    ("V-AAI-3S", False, "V-AAI", "aorist active indicative"),
    ("V-2AAI-3S", False, "V-2AAI", "second aorist active indicative"),
    ("V-PAP-NSM", False, "V-PAP", "present active participle"),
    ("N-ASM", False, "N-AS", "accusative singular"),
    ("ADV", False, "ADV", "adverb"),
    ("HVqp3ms", True, "Vqp", "Qal perfect"),
    ("HC/Vqw3ms", True, "Vqw", "Qal sequential imperfect"),
    ("HVNrmsa", True, "VNr", "Niphal participle"),
    ("HNcmpc/Sp2ms", True, "N-pc", "plural construct"),
    ("AVqp3ms", True, "Vqp", "Peal perfect"),
])
def test_form_labels(code, hebrew, key, label):
    assert form_of(code, hebrew) == (key, label)


def test_editions_exact_names():
    eds = editions_of("NA28+NA27+Tyn+SBL+WH+Treg+TR«3+Byz»1")
    assert "TR" in eds and "Byz" in eds and "Treg" in eds
    assert "TR" not in editions_of("NA28+SBL+WH+Treg")


def test_function_lemmas_and_sections():
    assert is_function_lemma("G3588", "T") and is_function_lemma("H3605", "N")
    assert not is_function_lemma("G26", "N")
    assert section_of(1) == "Law" and section_of(19) == "Wisdom and Poetry"
    assert section_of(45) == "Paul's Letters" and section_of(66) == "Revelation"


def test_association_measures():
    # 24 shared verses of 106 and 226 in 7,917 (agape/pistis in the NT)
    assert round(g2(24, 106, 226, 7917), 1) == 64.1
    assert round(log_dice(24, 106, 226), 2) == 11.21
    # independence gives G2 = 0
    assert abs(g2(10, 100, 100, 1000)) < 1e-9


# --- lexicon import rules --------------------------------------------------------------------

TEI = "http://www.crosswire.org/2013/TEIOSIS/namespace"


def _seg(xml):
    return ET.fromstring(f'<seg xmlns="{TEI}" type="derivation">{xml}</seg>')


def test_abbott_smith_derivation_words():
    assert derivation_words(_seg("(&lt; <foreign>τέλος</foreign>, <foreign>ὠνέομαι</foreign>)")) \
        == ["τέλος", "ὠνέομαι"]
    assert derivation_words(_seg("(&lt; <ref><foreign>βαπτίζω</foreign></ref>) , prop., "
                                 "the act of which <ref><foreign>βάπτισμα</foreign></ref>")) \
        == ["βαπτίζω"]
    # a "see under" pointer is not a source
    assert derivation_words(_seg("(&lt; <foreign>στοργή</foreign>, family affection, v.s. "
                                 "<foreign>ἀγάπη</foreign>)")) == ["στοργή"]
    assert derivation_words(_seg("(an Oriental word, <foreign>x</foreign>)")) == []


def test_sense_text_indents_nested_senses():
    el = ET.fromstring(f'<sense xmlns="{TEI}">love, <sense n="1.">of men: <sense n="(a)">to one '
                       'another</sense></sense><sense n="2.">of God</sense></sense>')
    assert sense_text(el) == "love,\n1. of men:\n  (a) to one another\n2. of God"


def test_strongs_derivation_relations():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE lexicon (strong_number TEXT, derivation TEXT)")
    conn.executemany("INSERT INTO lexicon VALUES (?, ?)", [
        ("G26", "from G25 (ἀγαπάω);"), ("G25", None),
        ("H1285", "from H1262 (in the sense of cutting (like H1254));"), ("H1262", None),
        ("H1254", None),
        ("G343", "from G303 (ἀνά) (in the sense of reversal) and G2572 (καλύπτω);"),
        ("G303", None), ("G2572", None), ("G63", "from G68 (ἀγρός) (in the sense of G833)"),
        ("G68", None), ("G833", None)])
    rel = set()
    strongs_relations(conn, rel)
    assert ("G26", "G25", "derived_from", "strongs", "") in rel
    assert ("G25", "G26", "source_of", "strongs", "") in rel
    assert ("H1285", "H1262", "derived_from", "strongs", "") in rel
    assert ("H1285", "H1254", "compare", "strongs", "") in rel
    assert ("G343", "G2572", "derived_from", "strongs", "") in rel
    assert ("G63", "G833", "compare", "strongs", "") in rel


# --- API on the built database -----------------------------------------------------------------

DB = ROOT / "data" / "bible.db"


def _built():
    if not DB.exists():
        return False
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        return all(conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (t,)).fetchone()
                   for t in ("lexicon_entries", "lemma_profile", "lemma_samples"))
    finally:
        conn.close()


needs_db = pytest.mark.skipif(not _built(), reason="word study tables not built")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from backend.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def agape(client):
    return client.get("/api/word/G26/study").json()


@needs_db
def test_counts_agree_with_the_printed_lexicons(client, agape):
    # Abbott-Smith prints 116 NT occurrences for ἀγάπη; BDB prints 247 for חֶסֶד I
    assert agape["occurrences"]["total"] == 116
    a_s = next(s for s in agape["lexicons"] if s["source"] == "abbott-smith")
    assert a_s["entries"][0]["meta"]["nt_occurrences"] == 116
    hesed = client.get("/api/word/H2617/study").json()
    assert hesed["occurrences"]["total"] == 247
    bdb = next(s for s in hesed["lexicons"] if s["source"] == "bdb")
    assert bdb["entries"][0]["meta"]["count"] == 247
    assert [e["meta"]["homograph"] for e in bdb["entries"]] == ["I", "II"]


@needs_db
def test_every_section_names_a_described_source(agape):
    srcs = agape["sources"]
    for key in ("occurrences", "renderings", "collocates", "topics", "cross_references",
                "samples"):
        assert agape[key]["source"] in srcs, key
    for lex in agape["lexicons"]:
        assert lex["source"] in srcs
    for item in agape["related"]["items"]:
        for link in item["links"]:
            assert link["source"] in srcs
    for meta in srcs.values():
        assert meta["name"] and meta["license"]


@needs_db
def test_lexicons_are_kept_apart(agape):
    assert [s["source"] for s in agape["lexicons"]] == ["abbott-smith", "dodson", "strongs"]


@needs_db
def test_collocates_related_topics_xrefs(client):
    berith = client.get("/api/word/H1285/study").json()
    col = [c["strong_number"] for c in berith["collocates"]["items"]]
    assert col[0] == "H3772"  # karat berith, "cut a covenant"
    assert all(c["together"] >= 3 and c["g2"] >= 15.1 for c in berith["collocates"]["items"])
    hesed = client.get("/api/word/H2617/study").json()
    rel = {r["strong_number"]: r for r in hesed["related"]["items"]}
    assert {"derived_from", "same_root"} <= {x["relation"] for x in rel["H2616"]["links"]}
    assert "MERCY" in [t["topic"] for t in hesed["topics"]["items"]]
    pairs = {(x["from"]["book"], x["to"]["book"]) for x in hesed["cross_references"]["items"]}
    assert ("Exodus", "Psalms") in pairs


@needs_db
def test_function_word_has_no_collocates(client):
    d = client.get("/api/word/G3588/study").json()
    assert d["lemma"]["function_word"] is True and d["collocates"]["items"] == []


@needs_db
def test_samples(client, agape):
    items = agape["samples"]["items"]
    assert 5 <= len(items) <= 12 and not agape["samples"]["all_occurrences"]
    assert len({(i["book"], i["chapter"], i["verse"]) for i in items}) == len(items)
    assert all(i["bsb_text"] and i["bsb_word_positions"] for i in items)
    rare = client.get("/api/word/G1/study").json()["samples"]
    assert rare["all_occurrences"] is True


@needs_db
def test_verses_endpoint(client):
    r = client.get("/api/word/G26/verses", params={"with": "G4102"}).json()
    assert r["verses"] == 24  # the collocate's "together" count
    tr = client.get("/api/word/G3056/verses", params={"edition": "TR"}).json()
    study = client.get("/api/word/G3056/study").json()
    assert tr["total"] == study["occurrences"]["by_edition"]["TR"]
    assert client.get("/api/word/G26/verses", params={"edition": "XX"}).status_code == 400


@needs_db
def test_errors(client):
    assert client.get("/api/word/G99999/study").status_code == 404
    assert client.get("/api/word/love/study").status_code == 400
