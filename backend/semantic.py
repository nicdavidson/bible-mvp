"""Meaning search: query encoder, compact vector storage, scoring.

One implementation shared by the build step (scripts/build_embeddings.py), the evaluation
harness (scripts/eval_semantic.py) and the API (routers/semantic.py), so the vectors and
the query are always produced by the same code.

Runtime dependencies are optional. numpy, onnxruntime and tokenizers are imported lazily;
if any is missing, or the model files or vectors are absent or do not match, `get_index()`
returns None and the API falls back to keyword search. Nothing here generates text.

Storage (table `semantic_vectors`, one row per unit, see `VECTOR_DDL`):
  - `vec_i8`: int8 vector, symmetric per-vector scale (`scale` = max|x| / 127)
  - `vec_bin`: sign bits packed (dim/8 bytes) for the browser / offline index
Scores are cosine similarities computed from the dequantized int8 vectors.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = Path(os.environ.get("SEMANTIC_MODELS_DIR", PROJECT_ROOT / "data" / "models"))


@dataclass(frozen=True)
class ModelSpec:
    key: str
    repo: str
    revision: str            # pinned commit sha on huggingface.co
    onnx_file: str           # path inside the repo ("" for static models)
    pooling: str             # "mean" | "cls" | "static"
    dim: int
    license: str
    query_prefix: str = ""
    doc_prefix: str = ""
    max_tokens: int = 256
    extra_files: tuple = field(default_factory=tuple)

    @property
    def files(self) -> tuple:
        main = ("model.safetensors",) if self.pooling == "static" else (self.onnx_file,)
        return main + ("tokenizer.json",) + tuple(self.extra_files)


_RETRIEVAL_PROMPT = "Represent this sentence for searching relevant passages: "

# Candidates evaluated in docs/SEMANTIC_SEARCH_2026-11.md. Quantized ONNX exports are the
# ones transformers.js loads too, so server and browser can share weights.
CANDIDATES: dict[str, ModelSpec] = {s.key: s for s in [
    ModelSpec("minilm-l6", "Xenova/all-MiniLM-L6-v2", "751bff37182d3f1213fa05d7196b954e230abad9",
              "onnx/model_quantized.onnx", "mean", 384, "Apache-2.0"),
    ModelSpec("bge-small", "Xenova/bge-small-en-v1.5", "ea104dacec62c0de699686887e3f920caeb4f3e3",
              "onnx/model_quantized.onnx", "cls", 384, "MIT", query_prefix=_RETRIEVAL_PROMPT),
    ModelSpec("gte-small", "Xenova/gte-small", "5927d1727bb12db490052a1b33265ad78058de08",
              "onnx/model_quantized.onnx", "mean", 384, "MIT"),
    ModelSpec("e5-small-v2", "Xenova/e5-small-v2", "02af79985278377e65c724a76275707cb0333c70",
              "onnx/model_quantized.onnx", "mean", 384, "MIT",
              query_prefix="query: ", doc_prefix="passage: "),
    ModelSpec("arctic-xs", "Snowflake/snowflake-arctic-embed-xs",
              "d8c86521100d3556476a063fc2342036d45c106f", "onnx/model_quantized.onnx", "cls", 384,
              "Apache-2.0", query_prefix=_RETRIEVAL_PROMPT),
    ModelSpec("arctic-s", "Snowflake/snowflake-arctic-embed-s",
              "e596f507467533e48a2e17c007f0e1dacc837b33", "onnx/model_quantized.onnx", "cls", 384,
              "Apache-2.0", query_prefix=_RETRIEVAL_PROMPT),
    ModelSpec("mxbai-xsmall", "mixedbread-ai/mxbai-embed-xsmall-v1",
              "e6ac24e5d6efb8782b59de1647b3ececb4ece94e", "onnx/model_quantized.onnx", "mean", 384,
              "Apache-2.0"),
    ModelSpec("potion-8m", "minishlab/potion-base-8M", "bf8b056651a2c21b8d2565580b8569da283cab23",
              "", "static", 256, "MIT"),
    ModelSpec("potion-retrieval-32m", "minishlab/potion-retrieval-32M",
              "6fc8051fab2a1e0ee76689cf08c853792ac285e7", "", "static", 512, "MIT"),
]}

# The model the build step embeds with and the API loads. Chosen in
# docs/SEMANTIC_SEARCH_2026-11.md; changing it means re-running the `embeddings` build step.
SHIPPED_MODEL = os.environ.get("SEMANTIC_MODEL", "gte-small")

VECTOR_DDL = """
CREATE TABLE IF NOT EXISTS semantic_vectors (
    unit_id INTEGER PRIMARY KEY,      -- 0..N-1, row index into the in-memory matrix
    kind TEXT NOT NULL,               -- 'verse' (one vector per BSB verse)
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    book_order INTEGER NOT NULL,
    scale REAL NOT NULL,              -- int8 dequantization factor
    vec_i8 BLOB NOT NULL,             -- dim bytes
    vec_bin BLOB NOT NULL             -- dim/8 bytes, sign bits (offline/browser index)
);
CREATE INDEX IF NOT EXISTS idx_semantic_ref ON semantic_vectors(book, chapter, verse);
CREATE TABLE IF NOT EXISTS semantic_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def model_dir(spec: ModelSpec) -> Path:
    return MODELS_DIR / f"{spec.key}@{spec.revision[:12]}"


