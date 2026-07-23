import json
import logging
import re
import sqlite3
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response

from ..database import get_db_connection, get_writable_db_connection, DATABASE_PATH
from ..core import (OT_BOOKS, NT_BOOKS, CANONICAL_BOOKS, limiter,
                    parse_reference, get_cross_references, get_speaker_verses)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/topics/search")
def search_topics(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=50, le=200)
):
    """Search Nave's Topical Bible by keyword or topic name."""
    conn = get_db_connection()
    try:
        results = []

        # First: exact topic name match (case-insensitive)
        cursor = conn.execute(
            "SELECT id, topic, section, entry_text FROM naves_topics "
            "WHERE UPPER(topic) = UPPER(?) LIMIT 1",
            (q.strip(),)
        )
        exact = cursor.fetchone()
        if exact:
            refs = _get_topic_refs(conn, exact["id"])
            results.append({
                "id": exact["id"],
                "topic": exact["topic"],
                "section": exact["section"],
                "entry_text": exact["entry_text"],
                "refs": refs,
                "exact": True,
            })

        # FTS search for broader matches
        try:
            fts_q = q.strip().replace('"', '""')
            cursor = conn.execute("""
                SELECT t.id, t.topic, t.section,
                       snippet(naves_topics_fts, 1, '<mark>', '</mark>', '...', 40) as snippet
                FROM naves_topics_fts fts
                JOIN naves_topics t ON t.id = fts.rowid
                WHERE naves_topics_fts MATCH ?
                LIMIT ?
            """, (f'"{fts_q}"', limit))

            for row in cursor.fetchall():
                if exact and row["id"] == exact["id"]:
                    continue
                results.append({
                    "id": row["id"],
                    "topic": row["topic"],
                    "section": row["section"],
                    "snippet": row["snippet"],
                })
        except Exception:
            # FTS match syntax error — fall back to LIKE
            # Escape LIKE wildcards (%, _) in user input to prevent pattern injection
            escaped_q = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            cursor = conn.execute(
                "SELECT id, topic, section FROM naves_topics "
                "WHERE topic LIKE ? ESCAPE '\\' OR entry_text LIKE ? ESCAPE '\\' LIMIT ?",
                (f'%{escaped_q}%', f'%{escaped_q}%', limit)
            )
            for row in cursor.fetchall():
                if exact and row["id"] == exact["id"]:
                    continue
                results.append({
                    "id": row["id"],
                    "topic": row["topic"],
                    "section": row["section"],
                })

        return {"query": q, "results": results}
    finally:
        conn.close()


@router.get("/api/topics/for-verse")
def get_topics_for_verse(
    book: str = Query(...),
    chapter: int = Query(...),
    verse: int = Query(...)
):
    """Get all Nave's topics that reference a specific verse."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            SELECT DISTINCT t.id, t.topic, t.section
            FROM naves_topics t
            JOIN naves_topic_refs r ON t.id = r.topic_id
            WHERE r.book = ? AND r.chapter = ?
              AND r.verse_start <= ?
              AND (r.verse_end >= ? OR r.verse_end IS NULL OR r.verse_end = r.verse_start)
            ORDER BY t.topic
            LIMIT 30
        """, (book, chapter, verse, verse))

        topics = [dict(row) for row in cursor.fetchall()]
        return {"book": book, "chapter": chapter, "verse": verse, "topics": topics}
    finally:
        conn.close()


@router.get("/api/topics/browse")
def browse_topics(
    section: str = Query(default=None, description="Filter by section letter (A-Z)"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, le=200)
):
    """Browse Nave's topics alphabetically."""
    conn = get_db_connection()
    try:
        offset = (page - 1) * per_page

        if section:
            cursor = conn.execute(
                "SELECT id, topic, section FROM naves_topics "
                "WHERE section = ? ORDER BY topic LIMIT ? OFFSET ?",
                (section.upper(), per_page, offset)
            )
            count_cursor = conn.execute(
                "SELECT COUNT(*) FROM naves_topics WHERE section = ?",
                (section.upper(),)
            )
        else:
            cursor = conn.execute(
                "SELECT id, topic, section FROM naves_topics "
                "ORDER BY topic LIMIT ? OFFSET ?",
                (per_page, offset)
            )
            count_cursor = conn.execute("SELECT COUNT(*) FROM naves_topics")

        topics = [dict(row) for row in cursor.fetchall()]
        total = count_cursor.fetchone()[0]

        # Section counts for navigation
        sec_cursor = conn.execute(
            "SELECT section, COUNT(*) as count FROM naves_topics GROUP BY section ORDER BY section"
        )
        sections = {row[0]: row[1] for row in sec_cursor.fetchall()}

        return {
            "topics": topics,
            "total": total,
            "page": page,
            "per_page": per_page,
            "sections": sections,
        }
    finally:
        conn.close()


@router.get("/api/topics/{topic_id}")
def get_topic(topic_id: int):
    """Get a single Nave's topic with full entry text and verse references."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT id, topic, section, entry_text FROM naves_topics WHERE id = ?",
            (topic_id,)
        )
        topic = cursor.fetchone()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        refs = _get_topic_refs(conn, topic_id)

        # Get verse text previews for up to 20 refs — one batched query
        # covering every ref's verse range, then slice per ref in Python.
        preview_refs = refs[:20]
        verses_by_bc = {}
        if preview_refs:
            conds = " OR ".join(
                "(book = ? AND chapter = ? AND verse BETWEEN ? AND ?)"
                for _ in preview_refs)
            params = []
            for ref in preview_refs:
                ve = ref["verse_end"] if ref["verse_end"] is not None else ref["verse_start"]
                params.extend((ref["book"], ref["chapter"], ref["verse_start"], ve))
            cursor = conn.execute(
                f"SELECT book, chapter, verse, text FROM verses "
                f"WHERE translation_id = 'BSB' AND ({conds})", params)
            for r in cursor:
                verses_by_bc.setdefault((r[0], r[1]), []).append((r[2], r[3]))
            for v in verses_by_bc.values():
                v.sort()

        ref_previews = []
        for ref in preview_refs:
            ve = ref["verse_end"] if ref["verse_end"] is not None else ref["verse_start"]
            texts = [t for vnum, t in verses_by_bc.get((ref["book"], ref["chapter"]), [])
                     if ref["verse_start"] <= vnum <= ve][:3]
            preview = " ".join(texts)
            if len(preview) > 150:
                preview = preview[:147] + "..."
            ref_previews.append({**ref, "preview": preview})

        return {
            "id": topic["id"],
            "topic": topic["topic"],
            "section": topic["section"],
            "entry_text": topic["entry_text"],
            "refs": ref_previews,
            "total_refs": len(refs),
        }
    finally:
        conn.close()


def _get_topic_refs(conn, topic_id):
    """Get verse references for a topic."""
    cursor = conn.execute(
        "SELECT book, chapter, verse_start, verse_end FROM naves_topic_refs "
        "WHERE topic_id = ? ORDER BY book, chapter, verse_start",
        (topic_id,)
    )
    return [dict(row) for row in cursor.fetchall()]


