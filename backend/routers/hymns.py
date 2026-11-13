"""Scripture-to-hymn index (docs/HYMN_INDEX_2026-11.md).

GET /api/hymns/for-passage?ref=Psalm 23:1-4   hymns built on or quoting a passage, ranked
GET /api/hymns/{hymn_id}                      one hymn with all its passages
GET /api/hymns?q=grace | ?key=amazinggrace    find hymns by words or by join key
"""
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..core import parse_reference
from ..database import get_db_connection
from ..hymn_keys import keys_for, title_key

router = APIRouter()

KIND_ORDER = {"quotes": 0, "paraphrase": 0, "reference": 1}
RANKING = ("1) hymns linked to verses inside the passage before hymns linked only elsewhere "
           "in the same chapter; 2) a quotation or a paraphrase before a plain reference; "
           "3) the share of the hymn's linked verses that fall inside the passage; 4) the share "
           "of all the hymn's Scripture links that touch the passage (a hymn citing 3 "
           "passages is more about each than one citing 12); 5) title")


def _hymn(row) -> dict:
    d = dict(row)
    for k in ("alt_titles", "topics", "keys"):
        d[k] = json.loads(d[k]) if d.get(k) else []
    d["words_public_domain"] = bool(d["words_public_domain"])
    d.pop("title_key", None)
    return d


def _link(r) -> dict:
    v = "" if r["verse_start"] is None else f":{r['verse_start']}" + (
        f"-{r['verse_end']}" if r["verse_end"] != r["verse_start"] else "")
    return {"reference": f"{r['book']} {r['chapter']}{v}", "book": r["book"],
            "chapter": r["chapter"], "verse_start": r["verse_start"],
            "verse_end": r["verse_end"], "kind": r["kind"], "source": r["source"],
            "as_written": r["ref_text"], "evidence": r["evidence"]}


def _sources(conn) -> dict:
    return {r["source"]: {k: r[k] for k in ("name", "license", "attribution", "url", "note")}
            for r in conn.execute("SELECT * FROM hymn_sources")}


def _require_table(conn):
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='hymns'").fetchone():
        raise HTTPException(status_code=503, detail="Hymn index not built")


@router.get("/api/hymns/for-passage")
def hymns_for_passage(
    ref: Optional[str] = Query(default=None, max_length=60,
                               description="A passage: 'Psalm 23', 'John 3:16-21'"),
    book: Optional[str] = None,
    chapter: Optional[int] = Query(default=None, ge=1),
    verse_start: Optional[int] = Query(default=None, ge=1),
    verse_end: Optional[int] = Query(default=None, ge=1),
    include_chapter: bool = Query(default=True,
                                  description="Also hymns linked elsewhere in the chapter"),
    limit: int = Query(default=30, ge=1, le=100),
):
    """Hymns linked to a passage, grouped by text (several tunes = one result), ranked."""
    if ref:
        parsed = parse_reference(ref)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {ref}")
        book, chapter, vs, ve, has_verse = parsed
        if not has_verse:
            vs, ve = 1, 999
    elif book and chapter:
        vs, ve = verse_start or 1, verse_end or verse_start or 999
    else:
        raise HTTPException(status_code=400, detail="Give `ref`, or `book` and `chapter`")
    if ve < vs:
        vs, ve = ve, vs
    conn = get_db_connection()
    try:
        _require_table(conn)
        maxv = conn.execute("SELECT MAX(verse) FROM verses WHERE translation_id = 'KJV' "
                            "AND book = ? AND chapter = ?", (book, chapter)).fetchone()[0]
        if not maxv:
            raise HTTPException(status_code=404, detail=f"No such chapter: {book} {chapter}")
        p1, p2 = vs, min(ve, maxv)
        links = conn.execute("SELECT * FROM hymn_scripture WHERE book = ? AND chapter = ?",
                             (book, chapter)).fetchall()
        totals = dict(conn.execute("SELECT hymn_id, COUNT(*) FROM hymn_scripture GROUP BY 1"))
        per_hymn = {}
        for r in links:
            a, b = (r["verse_start"], r["verse_end"]) if r["verse_start"] else (1, maxv)
            overlap = max(0, min(b, p2) - max(a, p1) + 1)
            if not overlap and not include_chapter:
                continue
            h = per_hymn.setdefault(r["hymn_id"], {"links": [], "best": None})
            share = overlap / (b - a + 1)
            key = (0 if overlap else 1, KIND_ORDER.get(r["kind"], 2) if overlap else 2, -share)
            h["links"].append((key, _link(r)))
            h["best"] = key if h["best"] is None else min(h["best"], key)
            if overlap:
                h["touching"] = h.get("touching", 0) + 1
        if not per_hymn:
            return {"passage": {"book": book, "chapter": chapter, "verse_start": p1,
                                "verse_end": p2}, "ranking": RANKING, "total": 0,
                    "hymns": [], "sources": _sources(conn)}
        ids = list(per_hymn)
        rows = {r["id"]: r for r in conn.execute(
            f"SELECT * FROM hymns WHERE id IN ({','.join('?' * len(ids))})", ids)}
        groups = {}
        for hid, h in per_hymn.items():
            row = rows[hid]
            focus = h.get("touching", 0) / max(totals.get(hid, 1), 1)
            rank = (*h["best"], -focus, row["title"].lower())
            g = groups.get(row["text_key"])
            if g is None or rank < g["rank"]:
                hymn = _hymn(row)
                hymn["links"] = [lk for _, lk in sorted(h["links"], key=lambda x: x[0])]
                hymn["match"] = "passage" if h["best"][0] == 0 else "chapter"
                settings = g["hymn"]["settings"] if g else []
                hymn["settings"] = settings
                g = {"rank": rank, "hymn": hymn}
                groups[row["text_key"]] = g
            g["hymn"]["settings"].append({"id": hid, "tune": row["tune"],
                                          "meter": row["meter"]})
        ordered = [g["hymn"] for g in sorted(groups.values(), key=lambda g: g["rank"])]
        for h in ordered:
            h["settings"].sort(key=lambda s: s["id"] != h["id"])
        return {"passage": {"book": book, "chapter": chapter, "verse_start": p1,
                            "verse_end": p2},
                "ranking": RANKING, "total": len(ordered), "hymns": ordered[:limit],
                "sources": _sources(conn)}
    finally:
        conn.close()


