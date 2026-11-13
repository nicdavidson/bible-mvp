#!/usr/bin/env python3
"""Publish trained meaning-search weights to the release bucket (design; not run yet).

Same bucket and credentials as scripts/release_db.py. Layout, immutable like DB releases:

    models/<key>/<sha12>/model_quantized.onnx   int8 ONNX the server and browser run
    models/<key>/<sha12>/tokenizer.json
    models/<key>/<sha12>/spec.json              pooling, dim, prefixes, per-file sha256
    models/<key>/<sha12>/run.json               base revision, seed, hyperparameters, data sha256
    models/<key>/<sha12>/train-data.tar.gz      train.jsonl + select.json + manifest.json

<sha12> is the first 12 hex of the ONNX file's sha256, the same name as the local
data/models/<key>@<sha12>/ directory. To ship, register the model in backend/semantic.py:

    ModelSpec("<key>", "bible-mvp/<key>", "<full onnx sha256>", "model_quantized.onnx", "mean",
              384, "MIT", source="bucket:models/<key>/<sha12>",
              sha256=(("model_quantized.onnx", "<sha>"), ("tokenizer.json", "<sha>")))

Builds then fetch it deterministically (scripts/fetch_model.py in CI, fetch_model() in the
build step), verified against the pins; a missing or altered object fails the build.

    set -a; . ~/.config/bible-mvp/tigris.env; set +a      # on crucible
    python scripts/release_model.py gte-small-bible data/finetune/<data>/run-1
"""
import hashlib
import json
import os
import sys
import tarfile
import tempfile
from pathlib import Path

FILES = ("model_quantized.onnx", "tokenizer.json", "spec.json")


def plan(key: str, run_dir: Path) -> tuple[str, list[tuple[Path, str]]]:
    """(prefix, [(local file, object key)]) without touching the network."""
    onnx = run_dir / "onnx" / "model_quantized.onnx"
    sha12 = hashlib.sha256(onnx.read_bytes()).hexdigest()[:12]
    prefix = f"models/{key}/{sha12}"
    items = [(run_dir / "onnx" / f, f"{prefix}/{f}") for f in FILES]
    items.append((run_dir / "run.json", f"{prefix}/run.json"))
    return prefix, items


def main(key: str, run_dir: Path) -> None:
    import boto3

    prefix, items = plan(key, run_dir)
    s3, bucket = boto3.client("s3"), os.environ["BUCKET_NAME"]
    if s3.list_objects_v2(Bucket=bucket, Prefix=f"{prefix}/").get("KeyCount"):
        sys.exit(f"{prefix} already exists; releases are immutable")
    data_dir = run_dir.parent
    with tempfile.TemporaryDirectory() as tmp:
        tar = Path(tmp) / "train-data.tar.gz"
        with tarfile.open(tar, "w:gz") as t:
            for f in ("train.jsonl", "select.json", "manifest.json"):
                t.add(data_dir / f, arcname=f)
        for path, obj in [*items, (tar, f"{prefix}/train-data.tar.gz")]:
            s3.upload_file(str(path), bucket, obj)
            print(f"uploaded {obj}")
    spec = json.loads((run_dir / "onnx" / "spec.json").read_text())
    print(json.dumps({"source": f"bucket:{prefix}", "sha256": spec["sha256"]}, indent=1))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], Path(sys.argv[2]))
