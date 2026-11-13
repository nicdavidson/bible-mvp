#!/bin/bash
# Fine-tune job for the crucible GPU queue (docs/SEMANTIC_SEARCH_2026-11.md, "Fine-tune").
#
#   ssh crucible gpu-job submit --tenant personal --gpu 1080 --mem 7 --max-hours 2 \
#       --name bible-gte-ft --cwd /data/projects/bible-mvp-wt/search \
#       -- scripts/finetune_job.sh 9e72fed6dc0a
#
# One-time venv (pinned; cu121 wheels still include Pascal kernels for the GTX 1080):
#   uv venv .venv-train -p 3.12
#   uv pip install -p .venv-train --index-url https://download.pytorch.org/whl/cu121 torch==2.5.1
#   uv pip install -p .venv-train sentence-transformers==3.3.1 transformers==4.46.3 \
#       datasets==3.1.0 accelerate==1.1.1 onnx==1.17.0 onnxruntime==1.20.1 \
#       tokenizers==0.20.3 numpy==2.1.3 safetensors==0.4.5
set -euo pipefail
cd "$(dirname "$0")/.."
DATA=data/finetune/${1:?usage: finetune_job.sh <data dir under data/finetune>}
OUT=$DATA/run-1
EXTRA=()
if [ "${SMOKE:-0}" = 1 ]; then OUT=$DATA/smoke; EXTRA=(--max-steps 10); fi
echo "[job] $(date -Is) host=$(hostname) gpu=${CUDA_VISIBLE_DEVICES:-none}"
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv || true

if [ "${SMOKE:-0}" = 1 ]; then
    .venv-train/bin/python scripts/finetune_semantic.py --data "$DATA" --out "$OUT" "${EXTRA[@]}"
    echo "[job] smoke done"; exit 0
fi
# Pre-registered sweep: three learning rates, best checkpoint of each chosen on the dev
# select queries; the run with the best select score wins. Test data is never consulted.
for LR in 1e-5 2e-5 5e-5; do
    .venv-train/bin/python scripts/finetune_semantic.py --data "$DATA" --out "$DATA/lr-$LR" --lr "$LR"
done
BEST=$(.venv-train/bin/python - "$DATA" <<'PY'
import json, sys, pathlib
runs = sorted(pathlib.Path(sys.argv[1]).glob("lr-*/run.json"))
best = max(runs, key=lambda p: json.loads(p.read_text())["best"]["score"])
for p in runs:
    print(p.parent.name, json.loads(p.read_text())["best"], file=sys.stderr)
print(best.parent)
PY
)
echo "[job] selected $BEST"
rm -rf "$OUT"; cp -r "$BEST" "$OUT"

# Install both exports under content-addressed names: data/models/<key>@<sha12 of onnx>/
install() {
    local key=$1 src=$2
    local sha
    sha=$(sha256sum "$src/model_quantized.onnx" | cut -c1-12)
    rm -rf "data/models/$key@$sha"
    mkdir -p "data/models/$key@$sha"
    cp "$src"/model_quantized.onnx "$src"/tokenizer.json "$src"/spec.json "data/models/$key@$sha/"
    echo "[job] installed data/models/$key@$sha"
}
install gte-small-bible "$OUT/onnx"
install gte-small-ctrl "$OUT/control"

# Corpus embeddings + full evaluation with the shipped (int8 ONNX, CPU) path. The GPU is
# done by now; this is CPU work in the bridge venv, which also runs on crucible.
SEMANTIC_THREADS=4 .venv/bin/python scripts/eval_semantic.py \
    --models gte-small-ctrl,gte-small-bible --verse-only --threads 4 \
    --out "$OUT/eval.json"
echo "[job] done $(date -Is)"
