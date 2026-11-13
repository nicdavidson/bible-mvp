#!/usr/bin/env python3
"""Build step `embeddings`: one meaning-search vector per BSB verse, stored compactly.

Reproducible: the model is pinned by repo + commit (backend/semantic.py CANDIDATES), files
are downloaded once into data/models/ (git-ignored) and their sha256 is stored with the
vectors, the ONNX session runs single-threaded and sequential, batches are fixed, and the
stored bytes are hashed (`semantic_meta.vectors_sha256`) so two builds can be compared.

Each verse vector mixes the verse alone and the verse with its neighbours (same chapter):
    v = ALPHA * embed(verse) + (1 - ALPHA) * embed(prev + verse + next)
Scoring is linear in v, so this equals mixing the two similarities (tuned on the Nave's
dev split, docs/SEMANTIC_SEARCH_2026-11.md). Stored as int8 + per-vector scale, plus a
packed sign-bit copy for the browser/offline index.

Usage:
    python scripts/build_embeddings.py                 # full build into $DATABASE_PATH
    python scripts/build_embeddings.py --limit 200     # first 200 verses (tests)
    python scripts/build_embeddings.py --export-browser data/semantic-browser
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.search_text import unit_texts  # noqa: E402
from backend.semantic import (  # noqa: E402
    CANDIDATES,
    SHIPPED_MODEL,
    VECTOR_DDL,
    Encoder,
    fetch_model,
    meta_json,
    model_fingerprint,
    pack_binary,
    quantize_int8,
)

DB_PATH = Path(os.environ.get("DATABASE_PATH", PROJECT_ROOT / "data" / "bible.db"))
TRANSLATION = "BSB"
ALPHA = 1.0          # verse vs +-1 verse window; 1.0 = verse only (see docstring)
BATCH = 32


def build(db_path: Path, model_key: str, limit: int | None = None, threads: int = 1) -> dict:

    spec = CANDIDATES[model_key]
    directory = fetch_model(spec)
    enc = Encoder(spec, directory, threads=threads)

    conn = sqlite3.connect(db_path)
    rows = conn.execute("""SELECT book, chapter, verse, book_order, text FROM verses
                           WHERE translation_id = ? ORDER BY book_order, chapter, verse""",
                        (TRANSLATION,)).fetchall()
    if limit:
        rows = rows[:limit]
    if not rows:
        raise SystemExit(f"No {TRANSLATION} verses in {db_path}; run the bsb step first")

    t0 = time.time()
    vecs = enc.embed(unit_texts(rows, "verse"), batch_size=BATCH)
    if ALPHA < 1.0:  # windows are 3x the text; skip them when they carry no weight
        vecs = ALPHA * vecs + (1 - ALPHA) * enc.embed(unit_texts(rows, "window"),
                                                      batch_size=BATCH)
    q8, scales = quantize_int8(vecs)
    bits = pack_binary(vecs)
    embed_s = time.time() - t0

    digest = hashlib.sha256(q8.tobytes() + scales.tobytes()).hexdigest()
    meta = meta_json(spec, model_sha256=model_fingerprint(spec, directory),
                     translation=TRANSLATION, alpha=ALPHA, count=len(rows), batch=BATCH,
                     threads=threads, vectors_sha256=digest, storage="int8+bin",
                     built_at=time.strftime("%Y-%m-%dT%H:%M:%S"))

    conn.executescript("DROP TABLE IF EXISTS semantic_vectors; DROP TABLE IF EXISTS semantic_meta;"
                       + VECTOR_DDL)
    conn.executemany(
        "INSERT INTO semantic_vectors VALUES (?, 'verse', ?, ?, ?, ?, ?, ?, ?)",
        [(i, r[0], r[1], r[2], r[3], float(scales[i]), q8[i].tobytes(), bits[i].tobytes())
         for i, r in enumerate(rows)])
    conn.executemany("INSERT INTO semantic_meta VALUES (?, ?)", sorted(meta.items()))
    conn.commit()
    conn.close()
    print(f"Model {spec.repo}@{spec.revision[:12]} ({spec.pooling}, dim {spec.dim})")
    print(f"Embedded {len(rows)} verse vectors in {embed_s:.0f}s; vectors sha256 {digest[:16]}")
    return meta


def export_browser(db_path: Path, out_dir: Path) -> dict:
    """Static files for in-browser/offline meaning search: refs, int8 matrix, scales."""
    import numpy as np

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    meta = dict(conn.execute("SELECT key, value FROM semantic_meta").fetchall())
    rows = conn.execute("SELECT book, chapter, verse, scale, vec_i8, vec_bin "
                        "FROM semantic_vectors ORDER BY unit_id").fetchall()
    conn.close()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "vectors.i8").write_bytes(b"".join(r[4] for r in rows))
    (out_dir / "vectors.bin").write_bytes(b"".join(r[5] for r in rows))
    (out_dir / "scales.f32").write_bytes(np.array([r[3] for r in rows], np.float32).tobytes())
    # Refs as book-index/chapter/verse triples; books in canonical order.
    books = []
    for r in rows:
        if not books or books[-1] != r[0]:
            books.append(r[0])
    idx = {b: i for i, b in enumerate(books)}
    (out_dir / "refs.json").write_text(json.dumps(
        {"books": books, "refs": [[idx[r[0]], r[1], r[2]] for r in rows]},
        separators=(",", ":")))
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    sizes = {p.name: p.stat().st_size for p in out_dir.iterdir()}
    print(json.dumps(sizes, indent=1))
    return sizes


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--model", default=SHIPPED_MODEL, choices=sorted(CANDIDATES))
    p.add_argument("--limit", type=int, help="only the first N verses (tests)")
    p.add_argument("--threads", type=int, default=1,
                   help="ONNX threads; 1 is the reproducible default")
    p.add_argument("--db", type=Path, default=DB_PATH)
    p.add_argument("--export-browser", type=Path, help="write static vector files and exit")
    args = p.parse_args()
    if args.export_browser:
        export_browser(args.db, args.export_browser)
        return
    build(args.db, args.model, args.limit, args.threads)


if __name__ == "__main__":
    main()