def fetch_model(spec: ModelSpec) -> Path:
    """Download the pinned model files once (build time) and return the local directory.

    Files land flat in data/models/<key>@<rev12>/ (git-ignored), fetched from the
    immutable revision URL, so rebuilds are offline and the Dockerfile COPYs one directory.
    """
    import urllib.request

    target = model_dir(spec)
    for f in spec.files:
        dest = target / Path(f).name
        if dest.exists() and dest.stat().st_size > 0:
            continue
        target.mkdir(parents=True, exist_ok=True)
        url = f"https://huggingface.co/{spec.repo}/resolve/{spec.revision}/{f}"
        tmp = dest.with_suffix(dest.suffix + ".part")
        req = urllib.request.Request(url, headers={"User-Agent": "BibleMVP/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as out:
            while chunk := r.read(1 << 20):
                out.write(chunk)
        tmp.rename(dest)
    return target


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def model_fingerprint(spec: ModelSpec, directory: Path) -> str:
    """sha256 over the model files, so vectors are never scored against a different model."""
    h = hashlib.sha256()
    for f in spec.files:
        h.update(file_sha256(directory / Path(f).name).encode())
    return h.hexdigest()


class Encoder:
    """Text -> L2-normalised float32 vectors. Deterministic for fixed files and threads=1."""

    def __init__(self, spec: ModelSpec, directory: Path | None = None, threads: int = 1):
        import numpy as np
        from tokenizers import Tokenizer

        self.np = np
        self.spec = spec
        self.dir = directory or model_dir(spec)
        self.tok = Tokenizer.from_file(str(self.dir / "tokenizer.json"))
        if spec.pooling == "static":
            from safetensors.numpy import load_file
            self.table = load_file(str(self.dir / "model.safetensors"))["embeddings"]
            self.tok.no_padding()
            self.tok.no_truncation()
            self.session = None
        else:
            import onnxruntime as ort
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = threads
            opts.inter_op_num_threads = 1
            opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            self.session = ort.InferenceSession(str(self.dir / Path(spec.onnx_file).name), opts,
                                                providers=["CPUExecutionProvider"])
            self.input_names = {i.name for i in self.session.get_inputs()}
            self.tok.enable_truncation(spec.max_tokens)
            self.tok.enable_padding(pad_id=self.tok.token_to_id("[PAD]") or 0)

    def _encode(self, texts: list[str]):
        np = self.np
        if self.session is None:  # static embeddings: mean of token rows
            out = np.zeros((len(texts), self.table.shape[1]), dtype=np.float32)
            for i, enc in enumerate(self.tok.encode_batch(texts, add_special_tokens=False)):
                ids = [t for t in enc.ids if t < len(self.table)]
                if ids:
                    out[i] = self.table[ids].mean(axis=0)
            return out
        encs = self.tok.encode_batch(texts)
        ids = np.array([e.ids for e in encs], dtype=np.int64)
        mask = np.array([e.attention_mask for e in encs], dtype=np.int64)
        feeds = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self.input_names:
            feeds["token_type_ids"] = np.zeros_like(ids)
        hidden = self.session.run(None, feeds)[0]
        if self.spec.pooling == "cls":
            return hidden[:, 0, :].astype(np.float32)
        m = mask[:, :, None].astype(np.float32)
        return ((hidden * m).sum(axis=1) / np.clip(m.sum(axis=1), 1e-9, None)).astype(np.float32)

    def embed(self, texts: list[str], is_query: bool = False, batch_size: int = 32):
        np = self.np
        prefix = self.spec.query_prefix if is_query else self.spec.doc_prefix
        texts = [prefix + t for t in texts]
        # Length-sorted batches cut padding; results are put back in input order.
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        out = np.zeros((len(texts), self.spec.dim), dtype=np.float32)
        for s in range(0, len(order), batch_size):
            idx = order[s:s + batch_size]
            out[idx] = self._encode([texts[i] for i in idx])
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.clip(norms, 1e-12, None)


# ---------- compact storage ----------

def quantize_int8(vecs):
    """Symmetric per-vector int8. Returns (int8 matrix, float32 scales)."""
    import numpy as np
    scale = np.abs(vecs).max(axis=1) / 127.0
    scale = np.where(scale == 0, 1.0, scale).astype(np.float32)
    q = np.clip(np.rint(vecs / scale[:, None]), -127, 127).astype(np.int8)
    return q, scale


def pack_binary(vecs):
    import numpy as np
    return np.packbits(vecs > 0, axis=1)


# ---------- in-memory index ----------

class VectorIndex:
    """All verse vectors as one float32 matrix (31K x 384 = 48 MB) or int8 + scales.

    Scoring is a single matrix-vector product: ~31K x 384 multiply-adds, a few ms on one core.
    Kept as int8 in memory (12 MB) and dequantized per query in chunks to save RAM.
    """

    def __init__(self, q8, scales, refs, book_orders, meta: dict):
        import numpy as np
        self.np = np
        self.q8 = q8                      # (N, dim) int8
        self.scales = scales              # (N,) float32
        self.refs = refs                  # list of (book, chapter, verse)
        self.book_orders = book_orders    # (N,) int16
        self.pos = {r: i for i, r in enumerate(refs)}
        self.meta = meta

    @classmethod
    def load(cls, conn: sqlite3.Connection):
        import numpy as np
        meta = dict(conn.execute("SELECT key, value FROM semantic_meta").fetchall())
        rows = conn.execute(
            "SELECT book, chapter, verse, book_order, scale, vec_i8 FROM semantic_vectors "
            "WHERE kind = 'verse' ORDER BY unit_id").fetchall()
        if not rows:
            raise ValueError("no vectors")
        dim = int(meta["dim"])
        q8 = np.frombuffer(b"".join(r[5] for r in rows), dtype=np.int8).reshape(len(rows), dim)
        scales = np.array([r[4] for r in rows], dtype=np.float32)
        refs = [(r[0], r[1], r[2]) for r in rows]
        orders = np.array([r[3] for r in rows], dtype=np.int16)
        return cls(q8, scales, refs, orders, meta)

    def scores(self, qvec):
        """Cosine similarity of qvec against every verse (vectors were unit length).

        int8 rows are converted to float32 4096 at a time: ~8 ms for 31K x 384 on one N100
        core with a 6 MB temporary, vs ~15-40 ms and a 48 MB temporary for one big upcast.
        """
        np = self.np
        q = qvec.astype(np.float32)
        out = np.empty(len(self.q8), dtype=np.float32)
        for s in range(0, len(self.q8), 4096):
            out[s:s + 4096] = self.q8[s:s + 4096].astype(np.float32) @ q
        return out * self.scales

    def vector(self, ref):
        i = self.pos.get(ref)
        if i is None:
            return None
        v = self.q8[i].astype(self.np.float32) * self.scales[i]
        return v / max(float(self.np.linalg.norm(v)), 1e-12)

    def top(self, scores, k: int, allowed_orders=None, exclude=()):
        """Indices of the k best scores, optionally restricted to a set of book_orders."""
        np = self.np
        s = scores.copy()
        if allowed_orders is not None:
            s[~np.isin(self.book_orders, list(allowed_orders))] = -np.inf
        for ref in exclude:
            i = self.pos.get(ref)
            if i is not None:
                s[i] = -np.inf
        k = min(k, int(np.isfinite(s).sum()))
        if k <= 0:
            return []
        idx = np.argpartition(-s, k - 1)[:k]
        return [int(i) for i in idx[np.argsort(-s[idx], kind="stable")]]


def rrf(rankings: list[list], k: int = 60, weights: list[float] | None = None) -> list:
    """Reciprocal rank fusion of ranked lists of hashable ids."""
    weights = weights or [1.0] * len(rankings)
    score: dict = {}
    for ranking, w in zip(rankings, weights):
        for rank, item in enumerate(ranking):
            score[item] = score.get(item, 0.0) + w / (k + rank + 1)
    return sorted(score, key=lambda x: (-score[x], rankings[0].index(x)
                                        if x in rankings[0] else 1 << 30))


# ---------- process-wide singleton ----------

_lock = threading.Lock()
_state: dict = {"loaded": False, "index": None, "encoder": None, "error": None}


def get_index(db_path: Path | None = None):
    """(VectorIndex, Encoder) or None if meaning search is unavailable. Loaded once."""
    if _state["loaded"]:
        return (_state["index"], _state["encoder"]) if _state["index"] else None
    with _lock:
        if _state["loaded"]:
            return (_state["index"], _state["encoder"]) if _state["index"] else None
        try:
            from .database import DATABASE_PATH
            path = db_path or DATABASE_PATH
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            try:
                index = VectorIndex.load(conn)
            finally:
                conn.close()
            spec = CANDIDATES[index.meta["model_key"]]
            directory = model_dir(spec)
            if index.meta.get("model_sha256") != model_fingerprint(spec, directory):
                raise ValueError(f"model files in {directory} do not match the stored vectors")
            threads = int(os.environ.get("SEMANTIC_THREADS", "1"))
            _state.update(index=index, encoder=Encoder(spec, directory, threads=threads))
            logger.info("Meaning search ready: %s, %d vectors", spec.key, len(index.refs))
        except Exception as e:  # missing deps/files/table: degrade to keyword search
            _state["error"] = f"{type(e).__name__}: {e}"
            logger.warning("Meaning search unavailable (%s); keyword search only", _state["error"])
        _state["loaded"] = True
    return (_state["index"], _state["encoder"]) if _state["index"] else None


def reset_for_tests():
    _state.update(loaded=False, index=None, encoder=None, error=None)


def status() -> dict:
    return {"available": bool(_state["index"]), "loaded": _state["loaded"],
            "error": _state["error"],
            "model": _state["index"].meta.get("model_key") if _state["index"] else None}


def meta_json(spec: ModelSpec, **extra) -> dict:
    return {"model_key": spec.key, "model_repo": spec.repo, "model_revision": spec.revision,
            "dim": str(spec.dim), "pooling": spec.pooling, **{k: str(v) for k, v in extra.items()},
            "query_prefix": json.dumps(spec.query_prefix)}
