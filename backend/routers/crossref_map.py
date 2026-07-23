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

# ============================================================
# Christological seed verses for "Points to Jesus" mode
# ============================================================
CHRISTOLOGICAL_SEEDS = {
    "gospel-peaks": [
        ("John", 1, 1), ("John", 14, 6), ("Matthew", 1, 23),
        ("Mark", 10, 45), ("Luke", 2, 11), ("Isaiah", 53, 5),
    ],
    "messianic": [
        ("Genesis", 3, 15), ("Psalms", 22, 1), ("Psalms", 110, 1),
        ("Isaiah", 7, 14), ("Isaiah", 9, 6), ("Isaiah", 53, 5),
        ("Isaiah", 53, 7), ("Isaiah", 61, 1), ("Micah", 5, 2),
        ("Zechariah", 9, 9), ("Daniel", 7, 13), ("Malachi", 3, 1),
        ("Jeremiah", 23, 5), ("Jeremiah", 31, 31), ("Hosea", 11, 1),
        ("Zechariah", 12, 10), ("Deuteronomy", 18, 15),
        ("Psalms", 16, 10), ("Psalms", 118, 22), ("Isaiah", 40, 3),
    ],
}

PRESET_META = {
    "gospel-peaks": {
        "name": "Gospel Peaks",
        "description": "The most direct declarations about Christ, one from each Gospel plus Isaiah.",
    },
    "messianic": {
        "name": "Messianic Thread",
        "description": "Old Testament prophecies fulfilled in Christ, from Genesis to Malachi.",
    },
    "red-letter": {
        "name": "Red Letter",
        "description": "Jesus's own words: the most cross-referenced verses He spoke.",
    },
}


# Bidirectional top-N neighbor query. Kept as a single template so the
# one-verse and batched-frontier paths run byte-identical SQL per verse
# (same query plan, same tie-breaking, same row order).
_NEIGHBOR_SQL = """
        SELECT target_book, target_chapter, target_verse, votes
        FROM (
            SELECT target_book, target_chapter, target_verse, votes
            FROM cross_references
            WHERE source_book = ? AND source_chapter = ? AND source_verse = ?
            UNION ALL
            SELECT source_book, source_chapter, source_verse, votes
            FROM cross_references
            WHERE target_book = ? AND target_chapter = ? AND target_verse = ?
        )
        GROUP BY target_book, target_chapter, target_verse
        ORDER BY {order_by}
        LIMIT ?
"""


def _neighbor_order(focus_books):
    """ORDER BY clause + extra params for the neighbor query."""
    if focus_books:
        placeholders = ",".join("?" for _ in focus_books)
        return (f"CASE WHEN target_book IN ({placeholders}) "
                "THEN 0 ELSE 1 END, MAX(votes) DESC", tuple(focus_books))
    return "MAX(votes) DESC", ()


def _get_neighbors(conn, book: str, chapter: int, verse: int, limit: int,
                   focus_books: list = None):
    """Top cross-reference neighbors of a verse (bidirectional), best votes first.

    Returns rows of (book, chapter, verse, votes). When focus_books is given,
    neighbors in those books sort ahead of everything else.
    """
    order_by, extra_params = _neighbor_order(focus_books)
    cursor = conn.execute(
        _NEIGHBOR_SQL.format(order_by=order_by),
        (book, chapter, verse, book, chapter, verse, *extra_params, limit))
    return cursor.fetchall()


