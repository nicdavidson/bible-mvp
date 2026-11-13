"""Computed word studies: everything for one Hebrew/Greek lemma, from data only.

GET /api/word/{strong}/study    the study page payload (docs/WORD_STUDY_2026-11.md)
GET /api/word/{strong}/verses   its occurrences, filterable by book, form, edition,
                                or a second lemma (to show collocation evidence)

Every section names its dataset in `source`, a key into the `sources` map (name,
license, credit line). Nothing in the payload is written by a model: lexicon
text is quoted from the lexicons, counts and associations are computed from
STEPBible tokens, renderings from the word alignments, topics from Nave's,
cross-references from OpenBible.info.
"""
import json
import re
import threading
from collections import Counter, OrderedDict, defaultdict
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from .. import alignment_store
from ..database import DATABASE_PATH, get_db_connection
from ..word_study import (FUNCTION_LEMMAS, NT_EDITIONS, PRIMARY_TEXT_LABEL, PRIMARY_TEXT_SQL,
                          edition_sql,
                          editions_of, form_of, pad, pos_label)

router = APIRouter()

RENDERINGS_PER_TRANSLATION = 12
RENDERING_MIN_CONFIDENCE = 0.5  # = lemma_renderings / words.py
VERSES_PAGE = 100

COLLOCATE_METHOD = {
    "unit": "verse",
    "measure": "logDice ranking; kept when the two lemmas share >= 3 verses, more than "
               "chance predicts, with log-likelihood G2 >= 15.13 (p < 0.0001)",
    "excluded": "function words (articles, conjunctions, prepositions, particles, pronouns, "
                "adverbs) and " + ", ".join(FUNCTION_LEMMAS.values()),
}
TOPIC_METHOD = ("Nave's topics sharing >= 3 verses with this lemma, more than chance "
                "predicts (G2 >= 15.13), ranked by G2")
XREF_METHOD = ("OpenBible.info cross-references whose two verses both contain this lemma, "
               "by votes")
SAMPLE_METHOD = ("Up to 12 verses: one for each BSB rendering used in at least 5% of "
                 "occurrences (at most 6), then one for each part of the canon "
                 "(Law, History, Wisdom, Prophets, Gospels, Acts, Paul, General Letters, "
                 "Revelation) not yet represented, largest first. Within a choice: the "
                 "least-represented part of the canon, then the verse with most "
                 "cross-reference votes. All occurrences when there are 12 or fewer.")

_cache: "OrderedDict[tuple, dict]" = OrderedDict()
_cache_lock = threading.Lock()
_CACHE_MAX = 256


def _parse_strong(strong: str) -> tuple[str, str]:
    m = re.fullmatch(r"([HGhg])0*(\d{1,5})", strong.strip())
    if not m:
        raise HTTPException(status_code=400, detail="Expected a Strong's number like H430 or G26")
    plain = f"{m.group(1).upper()}{int(m.group(2))}"
    return plain, pad(plain)


def _db_key():
    try:
        st = DATABASE_PATH.stat()
        return st.st_mtime_ns, st.st_size
    except OSError:
        return None


def _has(conn, table):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (table,)).fetchone()


def _brief(conn, strongs) -> dict:
    """Display fields for a set of lemmas: original, transliteration, gloss (+ its source)."""
    strongs = sorted(set(strongs))
    if not strongs:
        return {}
    q = ",".join("?" * len(strongs))
    out = {r["strong_number"]: {"strong_number": r["strong_number"], "original": r["original"],
                                "transliteration": r["transliteration"],
                                "gloss": (r["definition"] or "").split(";")[0].strip(),
                                "gloss_source": "strongs"}
           for r in conn.execute(f"SELECT strong_number, original, transliteration, definition "
                                 f"FROM lexicon WHERE strong_number IN ({q})", strongs)}
    if _has(conn, "lexicon_entries"):
        for r in conn.execute(f"""SELECT strong_number, source, gloss, meta FROM lexicon_entries
                                  WHERE strong_number IN ({q}) AND seq = 1
                                    AND source IN ('dodson', 'bdb') AND gloss IS NOT NULL""",
                              strongs):
            d = out.setdefault(r["strong_number"], {"strong_number": r["strong_number"]})
            d["gloss"], d["gloss_source"] = r["gloss"], r["source"]
            if not d.get("transliteration") and r["meta"]:
                d["transliteration"] = json.loads(r["meta"]).get("xlit")
    return out


