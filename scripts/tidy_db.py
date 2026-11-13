#!/usr/bin/env python3
"""Drop indexes that no query needs (build step `tidy`). Idempotent.

- idx_alignment_ref ON word_alignments(book, chapter, verse): a prefix of the
  UNIQUE(book, chapter, verse, word_position) index, which every query that
  used it now uses instead (same plans; checked in tests/test_alignment_store.py). ~9.8 MB.
- idx_alignment_word_type ON word_alignments(word_type): no query filters on
  word_type (it is only selected). ~5.1 MB.

The interlinear importer still creates both; this step runs after it.
Other size options and their risks: docs/ALIGNMENT_2026-11.md, "Storage".
"""
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("DATABASE_PATH", Path(__file__).parent.parent / "data" / "bible.db"))

REDUNDANT_INDEXES = ("idx_alignment_ref", "idx_alignment_word_type")


def tidy(conn) -> list[str]:
    dropped = []
    for name in REDUNDANT_INDEXES:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
                        (name,)).fetchone():
            conn.execute(f"DROP INDEX {name}")
            dropped.append(name)
    conn.commit()
    return dropped


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    print(f"dropped {tidy(conn) or 'nothing'} (run VACUUM, e.g. via release_db.py, to reclaim)")