def _get_neighbors_batch(conn, frontier, limit: int, focus_books: list = None):
    """Fetch neighbors for a whole BFS frontier level in one query per chunk.

    frontier: iterable of (book, chapter, verse) triples. Returns a dict
    mapping each triple to its ordered neighbor rows. Each frontier verse gets
    its own subquery (the exact _NEIGHBOR_SQL with its own ORDER BY/LIMIT),
    concatenated with UNION ALL, so per-verse top-N semantics and row order
    match _get_neighbors exactly — one round-trip instead of N.
    """
    order_by, extra_params = _neighbor_order(focus_books)
    uniq = list(dict.fromkeys(frontier))
    result = {t: [] for t in uniq}
    if len(uniq) <= 4:
        # Tiny frontier: per-verse queries are cheaper than parsing a
        # multi-arm compound statement. Same SQL per verse, same results.
        for t in uniq:
            result[t] = [tuple(r) for r in
                         _get_neighbors(conn, *t, limit, focus_books=focus_books)]
        return result
    arm_sql = ("SELECT ? AS src_idx, * FROM ("
               + _NEIGHBOR_SQL.format(order_by=order_by) + ")")
    CHUNK = 50  # keep well under SQLITE_MAX_COMPOUND_SELECT (500)
    for start in range(0, len(uniq), CHUNK):
        chunk = uniq[start:start + CHUNK]
        sql = "\nUNION ALL\n".join([arm_sql] * len(chunk))
        params = []
        for offset, (b, c, v) in enumerate(chunk):
            params.extend((start + offset, b, c, v, b, c, v,
                           *extra_params, limit))
        for row in conn.execute(sql, params):
            result[uniq[row[0]]].append(tuple(row)[1:])
    return result


def _fetch_verse_texts(conn, triples, translation: str = "BSB"):
    """Batch-fetch verse text for (book, chapter, verse) triples.

    Returns {(book, chapter, verse): text}; missing verses are absent.
    """
    texts = {}
    uniq = list(dict.fromkeys(triples))
    CHUNK = 300  # 900 bound params per statement, well under SQLite's limit
    for start in range(0, len(uniq), CHUNK):
        chunk = uniq[start:start + CHUNK]
        values = ",".join("(?,?,?)" for _ in chunk)
        params = [x for t in chunk for x in t]
        params.append(translation)
        # VALUES-list joined against verses: the planner does one full index
        # seek per triple (a bare row-value IN clause degrades to per-book
        # range scans — measured ~12x slower).
        cursor = conn.execute(f"""
            WITH t(b, c, v) AS (VALUES {values})
            SELECT vs.book, vs.chapter, vs.verse, vs.text
            FROM t JOIN verses vs
              ON vs.book = t.b AND vs.chapter = t.c AND vs.verse = t.v
             AND vs.translation_id = ?
        """, params)
        for row in cursor:
            texts[(row[0], row[1], row[2])] = row[3]
    return texts


def _enrich_nodes(conn, nodes: dict):
    """Add verse text preview and book metadata (testament, book_order) to nodes.

    Two batched queries total (verses + books) instead of one query per node.
    """
    real_nodes = [n for n in nodes.values() if not n.get("isChrist")]
    if not real_nodes:
        return

    texts = _fetch_verse_texts(
        conn, [(n["book"], n["chapter"], n["verse"]) for n in real_nodes])
    for node in real_nodes:
        node["text"] = texts.get((node["book"], node["chapter"], node["verse"]), "")

    books = list(dict.fromkeys(n["book"] for n in real_nodes))
    placeholders = ",".join("?" for _ in books)
    cursor = conn.execute(
        f"SELECT name, book_order, testament FROM books WHERE name IN ({placeholders})",
        books)
    book_meta = {row[0]: {"book_order": row[1], "testament": row[2]} for row in cursor}
    for node in real_nodes:
        meta = book_meta.get(node["book"], {"book_order": 0, "testament": "OT"})
        node["testament"] = meta["testament"]
        node["book_order"] = meta["book_order"]


