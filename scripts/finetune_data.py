#!/usr/bin/env python3
"""Training data for the gte-small fine-tune (docs/SEMANTIC_SEARCH_2026-11.md, round two).

No generated text: every query is a Nave's topic name, a Nave's sub-topic line, or a BSB
verse; every positive is a verse the 1896 Nave's or the OpenBible/TSK cross-references
attach to it.

Leakage rules (checked by tests/test_finetune_data.py):
  - only the *dev* side of the evaluation split is used: split_of(topic) for Nave's,
    split_of(repr(source verse)) for cross-references (same function as scripts/eval_semantic.py)
  - cross-reference pairs never touch a test-split evaluation source verse (as query or
    positive), and the evaluation's +-3 neighbour rule is applied
  - the 64 hand-written questions (and their pooled labels) are never read
  - dev is split again, by sha1("select:" + key): 20% "select" (model selection only,
    never trained on) and 80% "train"
Hard negatives: for each training query, one verse sampled (seeded) from qwen3-embedding
ranks 30-100 that is not a positive or within +-2 verses of one. Skipping the top 30
keeps likely-relevant-but-unlabelled verses out of the negatives.

Writes data/finetune/<sha12>/{train.jsonl, select.json, manifest.json}; the directory
name is the sha256 of train.jsonl + select.json.

    python scripts/finetune_data.py            # needs Ollama qwen3-embedding:0.6b (OLLAMA_URL)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import sqlite3
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT))

from eval_semantic import (  # noqa: E402
    _REF_LINE,
    _SKIP_LABEL,
    DB_PATH,
    build_sets,
    concept_topics,
    load_corpus,
    ollama_embed,
    parse_naves_refs,
    split_of,
)

OUT = PROJECT_ROOT / "data" / "finetune"
SEED = 1234
MAX_POS_PER_QUERY = 8       # Nave's lines can list 60 verses; cap so one line can't dominate
MAX_XREF_PER_SOURCE = 5     # highest-voted first
NEG_RANKS = (30, 100)


def select_of(key: str) -> str:
    return "select" if int(hashlib.sha1(("select:" + key).encode()).hexdigest(), 16) % 5 == 0 \
        else "train"


def naves_queries(conn, corpus):
    """(query, positives, group_key) for dev-side concept topics and their sub-topic lines."""
    pos = corpus["pos"]
    out = []
    for _tid, topic, entry in concept_topics(conn, corpus):
        if split_of(topic) != "dev":
            continue
        name = topic.title()
        rel = sorted({pos[r] for r in parse_naves_refs(entry) if r in pos})
        if 5 <= len(rel) <= 150:
            out.append((name, rel, topic))
        for line in entry.splitlines():
            m = _REF_LINE.match(line)
            if not m:
                continue
            label = m.group(1).strip(" ,;-")
            if len(label.split()) < 3 or _SKIP_LABEL.match(label):
                continue
            lrel = sorted({pos[r] for r in parse_naves_refs(m.group(2)) if r in pos})
            if 1 <= len(lrel) <= 60:
                out.append((f"{name}: {label}", lrel, topic))
    return out


def xref_queries(conn, corpus, test_sources: set):
    pos = corpus["pos"]
    rows = conn.execute("""SELECT source_book, source_chapter, source_verse,
                                  target_book, target_chapter, target_verse, votes
                           FROM cross_references ORDER BY votes DESC, id""").fetchall()
    by_src: dict = {}
    for r in rows:
        s, t = (r[0], r[1], r[2]), (r[3], r[4], r[5])
        if s not in pos or t not in pos or split_of(repr(s)) != "dev":
            continue
        if pos[s] in test_sources or pos[t] in test_sources:
            continue
        if s[0] == t[0] and s[1] == t[1] and abs(s[2] - t[2]) <= 3:
            continue
        lst = by_src.setdefault(s, [])
        if len(lst) < MAX_XREF_PER_SOURCE:
            lst.append(pos[t])
    return [(pos[s], ts, repr(s)) for s, ts in by_src.items()]


def build(cache: Path, max_queries: int | None = None) -> Path:
    rng = random.Random(SEED)
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    corpus = load_corpus(conn)
    texts = corpus["texts"]
    sets = build_sets(conn, corpus)
    test_sources = {it["src"] for it in sets["xref"] if it["split"] == "test"}
    test_queries = {it["q"] for name in ("naves", "subtopics", "xref", "questions")
                    for it in sets[name] if it["split"] == "test"}

    nq = naves_queries(conn, corpus)
    xq = xref_queries(conn, corpus, test_sources)
    assert not {q for q, _, _ in nq} & test_queries, "a test query leaked into training"
    if max_queries:
        nq, xq = nq[:max_queries], xq[:max_queries]

    qwen = np.load(cache / "qwen3__verse.npy", mmap_mode="r")
    nq_vecs = ollama_embed([q for q, _, _ in nq], query=True)

    def negative(qv, positives, exclude):
        s = np.asarray(qwen @ qv)
        order = np.argsort(-s)[NEG_RANKS[0]:NEG_RANKS[1]]
        bad = set(exclude)
        for p in positives:
            b, c, v = corpus["refs"][p]
            bad.update(corpus["pos"][(b, c, x)] for x in range(v - 2, v + 3)
                       if (b, c, x) in corpus["pos"])
        cand = [int(i) for i in order if int(i) not in bad]
        return rng.choice(cand) if cand else None

    # Identical text counts as the same query: 423 BSB verse texts occur more than once
    # (Ps 136 refrain, Ps 14 = Ps 53, the commandments), so exclude by text as well.
    banned = {texts[i] for i in test_sources} | test_queries | \
        {texts[src] for src, _, key in xq if select_of(key) == "select"} | \
        {q for q, _, key in nq if select_of(key) == "select"}

    train, select = [], {"naves": [], "xref": []}
    for (q, rel, key), qv in zip(nq, nq_vecs):
        if select_of(key) == "select":
            select["naves"].append({"q": q, "rel": rel})
            continue
        neg = negative(qv, rel, ())
        for p in rng.sample(rel, min(len(rel), MAX_POS_PER_QUERY)):
            if texts[p] in banned or texts[neg] == texts[p]:
                continue
            train.append({"anchor": q, "positive": texts[p], "negative": texts[neg],
                          "kind": "naves"})
    for src, rel, key in xq:
        if select_of(key) == "select":
            select["xref"].append({"src": src, "rel": rel})
            continue
        if texts[src] in banned:
            continue
        neg = negative(np.asarray(qwen[src]), rel, (src,))
        for p in rel:
            if texts[p] in banned or texts[neg] == texts[p]:
                continue
            train.append({"anchor": texts[src], "positive": texts[p],
                          "negative": texts[neg], "kind": "xref"})
    rng.shuffle(train)

    body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in train)
    sel = json.dumps(select, sort_keys=True)
    digest = hashlib.sha256(body.encode() + sel.encode()).hexdigest()
    out = OUT / digest[:12]
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / "train.jsonl").write_text(body)
    (out / "select.json").write_text(sel)
    manifest = {
        "sha256": digest, "seed": SEED, "neg_ranks": NEG_RANKS,
        "max_pos_per_query": MAX_POS_PER_QUERY, "max_xref_per_source": MAX_XREF_PER_SOURCE,
        "train_examples": len(train),
        "train_by_kind": {k: sum(r["kind"] == k for r in train) for k in ("naves", "xref")},
        "select_queries": {k: len(v) for k, v in select.items()},
        "train_queries": {"naves": sum(select_of(k) == "train" for _, _, k in nq),
                          "xref": sum(select_of(k) == "train" for _, _, k in xq)},
        "teacher": "qwen3-embedding:0.6b via Ollama (negatives only)",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps(manifest, indent=1))
    print(f"wrote {out}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--cache", default=str(PROJECT_ROOT / "data" / "sources" / "semantic-eval"))
    ap.add_argument("--max-queries", type=int, help="small sample (tests)")
    a = ap.parse_args()
    build(Path(a.cache), a.max_queries)


if __name__ == "__main__":
    main()
