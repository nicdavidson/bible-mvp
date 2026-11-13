#!/usr/bin/env python3
"""Build word alignments for every English translation, and evaluate them.

    python scripts/build_alignments.py bsb       # BSB: Clear-Bible gold re-keyed (+ aligner for shifted verses)
    python scripts/build_alignments.py kjv       # KJV: eBible Strong's tags + aligner
    python scripts/build_alignments.py web       # WEB: aligner
    python scripts/build_alignments.py index     # lemma_renderings table
    python scripts/build_alignments.py all       # the four above
    python scripts/build_alignments.py evaluate  # held-out scores -> docs/alignment-eval-2026-11.json

Inputs: data/clear-bible (Clear-Bible/Alignments, cloned by build_db.py),
data/alignment (STEPBible TAHOT/TAGNT, in git), the eBible KJV USFM zip
(downloaded once into data/sources/), and the verses table.
Deterministic: no random state anywhere. See docs/ALIGNMENT_2026-11.md.
"""
import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from aligner.data import TEST_BOOKS, split_of, ylt_examples  # noqa: E402
from aligner.kjv import KJV_CACHE_KEY, KJV_USFM_URL  # noqa: E402
from aligner.metrics import (calibration, error_classes, score_examples,  # noqa: E402
                             threshold_curve)
from aligner.pipeline import (ClassCalibrator, Context, Predictor,  # noqa: E402
                              bsb_rows, fit_calibrator, kjv_rows, model_rows, self_train,
                              train, train_reranker, write_rows)
from aligner.rerank import is_function  # noqa: E402
from aligner.renderings import build_renderings  # noqa: E402
from source_cache import cached_fetch_bytes  # noqa: E402

DB_PATH = Path(os.environ.get("DATABASE_PATH", SCRIPTS.parent / "data" / "bible.db"))
EVAL_PATH = SCRIPTS.parent / "docs" / "alignment-eval-2026-11.json"

# Links below this calibrated confidence are kept in english_word_alignments
# (the UI can mark them) but left out of lemma_renderings. See the doc.
RENDERING_MIN_CONFIDENCE = 0.5


def kjv_zip():
    path = cached_fetch_bytes(KJV_CACHE_KEY, KJV_USFM_URL)
    if path is None:
        sys.exit(f"Could not download {KJV_USFM_URL}")
    return path


USE_RERANK = True  # see docs/ALIGNMENT_2026-11.md, "Round two"


def reranker(ctx):
    """One reranker for every translation, trained out-of-fold on the train+test books
    (not dev, so dev-book calibration stays out-of-sample)."""
    if "_reranker" not in ctx.__dict__:
        ctx._reranker = train_reranker(ctx, ("train", "test")) if USE_RERANK else None
    return ctx._reranker


def production_predictor(ctx, translation):
    """The predictor that writes one translation's rows.

    HMM on all clean BSB gold, then (for a translation other than BSB) one round
    of self-training on that translation's own text; reranker on top. Calibrated
    on the dev books with a predictor built by the same recipe without them.
    """
    cache = ctx.__dict__.setdefault("_production", {})
    if translation not in cache:
        def recipe(splits):
            m = train(ctx, splits, with_kjv=False)
            return m if translation == "BSB" else self_train(ctx, m, splits, translation)
        rr = reranker(ctx)
        calib = fit_calibrator(Predictor(recipe(("train", "test")), rr),
                               ctx.bsb_clean(("dev",)))
        cache[translation] = Predictor(recipe(("train", "dev", "test")), rr, calib)
    return cache[translation]


def step_bsb(ctx):
    rows = list(bsb_rows(ctx, production_predictor(ctx, "BSB")))
    write_rows(ctx.conn, "BSB", rows)
    print(f"BSB: {len(rows)} alignments ({Counter(r[5] for r in rows)})")


def step_kjv(ctx):
    stats = {}
    rows = list(kjv_rows(ctx, production_predictor(ctx, "KJV"), stats))
    write_rows(ctx.conn, "KJV", rows)
    print(f"KJV: {len(rows)} alignments ({Counter(r[5] for r in rows)})")
    for (status, linked), n in sorted(stats.items()):
        print(f"  {status:10s} {'linked' if linked else 'no link':8s} {n}")


def step_web(ctx):
    rows = list(model_rows(ctx, "WEB", production_predictor(ctx, "WEB")))
    write_rows(ctx.conn, "WEB", rows)
    print(f"WEB: {len(rows)} alignments")


def step_index(ctx):
    n = build_renderings(ctx.conn, RENDERING_MIN_CONFIDENCE)
    print(f"lemma_renderings: {n} rows")


def _fmt(d):
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}


def _scores(exs, preds, threshold=0.0, word_filter=None):
    return {k: _fmt(v.as_dict()) for k, v in
            sorted(score_examples(exs, preds, threshold, word_filter).items())}


