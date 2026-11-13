"""The reader's word-link confidence rule (frontend/static/js/modules/wordlink.js).

A tapped word's source link shows as fact at confidence >= 0.5 for content words and
>= 0.7 for function words (docs/ALIGNMENT_2026-11.md). Which words are "function
words" must be exactly what the alignment calibration used: is_function(normalize(w))
in scripts/aligner. The JS list is checked against that over every word in the
alignment table, so a change to the aligner's word classes fails here.
"""
import re
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from aligner.rerank import is_function  # noqa: E402
from aligner.text import normalize  # noqa: E402

from backend.main import app  # noqa: E402

JS = ROOT / "frontend" / "static" / "js" / "modules" / "wordlink.js"
DB = ROOT / "data" / "bible.db"


def _js_function_words():
    src = JS.read_text()
    block = re.search(r"FUNCTION_WORDS = new Set\(\((.*?)\)\.split", src, re.S).group(1)
    return set(" ".join(re.findall(r'"([^"]*)"', block)).split())


def _key(w):
    return w.lower().replace("'", "’")


def test_js_list_words_are_function_words():
    for w in _js_function_words():
        assert is_function(normalize(w)), w


def test_thresholds_match_the_alignment_doc():
    src = JS.read_text()
    assert "CONTENT_MIN = 0.5" in src and "FUNCTION_MIN = 0.7" in src


@pytest.mark.skipif(not DB.exists(), reason="no data/bible.db")
def test_js_list_matches_aligner_over_the_vocabulary():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    # Alignments are packed per verse now; the vocabulary is every tappable word of an aligned verse.
    from backend import alignment_store
    vocab = set()
    for (text,) in con.execute(f"""
            SELECT v.text FROM {alignment_store.TABLE} p
            JOIN verses v ON v.translation_id = p.translation_id AND v.book = p.book
                 AND v.chapter = p.chapter AND v.verse = p.verse"""):
        vocab.update(_key(w) for w in alignment_store.tappable_words(text))
    expected = {w for w in vocab if is_function(normalize(w))}
    js = _js_function_words()
    assert expected - js == set(), "function words missing from wordlink.js"
    assert (js & vocab) == expected, "wordlink.js lists words the aligner treats as content"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_word_alignment_returns_confidence_and_method(client):
    d = client.get("/api/word-alignment?book=John&chapter=3&verse=3&word_position=5&translation=WEB").json()
    if not d.get("found"):
        pytest.skip("DB without WEB alignments")
    a = d["alignment"]
    assert a["english_word"] == "certainly"
    assert a["confidence"] < 0.5 and a["method"] == 2
    bsb = client.get("/api/word-alignment?book=John&chapter=3&verse=1&word_position=4&translation=BSB").json()
    assert bsb["alignment"]["method"] == 0


def test_offline_exports_carry_confidence_and_method(client):
    ch = client.get("/api/offline/chapter?book=John&chapter=3&translation=WEB").json()
    if not ch.get("alignments"):
        pytest.skip("DB without WEB alignments")
    assert {"confidence", "method"} <= set(ch["alignments"][0])
    r = client.get("/api/offline/book?book=Jude&translation=WEB")
    if r.status_code == 200:
        rows = [a for chap in (r.json().get("chapters") or {}).values() for a in (chap.get("alignments") or [])]
        if rows:
            assert {"confidence", "method"} <= set(rows[0])