@router.get("/api/hymns")
def find_hymns(
    q: Optional[str] = Query(default=None, max_length=100,
                             description="Words in the title or first line"),
    key: Optional[str] = Query(default=None, max_length=200,
                               description="A title or first line; matched by join key "
                                           "(backend/hymn_keys.py)"),
    limit: int = Query(default=50, ge=1, le=400),
):
    """Find hymns by words, by join key, or list all (title order)."""
    conn = get_db_connection()
    try:
        _require_table(conn)
        rows = conn.execute("SELECT * FROM hymns ORDER BY title").fetchall()
        if key:
            want = keys_for(key)
            rows = [r for r in rows if want & set(json.loads(r["keys"]))]
        if q:
            words = [title_key(w) for w in q.split() if title_key(w)]
            rows = [r for r in rows if all(
                w in title_key(f"{r['title']} {r['first_line'] or ''} {r['alt_titles'] or ''}")
                for w in words)]
        counts = dict(conn.execute("SELECT hymn_id, COUNT(*) FROM hymn_scripture GROUP BY 1"))
        out = []
        for r in rows[:limit]:
            h = _hymn(r)
            h["scripture_links"] = counts.get(r["id"], 0)
            out.append(h)
        return {"total": len(rows), "hymns": out}
    finally:
        conn.close()


@router.get("/api/hymns/{hymn_id}")
def get_hymn(hymn_id: str):
    """One hymn: metadata and every passage it is linked to, in canonical order."""
    conn = get_db_connection()
    try:
        _require_table(conn)
        row = conn.execute("SELECT * FROM hymns WHERE id = ?", (hymn_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Hymn not found: {hymn_id}")
        hymn = _hymn(row)
        hymn["passages"] = [_link(r) for r in conn.execute("""
            SELECT s.* FROM hymn_scripture s JOIN books b ON b.name = s.book
            WHERE s.hymn_id = ?
            ORDER BY b.book_order, s.chapter, COALESCE(s.verse_start, 0), s.kind""",
            (hymn_id,))]
        hymn["other_settings"] = [dict(r) for r in conn.execute(
            "SELECT id, tune, meter FROM hymns WHERE text_key = ? AND id != ? ORDER BY id",
            (row["text_key"], hymn_id))]
        hymn["sources"] = _sources(conn)
        return hymn
    finally:
        conn.close()
