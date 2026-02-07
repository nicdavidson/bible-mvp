#!/usr/bin/env python3
"""
Build the Bible database from source data.

This orchestrates all import scripts in the correct order, with incremental
support via a _build_meta table. Only runs imports that haven't completed yet
(or have changed version).

Usage:
    python scripts/build_db.py              # Incremental build (skip completed steps)
    python scripts/build_db.py --full       # Full rebuild from scratch
    python scripts/build_db.py --step bsb   # Run only a specific step
    python scripts/build_db.py --list       # List all steps and their status

Data sources:
    Local files (in repo):
        - data/alignment/TAHOT_*.txt, TAGNT_*.txt  (STEPBible, ~100MB)
        - data/cross_references.txt                  (OpenBible.info, 8MB)
        - data/naves/NavesTopicalDictionary.csv      (Nave's Topical Bible, 1.4MB)
    Cloned repos (auto-downloaded):
        - data/clear-bible/     (Clear-Bible/Alignments - BSB word alignments)
        - data/speaker-quotations/ (Clear-Bible/speaker-quotations - red letter)
    Network APIs:
        - KJV/WEB translations  (GitHub raw files)
        - Strong's lexicon      (openscriptures GitHub)
        - Commentary            (HelloAO Bible API)
        - Spurgeon devotionals  (CCEL)
"""
import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DB_PATH = Path(os.environ.get("DATABASE_PATH", DATA_DIR / "bible.db"))

# Import steps in dependency order
# Each step: (name, script, description, version, dependencies)
IMPORT_STEPS = [
    {
        "name": "schema",
        "description": "Initialize database schema",
        "version": "1.0",
        "script": None,  # Built-in
    },
    {
        "name": "bsb",
        "description": "BSB translation + Clear-Bible word alignments (724K alignments)",
        "version": "1.0",
        "script": "import_bsb.py",
        "requires_data": "clear-bible",
        "data_source": "https://github.com/Clear-Bible/Alignments",
    },
    {
        "name": "full_bibles",
        "description": "KJV translation from GitHub (~31K verses)",
        "version": "1.1",
        "script": "import_full_bibles.py",
        "args": ["--kjv-only"],
    },
    {
        "name": "web",
        "description": "WEB translation from seven1m/open-bibles XML (~31K verses)",
        "version": "1.0",
        "script": "import_web_xml.py",
    },
    {
        "name": "interlinear",
        "description": "STEPBible Hebrew/Greek interlinear (426K words)",
        "version": "1.0",
        "script": "import_stepbible_alignment.py",
        "requires_data": "alignment",
    },
    {
        "name": "strongs",
        "description": "Strong's Hebrew & Greek lexicon",
        "version": "1.0",
        "script": "import_strongs.py",
    },
    {
        "name": "cross_refs",
        "description": "Treasury of Scripture Knowledge cross-references (41K entries)",
        "version": "1.0",
        "script": "import_cross_refs.py",
        "requires_data": "cross_references.txt",
    },
    {
        "name": "commentary_mh",
        "description": "Matthew Henry Concise Commentary (65/66 books)",
        "version": "1.0",
        "script": "import_commentary.py",
        "args": ["matthew-henry"],
    },
    {
        "name": "commentary_jg",
        "description": "John Gill Exposition (28K+ verses)",
        "version": "1.0",
        "script": "import_commentary.py",
        "args": ["john-gill"],
    },
    {
        "name": "speakers",
        "description": "Red letter speaker data (6,896 divine speech verses)",
        "version": "1.0",
        "script": "import_speakers.py",
        "requires_data": "speaker-quotations",
        "data_source": "https://github.com/Clear-Bible/speaker-quotations",
    },
    {
        "name": "spurgeon",
        "description": "Spurgeon Morning & Evening devotionals (730 entries)",
        "version": "1.0",
        "script": "import_spurgeon.py",
    },
    {
        "name": "naves",
        "description": "Nave's Topical Bible (5,319 topics, 49K refs)",
        "version": "1.0",
        "script": "import_naves.py",
        "requires_data": "naves/NavesTopicalDictionary.csv",
    },
]


