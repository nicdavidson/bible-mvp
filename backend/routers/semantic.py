"""Meaning search over Bible verses ("search by meaning") and "more like this verse".

Finds and ranks existing verses; it never generates text. If the query is a reference
("John 3:16") or a Strong's number, the endpoint declines with mode="reference"/"strongs"
so the client keeps today's behaviour. If the model or vectors are unavailable, it answers
with keyword results (mode="keyword", fallback=true) in the same shape.

Spec for the UI: docs/SEMANTIC_SEARCH_2026-11.md#api
"""
from __future__ import annotations

import html
import logging
import re
import sqlite3
import threading
import time

from fastapi import APIRouter, HTTPException, Query, Request, Response

from .. import semantic
from ..core import CANONICAL_BOOKS, NT_BOOKS, OT_BOOKS, limiter, parse_reference
from ..database import get_db_connection
from ..search_text import _stem, content_terms, fts_or_query

logger = logging.getLogger(__name__)
router = APIRouter()

KEYWORD_POOL = 100      # keyword candidates fused with meaning candidates
MEANING_POOL = 100
HYBRID_WEIGHT = 0.5     # RRF weight of meaning vs keyword (tuned on Nave's dev split)
SIMILAR_WEIGHT = 1.0    # "more like this" RRF weight, tuned on the cross-reference dev split
AUTO_MAX_TERMS = 2      # mode=auto: <= 2 content words -> hybrid, longer -> meaning only
NO_STORE = "no-store"   # a fallback must not be cached in place of real results
NEIGHBOURS = 3          # "more like this" skips verses within +-3 in the same chapter
_STRONGS = re.compile(r"^[GH]\d+$", re.I)
_BOOK_ORDER = {b: i + 1 for i, b in enumerate(CANONICAL_BOOKS)}


def _warm():
    try:
        semantic.get_index()
    except Exception:  # never let warm-up break startup
        logger.exception("meaning search warm-up failed")


# Load vectors + model in the background at import so the first search is not the slow one.
threading.Thread(target=_warm, daemon=True, name="semantic-warmup").start()


def _scope_orders(scope: str):
    """Book orders allowed by scope, or None for all. Raises 400 on an unknown book."""
    if scope in ("all", "bible"):
        return None
    if scope == "ot":
        return {_BOOK_ORDER[b] for b in OT_BOOKS}
    if scope == "nt":
        return {_BOOK_ORDER[b] for b in NT_BOOKS}
    if scope.startswith("book:"):
        book = scope[5:]
        if book not in _BOOK_ORDER:
            raise HTTPException(status_code=400, detail=f"Unknown book: {book}")
        return {_BOOK_ORDER[book]}
    raise HTTPException(status_code=400, detail="scope must be all, bible, ot, nt or book:<Book>")


def _as_reference(q: str):
    parsed = parse_reference(q)
    if parsed and parsed[0] in _BOOK_ORDER:
        book, chapter, vs, ve, has_verse = parsed
        ref = (f"{book} {chapter}" if not has_verse else
               f"{book} {chapter}:{vs}" if vs == ve else f"{book} {chapter}:{vs}-{ve}")
        return ref
    return None


def _highlight(text: str, terms: list[str]) -> str:
    out = html.escape(text, quote=False)
    stems = sorted({_stem(t) for t in terms if len(_stem(t)) >= 3}, key=len, reverse=True)
    if not stems:
        return out
    pat = re.compile(r"\b(" + "|".join(re.escape(s) for s in stems) + r")\w*", re.I)
    return pat.sub(lambda m: f"<mark>{m.group(0)}</mark>", out)


