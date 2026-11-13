import html
import json
import logging
import re
import sqlite3
import unicodedata
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response

from ..database import get_db_connection, get_writable_db_connection, DATABASE_PATH
from ..core import (OT_BOOKS, NT_BOOKS, CANONICAL_BOOKS, limiter,
                    parse_reference, get_cross_references, get_speaker_verses)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/passage/{reference}")
def get_passage(
    reference: str,
    translation: str = Query(default="WEB", description="Bible translation")
):
    """
    Get verse(s) with interlinear data and cross-references.

    Reference formats:
    - John 3:16 (single verse) - returns full chapter, highlights verse 16
    - John 3:16-18 (verse range) - returns full chapter, highlights verses 16-18
    - John 3 (full chapter) - returns full chapter, no highlighting
    - Rom 3:25 (abbreviations supported)
    """
    conn = get_db_connection()
    try:
        # Parse reference and fetch verses
        parsed = parse_reference(reference)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")

        book, chapter, verse_start, verse_end, has_verse = parsed

        # Always fetch the full chapter
        cursor = conn.execute("""
            SELECT v.id, v.book, v.chapter, v.verse, v.text
            FROM verses v
            WHERE v.book = ? AND v.chapter = ?
                  AND v.translation_id = ?
            ORDER BY v.verse
        """, (book, chapter, translation))

        verses = cursor.fetchall()
        if not verses:
            raise HTTPException(status_code=404, detail=f"Passage not found: {reference}")

        # Build highlighted verses list (only if specific verse was requested)
        highlighted_verses = []
        if has_verse:
            highlighted_verses = list(range(verse_start, verse_end + 1))

        # Get cross-references for the requested verses
        cross_refs = get_cross_references(conn, book, chapter, verse_start, verse_end)

        # Get verses with divine speech for red-letter display
        speaker_verses = get_speaker_verses(conn, book, chapter)

        return {
            # Always canonical ("rom 8:28" -> "Romans 8:28"); the client uses this as state (P1-3)
            "reference": (f"{book} {chapter}" if not has_verse
                          else f"{book} {chapter}:{verse_start}" if verse_end == verse_start
                          else f"{book} {chapter}:{verse_start}-{verse_end}"),
            "translation": translation,
            "verses": [dict(v) for v in verses],
            "cross_references": cross_refs,
            "highlighted_verses": highlighted_verses,
            "speaker_verses": speaker_verses
        }
    finally:
        conn.close()


@router.get("/api/passage/{reference}/parallel")
def get_parallel_passage(
    reference: str,
    translations: str = Query(default="BSB,KJV,WEB", description="Comma-separated translation IDs")
):
    """
    Get verse(s) for multiple translations in parallel.
    Returns all requested translations for the same passage.
    """
    conn = get_db_connection()
    try:
        parsed = parse_reference(reference)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")

        book, chapter, verse_start, verse_end, has_verse = parsed

        translation_list = [t.strip() for t in translations.split(",") if t.strip()]
        if not translation_list:
            raise HTTPException(status_code=400, detail="No translations specified")

        result_translations = {}
        for tid in translation_list:
            cursor = conn.execute("""
                SELECT v.verse, v.text
                FROM verses v
                WHERE v.book = ? AND v.chapter = ? AND v.translation_id = ?
                ORDER BY v.verse
            """, (book, chapter, tid))
            result_translations[tid] = [dict(row) for row in cursor.fetchall()]

        return {
            "reference": f"{book} {chapter}",
            "book": book,
            "chapter": chapter,
            "translations": result_translations
        }
    finally:
        conn.close()


# /api/passage/{reference}/commentary lives in routers/study.py (effective ranges)


@router.get("/api/passage/{reference}/crossrefs")
def get_crossrefs(reference: str):
    """Get cross-references for a passage."""
    conn = get_db_connection()
    try:
        parsed = parse_reference(reference)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")

        book, chapter, verse_start, verse_end, _ = parsed
        cross_refs = get_cross_references(conn, book, chapter, verse_start, verse_end)
        return {"reference": reference, "cross_references": cross_refs}
    finally:
        conn.close()


@router.get("/api/verse/{reference}")
def get_single_verse(
    reference: str,
    translation: str = Query(default="WEB", description="Bible translation")
):
    """Get a single verse text for previews."""
    conn = get_db_connection()
    try:
        parsed = parse_reference(reference)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")

        book, chapter, verse_start, _, _ = parsed

        cursor = conn.execute("""
            SELECT text FROM verses
            WHERE book = ? AND chapter = ? AND verse = ? AND translation_id = ?
        """, (book, chapter, verse_start, translation))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Verse not found: {reference}")

        return {"reference": reference, "text": row["text"]}
    finally:
        conn.close()


