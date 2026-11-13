"""Meaning search: API shape, scope filters, fallback, build determinism, quality pins.

API and quality tests need the `embeddings` build step in data/bible.db and the model in
data/models/ (python scripts/build_db.py --step embeddings); they skip otherwise. The
fallback and reference tests always run.
"""
import json
import re
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import semantic
from backend.core import NT_BOOKS, OT_BOOKS
from backend.database import DATABASE_PATH
from backend.main import app

ROOT = Path(__file__).parent.parent


def _vectors_built() -> bool:
    try:
        conn = sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True)
        n = conn.execute("SELECT COUNT(*) FROM semantic_vectors").fetchone()[0]
        conn.close()
        return n > 30000
    except sqlite3.Error:
        return False


needs_vectors = pytest.mark.skipif(not _vectors_built(),
                                   reason="run: python scripts/build_db.py --step embeddings")


@pytest.fixture(scope="module")
def client():
    semantic.reset_for_tests()
    return TestClient(app)


def _get(client, path, **params):
    # Rate limit is 30/min per IP; tests use distinct forwarded IPs per call.
    _get.n = getattr(_get, "n", 0) + 1
    r = client.get(path, params=params, headers={"X-Forwarded-For": f"10.9.{_get.n // 250}.{_get.n % 250}"})
    return r


def _refs(data):
    return [f"{r['book']} {r['chapter']}:{r['verse']}" for r in data["results"]]


# ---------- always run ----------

class TestDeclines:
    def test_reference_query_defers_to_reference(self, client):
        data = _get(client, "/api/search/meaning", q="john 3:16").json()
        assert data["mode"] == "reference"
        assert data["reference"] == "John 3:16"
        assert data["results"] == []

    def test_bare_book_is_reference(self, client):
        assert _get(client, "/api/search/meaning", q="Psalms").json()["mode"] == "reference"

    def test_strongs_defers(self, client):
        assert _get(client, "/api/search/meaning", q="G26").json()["mode"] == "strongs"

    def test_bad_scope(self, client):
        assert _get(client, "/api/search/meaning", q="hope", scope="book:Nope").status_code == 400

    def test_words_that_start_like_books_are_not_references(self, client):
        data = _get(client, "/api/search/meaning", q="acts of kindness").json()
        assert data["mode"] != "reference"


class TestFallback:
    def test_keyword_fallback_same_shape(self, client, monkeypatch):
        monkeypatch.setattr(semantic, "get_index", lambda *a, **k: None)
        data = _get(client, "/api/search/meaning", q="waiting on the LORD", scope="ot").json()
        assert data["mode"] == "keyword" and data["fallback"] is True
        assert data["results"], "keyword fallback should still find verses"
        r = data["results"][0]
        assert {"type", "book", "chapter", "verse", "snippet", "score", "match"} <= r.keys()
        assert r["type"] == "verse" and r["match"] == "keyword"
        assert "<mark>" in "".join(x["snippet"] for x in data["results"])
        assert all(x["book"] in OT_BOOKS for x in data["results"])

    def test_similar_fallback(self, client, monkeypatch):
        monkeypatch.setattr(semantic, "get_index", lambda *a, **k: None)
        data = _get(client, "/api/search/similar/Isaiah 40:31").json()
        assert data["fallback"] is True and data["results"] == []

    def test_missing_model_files_degrade(self, tmp_path, monkeypatch):
        semantic.reset_for_tests()
        monkeypatch.setattr(semantic, "MODELS_DIR", tmp_path)  # model files "missing"
        assert semantic.get_index() is None
        assert semantic.status()["available"] is False
        semantic.reset_for_tests()


def test_rrf_prefers_items_in_both_lists():
    fused = semantic.rrf([["a", "b", "c"], ["c", "d"]])
    assert fused[0] == "c"
    assert set(fused) == {"a", "b", "c", "d"}


def test_int8_roundtrip_keeps_cosine():
    np = pytest.importorskip("numpy")
    rng = np.random.default_rng(0)
    v = rng.normal(size=(50, 384)).astype(np.float32)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    q8, sc = semantic.quantize_int8(v)
    deq = q8.astype(np.float32) * sc[:, None]
    assert np.abs((deq * v).sum(axis=1) - 1).max() < 0.01


# ---------- need built vectors ----------