HOMOGRAPH_ORDER = ("Several BDB entries share this Strong's number. Ordered by how often "
                   "BSB, KJV and WEB render the lemma with a word from the entry's glosses, "
                   "then by the count BDB prints, then the longer article first.")


def _order_homographs(conn, plain, entries):
    """BDB homographs (e.g. H3581 'chameleon' vs 'strength, power'): the entry whose
    glosses match the lemma's actual renderings first. Each entry gets `rendering_matches`."""
    renderings = conn.execute("SELECT rendering, SUM(count) FROM lemma_renderings "
                              "WHERE strong_number = ? GROUP BY rendering", (plain,)).fetchall() \
        if _has(conn, "lemma_renderings") else []

    def stems(text):
        return {w[:5] for w in re.findall(r"[a-z]{3,}", (text or "").lower())}

    for e in entries:
        g = stems(e["gloss"])
        e["rendering_matches"] = sum(n for r, n in renderings if g & stems(r))
    return sorted(entries, key=lambda e: (-e["rendering_matches"],
                                          -(e["meta"].get("count") or 0),
                                          -len(e["definition"] or ""),
                                          e["meta"].get("aug") or ""))


def _lexicons(conn, plain, hebrew, word):
    sections = []
    if _has(conn, "lexicon_entries"):
        rows = defaultdict(list)
        for r in conn.execute("SELECT * FROM lexicon_entries WHERE strong_number = ? "
                              "ORDER BY source, seq", (plain,)):
            rows[r["source"]].append({
                "headword": r["headword"], "gloss": r["gloss"], "definition": r["definition"],
                "notes": r["notes"], "source_key": r["source_key"],
                "meta": json.loads(r["meta"]) if r["meta"] else {}})
        if len(rows.get("bdb", [])) > 1:
            rows["bdb"] = _order_homographs(conn, plain, rows["bdb"])
        for src in (("bdb",) if hebrew else ("abbott-smith", "dodson")):
            if rows.get(src):
                section = {"source": src, "entries": rows[src]}
                if src == "bdb" and len(rows[src]) > 1:
                    section["order"] = HOMOGRAPH_ORDER
                sections.append(section)
    if word:
        sections.append({"source": "strongs", "entries": [{
            "headword": word["original"], "transliteration": word["transliteration"],
            "pronunciation": word["pronunciation"], "definition": word["definition"],
            "kjv_usage": word["extended_definition"], "derivation": word["derivation"]}]})
    return sections


def _occurrences(conn, plain, padded, hebrew):
    total = Counter()
    by_book, by_form, form_label, editions = Counter(), Counter(), {}, Counter()
    verses = set()
    order = {}
    for r in conn.execute("""
            SELECT w.book, w.chapter, w.verse, w.grammar, w.word_type, w.editions,
                   b.testament, b.book_order
            FROM word_alignments w JOIN books b ON b.name = w.book
            WHERE w.strong_number IN (?, ?)""", (plain, padded)):
        if r["testament"] == "NT":
            eds = editions_of(r["editions"])
            for e in NT_EDITIONS:
                editions[e] += e in eds
            if "SBL" not in eds:
                continue
        elif (r["word_type"] or "").startswith("X"):
            continue
        total[r["testament"]] += 1
        by_book[r["book"]] += 1
        order[r["book"]] = r["book_order"]
        verses.add((r["book"], r["chapter"], r["verse"]))
        key, label = form_of(r["grammar"], hebrew)
        by_form[key] += 1
        form_label[key] = label
    testament = "OT" if hebrew else "NT"
    out = {
        "source": "stepbible",
        "text": PRIMARY_TEXT_LABEL[testament],
        "total": sum(total.values()),
        "verses": len(verses),
        "by_testament": {"OT": total["OT"], "NT": total["NT"]},
        "by_book": [{"book": b, "count": n} for b, n in
                    sorted(by_book.items(), key=lambda kv: order[kv[0]])],
        "by_form": [{"form": k, "label": form_label[k], "count": n}
                    for k, n in sorted(by_form.items(), key=lambda kv: (-kv[1], kv[0]))],
    }
    if not hebrew:
        out["by_edition"] = {e: editions[e] for e in NT_EDITIONS}
    return out