def _fts_query(q: str) -> str:
    """Build an FTS5 query from user text using only quoted terms.

    "Quoted phrases" stay phrases; every other word becomes its own quoted term,
    so FTS5 syntax (OR, NEAR, column filters, parens) can't be injected and
    queries stay cheap (security review M3). Last bare word gets a prefix match.
    """
    parts = []
    for phrase, word in re.findall(r'"([^"]*)"|(\w+)', q)[:8]:
        if phrase:
            words = re.findall(r"\w+", phrase)
            if words:
                parts.append('"' + " ".join(words) + '"')
        elif word:
            parts.append(f'"{word}"')
    last = re.findall(r'"[^"]*"|\w+', q)
    if parts and last and not last[-1].startswith('"') and len(last[-1]) >= 3:
        parts[-1] += "*"
    return " ".join(parts)


_ORIGINAL_SCRIPT = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff\u0590-\u05ff]")
_lexicon_keys: dict = {}   # (kind, folded) -> [strong numbers], built once per process
_ON, _OFF = "\x01", "\x02"   # highlight() markers, swapped for <mark> after escaping
VERSE_LIMIT = 50


def _fold(s: str) -> str:
    """Letters only, without accents, breathings or Hebrew points: ἀγάπη -> αγαπη, agápē -> agape."""
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^\w]", "", s.lower().replace("ς", "σ"))


def _lexicon_lookup(conn, q: str) -> list:
    """Strong's numbers whose original word (Greek/Hebrew typed) or transliteration (one
    Latin word of 4+ letters) is exactly the query, ignoring accents."""
    if not _lexicon_keys:
        for r in conn.execute("SELECT strong_number, original, transliteration FROM lexicon"):
            _lexicon_keys.setdefault(("orig", _fold(r["original"])), []).append(r["strong_number"])
            if r["transliteration"]:
                _lexicon_keys.setdefault(("tr", _fold(r["transliteration"])), []).append(
                    r["strong_number"])
    q = q.strip()
    if _ORIGINAL_SCRIPT.search(q):
        found = _lexicon_keys.get(("orig", _fold(q)), [])
    elif re.fullmatch(r"[A-Za-z\u00c0-\u024f\u1e00-\u1eff']{4,}", q):
        found = _lexicon_keys.get(("tr", _fold(q)), [])
    else:
        return []
    if len(found) < 2:
        return list(found)
    # Unpointed Hebrew names several entries (חסד: H2616-H2618): the commonest first
    uses = {s: conn.execute("SELECT COUNT(*) FROM word_alignments WHERE strong_number IN (?, ?)",
                            (s, s[0] + s[1:].zfill(4))).fetchone()[0] for s in found}
    return sorted(found, key=lambda s: -uses[s])


def _word_info(conn, strongs_num: str):
    row = conn.execute("SELECT original, transliteration, definition FROM lexicon "
                       "WHERE strong_number = ?", (strongs_num,)).fetchone()
    if not row:
        return None
    return {"strong_number": strongs_num, "original": row["original"],
            "transliteration": row["transliteration"], "definition": row["definition"]}


def _marked(text: str) -> str:
    return html.escape(text, quote=False).replace(_ON, "<mark>").replace(_OFF, "</mark>")


def _verse_hits(conn, verses_query: str, books, translation: str) -> list:
    """One result per verse, whichever translations matched (P1-7).

    The snippet is the whole verse in the reader's translation, marked where it matched.
    When only other translations hold the words ("thou" in the KJV), the reader's text is
    still shown, and `also` carries the first matching translation's marked text so the
    reader can see why the verse is here. Order: the verse's best-ranked row.
    """
    sql = (f"SELECT v.book, v.chapter, v.verse, v.translation_id AS tr, "
           f"highlight(verses_fts, 0, '{_ON}', '{_OFF}') AS hl "
           f"FROM verses_fts JOIN verses v ON v.id = verses_fts.rowid WHERE verses_fts MATCH ?")
    params: list = [verses_query]
    if books:
        sql += f" AND verses_fts.book IN ({','.join('?' * len(books))})"
        params += list(books)
    sql += " ORDER BY rank LIMIT ?"
    params.append(VERSE_LIMIT * 4)   # every translation's row; deduplicated below
    hits: dict = {}
    for r in conn.execute(sql, params):
        key = (r["book"], int(r["chapter"]), int(r["verse"]))
        h = hits.setdefault(key, {"matched": {}})
        h["matched"].setdefault(r["tr"], r["hl"])
    keys = list(hits)[:VERSE_LIMIT]
    need = [k for k in keys if translation not in hits[k]["matched"]]
    own = {}
    if need:
        clause = " OR ".join(["(book = ? AND chapter = ? AND verse = ?)"] * len(need))
        for b, c, v, t in conn.execute(
                f"SELECT book, chapter, verse, text FROM verses WHERE translation_id = ? "
                f"AND ({clause})", [translation, *[x for k in need for x in k]]):
            own[(b, c, v)] = t
    out = []
    for k in keys:
        matched = hits[k]["matched"]
        item = {"type": "verse", "book": k[0], "chapter": k[1], "verse": k[2],
                "translation": translation, "matched_in": sorted(matched)}
        if translation in matched:
            item["snippet"] = _marked(matched[translation])
        else:
            other = next(iter(matched))
            item["snippet"] = html.escape(own.get(k, ""), quote=False) or _marked(matched[other])
            if k in own:
                item["also"] = {"translation": other, "snippet": _marked(matched[other])}
            else:   # the reader's translation lacks this verse (versification)
                item["translation"] = other
        out.append(item)
    return out