@needs_vectors
class TestMeaningApi:
    def test_waiting_on_god_finds_waiting_verses(self, client):
        data = _get(client, "/api/search/meaning",
                    q="where does Scripture talk about waiting on God", mode="meaning").json()
        assert data["mode"] == "meaning" and data["fallback"] is False
        top = _refs(data)[:10]
        # None of these contain the word "God" next to "waiting"; found by meaning.
        assert {"Psalms 27:14", "Psalms 130:5", "Lamentations 3:25"} <= set(top)

    def test_auto_mode_picks_by_query_length(self, client):
        assert _get(client, "/api/search/meaning", q="fasting").json()["mode"] == "hybrid"
        long_q = "verses about forgiving someone who keeps hurting you"  # 3 content words
        assert _get(client, "/api/search/meaning", q=long_q).json()["mode"] == "meaning"

    def test_hybrid_shape_and_scores(self, client):
        data = _get(client, "/api/search/meaning", q="God's promises when afraid",
                    mode="hybrid").json()
        assert data["mode"] == "hybrid"
        assert any(r["match"] == "both" for r in data["results"])
        assert 1 <= len(data["results"]) <= 30
        for r in data["results"]:
            assert r["match"] in ("meaning", "keyword", "both")
            assert -1.0 <= r["score"] <= 1.0
            assert r["snippet"]

    @pytest.mark.parametrize("scope,books", [("nt", NT_BOOKS), ("ot", OT_BOOKS),
                                             ("book:Psalms", ["Psalms"])])
    def test_scope_filters(self, client, scope, books):
        data = _get(client, "/api/search/meaning", q="trusting God when afraid", scope=scope).json()
        assert data["results"]
        assert all(r["book"] in books for r in data["results"])

    def test_translation_text(self, client):
        data = _get(client, "/api/search/meaning", q="the Lord is my shepherd",
                    translation="KJV", mode="meaning", limit=5).json()
        texts = [re.sub(r"</?mark>", "", r["snippet"]) for r in data["results"]]
        assert "The LORD is my shepherd; I shall not want." in texts

    def test_similar_excludes_neighbours(self, client):
        data = _get(client, "/api/search/similar/Isaiah 40:31").json()
        refs = _refs(data)
        assert len(refs) == 20
        assert not any(r.startswith("Isaiah 40:") and 28 <= int(r.split(":")[1]) <= 34
                       for r in refs)
        assert {r["match"] for r in data["results"]} <= {"meaning", "keyword", "both"}
        assert all("<mark>" not in r["snippet"] for r in data["results"])

    def test_similar_needs_one_verse(self, client):
        assert _get(client, "/api/search/similar/John 3").status_code == 400
        assert _get(client, "/api/search/similar/Nope 1:1").status_code == 400


# ---------- quality pins (fail loudly on a model or quantization regression) ----------

QUESTIONS = json.loads((ROOT / "tests/fixtures/semantic_questions.json").read_text())["questions"]

# (query, a verse that must be in the top 10 of meaning-only search)
PINNED = [  # verified with gte-small @ 5927d1727bb1, int8 (docs/SEMANTIC_SEARCH_2026-11.md)
    ("where does Scripture talk about waiting on God", "Psalms 27:14"),
    ("verses about forgiving someone who keeps hurting you", "Luke 17:4"),
    ("God makes bad things work out for good", "Romans 8:28"),
    ("what is faith", "Hebrews 11:1"),
    ("the Lord is my shepherd who cares for me", "Psalms 23:1"),
    ("God knew me before I was born", "Jeremiah 1:5"),
]
# Floor for meaning-only hit@10 over all hand-written questions (measured value is in
# docs/SEMANTIC_SEARCH_2026-11.md; the floor leaves a few questions of slack).
MIN_HIT_AT_10 = 0.70


@needs_vectors
@pytest.mark.parametrize("q,ref", PINNED)
def test_pinned_queries(q, ref):
    index, enc = semantic.get_index()
    top = index.top(index.scores(enc.embed([q], is_query=True)[0]), 10)
    got = [f"{b} {c}:{v}" for b, c, v in (index.refs[i] for i in top)]
    assert ref in got, f"{q!r}: {ref} fell out of the top 10: {got}"