def _bfs_to_seeds(conn, book: str, chapter: int, verse: int, seed_ids: set,
                  per_hop: int = 15, max_depth: int = 6):
    """BFS the cross-reference graph from a start verse until any seed is reached.

    Returns (found_seed, path_keys, nodes, edges):
    - found_seed: key of the seed reached, or None
    - path_keys: [start_key, ..., found_seed], empty list if no seed found
    - nodes: key -> {id, book, chapter, verse, depth[, isSeed]} for verses seen
    - edges: deduped edge dicts {source, target, votes} discovered on the way
    """
    start_key = f"{book}.{chapter}.{verse}"
    nodes = {start_key: {"id": start_key, "book": book, "chapter": chapter,
                         "verse": verse, "depth": 0}}
    edges = []
    edge_set = set()
    visited = set()
    parent = {}  # for path reconstruction
    queue = [(book, chapter, verse, 0)]
    found_seed = None

    while queue and not found_seed:
        # Queue depths are non-decreasing, so the front run of equal-depth
        # entries is a whole frontier level: prefetch its neighbors in one
        # batched query, then replay the per-node logic in original order.
        current_depth = queue[0][3]
        level = []
        while queue and queue[0][3] == current_depth:
            level.append(queue.pop(0))

        neighbors = {}
        if current_depth < max_depth:
            neighbors = _get_neighbors_batch(
                conn,
                [(b, c, v) for b, c, v, _ in level
                 if f"{b}.{c}.{v}" not in visited],
                per_hop)

        for src_book, src_chapter, src_verse, _ in level:
            src_key = f"{src_book}.{src_chapter}.{src_verse}"
            if src_key in visited:
                continue
            visited.add(src_key)

            if src_key in seed_ids and src_key != start_key:
                found_seed = src_key
                break

            if current_depth >= max_depth:
                continue

            for row in neighbors[(src_book, src_chapter, src_verse)]:
                tgt_book, tgt_chapter, tgt_verse, votes = row
                tgt_key = f"{tgt_book}.{tgt_chapter}.{tgt_verse}"

                edge_key = (min(src_key, tgt_key), max(src_key, tgt_key))
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        "source": src_key, "target": tgt_key, "votes": votes
                    })

                if tgt_key not in nodes:
                    nodes[tgt_key] = {
                        "id": tgt_key, "book": tgt_book,
                        "chapter": tgt_chapter, "verse": tgt_verse,
                        "depth": current_depth + 1,
                        "isSeed": tgt_key in seed_ids,
                    }
                # Record the first (shortest) parent even when the node is already
                # known; recording only on node creation reconstructed false paths.
                if tgt_key not in parent and tgt_key != start_key:
                    parent[tgt_key] = src_key

                if tgt_key in seed_ids:
                    found_seed = tgt_key
                    break

                if tgt_key not in visited:
                    queue.append((tgt_book, tgt_chapter, tgt_verse, current_depth + 1))

            if found_seed:
                break

    path_keys = []
    if found_seed:
        curr = found_seed
        while curr and curr != start_key:
            path_keys.append(curr)
            curr = parent.get(curr)
        path_keys.append(start_key)
        path_keys.reverse()

    return found_seed, path_keys, nodes, edges


def _get_red_letter_seeds(conn):
    """Get top cross-referenced Jesus-spoken verses."""
    cursor = conn.execute("""
        SELECT sv.book, sv.chapter, sv.verse,
               COUNT(cr.source_book) as xref_count
        FROM speaker_verses sv
        LEFT JOIN cross_references cr
            ON (cr.source_book = sv.book AND cr.source_chapter = sv.chapter
                AND cr.source_verse = sv.verse)
            OR (cr.target_book = sv.book AND cr.target_chapter = sv.chapter
                AND cr.target_verse = sv.verse)
        WHERE sv.speaker = 'Jesus'
        GROUP BY sv.book, sv.chapter, sv.verse
        ORDER BY xref_count DESC
        LIMIT 20
    """)
    return [(row[0], row[1], row[2]) for row in cursor.fetchall()]


def _parse_seed_ids(seeds_str: str):
    """Parse comma-separated seed IDs like 'John.1.1,Isaiah.53.5' into tuples."""
    result = []
    for sid in seeds_str.split(","):
        sid = sid.strip()
        parts = sid.rsplit(".", 2)
        if len(parts) == 3:
            try:
                result.append((parts[0], int(parts[1]), int(parts[2])))
            except ValueError:
                continue
    return result


