# BibleMVP - TODO

## Current Status

**Deployment:** Fly.io with persistent volume for SQLite database (too large for GitHub)

**Working:**
- [x] Bible text (93,505 verses - BSB + WEB + KJV)
- [x] **BSB as default translation** with full word-level Hebrew/Greek alignment (724,050 alignments)
- [x] Click any BSB word → see original Hebrew/Greek with Strong's definition (deterministic, not fuzzy)
- [x] Search autocomplete for book names
- [x] Chapter context with verse highlighting
- [x] Prev/next chapter and verse navigation
- [x] Clickable verse boxes for commentary
- [x] Cross-references (41,649 entries) with hover previews
- [x] Commentary display (4,124 entries - Matthew Henry, 65/66 books - Song of Solomon missing from API)
- [x] Dark mode
- [x] Notes (localStorage)
- [x] Book-only reference defaults to chapter 1
- [x] Hebrew interlinear for entire OT (304,400 words from STEPBible)
- [x] Greek interlinear for entire NT (122,286 words from STEPBible)
- [x] Word click shows Greek/Hebrew details with Strong's definitions
- [x] Loading states & empty state messaging
- [x] Mobile touch support for word study
- [x] "Original Language" toggle in header (always visible)
- [x] Expandable word occurrence list ("and xxx more" clickable)
- [x] PWA manifest for installability
- [x] Service worker for offline caching (requires localhost or HTTPS)
- [x] Auto-cache browsed chapters with visual toast feedback
- [x] Offline settings panel with cache stats display
- [x] Book/chapter picker dropdown
- [x] Mobile-optimized header with hamburger menu
- [x] Resource tab indicators (shows when commentary/notes/cross-refs available)
- [x] Clickable Bible references in commentary (56,228 links auto-parsed)
- [x] Enhanced search (live debounced search, keyboard navigation, grouped results)
- [x] Strong's number search with word info card (e.g., G26 shows ἀγάπη with definition)
- [x] Search scope filters (OT/NT/current book/commentary)

## High Priority

### Data Import
- [x] Import Matthew Henry commentary (65/66 books - Song of Solomon missing from source API)
- [x] Import Strong's lexicon for word studies (DONE)
- [x] Add John Gill commentary (28,300 verses from HelloAO API)
- [x] Add Spurgeon Morning & Evening devotionals (730 entries from CCEL)
- [ ] Find alternative source for Song of Solomon commentary

### UI/UX
- [ ] **Draggable/resizable panels** - VSCode-style layout where Word details, Notes, Commentary, Cross-refs can all be visible simultaneously and rearranged. Consider using Golden Layout or split.js library.
- [ ] **Devotionals as standalone section** - Move devotionals (Spurgeon Morning & Evening) out of the resources tabs into their own dedicated section/page. Consider: daily reading view, calendar navigation, integration with reading plans.

### Core Features (from spec)
- [x] Interlinear data import (OpenGNT, OpenHebrewBible) - DONE for all 66 books
- [x] Word click shows Greek/Hebrew details - DONE
- [x] Service worker + offline caching - DONE
- [x] PWA manifest + install prompt - DONE
- [x] Smart offline caching with IndexedDB - DONE (auto-caches browsed chapters)
- [x] Offline data manager UI - DONE (download books/lexicon for offline use)

## Medium Priority

### Search Improvements
- [x] Live search as you type (debounced) - DONE
- [x] Keyboard navigation for results - DONE
- [x] Group results by type (Bible/Commentary) - DONE
- [x] Search scope filters (OT/NT/book/commentary) - DONE
- [x] Strong's number search (G###/H###) - DONE
- [x] Phrase search with quotes - DONE
- [ ] Search suggestions for book names

### Notes System
- [x] IndexedDB storage layer (for offline data) - DONE
- [ ] Migrate notes from localStorage to IndexedDB
- [ ] Note tags/categories
- [ ] Highlight colors
- [ ] Export notes

### Navigation
- [x] Book/chapter picker dropdown - DONE
- [ ] Reading history
- [ ] Bookmarks

## Lower Priority

### Content
- [x] Spurgeon Morning/Evening devotionals - DONE (via "Today" tab)
- [ ] Additional translations (ASV already in dropdown but may need import)

### Polish
- [x] Keyboard shortcuts (arrows for nav, / for search, G for go-to, D for dark mode, ? for help)
- [ ] Print-friendly styles
- [ ] Share verse functionality

## Technical Debt
- [ ] Add tests
- [ ] Error handling improvements
- [x] Loading states/skeletons - DONE

## Word-by-Word Alignment (MOSTLY COMPLETE)

**Status:** Core functionality implemented for BSB translation using Clear-Bible alignment data.

### Completed
- [x] Research & select primary data sources:
  - BSB word alignments from [Clear-Bible/Alignments](https://github.com/Clear-Bible/Alignments) (CC-BY 4.0)
  - Hebrew source: WLCM (Westminster Leningrad Codex Morphology)
  - Greek source: SBLGNT
  - Strong's lexicon integrated
- [x] Database tables for word-level data:
  - `word_alignments` - Hebrew/Greek words with Strong's, morphology, glosses (426,686 words)
  - `english_word_alignments` - Translation-specific word→original mappings
  - `lexicon` - Strong's definitions
- [x] Import scripts:
  - `scripts/import_bsb.py` - Imports BSB text and Clear-Bible alignment data
  - `scripts/import_interlinear.py` - Imports STEPBible Hebrew/Greek data
- [x] Word click handler:
  - Click any BSB word → `/api/word-alignment` → returns Hebrew/Greek + Strong's definition
  - Deterministic lookup (no fuzzy matching)
- [x] Full coverage: 724,050 BSB word alignments (OT Hebrew + NT Greek)

### Remaining / Future
- [ ] Add word-level alignments for KJV (data available from kaiserlik/kjv repo)
- [ ] WEB alignments (no good public source found - using STEPBible gloss fallback)
- [ ] Advanced word features: Morphology breakdown, usage stats
- [ ] Pronoun/entity resolution
- [ ] User-contributed word notes linked to original words

## Study Spaces & Templates

- [ ] Design template system: JSON configs for panels, resources (translations, commentary, originals, cross-refs), and layouts
- [ ] Backend: New `user_templates` table in SQLite (id, name, config_json)
- [ ] Frontend: Template selector dropdown; load/save current view as template
- [ ] Prototype 2-3 defaults: "Daily Reading" (NIV + commentary), "Deep Study" (add originals + extra refs)

## Highlighting & Tagging

- [ ] Implement text selection highlighting with color picker
- [ ] Add tagging: Assign tags to highlights, default colors per tag
- [ ] Quick mode: Color implies tag; detailed mode: Popup for tag input
- [ ] New/expand SQLite table: `highlights` (verse_ref, selection, color, tag)
- [ ] Filtering: Search/show highlights by tag/color

## Custom & Commentary Hyperlinks

- [ ] User custom links: Create/save verse/note chains (new `user_links` table)
- [x] Auto-parse commentary for Bible refs during import → make clickable (DONE - 56,228 links)
- [x] Frontend handlers: Click ref → load verse/panel (DONE)

## Swipe Mode

- [ ] Full-screen verse view with swipe navigation (Alpine.js touch events)
- [ ] Toggles: Originals, cross-refs, commentary overlays
- [ ] Integrate as template "screen" type (e.g., optional in "Daily Reading")

---

Last updated: 2026-01-18
