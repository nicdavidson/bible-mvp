#!/usr/bin/env python3
"""Fine-tune gte-small on Nave's + cross-reference pairs, select on dev, export int8 ONNX.

Runs on a CUDA GPU in .venv-train (torch 2.5.1+cu121, sentence-transformers 3.3.1; pins in
scripts/finetune_job.sh). Input: a directory written by scripts/finetune_data.py.

  1. MultipleNegativesRankingLoss on (anchor, positive, hard negative), in-batch negatives,
     NO_DUPLICATES batches, fixed seed, fp32 (the GTX 1080 has no fast fp16).
  2. Every EVAL_EVERY steps: nDCG@10 on the *select* queries only (dev side, never trained
     on). The best step's weights are kept. Test splits and the 64 questions are never read.
  3. Export the best model and, as a control, the untouched base model with the same
     torch.onnx.export + onnxruntime dynamic int8 quantization, so the comparison isolates
     the fine-tune from the export.

Output (in --out): best/ (sentence-transformers), onnx/{model_quantized.onnx, tokenizer.json,
spec.json}, control/{...}, run.json (hyperparameters, versions, select curve, hashes).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import sqlite3
import time
from pathlib import Path

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("DATABASE_PATH", PROJECT_ROOT / "data" / "bible.db"))

BASE_REPO = "thenlper/gte-small"
BASE_REVISION = "17e1f347d17fe144873b1201da91788898c639cd"
HPARAMS = {
    "seed": 1234, "lr": 2e-5, "batch_size": 64, "epochs": 3, "warmup_ratio": 0.1,
    "max_seq_length": 128, "loss": "MultipleNegativesRankingLoss", "scale": 20.0,
    "batch_sampler": "no_duplicates", "weight_decay": 0.01, "eval_every": 100,
}


def seed_everything(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.use_deterministic_algorithms(True, warn_only=True)


def load_corpus():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    rows = conn.execute("""SELECT book, chapter, verse, text FROM verses
                           WHERE translation_id = 'BSB' ORDER BY book_order, chapter, verse""").fetchall()
    conn.close()
    return [(r[0], r[1], r[2]) for r in rows], [r[3] for r in rows]


def ndcg10(ranked, rel):
    rel = set(rel)
    dcg = sum(1 / math.log2(r + 2) for r, i in enumerate(ranked[:10]) if i in rel)
    return dcg / sum(1 / math.log2(r + 2) for r in range(min(10, len(rel))))


class SelectEval:
    """nDCG@10 on the dev-side select queries; mean of the Nave's and xref halves."""

    def __init__(self, select: dict, refs, texts):
        self.select, self.refs, self.texts = select, refs, texts
        self.pos = {r: i for i, r in enumerate(refs)}

    def __call__(self, model) -> dict:
        model.eval()
        with torch.no_grad():
            docs = model.encode(self.texts, batch_size=256, convert_to_tensor=True,
                                normalize_embeddings=True, show_progress_bar=False)
            qs = model.encode([x["q"] for x in self.select["naves"]], batch_size=256,
                              convert_to_tensor=True, normalize_embeddings=True,
                              show_progress_bar=False)
        nav = []
        for x, qv in zip(self.select["naves"], qs):
            ranked = torch.topk(docs @ qv, 10).indices.tolist()
            nav.append(ndcg10(ranked, x["rel"]))
        xr = []
        for x in self.select["xref"]:
            s = docs @ docs[x["src"]]
            b, c, v = self.refs[x["src"]]
            for n in range(v - 3, v + 4):
                i = self.pos.get((b, c, n))
                if i is not None:
                    s[i] = -1e9
            xr.append(ndcg10(torch.topk(s, 10).indices.tolist(), x["rel"]))
        model.train()
        out = {"naves": float(np.mean(nav)), "xref": float(np.mean(xr))}
        out["mean"] = (out["naves"] + out["xref"]) / 2
        return out


def export_int8(st_model, out: Path):
    """torch.onnx.export of the transformer (last_hidden_state) + dynamic int8 weights."""
    from onnxruntime.quantization import QuantType, quantize_dynamic

    out.mkdir(parents=True, exist_ok=True)
    hf = st_model[0].auto_model.to("cpu").eval()
    tok = st_model.tokenizer
    enc = tok(["a short example", "another example sentence here"], padding=True,
              return_tensors="pt")
    names = ["input_ids", "attention_mask", "token_type_ids"]
    dyn = {n: {0: "batch", 1: "seq"} for n in names}
    dyn["last_hidden_state"] = {0: "batch", 1: "seq"}
    fp32 = out / "model.onnx"
    with torch.no_grad():
        torch.onnx.export(hf, tuple(enc[n] for n in names), str(fp32), input_names=names,
                          output_names=["last_hidden_state"], dynamic_axes=dyn,
                          opset_version=14, do_constant_folding=True)
    quantize_dynamic(str(fp32), str(out / "model_quantized.onnx"), weight_type=QuantType.QInt8,
                     per_channel=True)
    fp32.unlink()
    tok.backend_tokenizer.save(str(out / "tokenizer.json"))
    hf.to("cuda" if torch.cuda.is_available() else "cpu")
    return {f: hashlib.sha256((out / f).read_bytes()).hexdigest()
            for f in ("model_quantized.onnx", "tokenizer.json")}


