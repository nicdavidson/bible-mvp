#!/usr/bin/env python3
"""Server-side cost of meaning search per model: load time, RAM, query latency on ONE core.

Each model runs in a fresh subprocess pinned to CPU 0 (taskset) with one ONNX thread, the
closest local stand-in for a Fly shared-cpu-1x machine. RSS is measured before importing
numpy/onnxruntime and after loading the model plus a 31K x dim int8 vector matrix, so the
number is what the feature adds to the web process.

Usage: python scripts/bench_semantic.py --models bge-small,minilm-l6 [--cpu 0]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
QUESTIONS = PROJECT_ROOT / "tests" / "fixtures" / "semantic_questions.json"


def rss_mb() -> float:
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    return 0.0


def child(key: str, n_vectors: int) -> dict:
    import time
    base = rss_mb()
    t0 = time.perf_counter()
    sys.path.insert(0, str(PROJECT_ROOT))
    import numpy as np

    from backend.semantic import CANDIDATES, Encoder, VectorIndex, fetch_model
    t_import = time.perf_counter() - t0
    spec = CANDIDATES[key]
    directory = fetch_model(spec)
    t1 = time.perf_counter()
    enc = Encoder(spec, directory, threads=1)
    rng = np.random.default_rng(0)
    q8 = rng.integers(-127, 128, size=(n_vectors, spec.dim), dtype=np.int8)
    scales = np.full(n_vectors, 0.01, dtype=np.float32)
    index = VectorIndex(q8, scales, [("B", 1, i) for i in range(n_vectors)],
                        np.ones(n_vectors, dtype=np.int16), {})
    t_load = time.perf_counter() - t1
    qs = [q["q"] for q in json.loads(QUESTIONS.read_text())["questions"]]
    enc.embed(qs[:3], is_query=True)  # warm-up
    lat, score = [], []
    for q in qs:
        a = time.perf_counter()
        v = enc.embed([q], is_query=True)[0]
        b = time.perf_counter()
        index.top(index.scores(v), 100)
        c = time.perf_counter()
        lat.append((b - a) * 1000)
        score.append((c - b) * 1000)
    model_bytes = sum((directory / Path(f).name).stat().st_size for f in spec.files)
    return {"model": key, "model_mb": round(model_bytes / 1e6, 1),
            "import_s": round(t_import, 2), "load_s": round(t_load, 2),
            "rss_added_mb": round(rss_mb() - base, 1),
            "embed_ms_p50": round(float(np.percentile(lat, 50)), 1),
            "embed_ms_p95": round(float(np.percentile(lat, 95)), 1),
            "score_ms_p50": round(float(np.percentile(score, 50)), 1)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--models", default="bge-small")
    p.add_argument("--cpu", default="0")
    p.add_argument("--vectors", type=int, default=31202)
    p.add_argument("--child", help=argparse.SUPPRESS)
    a = p.parse_args()
    if a.child:
        print(json.dumps(child(a.child, a.vectors)))
        return
    env = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
    for key in a.models.split(","):
        out = subprocess.run(["taskset", "-c", a.cpu, sys.executable, __file__, "--child", key,
                              "--vectors", str(a.vectors)], capture_output=True, text=True,
                             env=env, cwd=PROJECT_ROOT)
        if out.returncode:
            print(key, "failed:", out.stderr[-800:])
            continue
        print(out.stdout.strip().splitlines()[-1], flush=True)


if __name__ == "__main__":
    main()