@needs_vectors
def test_question_set_hit_rate():
    index, enc = semantic.get_index()
    vecs = enc.embed([q["q"] for q in QUESTIONS], is_query=True)
    hits = 0
    for q, v in zip(QUESTIONS, vecs):
        top = {"%s %d:%d" % index.refs[i] for i in index.top(index.scores(v), 10)}
        hits += bool(top & set(q["refs"]))
    rate = hits / len(QUESTIONS)
    assert rate >= MIN_HIT_AT_10, f"hit@10 dropped to {rate:.2f}"


# ---------- build determinism ----------

def test_build_is_deterministic(tmp_path):
    pytest.importorskip("onnxruntime")
    pytest.importorskip("tokenizers")
    spec = semantic.CANDIDATES[semantic.SHIPPED_MODEL]
    if not all((semantic.model_dir(spec) / Path(f).name).exists() for f in spec.files):
        pytest.skip("model not downloaded (python scripts/build_db.py --step embeddings)")
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_embeddings import build

    src = sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True)
    rows = src.execute("SELECT translation_id, book, book_order, chapter, verse, text FROM verses "
                       "WHERE translation_id = 'BSB' AND book = 'Ruth'").fetchall()
    src.close()
    digests, blobs = [], []
    for n in range(2):
        db = tmp_path / f"t{n}.db"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE verses (translation_id, book, book_order, chapter, verse, text)")
        conn.executemany("INSERT INTO verses VALUES (?, ?, ?, ?, ?, ?)", rows)
        conn.commit()
        conn.close()
        meta = build(db, spec.key)
        digests.append(meta["vectors_sha256"])
        conn = sqlite3.connect(db)
        blobs.append(conn.execute("SELECT group_concat(hex(vec_i8)) FROM semantic_vectors").fetchone())
        n_rows = conn.execute("SELECT COUNT(*) FROM semantic_vectors").fetchone()[0]
        conn.close()
        assert n_rows == len(rows) == 85
    assert digests[0] == digests[1]
    assert blobs[0] == blobs[1]


# ---------- caching (a fallback must never be cached; search ETag follows the DB release) ----------

class TestCaching:
    def test_fallback_is_not_stored(self, client, monkeypatch):
        monkeypatch.setattr(semantic, "get_index", lambda *a, **k: None)
        r = _get(client, "/api/search/meaning", q="waiting on the LORD")
        assert r.json()["fallback"] is True
        assert r.headers["cache-control"] == "no-store"
        assert "etag" not in r.headers
        r = _get(client, "/api/search/similar/Isaiah 40:31")
        assert r.headers["cache-control"] == "no-store"

    def test_keyword_search_gets_release_etag_and_304(self, client):
        r = _get(client, "/api/search", q="shepherd")
        assert r.headers["cache-control"] == "public, max-age=3600"
        etag = r.headers["etag"]
        r2 = client.get("/api/search", params={"q": "shepherd"},
                        headers={"If-None-Match": etag, "X-Forwarded-For": "10.77.0.1"})
        assert r2.status_code == 304 and r2.headers["etag"] == etag
        other = _get(client, "/api/search", q="shepherds")
        assert other.headers["etag"] != etag

    def test_etag_changes_with_db_release(self, monkeypatch):
        from backend import release
        a = release.search_etag("/api/search/meaning?q=x")
        monkeypatch.setattr(release, "db_release", lambda: "otherrelease")
        assert release.search_etag("/api/search/meaning?q=x") != a
        monkeypatch.setenv("FLY_IMAGE_REF", "registry.fly.io/bible-mvp:deployment-2")
        b = release.search_etag("/api/search/meaning?q=x")
        monkeypatch.setenv("FLY_IMAGE_REF", "registry.fly.io/bible-mvp:deployment-3")
        assert release.search_etag("/api/search/meaning?q=x") != b

    def test_other_immutable_paths_unchanged(self, client):
        r = client.get("/api/passage/John 3:16?translation=BSB")
        assert r.headers["cache-control"] == "public, max-age=86400"
        assert "etag" not in r.headers


@needs_vectors
def test_meaning_results_cacheable_with_etag(client):
    r = _get(client, "/api/search/meaning", q="rest for the weary", mode="meaning")
    assert r.json()["fallback"] is False
    assert r.headers["cache-control"] == "public, max-age=3600"
    assert r.headers["etag"].startswith('W/"')
