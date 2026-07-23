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

@router.get("/api/devotional")
def get_devotional(
    date: Optional[str] = None,
    time_of_day: Optional[str] = None
):
    """
    Get today's devotional or specified date.

    Parameters:
    - date: MM-DD format (e.g., "01-15" for January 15). Defaults to today.
    - time_of_day: "morning" or "evening". If omitted, returns both.
    """
    from datetime import datetime

    if date is None:
        now = datetime.now()
        month = now.month
        day = now.day
    else:
        parts = date.split("-")
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Date must be in MM-DD format")
        try:
            month = int(parts[0])
            day = int(parts[1])
        except ValueError:
            raise HTTPException(status_code=400, detail="Date must be in MM-DD format with numeric values")
        if not (1 <= month <= 12 and 1 <= day <= 31):
            raise HTTPException(status_code=400, detail="Invalid month or day")

    conn = get_db_connection()
    try:
        if time_of_day:
            cursor = conn.execute("""
                SELECT source, month, day, time_of_day, title, verse_ref, content
                FROM devotionals
                WHERE month = ? AND day = ? AND time_of_day = ?
                ORDER BY source
            """, (month, day, time_of_day))
        else:
            cursor = conn.execute("""
                SELECT source, month, day, time_of_day, title, verse_ref, content
                FROM devotionals
                WHERE month = ? AND day = ?
                ORDER BY time_of_day DESC, source
            """, (month, day))

        entries = cursor.fetchall()
        if not entries:
            raise HTTPException(status_code=404, detail=f"No devotional for: {month:02d}-{day:02d}")

        return {
            "date": f"{month:02d}-{day:02d}",
            "month": month,
            "day": day,
            "entries": [dict(e) for e in entries]
        }
    finally:
        conn.close()


@router.get("/api/devotional/sources")
def get_devotional_sources():
    """Get available devotional sources and their entry counts."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            SELECT source, COUNT(*) as entry_count
            FROM devotionals
            GROUP BY source
            ORDER BY source
        """)
        sources = [dict(row) for row in cursor.fetchall()]
        return {"sources": sources}
    finally:
        conn.close()