def main():
    from datasets import Dataset
    from sentence_transformers import (
        SentenceTransformer,
        SentenceTransformerTrainer,
        SentenceTransformerTrainingArguments,
    )
    from sentence_transformers.losses import MultipleNegativesRankingLoss
    from sentence_transformers.training_args import BatchSamplers
    from transformers import TrainerCallback

    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--max-steps", type=int, default=-1, help="smoke test")
    ap.add_argument("--lr", type=float, help="override HPARAMS lr (the job sweeps 3 values)")
    a = ap.parse_args()
    hp = dict(HPARAMS)
    if a.lr:
        hp["lr"] = a.lr
    seed_everything(hp["seed"])
    started = time.time()

    data_manifest = json.loads((a.data / "manifest.json").read_text())
    select = json.loads((a.data / "select.json").read_text())
    rows = [json.loads(line) for line in (a.data / "train.jsonl").read_text().splitlines()]
    train = Dataset.from_dict({k: [r[k] for r in rows] for k in ("anchor", "positive",
                                                                  "negative")})
    refs, texts = load_corpus()
    evaluate = SelectEval(select, refs, texts)

    cache = PROJECT_ROOT / "data" / "sources" / "hf"
    model = SentenceTransformer(BASE_REPO, revision=BASE_REVISION, cache_folder=str(cache),
                                device="cuda")
    model.max_seq_length = hp["max_seq_length"]
    curve = [{"step": 0, **evaluate(model)}]
    print("select @0", curve[-1], flush=True)
    best = {"score": curve[-1]["mean"], "step": 0}
    best_dir = a.out / "best"
    a.out.mkdir(parents=True, exist_ok=True)
    model.save(str(best_dir))

    class Select(TrainerCallback):
        def on_step_end(self, args, state, control, **kw):
            if state.global_step % hp["eval_every"] == 0:
                r = {"step": state.global_step, **evaluate(model)}
                curve.append(r)
                print("select", r, flush=True)
                if r["mean"] > best["score"]:
                    best.update(score=r["mean"], step=state.global_step)
                    model.save(str(best_dir))

    args = SentenceTransformerTrainingArguments(
        output_dir=str(a.out / "trainer"), num_train_epochs=hp["epochs"],
        per_device_train_batch_size=hp["batch_size"], learning_rate=hp["lr"],
        warmup_ratio=hp["warmup_ratio"], weight_decay=hp["weight_decay"], seed=hp["seed"],
        data_seed=hp["seed"], fp16=False, bf16=False, batch_sampler=BatchSamplers.NO_DUPLICATES,
        save_strategy="no", logging_steps=50, report_to=[], max_steps=a.max_steps,
        dataloader_num_workers=0)
    trainer = SentenceTransformerTrainer(
        model=model, args=args, train_dataset=train,
        loss=MultipleNegativesRankingLoss(model, scale=hp["scale"]), callbacks=[Select()])
    trainer.train()
    final = {"step": trainer.state.global_step, **evaluate(model)}
    curve.append(final)
    print("select final", final, flush=True)
    if final["mean"] > best["score"]:
        best.update(score=final["mean"], step=final["step"])
        model.save(str(best_dir))
    shutil.rmtree(a.out / "trainer", ignore_errors=True)

    best_model = SentenceTransformer(str(best_dir), device="cuda")
    hashes = export_int8(best_model, a.out / "onnx")
    base = SentenceTransformer(BASE_REPO, revision=BASE_REVISION, cache_folder=str(cache),
                               device="cuda")
    control_hashes = export_int8(base, a.out / "control")
    spec = {"pooling": "mean", "dim": 384, "query_prefix": "", "doc_prefix": "",
            "onnx_file": "model_quantized.onnx", "license": "MIT (derived from thenlper/gte-small)"}
    for d, h in (("onnx", hashes), ("control", control_hashes)):
        (a.out / d / "spec.json").write_text(json.dumps({**spec, "sha256": h}, indent=1))

    import importlib.metadata as md
    run = {
        "base": {"repo": BASE_REPO, "revision": BASE_REVISION},
        "data": {"dir": a.data.name, "sha256": data_manifest["sha256"],
                 "train_examples": len(rows)},
        "hparams": hp, "best": best, "select_curve": curve,
        "versions": {p: md.version(p) for p in ("torch", "sentence-transformers",
                                                 "transformers", "onnx", "onnxruntime",
                                                 "tokenizers")},
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "sha256": {"onnx": hashes, "control": control_hashes},
        "minutes": round((time.time() - started) / 60, 1),
    }
    (a.out / "run.json").write_text(json.dumps(run, indent=1))
    print(json.dumps({k: run[k] for k in ("best", "sha256", "minutes")}, indent=1))


if __name__ == "__main__":
    main()
