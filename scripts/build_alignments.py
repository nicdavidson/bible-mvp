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
from aligner.pipeline import (Context, bsb_rows, fit_calibrator, kjv_rows,  # noqa: E402
                              model_rows, self_train, train, write_rows)
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


def production_model(ctx, translation):
    """The model used to write one translation's rows, and its calibrator.

    Trained on all clean BSB gold, then (for a translation other than BSB) one
    round of self-training on that translation's own text. Calibrated on the
    dev books with a model built by the same recipe without them, so the
    calibration is out-of-sample.
    """
    cache = ctx.__dict__.setdefault("_production", {})
    if translation not in cache:
        def recipe(splits):
            m = train(ctx, splits, with_kjv=False)
            return m if translation == "BSB" else self_train(ctx, m, splits, translation)
        calib = fit_calibrator(recipe(("train", "test")), ctx.bsb_clean(("dev",)))
        cache[translation] = (recipe(("train", "dev", "test")), calib)
    return cache[translation]


def step_bsb(ctx):
    model, calib = production_model(ctx, "BSB")
    rows = list(bsb_rows(ctx, model, calib))
    write_rows(ctx.conn, "BSB", rows)
    print(f"BSB: {len(rows)} alignments ({Counter(r[5] for r in rows)})")


def step_kjv(ctx):
    model, calib = production_model(ctx, "KJV")
    stats = {}
    rows = list(kjv_rows(ctx, model, calib, stats))
    write_rows(ctx.conn, "KJV", rows)
    print(f"KJV: {len(rows)} alignments ({Counter(r[5] for r in rows)})")
    for (status, linked), n in sorted(stats.items()):
        print(f"  {status:10s} {'linked' if linked else 'no link':8s} {n}")


def step_web(ctx):
    model, calib = production_model(ctx, "WEB")
    rows = list(model_rows(ctx, "WEB", model, calib))
    write_rows(ctx.conn, "WEB", rows)
    print(f"WEB: {len(rows)} alignments")


def step_index(ctx):
    n = build_renderings(ctx.conn, RENDERING_MIN_CONFIDENCE)
    print(f"lemma_renderings: {n} rows")


def _fmt(d):
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}


def _scores(exs, preds):
    return {k: _fmt(v.as_dict()) for k, v in sorted(score_examples(exs, preds).items())}


def step_evaluate(ctx):
    out = {}
    t = time.time()
    model = train(ctx, ("train",), with_kjv=False)
    calib = fit_calibrator(model, ctx.bsb_clean(("dev",)))

    def predict(exs, constraints=None):
        return {e.key: [(p, calib(c)) for p, c in model.align(e.english, e.sources)]
                for e in exs}

    srcidx = lambda k: {tok.pos: tok for tok in ctx.src.get(k, [])}  # noqa: E731
    out["suspect_gold_verses"] = len(ctx.suspect)
    out["suspect_examples"] = sorted(f"{k[0]} {k[1]}:{k[2]}" for k in ctx.suspect)[:40]

    # 1. Held-out BSB.
    test_all = [e for e in ctx.bsb if split_of(e.key[0]) == "test"]
    test_clean = [e for e in test_all if e.key not in ctx.suspect]
    preds = predict(test_all)
    out["bsb_test_clean"] = _scores(test_clean, preds)
    out["bsb_test_all_gold"] = _scores(test_all, preds)
    out["bsb_calibration"] = calibration(test_clean, preds)
    out["bsb_thresholds"] = threshold_curve(test_clean, preds)
    c, s = error_classes(test_clean, preds, srcidx)
    out["bsb_errors"] = {"counts": dict(c), "examples": s}
    print(f"BSB test done ({time.time() - t:.0f}s)", out["bsb_test_clean"]["all"])

    # 2. KJV aligned as if untagged, scored against its Strong's tags.
    kjv_exs, resolution = ctx.kjv
    kjv_test = [e for e in kjv_exs if e.key[0] in TEST_BOOKS]
    preds = predict(kjv_test)
    out["kjv_test_vs_tags"] = _scores(kjv_test, preds)
    out["kjv_calibration"] = calibration(kjv_test, preds)
    out["kjv_thresholds"] = threshold_curve(kjv_test, preds)
    c, s = error_classes(kjv_test, preds, srcidx)
    out["kjv_errors"] = {"counts": dict(c), "examples": s}
    # 2b. The production recipe for an untagged translation: + self-training on
    #     the KJV's own text (no tags used), calibrated on BSB dev.
    st = self_train(ctx, model, ("train",), "KJV")
    st_calib = fit_calibrator(st, ctx.bsb_clean(("dev",)))
    preds = {e.key: [(p, st_calib(c)) for p, c in st.align(e.english, e.sources)]
             for e in kjv_test}
    out["kjv_test_selftrained"] = _scores(kjv_test, preds)
    out["kjv_selftrained_calibration"] = calibration(kjv_test, preds)
    out["kjv_selftrained_thresholds"] = threshold_curve(kjv_test, preds)
    c, s = error_classes(kjv_test, preds, srcidx)
    out["kjv_selftrained_errors"] = {"counts": dict(c), "examples": s}
    print(f"KJV self-trained done ({time.time() - t:.0f}s)", out["kjv_test_selftrained"]["all"])
    status = Counter(st for res in resolution.values() for st, _ in res)
    out["kjv_tag_resolution"] = dict(status)
    print(f"KJV test done ({time.time() - t:.0f}s)", out["kjv_test_vs_tags"]["all"])

    # 3. YLT (Clear-Bible manual alignment; not in the app) as a second modern gold.
    ylt = [e for e in ylt_examples(ctx.src, ctx.vocab, log=lambda *a: None)
           if e.key[0] in TEST_BOOKS]
    preds = predict(ylt)
    out["ylt_test"] = _scores(ylt, preds)
    print(f"YLT test done ({time.time() - t:.0f}s)", out["ylt_test"]["all"])

    # 4. Does adding KJV tag data help on modern English (BSB dev)?
    dev = ctx.bsb_clean(("dev",))
    m2 = train(ctx, ("train",), with_kjv=True)
    out["bsb_dev_bsb_only"] = _scores(dev, {e.key: model.align(e.english, e.sources)
                                            for e in dev})["all"]
    out["bsb_dev_with_kjv"] = _scores(dev, {e.key: m2.align(e.english, e.sources)
                                            for e in dev})["all"]
    out["calibrator"] = calib.points[:: max(1, len(calib.points) // 40)]
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
