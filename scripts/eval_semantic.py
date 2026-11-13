#!/usr/bin/env python3
"""Evaluate keyword vs meaning vs hybrid verse search against labels already in the DB.

Query sets (dev/test split is deterministic by sha1 of the topic or verse; hybrid
weights and passage-mixing are tuned on dev only, reported on test):
  questions  hand-written natural questions (tests/fixtures/semantic_questions.json);
             not used for tuning
  naves      Nave's Topical Bible concept topics: query = topic name, relevant = its verses
  subtopics  Nave's sub-topic lines: query = "Topic: sub-topic label", relevant = that line's refs
  xref       verse -> verse: query = a verse, relevant = its OpenBible.info cross-references
             (TSK-derived, votes >= 10); the source verse and +-3 neighbours are excluded

Methods: fts_today (the exact /api/search verse query), fts_or (stop-worded OR + BM25),
vec:<model> (cosine), hybrid:<model> (RRF of fts_or and vec), ceiling:qwen3 (Ollama, not shippable).

Usage:
  python scripts/eval_semantic.py --models bge-small,minilm-l6 --sets questions,naves
  python scripts/eval_semantic.py --models all --out docs/semantic-eval-2026-11.json
Embeddings are cached in --cache (default data/sources/semantic-eval/), keyed by model+variant.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from import_naves import NAVES_BOOK_MAP  # noqa: E402

from backend.search_text import content_terms, fts_or_query, fts_today_query, unit_texts  # noqa: E402
from backend.semantic import (  # noqa: E402
    CANDIDATES,
    Encoder,
    fetch_model,
    get_spec,
    pack_binary,
    quantize_int8,
    rrf,
)

DB_PATH = Path(os.environ.get("DATABASE_PATH", PROJECT_ROOT / "data" / "bible.db"))
QUESTIONS = PROJECT_ROOT / "tests" / "fixtures" / "semantic_questions.json"
TOPK = 100
AUTO_MAX_TERMS = 2   # backend/routers/semantic.py uses the same cut


def split_of(key: str) -> str:
    return "dev" if int(hashlib.sha1(key.encode()).hexdigest(), 16) % 2 == 0 else "test"


# ---------------- corpus ----------------

def load_corpus(conn):
    rows = conn.execute("""SELECT book, chapter, verse, book_order, text FROM verses
                           WHERE translation_id = 'BSB' ORDER BY book_order, chapter, verse""").fetchall()
    refs = [(r[0], r[1], r[2]) for r in rows]
    return {"refs": refs, "pos": {r: i for i, r in enumerate(refs)},
            "orders": np.array([r[3] for r in rows]), "texts": [r[4] for r in rows],
            "rows": rows}


# ---------------- query sets ----------------

_REF_LINE = re.compile(r"^\s*-(.*?)\s+((?:[1-3]?[A-Z]{2,4})\s+\d.*)$")
_BOOK_TOKEN = re.compile(r"([1-3]?[A-Z]{2,4})\s+(\d+(?::[\d,\-]+)?)|(?<=;)\s*(\d+(?::[\d,\-]+)?)")
_SKIP_LABEL = re.compile(r"^(see|instances|general|miscellany|also|figurative|symbolical|"
                         r"unclassified|scriptures)", re.I)


def parse_naves_refs(text: str, max_span: int = 10):
    """Nave's refs incl. same-book continuations ("PSA 39:6; 127:2"); skips whole chapters
    and ranges longer than max_span (too broad to be a fair label)."""
    out, book = [], None
    for m in re.finditer(r"([1-3]?[A-Z]{2,4})\s+(\d+(?::[\d,\-]+)?)|;\s*(\d+:[\d,\-]+)", text):
        if m.group(1):
            book = NAVES_BOOK_MAP.get(m.group(1))
            part = m.group(2)
        else:
            part = m.group(3)
        if not book or ":" not in part:
            continue
        ch, verses = part.split(":", 1)
        for seg in verses.split(","):
            if not seg:
                continue
            a, _, b = seg.partition("-")
            try:
                a, b = int(a), int(b or a)
            except ValueError:
                continue
            if 0 <= b - a < max_span:
                out.extend((book, int(ch), v) for v in range(a, b + 1))
    return out


def concept_topics(conn, corpus):
    """Topics that are ideas, not people or places: the name occurs mostly lowercase in BSB."""
    text = " ".join(corpus["texts"])
    words = re.findall(r"[A-Za-z]+", text)
    lower, cap = {}, {}
    for w in words:
        d = lower if w.islower() else cap
        d[w.lower()] = d.get(w.lower(), 0) + 1
    keep = []
    for tid, topic, entry in conn.execute("SELECT id, topic, entry_text FROM naves_topics"):
        first = re.findall(r"[A-Za-z]+", topic)
        if not first:
            continue
        w = first[0].lower()
        if lower.get(w, 0) >= 3 and lower.get(w, 0) >= cap.get(w, 0):
            keep.append((tid, topic, entry))
    return keep


def build_sets(conn, corpus, max_subtopics=400, max_xref=300):
    pos = corpus["pos"]
    sets = {"questions": [], "qpooled": [], "naves": [], "subtopics": [], "xref": []}

    def idx(refs):
        out = set()
        for r in refs:
            b, cv = r.rsplit(" ", 1)
            c, v = cv.split(":")
            if (b, int(c), int(v)) in pos:
                out.add(pos[(b, int(c), int(v))])
        return out

    for q in json.loads(QUESTIONS.read_text())["questions"]:
        orig = idx(q["refs"])
        # questions: the labels written up front; qpooled: plus pooled judgements
        sets["questions"].append({"q": q["q"], "rel": orig, "orig": orig, "split": "test",
                                  "pool": True})
        sets["qpooled"].append({"q": q["q"], "rel": orig | idx(q.get("pooled_refs", [])),
                                "orig": orig, "split": "test"})
    subs = []
    for tid, topic, entry in concept_topics(conn, corpus):
        rel = {pos[r] for r in parse_naves_refs(entry) if r in pos}
        name = topic.title()
        if 5 <= len(rel) <= 150:
            sets["naves"].append({"q": name, "rel": rel, "split": split_of(topic)})
        for line in entry.splitlines():
            m = _REF_LINE.match(line)
            if not m:
                continue
            label = m.group(1).strip(" ,;-")
            if len(label.split()) < 3 or _SKIP_LABEL.match(label):
                continue
            lrel = {pos[r] for r in parse_naves_refs(m.group(2)) if r in pos}
            if 2 <= len(lrel) <= 60:
                subs.append({"q": f"{name}: {label}", "rel": lrel, "split": split_of(topic)})
    subs.sort(key=lambda s: hashlib.sha1(s["q"].encode()).hexdigest())
    sets["subtopics"] = subs[:max_subtopics]
    rows = conn.execute("""SELECT source_book, source_chapter, source_verse,
                                  target_book, target_chapter, target_verse
                           FROM cross_references""").fetchall()
    by_src: dict = {}
    for r in rows:
        by_src.setdefault((r[0], r[1], r[2]), set()).add((r[3], r[4], r[5]))
    srcs = sorted((s for s, t in by_src.items() if len(t) >= 3 and s in pos),
                  key=lambda s: hashlib.sha1(repr(s).encode()).hexdigest())[:max_xref * 2]
    for s in srcs:
        rel = {pos[t] for t in by_src[s] if t in pos and not _near(s, t)}
        if rel:
            sets["xref"].append({"q": corpus["texts"][pos[s]], "src": pos[s], "rel": rel,
                                 "split": split_of(repr(s))})
    return sets


def _near(a, b, n=3):
    return a[0] == b[0] and a[1] == b[1] and abs(a[2] - b[2]) <= n


def excluded_for(item, corpus):
    if "src" not in item:
        return set()
    b, c, v = corpus["refs"][item["src"]]
    return {corpus["pos"][(b, c, x)] for x in range(v - 3, v + 4) if (b, c, x) in corpus["pos"]}


# ---------------- methods ----------------

def fts_rank(conn, corpus, match: str, limit: int):
    """Unique BSB verse indices in FTS rank order (verses_fts covers all translations)."""
    if not match:
        return []
    out, seen = [], set()
    try:
        rows = conn.execute("""SELECT book, chapter, verse FROM verses_fts
                               WHERE verses_fts MATCH ? ORDER BY rank LIMIT ?""",
                            (f"text: ({match})", limit)).fetchall()
    except sqlite3.OperationalError:
        return []
    for b, c, v in rows:
        i = corpus["pos"].get((b, int(c), int(v)))
        if i is not None and i not in seen:
            seen.add(i)
            out.append(i)
    return out


def embed_corpus(key, variant, corpus, cache: Path, threads: int):
    path = cache / f"{key}__{variant}.npy"
    if path.exists():
        return np.load(path)
    texts = unit_texts(corpus["rows"], variant)
    t0 = time.time()
    if key == "qwen3":
        vecs = ollama_embed(texts, query=False)
    else:
        spec = get_spec(key)
        enc = Encoder(spec, fetch_model(spec), threads=threads)
        vecs = enc.embed(texts, batch_size=64)
    print(f"  embedded {len(texts)} {variant} units with {key} in {time.time() - t0:.0f}s",
          flush=True)
    cache.mkdir(parents=True, exist_ok=True)
    np.save(path, vecs.astype(np.float32))
    return vecs


_ENCODERS: dict = {}


def embed_queries(key, queries, threads):
    if key == "qwen3":
        return ollama_embed(queries, query=True)
    if key not in _ENCODERS:
        spec = get_spec(key)
        _ENCODERS[key] = Encoder(spec, fetch_model(spec), threads=threads)
    return _ENCODERS[key].embed(queries, is_query=True)


def ollama_embed(texts, query: bool):
    """Quality ceiling only: qwen3-embedding:0.6b on crucible. Never on the request path."""
    import urllib.request
    url = os.environ.get("OLLAMA_URL", "http://crucible:11434") + "/api/embed"
    if query:
        texts = ["Instruct: Given a question, retrieve Bible verses that answer it\nQuery: " + t
                 for t in texts]
    out = []
    for s in range(0, len(texts), 64):
        body = json.dumps({"model": "qwen3-embedding:0.6b", "input": texts[s:s + 64]}).encode()
        req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            out.extend(json.load(r)["embeddings"])
    v = np.array(out, dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def topk(scores, k, exclude=()):
    s = scores.copy()
    if exclude:
        s[list(exclude)] = -np.inf
    idx = np.argpartition(-s, k)[:k]
    return [int(i) for i in idx[np.argsort(-s[idx], kind="stable")]]


# ---------------- metrics ----------------

def metrics(ranked, rel):
    out = {}
    for k in (10, 50):
        out[f"R@{k}"] = len(set(ranked[:k]) & rel) / len(rel)
    dcg = sum(1 / math.log2(r + 2) for r, i in enumerate(ranked[:10]) if i in rel)
    idcg = sum(1 / math.log2(r + 2) for r in range(min(10, len(rel))))
    out["nDCG@10"] = dcg / idcg
    first = next((r for r, i in enumerate(ranked[:TOPK]) if i in rel), None)
    out["MRR"] = 0.0 if first is None else 1 / (first + 1)
    out["hit@10"] = 1.0 if first is not None and first < 10 else 0.0
    return out


POOL: dict = {}  # question -> set of corpus indices seen in any method's top 10 (--pool)


def scored(ranked, it):
    if it.get("pool"):
        POOL.setdefault(it["q"], set()).update(ranked[:10])
    return metrics(ranked, it["rel"])


def mean_metrics(rows):
    keys = rows[0].keys() if rows else []
    return {k: round(float(np.mean([r[k] for r in rows])), 4) for k in keys}


# ---------------- runner ----------------

def fuse(kind, meaning, keyword, w):
    """hybrid: RRF of both lists. boost: meaning list re-ranked by RRF with only those
    keyword hits that are already in the meaning top-K (keyword-only verses never enter)."""
    if kind == "boost":
        mset = set(meaning)
        keyword = [i for i in keyword if i in mset]
    return rrf([meaning, keyword], weights=[w, 1.0])[:TOPK]


def vec_scores(item, qv, docs, alpha):
    """alpha weights the single-verse vectors vs the +-1 verse window vectors."""
    s = alpha * (docs["verse"] @ qv)
    if alpha < 1:
        s = s + (1 - alpha) * (docs["window"] @ qv)
    return s


def run(args):
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    corpus = load_corpus(conn)
    sets = build_sets(conn, corpus)
    want_sets = args.sets.split(",")
    for name in want_sets:
        n = sets[name]
        print(f"{name}: {len(n)} queries ({sum(i['split'] == 'test' for i in n)} test), "
              f"median relevant {int(np.median([len(i['rel']) for i in n]))}")
    cache = Path(args.cache)
    models = list(CANDIDATES) if args.models == "all" else [m for m in args.models.split(",") if m]
    results: dict = {"sets": {s: len(sets[s]) for s in want_sets}, "rows": []}

    def record(method, name, split, per_query, extra=None):
        m = mean_metrics(per_query)
        results["rows"].append({"method": method, "set": name, "split": split, **m,
                                **(extra or {}),
                                "per_query": {"nDCG@10": [round(r["nDCG@10"], 4)
                                                          for r in per_query],
                                              "hit@10": [r["hit@10"] for r in per_query]}})
        print(f"  {method:34} {name:10} {split:5} " +
              " ".join(f"{k}={v:.3f}" for k, v in m.items()), flush=True)

    # Keyword baselines (no tuning)
    fts_cache: dict = {}
    for name in want_sets:
        for split in ("dev", "test"):
            items = [i for i in sets[name] if i["split"] == split]
            if not items:
                continue
            for method, build, limit in (("fts_today", fts_today_query, 50),
                                         ("fts_or", fts_or_query, TOPK + 10)):
                pq = []
                for it in items:
                    if name == "xref" and method == "fts_today":
                        ranked = []  # AND of a whole verse's words finds only the verse itself
                    else:
                        ranked = fts_rank(conn, corpus, build(it["q"]), limit)
                    ex = excluded_for(it, corpus)
                    ranked = [i for i in ranked if i not in ex]
                    fts_cache[(method, it["q"])] = ranked
                    pq.append(scored(ranked, it))
                record(method, name, split, pq)

    # Questions have no dev split: they borrow the settings tuned on Nave's sub-topics dev.
    order = sorted(want_sets, key=lambda s: s in ("questions", "qpooled"))
    for key in models:
        variants = ("verse",) if args.verse_only else ("verse", "window")
        docs = {v: embed_corpus(key, v, corpus, cache, args.threads) for v in variants}
        tuned: dict = {}
        for name in order:
            all_items = sets[name]
            if name == "xref":
                qvecs = None
            else:
                qvecs = embed_queries(key, [i["q"] for i in all_items], args.threads)
            # Tune alpha (verse vs window mix) and hybrid weight on dev; report test.
            def ranked_for(it, j, alpha):
                qv = docs["verse"][it["src"]] if qvecs is None else qvecs[j]
                return topk(vec_scores(it, qv, docs, alpha), TOPK, excluded_for(it, corpus) |
                            ({it["src"]} if "src" in it else set()))

            dev = [(j, it) for j, it in enumerate(all_items) if it["split"] == "dev"]
            kw = lambda it: fts_cache[("fts_or", it["q"])]  # noqa: E731
            best = {"alpha": 1.0, "hybrid": 1.0, "boost": 1.0}
            if dev and not args.no_tune and not args.verse_only:
                score_a = {a: np.mean([scored(ranked_for(it, j, a), it)["nDCG@10"]
                                       for j, it in dev]) for a in (1.0, 0.7, 0.5, 0.3, 0.0)}
                best["alpha"] = max(score_a, key=score_a.get)
            if dev and not args.no_tune:
                for kind in ("hybrid", "boost"):
                    score_w = {w: np.mean([scored(fuse(kind, ranked_for(it, j, best["alpha"]),
                                                        kw(it), w), it)["nDCG@10"]
                                           for j, it in dev]) for w in (0.25, 0.5, 1.0, 2.0)}
                    best[kind] = max(score_w, key=score_w.get)
                tuned[name] = dict(best)
                print(f"  tuned on {name} dev: {best}", flush=True)
            elif name in ("questions", "qpooled"):
                best = tuned.get("subtopics", best)
            for split in ("dev", "test"):
                items = [(j, it) for j, it in enumerate(all_items) if it["split"] == split]
                if not items:
                    continue
                for label, alpha in (("verse", 1.0), ("mix", best["alpha"])):
                    if label == "mix" and alpha == 1.0:
                        continue
                    pq = [scored(ranked_for(it, j, alpha), it) for j, it in items]
                    record(f"vec:{key}:{label}", name, split, pq, {"alpha": alpha})
                for kind in ("hybrid", "boost"):
                    pq = [scored(fuse(kind, ranked_for(it, j, best["alpha"]), kw(it), best[kind]),
                                 it) for j, it in items]
                    record(f"{kind}:{key}", name, split, pq,
                           {"alpha": best["alpha"], "w": best[kind]})
                # auto: rule fixed before looking at test results (no tuning of the cut):
                # <= 2 content words -> hybrid (keyword-like query), else meaning only.
                pq = [scored(fuse("hybrid", ranked_for(it, j, best["alpha"]), kw(it),
                                   best["hybrid"])
                              if len(content_terms(it["q"])) <= AUTO_MAX_TERMS
                              else ranked_for(it, j, best["alpha"]), it)
                      for j, it in items]
                record(f"auto:{key}", name, split, pq, {"alpha": best["alpha"],
                                                         "w": best["hybrid"]})
        if args.notes:
            notes_report(key, conn, docs, sets, order, corpus, cache, args, record, tuned)
        if args.quant and key != "qwen3":
            quant_report(key, docs, sets, want_sets, corpus, args, record)

    if args.pool:
        write_pool(Path(args.pool), sets, corpus)
    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=1))
        print(f"wrote {args.out}")
    if args.examples:
        show_examples(conn, corpus, sets, models[0], docs, args)


def load_notes(conn, corpus, max_span=5):
    """Tyndale Study Notes covering <= max_span verses, with the verses each covers."""
    rows = conn.execute("""SELECT book, chapter, reference_start, COALESCE(reference_end,
                                  reference_start), searchable_text FROM commentary_entries
                           WHERE source = 'Tyndale Study Notes' ORDER BY id""").fetchall()
    texts, covers = [], []
    for b, c, a, e, t in rows:
        if e - a >= max_span:
            continue
        idx = [corpus["pos"][(b, c, v)] for v in range(a, e + 1) if (b, c, v) in corpus["pos"]]
        if not idx:
            continue
        t = re.sub(r"^\S+\s+", "", t.strip())[:600]  # drop the leading "40:2" reference
        texts.append(t)
        covers.append(idx)
    return texts, covers


def notes_report(key, conn, docs, sets, order, corpus, cache, args, record, tuned):
    """Verse score + gamma * best covering Tyndale note score (gamma tuned on dev)."""
    texts, covers = load_notes(conn, corpus)
    path = cache / f"{key}__tyndale.npy"
    if path.exists():
        nv = np.load(path)
    else:
        t0 = time.time()
        if key == "qwen3":
            nv = ollama_embed(texts, query=False)
        else:
            spec = get_spec(key)
            nv = Encoder(spec, fetch_model(spec), threads=args.threads).embed(texts, batch_size=64)
        print(f"  embedded {len(texts)} Tyndale notes with {key} in {time.time() - t0:.0f}s")
        np.save(path, nv.astype(np.float32))
    owner = np.concatenate([np.array(c) for c in covers])
    note_of = np.concatenate([np.full(len(c), i) for i, c in enumerate(covers)])
    for name in order:
        if name == "xref":
            continue
        items = sets[name]
        qv = embed_queries(key, [i["q"] for i in items], args.threads)
        alpha = tuned.get(name, tuned.get("subtopics", {})).get("alpha", 1.0)

        def ranked(j, it, gamma):
            s = vec_scores(it, qv[j], docs, alpha)
            if gamma:
                ns = nv @ qv[j]
                best = np.full(len(s), -1.0, dtype=np.float32)
                np.maximum.at(best, owner, ns[note_of])
                s = s + gamma * np.maximum(best, 0)
            return topk(s, TOPK)

        dev = [(j, it) for j, it in enumerate(items) if it["split"] == "dev"]
        if dev:
            sc = {g: np.mean([scored(ranked(j, it, g), it)["nDCG@10"] for j, it in dev])
                  for g in (0.0, 0.25, 0.5, 1.0)}
            gamma = max(sc, key=sc.get)
            tuned.setdefault("notes", {})[name] = gamma
        else:
            gamma = tuned.get("notes", {}).get("subtopics", 0.5)
        test = [(j, it) for j, it in enumerate(items) if it["split"] == "test"]
        record(f"vec+notes:{key}", name, "test",
               [scored(ranked(j, it, gamma), it) for j, it in test], {"gamma": gamma})


def quant_report(key, docs, sets, want_sets, corpus, args, record):
    """Same retrieval with int8 and binary-with-int8-rescoring storage (verse vectors)."""
    q8, sc = quantize_int8(docs["verse"])
    deq = q8.astype(np.float32) * sc[:, None]
    bits = pack_binary(docs["verse"])
    for name in want_sets:
        items = [i for i in sets[name] if i["split"] == "test"]
        if name == "xref":
            qv_all = None
        else:
            qv_all = embed_queries(key, [i["q"] for i in items], args.threads)
        for label in ("int8", "binary", "binary+int8"):
            pq = []
            for j, it in enumerate(items):
                qv = docs["verse"][it["src"]] if qv_all is None else qv_all[j]
                ex = excluded_for(it, corpus) | ({it["src"]} if "src" in it else set())
                if label == "int8":
                    ranked = topk(deq @ qv, TOPK, ex)
                else:
                    qb = np.packbits(qv > 0)
                    ham = np.unpackbits(bits ^ qb, axis=1).sum(axis=1).astype(np.float32)
                    cand = topk(-ham, 400 if label == "binary+int8" else TOPK, ex)
                    if label == "binary+int8":
                        s = deq[cand] @ qv
                        cand = [cand[i] for i in np.argsort(-s, kind="stable")][:TOPK]
                    ranked = cand
                pq.append(metrics(ranked, it["rel"]))
            record(f"vec:{key}:verse:{label}", name, "test", pq)


def show_examples(conn, corpus, sets, key, docs, args):
    qs = [i for i in sets["questions"]]
    qv = embed_queries(key, [i["q"] for i in qs], args.threads)
    for j, it in enumerate(qs):
        ranked = topk(vec_scores(it, qv[j], docs, args.alpha), 5)
        hits = sum(1 for i in ranked if i in it["rel"])
        print(f"\n[{hits}/5] {it['q']}")
        for i in ranked:
            b, c, v = corpus["refs"][i]
            mark = "*" if i in it["rel"] else " "
            print(f"   {mark} {b} {c}:{v}  {corpus['texts'][i][:90]}")


def write_pool(path: Path, sets, corpus):
    """Unjudged pooled candidates per question: union of every method's top 10, minus the
    verses already listed, in canonical order (no method attribution, for blind judging)."""
    out = []
    for it in sets["questions"]:
        cand = sorted(POOL.get(it["q"], set()) - it["orig"])
        out.append({"q": it["q"], "candidates": [
            {"ref": "%s %d:%d" % corpus["refs"][i], "text": corpus["texts"][i]} for i in cand]})
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"pool: {sum(len(x['candidates']) for x in out)} unjudged candidates -> {path}")


def compare(results: dict, a: str, b: str, n_boot: int = 10000, seed: int = 0):
    """Paired bootstrap of (b - a) per test set: mean difference and 95% interval."""
    rng = np.random.default_rng(seed)
    rows = {(r["method"], r["set"]): r for r in results["rows"] if r["split"] == "test"}
    for name in ("questions", "qpooled", "naves", "subtopics", "xref"):
        if (a, name) not in rows or (b, name) not in rows:
            continue
        for metric in ("nDCG@10", "hit@10"):
            x = np.array(rows[(a, name)]["per_query"][metric])
            y = np.array(rows[(b, name)]["per_query"][metric])
            d = y - x
            boots = d[rng.integers(0, len(d), size=(n_boot, len(d)))].mean(axis=1)
            lo, hi = np.percentile(boots, [2.5, 97.5])
            verdict = "better" if lo > 0 else "worse" if hi < 0 else "no clear difference"
            print(f"{name:10} {metric:8} {b} - {a}: {d.mean():+.3f} "
                  f"[95% {lo:+.3f}, {hi:+.3f}] n={len(d)}  {verdict}")


def markdown_table(results: dict, split: str = "test") -> str:
    """One row per method, nDCG@10 / hit@10 per query set (test split)."""
    sets = [s for s in ("questions", "qpooled", "naves", "subtopics", "xref")
            if s in results["sets"]]
    rows: dict = {}
    for r in results["rows"]:
        if r["split"] == split:
            rows.setdefault(r["method"], {})[r["set"]] = r
    head = "| Method | " + " | ".join(f"{s} nDCG@10 / hit@10" for s in sets) + " |"
    out = [head, "|---|" + "---:|" * len(sets)]
    for method, by_set in rows.items():
        cells = [f"{by_set[s]['nDCG@10']:.3f} / {by_set[s]['hit@10']:.2f}" if s in by_set
                 else "-" for s in sets]
        out.append(f"| `{method}` | " + " | ".join(cells) + " |")
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--models", default="bge-small", help="comma list, 'all', or include qwen3")
    p.add_argument("--sets", default="questions,qpooled,naves,subtopics,xref")
    p.add_argument("--cache", default=str(PROJECT_ROOT / "data" / "sources" / "semantic-eval"))
    p.add_argument("--threads", type=int, default=3)
    p.add_argument("--quant", action="store_true", help="also score int8/binary storage")
    p.add_argument("--notes", action="store_true",
                   help="experiment: add Tyndale Study Note vectors to verse scores")
    p.add_argument("--no-tune", action="store_true")
    p.add_argument("--verse-only", action="store_true",
                   help="screening: single-verse vectors only, no window mix, hybrid w=1")
    p.add_argument("--alpha", type=float, default=1.0, help="verse/window mix for questions")
    p.add_argument("--hybrid-weight", type=float, default=1.0)
    p.add_argument("--examples", action="store_true", help="print top 5 per question")
    p.add_argument("--out")
    p.add_argument("--pool", help="write unjudged pooled candidates for the questions set")
    p.add_argument("--table", help="print the markdown table for an existing --out JSON")
    p.add_argument("--compare", nargs=3, metavar=("JSON", "METHOD_A", "METHOD_B"),
                   help="paired bootstrap of METHOD_B - METHOD_A on each test set")
    args = p.parse_args()
    if args.compare:
        compare(json.loads(Path(args.compare[0]).read_text()), *args.compare[1:])
        return
    if args.table:
        print(markdown_table(json.loads(Path(args.table).read_text())))
        return
    run(args)


if __name__ == "__main__":
    main()
