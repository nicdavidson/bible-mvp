"""Tests for the word aligner (scripts/aligner) and its scoring.

Unit tests use small synthetic inputs. The API checks at the bottom need a DB
built with `scripts/build_alignments.py all` and are skipped otherwise.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from aligner.data import flag_suspect_gold  # noqa: E402
from aligner.kjv import (ADDED, AMBIGUOUS, MISSING, ORDERED, UNIQUE, UNTAGGED,  # noqa: E402
                         KjvWord, lemma_class, parse_verse_usfm, project_to_text,
                         resolve_tags)
from aligner.metrics import Score, score_examples  # noqa: E402
from aligner.model import NO_LINK, Aligner, Example, Params  # noqa: E402
from aligner.pipeline import Calibrator  # noqa: E402
from aligner.renderings import group_rendering, unpad  # noqa: E402
from aligner.sources import SourceToken, candidate_tokens, token_features  # noqa: E402
from aligner.text import normalize, tappable_words  # noqa: E402
from import_stepbible_alignment import parse_reference, renumber_split_verses  # noqa: E402


# --- tokenization: the UI's position contract ------------------------------------------

def test_tappable_words_match_ui_rules():
    text = "And God said, “Let there be light,” and there was light."
    # Words touching curly quotes are tappable (they were not before 2026-11).
    assert tappable_words(text) == ["And", "God", "said", "Let", "there", "be", "light",
                                    "and", "there", "was", "light"]


def test_tappable_words_keep_apostrophes_and_hyphens():
    assert tappable_words("Beth-el, God's (house)") == ["Beth-el", "God's", "house"]


def test_normalize_early_modern_english():
    vocab = {"love", "walk", "beast", "know", "believe", "midst"}
    assert normalize("loveth", vocab) == normalize("love", vocab)
    assert normalize("walketh", vocab) == normalize("walks", vocab)
    assert normalize("believest", vocab) == normalize("believe", vocab)
    assert normalize("beast", vocab) == "beast"      # not 'bea'
    assert normalize("midst", vocab) == "midst"
    assert normalize("Thou") == normalize("you")
    assert normalize("unto") == "to"


# --- STEPBible references -------------------------------------------------------------

def test_parse_reference_with_alternative_versification():
    assert parse_reference("Psa.3.1(3.2)#01=L") == ("Psalms", 3, 1, 1, "L")
    assert parse_reference("Mat.17.15[17.14]#02=NKO") == ("Matthew", 17, 15, 2, "NKO")
    assert parse_reference("Rom.16.25{14.24}#01=NKO")[:4] == ("Romans", 16, 25, 1)


def test_renumber_only_colliding_verses():
    rows = [("Num", 26, 1, 1, "a"), ("Num", 26, 1, 2, "b"), ("Num", 26, 1, 1, "c"),
            ("Num", 26, 2, 1, "d"), ("Num", 26, 2, 3, "e")]
    out = renumber_split_verses(rows)
    assert [r[3] for r in out if r[2] == 1] == [1, 2, 3]
    assert [r[3] for r in out if r[2] == 2] == [1, 3]   # untouched


# --- edition filtering: verses present in one tradition only ---------------------------

def _tok(pos, strong, editions=None, gloss="", grammar="", text="x", word_type=None):
    return SourceToken(pos=pos, text=text, strong=strong, grammar=grammar, gloss=gloss,
                       editions=editions, word_type=word_type)


ALL = "NA28+NA27+Tyn+SBL+WH+Treg+TR+Byz"


def test_candidate_tokens_follow_each_translations_edition():
    toks = [_tok(1, "G2532", ALL), _tok(2, "G3962", "TR"), _tok(3, "G1161", "NA28+SBL+Byz")]
    assert [t.pos for t in candidate_tokens(toks, "BSB")] == [1, 3]
    assert [t.pos for t in candidate_tokens(toks, "KJV")] == [1, 2]
    assert [t.pos for t in candidate_tokens(toks, "WEB")] == [1, 3]


def test_tr_only_verse_has_no_candidates_for_critical_text():
    acts_8_37 = [_tok(i, "G0000", "TR") for i in range(1, 6)]
    assert candidate_tokens(acts_8_37, "BSB") == []
    assert candidate_tokens(acts_8_37, "WEB") == []
    assert len(candidate_tokens(acts_8_37, "KJV")) == 5


def test_lxx_only_hebrew_rows_are_never_candidates():
    toks = [_tok(1, "H0430"), _tok(2, "H1254", word_type="X")]
    assert [t.pos for t in candidate_tokens(toks, "KJV")] == [1]


# --- KJV tags --------------------------------------------------------------------------

def test_parse_kjv_usfm_tags_italics_and_possessives():
    words = parse_verse_usfm(
        r'\w And|strong="H1961"\w* \w God|strong="H0430"\w*’s \add was\add* '
        r'\wj \+w for you|strong="G5216"\+w*\wj*.\f + \fr 1.4 \ft Heb. note\f*')
    assert [(w.key, w.strongs, w.added) for w in words] == [
        ("and", ("H1961",), False), ("gods", ("H0430",), False), ("was", (), True),
        ("for", ("G5216",), False), ("you", ("G5216",), False)]


def test_strongs_form_numbers_share_a_lemma_class():
    assert lemma_class("G5213") == lemma_class("G4771")      # humin -> su
    assert lemma_class("G2076") == lemma_class("G1510")      # esti -> eimi
    assert lemma_class("H0430") == "H0430"


def _kw(key, strong=None, added=False):
    return KjvWord(key, (strong,) if strong else (), added)


def test_resolve_unique_ordered_ambiguous_added_missing():
    cands = [_tok(1, "H0430"), _tok(2, "H0559"), _tok(3, "H0216"), _tok(4, "H0216")]
    projected = [_kw("god", "H0430"), _kw("said", "H0559"), _kw("let"),
                 _kw("light", "H0216"), _kw("and"), _kw("light", "H0216"),
                 _kw("was", added=True), _kw("lord", "H3068"), None]
    res = resolve_tags(projected, cands)
    assert res[0] == (UNIQUE, (1,))
    assert res[2] == (UNTAGGED, ())
    # repeated lemma, as many tagged spans as source occurrences -> in order
    assert res[3] == (ORDERED, (3,)) and res[5] == (ORDERED, (4,))
    assert res[6] == (ADDED, ())          # italic supplied word: no source
    assert res[7] == (MISSING, ())        # lemma not in this verse's source text
    assert res[8] == (MISSING, ())        # word not found in the tagged text


def test_resolve_repeated_lemma_with_unequal_counts_is_ambiguous():
    cands = [_tok(1, "H0216"), _tok(2, "H0216"), _tok(3, "H0216")]
    res = resolve_tags([_kw("light", "H0216"), _kw("x"), _kw("light", "H0216")], cands)
    assert res[0] == (AMBIGUOUS, (1, 2, 3))


def test_resolve_with_no_source_text_marks_everything_missing():
    res = resolve_tags([_kw("philip", "G5376"), _kw("said", "G2036")], [])
    assert [r[0] for r in res] == [MISSING, MISSING]


def test_project_kjv_words_onto_db_text():
    words = [_kw("in"), _kw("the"), _kw("beginning", "H7225"), _kw("god", "H0430")]
    out = project_to_text(words, "In the beginning God.")
    assert [w.strongs for w in out] == [(), (), ("H7225",), ("H0430",)]


# --- model ----------------------------------------------------------------------------

def _toy_examples():
    god, said = _tok(1, "H0430", gloss="God"), _tok(2, "H0559", gloss="said")
    light = _tok(3, "H0216", gloss="light")
    ex = []
    for i in range(30):
        ex.append(Example(("Genesis", 1, i + 1), ["god", "say", "light"], [god, said, light],
                          [frozenset({1}), frozenset({2}), frozenset({3})]))
    return ex


def test_model_learns_and_aligns_toy_data():
    m = Aligner(Params(em_iters=2))
    m.fit(_toy_examples(), log=lambda *a: None)
    srcs = _toy_examples()[0].sources
    # reordered English still finds the right source words
    out = m.align(["light", "god", "say"], srcs)
    assert [p for p, _ in out] == [3, 1, 2]
    assert all(0.0 <= c <= 1.0 for _, c in out)


def test_model_handles_repeated_lemma_by_position():
    m = Aligner(Params(em_iters=2))
    m.fit(_toy_examples(), log=lambda *a: None)
    srcs = [_tok(1, "H0216", gloss="light"), _tok(2, "H0430", gloss="God"),
            _tok(3, "H0216", gloss="light")]
    out = m.align(["light", "god", "light"], srcs)
    assert [p for p, _ in out] == [1, 2, 3]


def test_constraints_force_no_link_and_restrict_positions():
    m = Aligner(Params(em_iters=2))
    m.fit(_toy_examples(), log=lambda *a: None)
    srcs = _toy_examples()[0].sources
    out = m.align(["god", "say", "light"], srcs, [NO_LINK, None, frozenset({1})])
    assert out[0][0] is None              # italic / supplied word
    assert out[2][0] == 1                 # tag says lemma at position 1
    assert out[1][0] == 2


def test_verse_without_source_words_gets_no_links():
    m = Aligner(Params(em_iters=1))
    m.fit(_toy_examples(), log=lambda *a: None)
    assert m.align(["philip", "said"], []) == [(None, 1.0), (None, 1.0)]


def test_hebrew_features_include_prefix_morphemes():
    tok = SourceToken(pos=1, text="וְ/הָ/אָרֶץ", strong="H0776", morphemes=["H9002", "H9009"],
                      grammar="HC/Td/Ncbsa")
    feats = token_features(tok)
    assert feats[0] == "L:H0776" and "M:H9002" in feats and "M:H9009" in feats


# --- scoring --------------------------------------------------------------------------

def test_score_precision_recall_aer():
    s = Score()
    s.add(frozenset({1}), 1)          # correct
    s.add(frozenset({2, 3}), 3)       # correct (in multi-source gold)
    s.add(frozenset({4}), 5)          # wrong
    s.add(frozenset({6}), None)       # missed
    s.add(frozenset(), None)          # correctly unlinked
    s.add(frozenset(), 7)             # spurious
    s.add(None, 9)                    # unscored
    d = s.as_dict()
    assert d["precision"] == pytest.approx(2 / 4)
    assert d["recall"] == pytest.approx(2 / 4)
    assert d["aer"] == pytest.approx(1 - 2 * 2 / (4 + 5))
    assert d["null_precision"] == pytest.approx(1 / 2)


def test_score_examples_threshold_drops_weak_links():
    ex = Example(("Mark", 1, 1), ["a", "b"], [], [frozenset({1}), frozenset({2})])
    preds = {ex.key: [(1, 0.9), (3, 0.2)]}
    assert score_examples([ex], preds)["all"].as_dict()["precision"] == 0.5
    assert score_examples([ex], preds, threshold=0.5)["all"].as_dict()["precision"] == 1.0


def test_calibrator_is_monotone_and_bounded():
    pairs = [(0.1, 0), (0.2, 1), (0.3, 0), (0.6, 1), (0.7, 0), (0.9, 1), (0.95, 1)]
    cal = Calibrator.fit(pairs)
    ys = [cal(x / 20) for x in range(21)]
    assert ys == sorted(ys)
    assert all(0.0 <= y <= 1.0 for y in ys)


def test_flag_suspect_gold_catches_shifted_links():
    good = _toy_examples()
    m = Aligner(Params(em_iters=2))
    m.fit(good, log=lambda *a: None)
    srcs = good[0].sources
    shifted = Example(("John", 10, 36), ["god", "say", "light"], srcs,
                      [frozenset({2}), frozenset({3}), frozenset({1})])
    assert flag_suspect_gold([good[0], shifted], m) == {("John", 10, 36)}


def test_group_rendering_and_unpad():
    assert group_rendering([(3, "beginning"), (1, "In"), (2, "the")]) == "beginning"
    assert group_rendering([(1, "his"), (2, "loving"), (3, "devotion")]) == "loving devotion"
    assert group_rendering([(1, "the")]) == "the"
    assert group_rendering([(1, "did"), (3, "go")]) == "did … go"
    assert unpad("H0430") == "H430" and unpad("G0026") == "G26"


# --- API against a built database ----------------------------------------------------

DB = ROOT / "data" / "bible.db"


def _built():
    if not DB.exists():
        return False
    conn = sqlite3.connect(DB)
    try:
        n = conn.execute("SELECT COUNT(*) FROM english_alignment_verses "
                         "WHERE translation_id IN ('KJV', 'WEB')").fetchone()[0]
        has_index = conn.execute("SELECT 1 FROM sqlite_master WHERE name='lemma_renderings'"
                                 ).fetchone()
        return n > 0 and bool(has_index)
    except sqlite3.Error:
        return False
    finally:
        conn.close()


needs_db = pytest.mark.skipif(not _built(), reason="alignment tables not built")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from backend.main import app
    return TestClient(app)


def _tap(client, tr, book, ch, v, word, nth=1):
    text = client.get(f"/api/passage/{book} {ch}:{v}?translation={tr}").json()
    verse = next(x for x in text["verses"] if x["verse"] == v)["text"]
    words = [w.lower() for w in tappable_words(verse)]
    pos = [i for i, w in enumerate(words, 1) if w == word][nth - 1]
    return client.get("/api/word-alignment", params={
        "book": book, "chapter": ch, "verse": v, "word_position": pos,
        "translation": tr}).json()


@needs_db
def test_api_kjv_and_web_taps_find_source_words(client):
    assert _tap(client, "KJV", "Genesis", 1, 1, "beginning")["alignment"]["strong_number"] == "H7225"
    assert _tap(client, "WEB", "Genesis", 1, 1, "created")["alignment"]["strong_number"] == "H1254"
    assert _tap(client, "WEB", "John", 3, 16, "loved")["alignment"]["strong_number"] == "G25"


@needs_db
def test_api_johannine_comma_kjv_links_tr_words_web_has_none(client):
    kjv = _tap(client, "KJV", "1 John", 5, 7, "father")
    assert kjv["found"] and kjv["alignment"]["strong_number"] == "G3962"
    web = _tap(client, "WEB", "1 John", 5, 7, "testify")
    assert web["found"] and web["alignment"]["strong_number"] in ("G3140", "G3141")


@needs_db
def test_api_kjv_italic_word_has_no_link(client):
    # Genesis 1:2 "darkness was upon the face": 'was' is italic in the KJV.
    assert _tap(client, "KJV", "Genesis", 1, 2, "was", nth=2)["found"] is False


@needs_db
def test_api_renderings(client):
    r = client.get("/api/word/G26/renderings").json()
    assert "love" in [x["rendering"] for x in r["translations"]["KJV"]["renderings"]][:3]
    occ = client.get("/api/word/G26/renderings",
                     params={"translation": "WEB", "rendering": "love"}).json()
    assert occ["total"] > 50


# --- reranker ------------------------------------------------------------------------

def test_reranker_learns_to_attach_function_words():
    from aligner.rerank import Reranker
    from aligner.rerank import align as rerank_align
    from aligner.rerank import training_data
    m = Aligner(Params(em_iters=2))
    exs = []
    god, said = _tok(1, "H0430", gloss="God"), _tok(2, "H0559", gloss="said")
    for i in range(40):
        exs.append(Example(("Genesis", 2, i + 1), ["the", "god", "say"], [god, said],
                           [frozenset({1}), frozenset({1}), frozenset({2})]))
    m.fit(exs, log=lambda *a: None)
    data, covered, total = training_data(m, exs)
    assert covered == total == 120
    rr = Reranker(epochs=3)
    rr.fit(data, log=lambda *a: None)
    out = rerank_align(m, rr, ["the", "god", "say"], [god, said])
    assert [p for p, _ in out] == [1, 1, 2]
    # constrained words keep the constrained decision
    out = rerank_align(m, rr, ["the", "god", "say"], [god, said], [NO_LINK, None, None])
    assert out[0][0] is None