def get_db_connection():
    """Get a database connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_build_meta_table(conn):
    """Create the _build_meta table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _build_meta (
            import_name TEXT PRIMARY KEY,
            version TEXT NOT NULL,
            row_count INTEGER DEFAULT 0,
            started_at TEXT,
            completed_at TEXT,
            duration_seconds REAL DEFAULT 0
        )
    """)
    conn.commit()


def get_step_status(conn, step_name):
    """Get the build status for a step. Returns dict or None."""
    try:
        cursor = conn.execute(
            "SELECT * FROM _build_meta WHERE import_name = ?", (step_name,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.OperationalError:
        return None


def mark_step_started(conn, step_name, version):
    """Mark a step as started."""
    conn.execute("""
        INSERT OR REPLACE INTO _build_meta (import_name, version, started_at)
        VALUES (?, ?, ?)
    """, (step_name, version, datetime.now().isoformat()))
    conn.commit()


def mark_step_completed(conn, step_name, version, row_count, duration):
    """Mark a step as completed."""
    conn.execute("""
        UPDATE _build_meta
        SET version = ?, row_count = ?, completed_at = ?, duration_seconds = ?
        WHERE import_name = ?
    """, (version, row_count, datetime.now().isoformat(), duration, step_name))
    conn.commit()


def should_run_step(conn, step, force=False):
    """Determine if a step needs to run."""
    if force:
        return True

    status = get_step_status(conn, step["name"])
    if not status:
        return True  # Never run

    if not status["completed_at"]:
        return True  # Started but didn't finish

    if status["version"] != step["version"]:
        return True  # Version changed

    return False


def check_data_available(step):
    """Check if required local data is available for a step."""
    requires = step.get("requires_data")
    if not requires:
        return True

    data_path = DATA_DIR / requires
    if data_path.exists():
        # For cloned repos, also verify key files exist
        if step["name"] == "bsb":
            bsb_target = data_path / "data" / "eng" / "targets" / "BSB" / "ot_BSB.tsv"
            return bsb_target.exists()
        return True

    return False


def download_source_data(step):
    """Download required source data for a step."""
    requires = step.get("requires_data")
    source = step.get("data_source")

    if not requires or not source:
        return False

    data_path = DATA_DIR / requires
    if data_path.exists():
        return True

    print(f"\n  Downloading {requires} from {source}...")

    if "github.com" in source:
        # Clone the repo
        repo_name = source.rstrip("/").split("/")[-1]
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", source, str(data_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"  Cloned {repo_name} to {data_path}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  Failed to clone {source}: {e.stderr}")
            return False
        except FileNotFoundError:
            print("  git not found - please install git")
            return False
    else:
        print(f"  Unknown source type: {source}")
        return False


def init_schema(conn):
    """Initialize the database schema."""
    # Import the schema from the main database module
    sys.path.insert(0, str(PROJECT_ROOT))
    from backend.database import SCHEMA

    conn.executescript(SCHEMA)
    conn.commit()

    # Count tables created
    cursor = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE '_build%'"
    )
    table_count = cursor.fetchone()[0]
    return table_count


def run_import_script(step):
    """Run an import script as a subprocess."""
    script = SCRIPTS_DIR / step["script"]
    if not script.exists():
        print(f"  Script not found: {script}")
        return False, 0

    cmd = [sys.executable, str(script)]
    if "args" in step:
        cmd.extend(step["args"])

    # Set DATABASE_PATH env var so scripts use the same DB
    env = os.environ.copy()
    env["DATABASE_PATH"] = str(DB_PATH)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            env=env,
            timeout=1800,  # 30 min timeout
        )

        if result.returncode != 0:
            print(f"  Script failed (exit {result.returncode}):")
            # Show last 20 lines of stderr
            for line in result.stderr.strip().split("\n")[-20:]:
                print(f"    {line}")
            return False, 0

        # Print script output (last 5 lines for brevity)
        output_lines = result.stdout.strip().split("\n")
        for line in output_lines[-5:]:
            print(f"  {line}")

        # Try to extract row count from output
        row_count = 0
        for line in output_lines:
            # Look for patterns like "Imported 31102 verses" or "12345 entries"
            import re
            match = re.search(r'(\d{3,})\s+(?:verse|word|entr|align|record|row|item|definition)', line, re.IGNORECASE)
            if match:
                row_count = max(row_count, int(match.group(1)))

        return True, row_count

    except subprocess.TimeoutExpired:
        print(f"  Script timed out after 30 minutes")
        return False, 0


def count_rows(conn, step_name):
    """Count rows for a completed step to estimate size."""
    table_map = {
        "bsb": "verses",
        "full_bibles": "verses",
        "web": "verses",
        "interlinear": "word_alignments",
        "strongs": "lexicon",
        "cross_refs": "cross_references",
        "commentary_mh": "commentary_entries",
        "commentary_jg": "commentary_entries",
        "speakers": "speaker_verses",
        "spurgeon": "devotionals",
        "naves": "naves_topics",
    }
    table = table_map.get(step_name)
    if not table:
        return 0
    try:
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
        return cursor.fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def generate_manifest(conn):
    """Generate the db-manifest.json file."""
    # Hash the database
    sha256 = hashlib.sha256()
    with open(DB_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)

    # Gather import stats
    imports = {}
    ensure_build_meta_table(conn)
    cursor = conn.execute("SELECT * FROM _build_meta WHERE completed_at IS NOT NULL")
    for row in cursor.fetchall():
        row = dict(row)
        imports[row["import_name"]] = {
            "version": row["version"],
            "row_count": row["row_count"],
            "completed_at": row["completed_at"],
        }

    manifest = {
        "version": datetime.now().strftime("%Y.%m.%d"),
        "sha256": sha256.hexdigest(),
        "size": DB_PATH.stat().st_size,
        "built": datetime.now().isoformat(),
        "imports": imports,
    }

    manifest_path = DATA_DIR / "db-manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nManifest written to {manifest_path}")
    print(f"  SHA256: {manifest['sha256'][:16]}...")
    print(f"  Size: {manifest['size'] / 1024 / 1024:.1f} MB")

    return manifest


def list_steps(conn):
    """Print the status of all import steps."""
    ensure_build_meta_table(conn)

    print(f"\nDatabase: {DB_PATH}")
    if DB_PATH.exists():
        size_mb = DB_PATH.stat().st_size / 1024 / 1024
        print(f"Size: {size_mb:.1f} MB")
    print()

    print(f"{'Step':<20} {'Version':<10} {'Status':<12} {'Rows':<12} {'Duration':<10}")
    print("-" * 70)

    for step in IMPORT_STEPS:
        status = get_step_status(conn, step["name"])
        if not status:
            state = "pending"
            version = step["version"]
            rows = ""
            duration = ""
        elif not status["completed_at"]:
            state = "incomplete"
            version = status["version"]
            rows = ""
            duration = ""
        elif status["version"] != step["version"]:
            state = "outdated"
            version = f"{status['version']} -> {step['version']}"
            rows = str(status["row_count"])
            duration = f"{status['duration_seconds']:.0f}s"
        else:
            state = "done"
            version = status["version"]
            rows = str(status["row_count"])
            duration = f"{status['duration_seconds']:.0f}s"

        # Check data availability
        if not check_data_available(step):
            data_note = " (needs download)"
        else:
            data_note = ""

        print(f"{step['name']:<20} {version:<10} {state:<12} {rows:<12} {duration}{data_note}")


def main():
    parser = argparse.ArgumentParser(
        description="Build the Bible database from source data"
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Full rebuild from scratch (deletes existing DB)"
    )
    parser.add_argument(
        "--step", type=str,
        help="Run only a specific step (e.g., 'bsb', 'strongs')"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List all steps and their status"
    )
    parser.add_argument(
        "--manifest", action="store_true",
        help="Generate db-manifest.json only"
    )
    parser.add_argument(
        "--skip-network", action="store_true",
        help="Skip steps that require network access"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("BibleMVP Database Builder")
    print(f"Database: {DB_PATH}")
    print("=" * 60)

    # Full rebuild: delete existing DB
    if args.full and DB_PATH.exists():
        print(f"\nDeleting existing database ({DB_PATH.stat().st_size / 1024 / 1024:.1f} MB)...")
        DB_PATH.unlink()

    conn = get_db_connection()
    ensure_build_meta_table(conn)

    # List mode
    if args.list:
        list_steps(conn)
        conn.close()
        return

    # Manifest-only mode
    if args.manifest:
        generate_manifest(conn)
        conn.close()
        return

    # Filter to specific step if requested
    steps = IMPORT_STEPS
    if args.step:
        steps = [s for s in steps if s["name"] == args.step]
        if not steps:
            print(f"\nUnknown step: {args.step}")
            print(f"Available: {', '.join(s['name'] for s in IMPORT_STEPS)}")
            conn.close()
            sys.exit(1)

    # Network steps
    NETWORK_STEPS = {"full_bibles", "web", "strongs", "commentary_mh", "commentary_jg", "spurgeon"}

    # Run each step
    completed = 0
    skipped = 0
    failed = 0

    for step in steps:
        name = step["name"]

        # Skip network steps if requested
        if args.skip_network and name in NETWORK_STEPS:
            print(f"\n[{name}] Skipping (--skip-network)")
            skipped += 1
            continue

        # Check if step needs to run
        force = args.full or bool(args.step)
        if not should_run_step(conn, step, force=force):
            print(f"\n[{name}] Already done (v{step['version']})")
            skipped += 1
            continue

        # Check data availability
        if not check_data_available(step):
            downloaded = download_source_data(step)
            if not downloaded:
                source = step.get("data_source", "unknown")
                print(f"\n[{name}] SKIPPED - required data not available")
                print(f"  Download from: {source}")
                skipped += 1
                continue

        print(f"\n[{name}] {step['description']}...")
        mark_step_started(conn, name, step["version"])
        start_time = time.time()

        if name == "schema":
            # Built-in schema initialization
            table_count = init_schema(conn)
            duration = time.time() - start_time
            mark_step_completed(conn, name, step["version"], table_count, duration)
            print(f"  Created {table_count} tables in {duration:.1f}s")
            completed += 1
        else:
            # Run external script
            success, row_count = run_import_script(step)
            duration = time.time() - start_time

            if success:
                # If script didn't report rows, count from DB
                if row_count == 0:
                    row_count = count_rows(conn, name)
                mark_step_completed(conn, name, step["version"], row_count, duration)
                print(f"  Completed in {duration:.1f}s ({row_count} rows)")
                completed += 1
            else:
                print(f"  FAILED after {duration:.1f}s")
                failed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"Build complete: {completed} done, {skipped} skipped, {failed} failed")

    if DB_PATH.exists() and DB_PATH.stat().st_size > 0:
        size_mb = DB_PATH.stat().st_size / 1024 / 1024
        print(f"Database size: {size_mb:.1f} MB")

        # Generate manifest
        generate_manifest(conn)

    conn.close()


if __name__ == "__main__":
    main()