def _renderings(conn, plain):
    if not _has(conn, "lemma_renderings"):
        return {"source": "alignments", "min_confidence": RENDERING_MIN_CONFIDENCE,
                "translations": {}}
    by_tr = defaultdict(list)
    for r in conn.execute("SELECT translation_id, rendering, count FROM lemma_renderings "
                          "WHERE strong_number = ? ORDER BY translation_id, count DESC, "
                          "rendering", (plain,)):
        by_tr[r["translation_id"]].append({"rendering": r["rendering"], "count": r["count"]})
    return {
        "source": "alignments",
        "min_confidence": RENDERING_MIN_CONFIDENCE,
        "verses_url": f"/api/word/{plain}/renderings?translation={{translation}}"
                      "&rendering={rendering}",
        "translations": {tr: {"total": sum(x["count"] for x in rs),
                              "distinct": len(rs),
                              "renderings": rs[:RENDERINGS_PER_TRANSLATION]}
                         for tr, rs in by_tr.items()},
    }


def _bsb_links(conn, refs):
    """{(book, chapter, verse): (text, {source position: [english positions]})} for BSB."""
    out = {}
    for b, c, v in refs:
        r = conn.execute(f"""
            SELECT v.text, p.method, p.links FROM verses v
            LEFT JOIN {alignment_store.TABLE} p ON p.translation_id = v.translation_id
                 AND p.book = v.book AND p.chapter = v.chapter AND p.verse = v.verse
            WHERE v.translation_id = 'BSB' AND v.book = ? AND v.chapter = ? AND v.verse = ?
        """, (b, c, v)).fetchone()
        if not r:
            continue
        links = defaultdict(list)
        for epos, opos, conf, _ in alignment_store.unpack(r["method"] or 0, r["links"] or ""):
            if conf >= RENDERING_MIN_CONFIDENCE:
                links[opos].append(epos)
        out[(b, c, v)] = (r["text"], links)
    return out


def _sample_rows(conn, plain, padded):
    rows = []
    if _has(conn, "lemma_samples"):
        rows = [dict(r) for r in conn.execute(
            "SELECT book, chapter, verse, word_position, rendering, reason FROM lemma_samples "
            "WHERE strong_number = ? ORDER BY rank", (plain,))]
    if rows:
        return rows, False
    # 12 or fewer occurrences: all of them (primary text)
    all_rows = [dict(r) for r in conn.execute(f"""
        SELECT w.book, w.chapter, w.verse, w.word_position, b.book_order
        FROM word_alignments w JOIN books b ON b.name = w.book
        WHERE w.strong_number IN (?, ?) AND {PRIMARY_TEXT_SQL}
        ORDER BY b.book_order, w.chapter, w.verse, w.word_position LIMIT 13""",
        (plain, padded))]
    if len(all_rows) > 12:  # samples table missing (build step not run): first 12
        all_rows = all_rows[:12]
    for r in all_rows:
        r.pop("book_order")
        r["rendering"], r["reason"] = None, "all occurrences"
    return all_rows, True


def _with_text(conn, rows):
    links = _bsb_links(conn, {(r["book"], r["chapter"], r["verse"]) for r in rows})
    words_of = {}
    for r in rows:
        key = (r["book"], r["chapter"], r["verse"])
        text, lk = links.get(key, (None, {}))
        r["bsb_text"] = text
        r["bsb_word_positions"] = sorted(lk.get(r["word_position"], []))
        if r.get("rendering") is None and r["bsb_word_positions"] and text:
            words = words_of.setdefault(key, alignment_store.tappable_words(text))
            ws = [words[p - 1] for p in r["bsb_word_positions"]]
            r["rendering"] = _group_rendering(list(zip(r["bsb_word_positions"], ws)))
    return rows


def _group_rendering(words):
    from .words import _group_rendering as g
    return g(words)


