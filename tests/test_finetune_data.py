"""No leakage from the evaluation's test side into the fine-tune data (scripts/finetune_data.py)."""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

DATA_DIRS = sorted((ROOT / "data" / "finetune").glob("*/train.jsonl"))
pytestmark = pytest.mark.skipif(not DATA_DIRS, reason="run scripts/finetune_data.py first")


@pytest.fixture(scope="module")
def sets_and_data():
    from eval_semantic import DB_PATH, build_sets, load_corpus
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    corpus = load_corpus(conn)
    sets = build_sets(conn, corpus)
    d = DATA_DIRS[-1].parent
    train = [json.loads(x) for x in (d / "train.jsonl").read_text().splitlines()]
    select = json.loads((d / "select.json").read_text())
    return corpus, sets, train, select


def test_no_test_query_is_a_training_anchor(sets_and_data):
    corpus, sets, train, _ = sets_and_data
    anchors = {r["anchor"] for r in train}
    for name in ("naves", "subtopics"):
        leaked = {it["q"] for it in sets[name] if it["split"] == "test"} & anchors
        assert not leaked, f"{name} test queries in training: {sorted(leaked)[:3]}"
    # the hand-written questions are never in training, test split or not
    assert not {it["q"] for it in sets["questions"]} & anchors


def test_no_test_xref_source_appears_as_anchor_or_positive(sets_and_data):
    corpus, sets, train, _ = sets_and_data
    test_src_texts = {corpus["texts"][it["src"]] for it in sets["xref"] if it["split"] == "test"}
    xref = [r for r in train if r["kind"] == "xref"]
    assert xref
    assert not {r["anchor"] for r in xref} & test_src_texts
    assert not {r["positive"] for r in xref} & test_src_texts


def test_select_queries_are_never_trained_on(sets_and_data):
    corpus, _, train, select = sets_and_data
    anchors = {r["anchor"] for r in train}
    assert not {x["q"] for x in select["naves"]} & anchors
    assert not {corpus["texts"][x["src"]] for x in select["xref"]} & anchors


def test_negatives_are_not_positives_of_the_same_example(sets_and_data):
    _, _, train, _ = sets_and_data
    assert all(r["negative"] != r["positive"] for r in train)