@router.get("/api/crossref-map/presets")
def get_crossref_presets():
    """Return available seed verse presets with their verse lists and text."""
    conn = get_db_connection()
    try:
        result = []
        for key, meta in PRESET_META.items():
            seeds = (CHRISTOLOGICAL_SEEDS.get(key)
                     or (_get_red_letter_seeds(conn) if key == "red-letter" else []))
            texts = _fetch_verse_texts(conn, seeds)
            seed_list = []
            for book, chapter, v in seeds:
                text = texts.get((book, chapter, v), "")
                if len(text) > 120:
                    text = text[:120] + "..."
                seed_list.append({
                    "id": f"{book}.{chapter}.{v}",
                    "ref": f"{book} {chapter}:{v}",
                    "text": text,
                })
            result.append({
                "id": key,
                "name": meta["name"],
                "description": meta["description"],
                "seeds": seed_list,
            })
        return {"presets": result}
    finally:
        conn.close()


@router.get("/api/crossref-map/christological")
def get_crossref_map_christological(
    method: str = Query(default="gospel-peaks", description="Calculation method"),
    verse: str = Query(default=None, description="Verse for find-path mode"),
    depth: int = Query(default=2, ge=1, le=5, description="BFS depth from seeds"),
    per_verse: int = Query(default=5, ge=1, le=30, description="Top N connections per verse"),
    limit: int = Query(default=200, ge=20, le=500, description="Max nodes to return"),
    seeds: str = Query(default=None, description="Comma-separated seed verse IDs to override preset"),
):
    """
    Generate a christological cross-reference graph.
    Center is a synthetic CHRIST node; seeds are christological verses connected to it.
    """
    conn = get_db_connection()
    try:
        # Determine seed verses (custom seeds override preset defaults)
        if seeds:
            seed_list = _parse_seed_ids(seeds)
            if not seed_list:
                seed_list = None  # fall back to method default
        else:
            seed_list = None

        if seed_list is None:
            if method == "red-letter":
                seed_list = _get_red_letter_seeds(conn)
            elif method == "messianic":
                seed_list = CHRISTOLOGICAL_SEEDS["messianic"]
            else:
                seed_list = CHRISTOLOGICAL_SEEDS["gospel-peaks"]

        # --- Find-path mode: BFS from user's verse to any seed ---
        if method == "find-path":
            if not verse:
                raise HTTPException(status_code=400, detail="Verse required for find-path mode")
            parsed = parse_reference(verse)
            if not parsed:
                raise HTTPException(status_code=400, detail=f"Invalid reference: {verse}")
            book, chapter, verse_start, verse_end, has_verse = parsed
            if not has_verse:
                raise HTTPException(status_code=400, detail="A specific verse is required")

            # Use custom seed_list as BFS targets, or default to all seeds
            all_seeds = seed_list if seed_list else (
                CHRISTOLOGICAL_SEEDS["gospel-peaks"]
                + CHRISTOLOGICAL_SEEDS["messianic"]
            )
            seed_ids = {f"{s[0]}.{s[1]}.{s[2]}" for s in all_seeds}

            start_key = f"{book}.{chapter}.{verse_start}"
            found_seed, path_to_christ, nodes, edges = _bfs_to_seeds(
                conn, book, chapter, verse_start, seed_ids
            )

            # Filter to only path + immediate neighbors for clarity
            path_set = set(path_to_christ) if path_to_christ else set(nodes.keys())
            filtered_nodes = {}
            filtered_edges = []
            for key in path_set:
                if key in nodes:
                    filtered_nodes[key] = nodes[key]
            # Also include one hop around the path for context
            for e in edges:
                if e["source"] in path_set or e["target"] in path_set:
                    if e["source"] in nodes:
                        filtered_nodes[e["source"]] = nodes[e["source"]]
                    if e["target"] in nodes:
                        filtered_nodes[e["target"]] = nodes[e["target"]]
                    filtered_edges.append(e)

            nodes = filtered_nodes
            edges = filtered_edges

            # Add Christ node at the end of the path
            christ_node = {
                "id": "__CHRIST__", "book": "", "chapter": 0, "verse": 0,
                "depth": 0, "isChrist": True, "text": "",
                "testament": "", "book_order": 0,
            }
            nodes["__CHRIST__"] = christ_node
            # Connect Christ to the found seed
            if found_seed:
                edges.append({
                    "source": "__CHRIST__", "target": found_seed, "votes": 9999
                })
                if found_seed in nodes:
                    nodes[found_seed]["isSeed"] = True

            _enrich_nodes(conn, nodes)

            return {
                "center": start_key,
                "nodes": list(nodes.values()),
                "edges": edges,
                "seedIds": list(seed_ids & set(nodes.keys())),
                "method": "find-path",
                "pathToChrist": path_to_christ if found_seed else None,
                "christNodeId": "__CHRIST__",
                "foundSeed": found_seed,
            }

        # --- Standard christological BFS (gospel-peaks, messianic, red-letter) ---
        nodes = {}
        edges = []
        edge_set = set()
        queue = []

        # Create synthetic Christ center node
        christ_node = {
            "id": "__CHRIST__", "book": "", "chapter": 0, "verse": 0,
            "depth": 0, "isChrist": True, "text": "",
            "testament": "", "book_order": 0,
        }
        nodes["__CHRIST__"] = christ_node
        seed_ids = []

        # Add seed verses at depth 1 with synthetic edges to Christ
        for s_book, s_chapter, s_verse in seed_list:
            key = f"{s_book}.{s_chapter}.{s_verse}"
            # Verify this verse exists
            cursor = conn.execute(
                "SELECT 1 FROM verses WHERE book = ? AND chapter = ? AND verse = ? LIMIT 1",
                (s_book, s_chapter, s_verse)
            )
            if not cursor.fetchone():
                continue
            nodes[key] = {
                "id": key, "book": s_book, "chapter": s_chapter,
                "verse": s_verse, "depth": 1, "isSeed": True,
            }
            seed_ids.append(key)
            edges.append({"source": "__CHRIST__", "target": key, "votes": 9999})
            edge_set.add(("__CHRIST__", key))
            queue.append((s_book, s_chapter, s_verse, 1))

        # BFS outward from seeds, one batched neighbor query per frontier level
        while queue and len(nodes) < limit:
            current_depth = queue[0][3]
            level = []
            while queue and queue[0][3] == current_depth:
                level.append(queue.pop(0))

            if current_depth >= depth:
                continue

            neighbors = _get_neighbors_batch(
                conn, [(b, c, v) for b, c, v, _ in level], per_verse)

            for src_book, src_chapter, src_verse, _ in level:
                if len(nodes) >= limit:
                    break
                src_key = f"{src_book}.{src_chapter}.{src_verse}"

                for row in neighbors[(src_book, src_chapter, src_verse)]:
                    tgt_book, tgt_chapter, tgt_verse, votes = row
                    tgt_key = f"{tgt_book}.{tgt_chapter}.{tgt_verse}"

                    edge_key = (min(src_key, tgt_key), max(src_key, tgt_key))
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        edges.append({
                            "source": src_key, "target": tgt_key, "votes": votes
                        })

                    if tgt_key not in nodes and len(nodes) < limit:
                        nodes[tgt_key] = {
                            "id": tgt_key, "book": tgt_book,
                            "chapter": tgt_chapter, "verse": tgt_verse,
                            "depth": current_depth + 1,
                        }
                        if current_depth + 1 < depth:
                            queue.append((tgt_book, tgt_chapter, tgt_verse, current_depth + 1))

        _enrich_nodes(conn, nodes)

        return {
            "center": "__CHRIST__",
            "nodes": list(nodes.values()),
            "edges": edges,
            "seedIds": seed_ids,
            "method": method,
            "pathToChrist": None,
        }
    finally:
        conn.close()