def _report(exs, preds, srcidx):
    """Scores overall / content / function words, at 0 and 0.5, plus calibration."""
    content = lambda e: not is_function(e)  # noqa: E731
    return {
        "all": _scores(exs, preds),
        "at_0.5": _scores(exs, preds, 0.5)["all"],
        "content": _scores(exs, preds, 0.0, content)["all"],
        "content_at_0.5": _scores(exs, preds, 0.5, content)["all"],
        "function": _scores(exs, preds, 0.0, is_function)["all"],
        "function_at_0.5": _scores(exs, preds, 0.5, is_function)["all"],
        "calibration": calibration(exs, preds),
        "thresholds_content": threshold_curve(exs, preds, word_filter=content),
        "thresholds_function": threshold_curve(exs, preds, word_filter=is_function),
        "thresholds_all": threshold_curve(exs, preds),
        "errors": dict(zip(("counts", "examples"), error_classes(exs, preds, srcidx))),
    }


def step_evaluate(ctx):
    out = {}
    t = time.time()

    def done(what, d):
        print(f"{what} ({time.time() - t:.0f}s)", {k: d["all"]["all"][k] for k in
                                                   ("precision", "recall", "f1")}, flush=True)

    srcidx = lambda k: {tok.pos: tok for tok in ctx.src.get(k, [])}  # noqa: E731
    out["suspect_gold_verses"] = len(ctx.suspect)
    out["suspect_examples"] = sorted(f"{k[0]} {k[1]}:{k[2]}" for k in ctx.suspect)[:40]
    dev = ctx.bsb_clean(("dev",))
    rr = train_reranker(ctx, ("train",))  # never sees dev or test books
    model = train(ctx, ("train",), with_kjv=False)
    variants = {"hmm": Predictor(model), "rerank": Predictor(model, rr)}
    for v in variants.values():
        v.calib = fit_calibrator(v, dev)

    def run(pred, exs, constraints=None):
        return {e.key: pred.align(e.english, e.sources) for e in exs}

    test_all = [e for e in ctx.bsb if split_of(e.key[0]) == "test"]
    test_clean = [e for e in test_all if e.key not in ctx.suspect]
    for name, pred in variants.items():
        preds = run(pred, test_all)
        out[f"bsb_{name}"] = _report(test_clean, preds, srcidx)
        out[f"bsb_{name}_all_gold"] = _scores(test_all, preds)["all"]
        done(f"BSB {name}", out[f"bsb_{name}"])

    ylt = [e for e in ylt_examples(ctx.src, ctx.vocab, log=lambda *a: None)
           if e.key[0] in TEST_BOOKS]
    for name, pred in variants.items():
        out[f"ylt_{name}"] = _report(ylt, run(pred, ylt), srcidx)
        done(f"YLT {name}", out[f"ylt_{name}"])
    del ylt

    # KJV as if untagged: production recipe (self-training on KJV text, no tags).
    kjv_exs, resolution = ctx.kjv
    kjv_test = [e for e in kjv_exs if e.key[0] in TEST_BOOKS]
    kjv_dev = [e for e in kjv_exs if split_of(e.key[0]) == "dev"]
    st = self_train(ctx, model, ("train",), "KJV")
    for name, rrk in (("hmm", None), ("rerank", rr)):
        pred = Predictor(st, rrk)
        pred.calib = fit_calibrator(pred, dev)
        preds = run(pred, kjv_test)
        out[f"kjv_{name}"] = _report(kjv_test, preds, srcidx)
        done(f"KJV {name}", out[f"kjv_{name}"])
        if rrk is not None:
            # KJV-specific calibration: content words refitted on KJV tags (dev books).
            kc = fit_calibrator(Predictor(st, rrk), kjv_dev)
            pred.calib = ClassCalibrator(pred.calib.function, kc.content)
            preds = run(pred, kjv_test)
            out["kjv_rerank_kjvcalib"] = _report(kjv_test, preds, srcidx)
            done("KJV rerank + KJV calibration", out["kjv_rerank_kjvcalib"])
    out["kjv_tag_resolution"] = dict(Counter(s for res in resolution.values() for s, _ in res))
    out["rerank_weights"] = dict(sorted(rr.w.items(), key=lambda kv: -abs(kv[1]))[:60])
    EVAL_PATH.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"Wrote {EVAL_PATH} ({time.time() - t:.0f}s)")


STEPS = {"bsb": step_bsb, "kjv": step_kjv, "web": step_web, "index": step_index,
         "evaluate": step_evaluate}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=[*STEPS, "all"])
    args = ap.parse_args()
    ctx = Context(DB_PATH, kjv_zip())
    steps = ["bsb", "kjv", "web", "index"] if args.step == "all" else [args.step]
    for name in steps:
        t = time.time()
        print(f"== {name}")
        STEPS[name](ctx)
        print(f"   {name} done in {time.time() - t:.0f}s")


if __name__ == "__main__":
    main()
