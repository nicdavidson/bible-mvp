"""
BibleMVP - FastAPI Backend
A free, open-source Bible study platform.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .database import get_db_connection, get_writable_db_connection, init_db, DATABASE_PATH
from .core import limiter

logger = logging.getLogger(__name__)

# Static files
frontend_path = Path(__file__).parent.parent / "frontend"



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    # Create indexes needed for bidirectional cross-reference lookups
    # (get_db_connection is read-only; index creation needs a writable one)
    conn = get_writable_db_connection()
    try:
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_crossref_target
            ON cross_references(target_book, target_chapter, target_verse)
        """)
        conn.commit()
    finally:
        conn.close()
    yield


app = FastAPI(
    title="BibleMVP API",
    description="Free Bible study platform with cross-resource linking",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiter lives in core so routers can decorate with the same instance
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.mount("/static", StaticFiles(directory=frontend_path / "static"), name="static")

# Bible text is immutable - set aggressive cache headers on API endpoints.
# This enables free scaling via CDN (e.g. Cloudflare) without any code changes.
CACHE_LONG = "public, max-age=86400"  # 24 hours for immutable content
CACHE_SHORT = "public, max-age=3600"  # 1 hour for semi-dynamic content (devotionals)

# Paths that serve immutable Bible data (passages, commentary, cross-refs, interlinear, lexicon)
_CACHEABLE_PREFIXES = (
    "/api/passage/", "/api/verse/", "/api/word/", "/api/word-alignment",
    "/api/offline/", "/api/reading-plans", "/api/crossref-map/",
    "/api/path-to-christ/", "/api/search", "/api/topics/",
)
_SHORT_CACHE_PREFIXES = ("/api/devotional",)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' https://*.supabase.co wss://*.supabase.co; "
        "font-src 'self'; "
        "frame-ancestors 'none'"
    )
    return response


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    """Add Cache-Control headers to API responses for CDN-friendly caching."""
    response: Response = await call_next(request)
    path = request.url.path
    if response.status_code == 200:
        # Service worker must never be cached — browser needs to fetch fresh to detect updates
        if path == "/static/sw.js":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        elif any(path.startswith(p) for p in _CACHEABLE_PREFIXES):
            response.headers["Cache-Control"] = CACHE_LONG
        elif any(path.startswith(p) for p in _SHORT_CACHE_PREFIXES):
            # Only cache when the date is explicit in the URL — the no-date form
            # resolves "today" server-side, and a cached copy would serve
            # yesterday's devotional after midnight (cache key has no date).
            if "date=" in request.url.query:
                response.headers["Cache-Control"] = CACHE_SHORT
    return response


@app.get("/api/health")
def health():
    """Health check with database stats."""
    # Table name -> label mapping (hardcoded allowlist, never from user input)
    _STAT_TABLES = {
        "verses": "verses",
        "cross_references": "cross_references",
        "commentary_entries": "commentary_entries",
        "lexicon": "lexicon_entries",
        "word_alignments": "word_alignments",
        "devotionals": "devotionals",
    }
    conn = get_db_connection()
    try:
        stats = {}
        for table, label in _STAT_TABLES.items():
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                stats[label] = row[0]
            except Exception:
                stats[label] = 0
        return {"status": "ok", "database_exists": DATABASE_PATH.exists(), "stats": stats}
    finally:
        conn.close()


@app.get("/")
def root():
    """Serve the main application page."""
    return FileResponse(frontend_path / "index.html")



from .routers import passages, words, devotional, plans, offline, crossref_map, topics  # noqa: E402

for _r in (passages, words, devotional, plans, offline, crossref_map, topics):
    app.include_router(_r.router)

@app.get("/map")
def serve_map():
    """Serve the cross-reference mapper visualization page."""
    return FileResponse(frontend_path / "map.html")


# Route for reading plan URLs (e.g., /plan/chronological-year/45)
# Must be registered before the catch-all book/chapter routes
@app.get("/plan/{plan_id}/{day}")
def serve_app_with_plan(plan_id: str, day: int):
    """Serve main app for reading plan URLs - JS handles the routing."""
    return FileResponse(frontend_path / "index.html")


# Catch-all route for clean URLs (e.g., /John/3/16)
# Must be registered last to not override other routes
@app.get("/{book}/{chapter}")
@app.get("/{book}/{chapter}/{verse}")
def serve_app_with_reference(book: str, chapter: int, verse: str = None):
    # verse is str, not int: share links use ranges like /John/3/16-18
    """Serve main app for clean URLs - JS handles the routing."""
    return FileResponse(frontend_path / "index.html")