@router.get("/api/path-to-christ/{reference}")
def get_path_to_christ(
    reference: str,
    translation: str = Query(default="BSB", description="Translation for verse text"),
):
    """Find shortest cross-reference path from a verse to a christological seed."""
    conn = get_db_connection()
    try:
        parsed = parse_reference(reference)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")
        book, chapter, verse_start, verse_end, has_verse = parsed
        if not has_verse:
            raise HTTPException(status_code=400, detail="A specific verse is required")

        all_seeds = CHRISTOLOGICAL_SEEDS["gospel-peaks"] + CHRISTOLOGICAL_SEEDS["messianic"]
        seed_ids = set()
        seed_info = {}  # key -> (book, chapter, verse)
        for s in all_seeds:
            key = f"{s[0]}.{s[1]}.{s[2]}"
            seed_ids.add(key)
            seed_info[key] = s

        start_key = f"{book}.{chapter}.{verse_start}"

        # If the start verse IS a seed, return immediately
        if start_key in seed_ids:
            cursor = conn.execute(
                "SELECT text FROM verses WHERE book = ? AND chapter = ? AND verse = ? AND translation_id = ?",
                (book, chapter, verse_start, translation)
            )
            row = cursor.fetchone()
            # Get testament
            bcur = conn.execute("SELECT testament FROM books WHERE name = ?", (book,))
            brow = bcur.fetchone()
            testament = brow[0] if brow else "NT"
            return {
                "found": True,
                "start": start_key,
                "seed": start_key,
                "path": [{
                    "key": start_key,
                    "book": book,
                    "chapter": chapter,
                    "verse": verse_start,
                    "text": row[0] if row else "",
                    "reference": f"{book} {chapter}:{verse_start}",
                    "isSeed": True,
                    "testament": testament,
                }],
                "hops": 0,
            }

        # BFS
        found_seed, path_keys, bfs_nodes, _ = _bfs_to_seeds(
            conn, book, chapter, verse_start, seed_ids
        )

        if not found_seed:
            return {"found": False, "start": start_key, "seed": None, "path": [], "hops": 0}

        # Enrich with full verse text
        # Cache testament lookups
        testament_cache = {}
        path = []
        for key in path_keys:
            n = bfs_nodes[key]
            v_book, v_chapter, v_verse = n["book"], n["chapter"], n["verse"]
            cursor = conn.execute(
                "SELECT text FROM verses WHERE book = ? AND chapter = ? AND verse = ? AND translation_id = ?",
                (v_book, v_chapter, v_verse, translation)
            )
            row = cursor.fetchone()
            # Testament
            if v_book not in testament_cache:
                bcur = conn.execute("SELECT testament FROM books WHERE name = ?", (v_book,))
                brow = bcur.fetchone()
                testament_cache[v_book] = brow[0] if brow else "NT"
            path.append({
                "key": key,
                "book": v_book,
                "chapter": v_chapter,
                "verse": v_verse,
                "text": row[0] if row else "",
                "reference": f"{v_book} {v_chapter}:{v_verse}",
                "isSeed": key in seed_ids,
                "testament": testament_cache[v_book],
            })

        return {
            "found": True,
            "start": start_key,
            "seed": found_seed,
            "path": path,
            "hops": len(path) - 1,
        }
    finally:
        conn.close()