def build_study(plain: str, padded: str) -> dict:
    conn = get_db_connection()
    try:
        word = conn.execute("SELECT * FROM lexicon WHERE strong_number = ?", (plain,)).fetchone()
        prof = conn.execute("SELECT * FROM lemma_profile WHERE strong_number = ?",
                            (plain,)).fetchone() if _has(conn, "lemma_profile") else None
        occ = _occurrences(conn, plain, padded, plain[0] == "H")
        if not word and not occ["total"]:
            raise HTTPException(status_code=404, detail=f"Word not found: {plain}")
        hebrew = plain[0] == "H"
        function_word = bool(prof["function_word"]) if prof else None
        lexicons = _lexicons(conn, plain, hebrew, word)
        translit = word["transliteration"] if word else None
        translit_source = "strongs" if translit else None
        if not translit:  # Strong's Hebrew has none: the OSHB lexical index's lemma form
            translit = next((e["meta"].get("xlit") for s in lexicons for e in s["entries"]
                             if s["source"] == "bdb" and e.get("meta", {}).get("xlit")), None)
            translit_source = "bdb" if translit else None
        out = {
            "strong_number": plain,
            "language": "hebrew" if hebrew else "greek",
            "lemma": {
                "original": word["original"] if word else None,
                "transliteration": translit,
                "transliteration_source": translit_source,
                "pronunciation": word["pronunciation"] if word else None,
                "pos": {"code": prof["pos"], "label": pos_label(prof["pos"], hebrew),
                        "source": "stepbible"} if prof else None,
                "function_word": function_word,
            },
            "lexicons": lexicons,
            "occurrences": occ,
            "renderings": _renderings(conn, plain),
        }

        collocates = []
        if _has(conn, "lemma_collocates"):
            rows = [dict(r) for r in conn.execute(
                "SELECT other, together, expected, g2, log_dice FROM lemma_collocates "
                "WHERE strong_number = ? ORDER BY rank", (plain,))]
            brief = _brief(conn, [r["other"] for r in rows])
            for r in rows:
                collocates.append({**brief.get(r["other"], {"strong_number": r["other"]}),
                                   "together": r["together"], "expected": r["expected"],
                                   "g2": r["g2"], "log_dice": r["log_dice"],
                                   "verses_url": f"/api/word/{plain}/verses?with={r['other']}"})
        out["collocates"] = {
            "source": "stepbible", "text": occ["text"], "method": COLLOCATE_METHOD,
            "items": collocates,
            "note": ("Not computed for function words." if function_word else None),
        }

        related = []
        if _has(conn, "lexicon_relations"):
            rels = [dict(r) for r in conn.execute(
                "SELECT related, relation, source, detail FROM lexicon_relations "
                "WHERE strong_number = ? ORDER BY relation, source, related", (plain,))]
            brief = _brief(conn, [r["related"] for r in rels])
            grouped = OrderedDict()
            for r in rels:
                d = grouped.setdefault(r["related"], {
                    **brief.get(r["related"], {"strong_number": r["related"]}), "links": []})
                d["links"].append({"relation": r["relation"], "source": r["source"],
                                   "detail": r["detail"] or None})
            related = list(grouped.values())
        out["related"] = {"items": related,
                          "note": "Only relations a lexicon states; none are inferred."}

        topics = []
        if _has(conn, "lemma_topics"):
            topics = [dict(r) for r in conn.execute("""
                SELECT t.topic_id, n.topic, n.section, t.hits, t.topic_verses, t.g2
                FROM lemma_topics t JOIN naves_topics n ON n.id = t.topic_id
                WHERE t.strong_number = ? ORDER BY t.rank""", (plain,))]
            for t in topics:
                t["url"] = f"/api/topics/{t['topic_id']}"
        out["topics"] = {"source": "naves", "method": TOPIC_METHOD, "items": topics}

        xrefs = []
        if _has(conn, "lemma_xrefs"):
            xrefs = [{"from": {"book": r["from_book"], "chapter": r["from_chapter"],
                               "verse": r["from_verse"]},
                      "to": {"book": r["to_book"], "chapter": r["to_chapter"],
                             "verse": r["to_verse"]},
                      "votes": r["votes"]}
                     for r in conn.execute("SELECT * FROM lemma_xrefs WHERE strong_number = ? "
                                           "ORDER BY rank", (plain,))]
        out["cross_references"] = {"source": "openbible-xrefs", "method": XREF_METHOD,
                                   "items": xrefs}

        rows, is_all = _sample_rows(conn, plain, padded)
        out["samples"] = {"source": "alignments", "method": SAMPLE_METHOD,
                          "all_occurrences": is_all, "items": _with_text(conn, rows)}

        used = {"strongs", "stepbible", "alignments", "naves", "openbible-xrefs"}
        used |= {s["source"] for s in out["lexicons"]}
        used |= {link["source"] for r in related for link in r["links"]}
        out["sources"] = {}
        if _has(conn, "word_study_sources"):
            out["sources"] = {r["source"]: {k: r[k] for k in ("name", "license", "attribution",
                                                             "url", "note")}
                              for r in conn.execute("SELECT * FROM word_study_sources")
                              if r["source"] in used}
        return out
    finally:
        conn.close()