@router.get("/api/search")
@limiter.limit("30/minute")
def search(
    request: Request,
    q: str = Query(..., min_length=2, max_length=100, description="Search query"),
    scope: str = Query(default="all", description="Search scope: bible, ot, nt, book:BookName, commentary, all"),
    translation: str = Query(default="BSB", max_length=10,
                             description="The reader's translation: verse text is shown in it"),
):
    """Full-text search across Bible text and commentaries.

    Verses: one result per verse, the reader's translation shown (see _verse_hits).
    A Strong's number (G26), or a Greek/Hebrew word (ἀγάπη), lists the verses with that
    word and returns `word_info`; a transliteration (agape) adds `word_suggestions`.
    """
    conn = get_db_connection()
    try:
        results = []
        query = q.strip()

        # A Strong's number, or an original-language word that names exactly one entry
        strongs_match = re.match(r'^([GH])(\d+)$', query, re.IGNORECASE)
        lex = [] if strongs_match else _lexicon_lookup(conn, query)
        original_typed = bool(_ORIGINAL_SCRIPT.search(query))
        if strongs_match or (original_typed and lex):
            if strongs_match:
                prefix, number = strongs_match.group(1).upper(), strongs_match.group(2)
            else:
                prefix, number = lex[0][0], lex[0][1:].lstrip("0") or "0"
            strongs_num = f"{prefix}{number}"
            word_info = _word_info(conn, strongs_num)

            # word_alignments stores zero-padded Strong's numbers (H430 -> H0430)
            padded_strong = f"{prefix}{number.zfill(4)}"

            # Verses with this Strong's number, with the original word
            cursor = conn.execute("""
                SELECT 'verse' as type, v.book, v.chapter, v.verse,
                       v.text as snippet, wa.hebrew_text as original_word,
                       wa.english_gloss as gloss
                FROM word_alignments wa
                JOIN verses v ON v.book = wa.book
                    AND v.chapter = wa.chapter
                    AND v.verse = wa.verse
                    AND v.translation_id = ?
                WHERE wa.strong_number IN (?, ?)
                GROUP BY v.book, v.chapter, v.verse
                ORDER BY v.book_order, v.chapter, v.verse
                LIMIT 50
            """, (translation, strongs_num, padded_strong))

            for row in cursor.fetchall():
                result = dict(row)
                result["translation"] = translation
                snippet = html.escape(result["snippet"], quote=False)
                # Highlight the translated word in the snippet if we have a gloss
                if result.get("gloss"):
                    pattern = re.compile(r'\b(' + re.escape(html.escape(result["gloss"], quote=False)) + r')\b', re.IGNORECASE)
                    snippet = pattern.sub(r'<mark>\1</mark>', snippet, count=1)
                result["snippet"] = snippet
                results.append(result)

            out = {"query": q, "scope": scope, "results": results, "word_info": word_info}
            if len(lex) > 1:
                out["word_suggestions"] = [w for w in (_word_info(conn, s) for s in lex[1:6]) if w]
            return out

        # Check if searching within a specific book
        books = None
        if scope.startswith("book:"):
            books = [scope[5:]]
            scope = "bible"
        elif scope == "ot":
            books = OT_BOOKS
            scope = "bible"
        elif scope == "nt":
            books = NT_BOOKS
            scope = "bible"

        fts_query = _fts_query(q)
        if not fts_query:
            return {"query": q, "scope": scope, "results": results}

        # Scope MATCH to the text column — the FTS tables also index book/chapter/verse
        # metadata, so a bare match on "john" returns every verse in the books of John.
        verses_query = f"text: ({fts_query})"
        commentary_query = f"searchable_text: ({fts_query})"

        try:
            if scope in ("all", "bible"):
                results.extend(_verse_hits(conn, verses_query, books, translation))

            if scope in ("all", "commentary"):
                cursor = conn.execute("""
                    SELECT 'commentary' as type, source, book, chapter,
                           snippet(commentary_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
                    FROM commentary_fts
                    WHERE commentary_fts MATCH ?
                    ORDER BY rank
                    LIMIT 50
                """, (commentary_query,))
                results.extend([dict(r) for r in cursor.fetchall()])
        except sqlite3.OperationalError as e:
            # Malformed FTS query - return empty results rather than 500
            logger.warning("FTS query error for %r: %s", q, e)

        out = {"query": q, "scope": scope, "results": results}
        if lex:   # a transliteration ("agape"): offer the word study beside the English hits
            out["word_suggestions"] = [w for w in (_word_info(conn, s) for s in lex[:5]) if w]
        return out
    finally:
        conn.close()


