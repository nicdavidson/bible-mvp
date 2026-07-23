import json
from pathlib import Path
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

# ========== READING PLAN ENDPOINTS ==========

def _load_plan(plan_id: str) -> dict:
    """Load a reading-plan JSON file by id. Raises 400/404 on bad id."""
    # Sanitize plan_id to prevent path traversal
    if not re.match(r'^[a-zA-Z0-9_-]+$', plan_id):
        raise HTTPException(status_code=400, detail="Invalid plan ID")
    data_path = Path(__file__).parent.parent.parent / "data"
    # 'chronological-year' is a legacy alias for the 'chronological' plan file
    plan_file = data_path / f"reading-plan-{plan_id.replace('chronological-year', 'chronological')}.json"

    if not plan_file.exists():
        raise HTTPException(status_code=404, detail=f"Reading plan not found: {plan_id}")

    with open(plan_file) as f:
        return json.load(f)


@router.get("/api/reading-plans")
def get_reading_plans():
    """Get list of available reading plans."""
    data_path = Path(__file__).parent.parent.parent / "data"
    plans = []

    for plan_file in data_path.glob("reading-plan-*.json"):
        with open(plan_file) as f:
            plan = json.load(f)
            plans.append({
                "id": plan["id"],
                "name": plan["name"],
                "description": plan["description"],
                "duration_days": plan["duration_days"],
                "tracks": plan.get("tracks", [])
            })

    return {"plans": plans}


@router.get("/api/reading-plans/{plan_id}")
def get_reading_plan(plan_id: str):
    """Get full reading plan with all days."""
    return _load_plan(plan_id)


@router.get("/api/reading-plans/{plan_id}/day/{day}")
def get_reading_plan_day(plan_id: str, day: int):
    """Get a specific day's reading from a plan."""
    plan = _load_plan(plan_id)

    # Find the day
    for d in plan["days"]:
        if d["day"] == day:
            return {
                "plan_id": plan_id,
                "plan_name": plan["name"],
                "day": day,
                "total_days": plan["duration_days"],
                "readings": d
            }

    raise HTTPException(status_code=404, detail=f"Day {day} not found in plan")


# Helper functions

