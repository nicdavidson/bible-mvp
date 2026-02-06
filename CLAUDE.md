# Bible MVP - Project Guide

## Quick Start
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
# Open http://localhost:8000
```

## Architecture
- **Backend**: FastAPI (Python) — `backend/main.py` (43K, all API routes), `backend/database.py` (17K, schema + migrations)
- **Frontend**: Single `frontend/index.html` (~1,650 lines) + Alpine.js + vanilla CSS
- **Database**: SQLite at `data/bible.db` (~500MB, too large for git) with FTS5 full-text search
- **Deployment**: Fly.io with persistent volume for SQLite

## Key Files
- `frontend/index.html` — The entire HTML/Alpine.js app (monolith)
- `frontend/static/js/app.js` — Main app logic (~3,200 lines) with Alpine.js `bibleApp()` component
- `frontend/static/js/offline-storage.js` — IndexedDB wrapper for offline caching
- `frontend/static/sw.js` — Service worker (network-first for API, cache-first for static)
- `frontend/static/css/style.css` — All styles (~5,900 lines)
- `backend/main.py` — FastAPI routes (passage, search, interlinear, offline export, etc.)
- `backend/database.py` — SQLite schema, migrations, init

## Database Tables
- `verses` (93,505 entries) — BSB, WEB, KJV translations
- `word_alignments` (426,686) — Hebrew/Greek original words with Strong's numbers
- `english_word_alignments` (724,050) — BSB word→original language mappings
- `lexicon` — Strong's definitions
- `words` — STEPBible interlinear data (304,400 Hebrew + 122,286 Greek)
- `commentary_entries` — Matthew Henry (65/66 books), John Gill (28,300 verses)
- `cross_references` (41,649) — Treasury of Scripture Knowledge
- `devotionals` (730) — Spurgeon Morning & Evening
- `speaker_verses` (6,896) — Red letter (divine speech) markers

## API Patterns
```
GET /api/passage/{reference}?translation=BSB  — Full chapter with verse highlighting
GET /api/passage/{ref}/interlinear?translation=BSB  — Hebrew/Greek interlinear words
GET /api/passage/{ref}/commentary  — Commentary entries
GET /api/passage/{ref}/crossrefs  — Cross-references
GET /api/word-alignment?book=X&chapter=Y&verse=Z&word_position=N&translation=BSB
GET /api/search?q=term&scope=all
GET /api/offline/chapter?book=X&chapter=Y&translation=Z  — Bulk offline download
GET /api/offline/lexicon  — Full Strong's dictionary
```

## Data Sources (all public domain or CC-BY 4.0)
- BSB text + Clear-Bible Alignments (SBLGNT Greek, WLCM Hebrew)
- STEPBible TAGNT/TAHOT for interlinear (includes variant edition markers: Byz, NA27/28, TR, SBL, WH, Tyn)
- WEB/KJV from open-bibles
- See LICENSES.md for full details

## Important Context
- The STEPBible data includes variant markers (NKO system) that indicate which manuscript editions
  contain each Greek word. This could be leveraged for translation-specific source text display.
- BSB alignment uses SBLGNT (Critical Text) for Greek, WLCM for Hebrew
- KJV uses Textus Receptus, WEB uses Majority Text — different from BSB's source
- Offline storage uses both Cache API (service worker) and IndexedDB (structured data)
- User data syncs via Supabase (notes, reading plan progress, tags)

## Conventions
- Python: ruff linting, line-length 100
- Frontend: No build step, vanilla JS + Alpine.js, CSS custom properties for theming
- Responsive breakpoints: 900px (single column), 768px (mobile resources panel), 600px (header compact), 380px (extra small)