def _keyword_ranked(conn, q: str, orders, limit: int):
    """Unique (book, chapter, verse) in BM25 order from the stop-worded OR query."""
    match = fts_or_query(q)
    if not match:
        return []
    sql = "SELECT book, chapter, verse FROM verses_fts WHERE verses_fts MATCH ?"
    params: list = [f"text: ({match})"]
    if orders is not None:
        books = [b for b, o in _BOOK_ORDER.items() if o in orders]
        sql += f" AND book IN ({','.join('?' * len(books))})"
        params += books
    sql += " ORDER BY rank LIMIT ?"
    params.append(limit * 3)  # verses_fts holds every translation; dedupe below
    out, seen = [], set()
    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:
        logger.warning("FTS query error for %r: %s", q, e)
        return []
    for b, c, v in rows:
        key = (b, int(c), int(v))
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out[:limit]


def _texts(conn, refs, translation: str) -> dict:
    """Verse text in the requested translation, falling back to BSB (versification gaps)."""
    if not refs:
        return {}
    out = {}
    for tid in dict.fromkeys([translation, "BSB"]):
        missing = [r for r in refs if r not in out]
        if not missing:
            break
        clause = " OR ".join(["(book = ? AND chapter = ? AND verse = ?)"] * len(missing))
        params = [x for r in missing for x in r]
        for b, c, v, t in conn.execute(
                f"SELECT book, chapter, verse, text FROM verses WHERE translation_id = ? "
                f"AND ({clause})", [tid, *params]).fetchall():
            out[(b, c, v)] = t
    return out


def _results(conn, ranked, translation, terms, meaning_rank, keyword_rank, scores):
    texts = _texts(conn, ranked, translation)
    out = []
    for ref in ranked:
        if ref not in texts:
            continue
        in_m, in_k = ref in meaning_rank, ref in keyword_rank
        out.append({
            "type": "verse", "book": ref[0], "chapter": ref[1], "verse": ref[2],
            "snippet": _highlight(texts[ref], terms if in_k else []),
            "score": round(float(scores.get(ref, 0.0)), 4),
            "match": "both" if in_m and in_k else "meaning" if in_m else "keyword",
            "meaning_rank": meaning_rank.get(ref), "keyword_rank": keyword_rank.get(ref),
        })
    return out


@router.get("/api/search/meaning")
@limiter.limit("30/minute")
def search_meaning(
    request: Request,
    response: Response,
    q: str = Query(..., min_length=2, max_length=200, description="Natural-language query"),
    scope: str = Query(default="all", description="all, bible, ot, nt, book:<Book>"),
    mode: str = Query(default="auto", pattern="^(auto|hybrid|meaning)$"),
    translation: str = Query(default="BSB", max_length=10),
    limit: int = Query(default=30, ge=1, le=100),
):
    """Verses ranked by meaning, or by meaning fused with keyword matches.

    auto (default): hybrid for short, keyword-like queries ("fasting", "love enemies"),
    meaning only for longer natural questions, where keyword fusion hurt in evaluation.
    """
    started = time.perf_counter()
    orders = _scope_orders(scope)
    base = {"query": q, "scope": scope, "translation": translation}
    query = q.strip()

    if _STRONGS.match(query):
        return {**base, "mode": "strongs", "results": [], "fallback": False,
                "note": "Strong's number: use /api/search"}
    ref = _as_reference(query)
    if ref:
        return {**base, "mode": "reference", "reference": ref, "results": [], "fallback": False,
                "note": "Bible reference: open it instead of searching"}

    terms = content_terms(query)
    conn = get_db_connection()
    try:
        keyword = _keyword_ranked(conn, query, orders, KEYWORD_POOL)
        keyword_rank = {r: i + 1 for i, r in enumerate(keyword)}
        loaded = semantic.get_index()
        if loaded is None:
            ranked = keyword[:limit]
            results = _results(conn, ranked, translation, terms, {}, keyword_rank,
                               {r: 1.0 / (60 + i + 1) for i, r in enumerate(keyword)})
            response.headers["Cache-Control"] = NO_STORE
            return {**base, "mode": "keyword", "fallback": True,
                    "fallback_reason": "meaning search unavailable", "results": results}

        index, encoder = loaded
        qvec = encoder.embed([query], is_query=True)[0]
        sims = index.scores(qvec)
        top = index.top(sims, MEANING_POOL, allowed_orders=orders)
        meaning = [index.refs[i] for i in top]
        meaning_rank = {r: i + 1 for i, r in enumerate(meaning)}
        if mode == "auto":
            mode = "hybrid" if len(terms) <= AUTO_MAX_TERMS else "meaning"
        # Score shown is always the cosine similarity, so the UI sees one kind of number.
        scores = {index.refs[i]: float(sims[i]) for i in top}
        if mode == "meaning" or not keyword:
            ranked = meaning[:limit]
        else:
            ranked = semantic.rrf([meaning, keyword], weights=[HYBRID_WEIGHT, 1.0])[:limit]
            for r in ranked:
                if r not in scores:
                    i = index.pos.get(r)
                    scores[r] = float(sims[i]) if i is not None else 0.0
        results = _results(conn, ranked, translation, terms, meaning_rank, keyword_rank, scores)
        return {**base, "mode": mode,
                "fallback": False, "model": index.meta.get("model_key"), "results": results,
                "took_ms": round((time.perf_counter() - started) * 1000, 1)}
    finally:
        conn.close()