@router.get("/api/crossref-map/{reference}")
def get_crossref_map(
    reference: str,
    depth: int = Query(default=1, ge=1, le=7, description="How many hops to follow"),
    per_verse: int = Query(default=5, ge=1, le=50, description="Top N connections per verse"),
    diminish: bool = Query(default=False, description="Reduce connections at each hop depth"),
    limit: int = Query(default=150, ge=10, le=500, description="Max nodes to return"),
    focus_books: str = Query(default=None, description="Comma-separated book names to prioritize in BFS")
):
    """
    Get cross-reference graph data for visualization.
    Uses per-verse top-N selection so every verse gets its best connections
    regardless of absolute vote count.
    """
    conn = get_db_connection()
    try:
        parsed = parse_reference(reference)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {reference}")

        book, chapter, verse_start, verse_end, has_verse = parsed

        # Parse focus books and auto-boost depth/limit when focusing
        focus_list = []
        if focus_books:
            focus_list = [b.strip() for b in focus_books.split(",") if b.strip()]
        if focus_list:
            depth = max(depth, 3)
            limit = max(limit, 250)

        # Build graph by BFS traversal of cross-references
        nodes = {}  # key -> node dict
        edges = []  # list of edge dicts
        edge_set = set()  # for O(1) dedup
        visited = set()
        queue = []

        # Seed with the requested verses
        if has_verse:
            for v in range(verse_start, verse_end + 1):
                key = f"{book}.{chapter}.{v}"
                nodes[key] = {"id": key, "book": book, "chapter": chapter, "verse": v, "depth": 0}
                queue.append((book, chapter, v, 0))
        else:
            # For whole chapter, get the top cross-referenced verses
            cursor = conn.execute("""
                SELECT source_verse, COUNT(*) as cnt
                FROM cross_references
                WHERE source_book = ? AND source_chapter = ?
                GROUP BY source_verse ORDER BY cnt DESC LIMIT 5
            """, (book, chapter))
            seed_verses = [row[0] for row in cursor.fetchall()]
            if not seed_verses:
                seed_verses = [1]
            for v in seed_verses:
                key = f"{book}.{chapter}.{v}"
                nodes[key] = {"id": key, "book": book, "chapter": chapter, "verse": v, "depth": 0}
                queue.append((book, chapter, v, 0))

        # BFS to collect graph
        # per_verse controls how many connections each verse contributes (top N by votes).
        # diminish mode: each hop gets fewer connections (tapers outward)
        # normal mode: deeper hops get slightly more connections
        while queue and len(nodes) < limit:
            # Queue depths are non-decreasing: the front run of equal-depth
            # entries is one frontier level. hop_limit depends only on depth,
            # so the whole level shares one batched neighbor query.
            current_depth = queue[0][3]
            level = []
            while queue and queue[0][3] == current_depth:
                level.append(queue.pop(0))

            if diminish:
                # Each hop gets ~60% of the previous hop's connections (min 2)
                hop_limit = max(2, round(per_verse * (0.6 ** current_depth)))
            else:
                hop_limit = per_verse + min(per_verse, current_depth * 2)

            # Get top cross-refs per verse (bidirectional), ordered by votes
            # When focus_books is set, prioritize those books in the sort order
            neighbors = _get_neighbors_batch(
                conn,
                [(b, c, v) for b, c, v, _ in level
                 if f"{b}.{c}.{v}" not in visited],
                hop_limit, focus_books=focus_list or None)

            for src_book, src_chapter, src_verse, _ in level:
                if len(nodes) >= limit:
                    break
                src_key = f"{src_book}.{src_chapter}.{src_verse}"

                if src_key in visited:
                    continue
                visited.add(src_key)

                for row in neighbors[(src_book, src_chapter, src_verse)]:
                    tgt_book, tgt_chapter, tgt_verse, votes = row
                    tgt_key = f"{tgt_book}.{tgt_chapter}.{tgt_verse}"

                    # Add edge (deduplicate with set)
                    edge_key = (min(src_key, tgt_key), max(src_key, tgt_key))
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        edges.append({
                            "source": src_key,
                            "target": tgt_key,
                            "votes": votes
                        })

                    # Add node if new
                    if tgt_key not in nodes and len(nodes) < limit:
                        nodes[tgt_key] = {
                            "id": tgt_key,
                            "book": tgt_book,
                            "chapter": tgt_chapter,
                            "verse": tgt_verse,
                            "depth": current_depth + 1
                        }

                        # Queue for next depth level
                        if current_depth + 1 < depth:
                            queue.append((tgt_book, tgt_chapter, tgt_verse, current_depth + 1))

        _enrich_nodes(conn, nodes)

        return {
            "center": f"{book}.{chapter}.{verse_start}" if has_verse else f"{book}.{chapter}.1",
            "nodes": list(nodes.values()),
            "edges": edges,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "depth": depth,
                "per_verse": per_verse,
                "focus_books": focus_list or None
            }
        }
    finally:
        conn.close()