@router.get("/api/word/{strong_number}/study")
def get_word_study(strong_number: str):
    """Everything about one lemma, computed from data; each section names its source."""
    plain, padded = _parse_strong(strong_number)
    key = (_db_key(), plain)
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    out = build_study(plain, padded)
    with _cache_lock:
        _cache[key] = out
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)
    return out


@router.get("/api/word/{strong_number}/verses")
def get_word_verses(
    strong_number: str,
    book: Optional[str] = Query(default=None, description="Only this book"),
    form: Optional[str] = Query(default=None, description="Only this form key (from by_form)"),
    edition: Optional[str] = Query(default=None, description="NT only: SBL (default), TR or Byz"),
    with_: Optional[str] = Query(default=None, alias="with",
                                 description="Only verses that also contain this lemma"),
    offset: int = Query(default=0, ge=0),
):
    """Occurrences of a lemma (one row per occurrence), in canonical order, 100 per page."""
    plain, padded = _parse_strong(strong_number)
    hebrew = plain[0] == "H"
    if edition and edition not in NT_EDITIONS:
        raise HTTPException(status_code=400, detail=f"edition must be one of {NT_EDITIONS}")
    ed = edition or "SBL"
    conn = get_db_connection()
    try:
        sql = f"""
            SELECT w.book, w.chapter, w.verse, w.word_position, w.hebrew_text AS original_text,
                   w.grammar, w.english_gloss AS gloss
            FROM word_alignments w JOIN books b ON b.name = w.book
            WHERE w.strong_number IN (?, ?)
              AND ((b.testament = 'OT' AND COALESCE(w.word_type, '') NOT LIKE 'X%')
                   OR (b.testament = 'NT' AND {edition_sql("w.editions")}))"""
        params = [plain, padded, ed]
        if book:
            sql += " AND w.book = ?"
            params.append(book)
        if with_:
            other, other_padded = _parse_strong(with_)
            sql += f""" AND EXISTS (SELECT 1 FROM word_alignments o
                       WHERE o.book = w.book AND o.chapter = w.chapter AND o.verse = w.verse
                         AND o.strong_number IN (?, ?)
                         AND (b.testament = 'OT' OR {edition_sql("o.editions")}))"""
            params += [other, other_padded, ed]
        sql += " ORDER BY b.book_order, w.chapter, w.verse, w.word_position"
        rows = []
        for r in conn.execute(sql, params):
            key, label = form_of(r["grammar"], hebrew)
            if form and key != form:
                continue
            rows.append({**dict(r), "form": key, "form_label": label})
        return {"strong_number": plain, "text": PRIMARY_TEXT_LABEL["OT" if hebrew else "NT"]
                if not edition else f"Greek NT ({edition} tokens in TAGNT)",
                "filters": {"book": book, "form": form, "edition": edition, "with": with_},
                "total": len(rows), "verses": len({(r["book"], r["chapter"], r["verse"])
                                                   for r in rows}),
                "offset": offset, "occurrences": rows[offset:offset + VERSES_PAGE]}
    finally:
        conn.close()