@router.get("/api/search/similar/{reference}")
@limiter.limit("30/minute")
def similar_verses(
    request: Request,
    response: Response,
    reference: str,
    scope: str = Query(default="all", description="all, bible, ot, nt, book:<Book>"),
    translation: str = Query(default="BSB", max_length=10),
    limit: int = Query(default=20, ge=1, le=50),
):
    """'More like this': verses close to one verse by meaning and shared words.

    Fuses vector similarity with a keyword query built from the verse's own content words
    (RRF, equal weights): on held-out OpenBible/TSK cross-references the fusion beat
    either alone. Verses within +-3 in the same chapter are excluded.
    """
    parsed = parse_reference(reference)
    if not parsed or parsed[0] not in _BOOK_ORDER or not parsed[4]:
        raise HTTPException(status_code=400, detail="Give one verse, e.g. Isaiah 40:31")
    book, chapter, verse = parsed[0], parsed[1], parsed[2]
    orders = _scope_orders(scope)
    base = {"reference": f"{book} {chapter}:{verse}", "scope": scope, "translation": translation}
    loaded = semantic.get_index()
    if loaded is None:
        response.headers["Cache-Control"] = NO_STORE
        return {**base, "results": [], "fallback": True,
                "fallback_reason": "meaning search unavailable"}
    index, _ = loaded
    qvec = index.vector((book, chapter, verse))
    if qvec is None:
        raise HTTPException(status_code=404, detail=f"Verse not found: {reference}")
    near = {(book, chapter, v) for v in range(verse - NEIGHBOURS, verse + NEIGHBOURS + 1)}
    sims = index.scores(qvec)
    top = index.top(sims, MEANING_POOL, allowed_orders=orders, exclude=near)
    meaning = [index.refs[i] for i in top]
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT text FROM verses WHERE translation_id = 'BSB' AND book = ? "
                           "AND chapter = ? AND verse = ?", (book, chapter, verse)).fetchone()
        keyword = [r for r in _keyword_ranked(conn, row[0] if row else "", orders,
                                              KEYWORD_POOL) if r not in near]
        ranked = semantic.rrf([meaning, keyword], weights=[SIMILAR_WEIGHT, 1.0])[:limit]
        scores = {r: float(sims[index.pos[r]]) for r in ranked if r in index.pos}
        results = _results(conn, ranked, translation, [],
                           {r: i + 1 for i, r in enumerate(meaning)},
                           {r: i + 1 for i, r in enumerate(keyword)}, scores)
    finally:
        conn.close()
    return {**base, "fallback": False, "model": index.meta.get("model_key"), "results": results}


@router.get("/api/semantic/status")
def meaning_status():
    """Whether meaning search is loaded (for the UI to label results or hide the toggle)."""
    semantic.get_index()
    return semantic.status()
