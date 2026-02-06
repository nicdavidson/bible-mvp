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
- [x] Notes (localStorage + Supabase sync)
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
- [x] **Reading Plans** with chronological Bible reading
- [x] **Combined "Read All Together" mode** for daily readings
- [x] **URL persistence for reading plans** (/plan/{planId}/{day})
- [x] **Supabase sync for reading plan progress** (user_reading_plans + reading_plan_progress tables)
- [x] **Note tags with colors** (Supabase sync)
- [x] **Plan completion indicator** with celebration banner
- [x] **Book genre color-coding** in book picker (Law, History, Wisdom, Prophets, etc.) with configurable colors
- [x] **Red Letter display** for words of God (OT) and Jesus (NT) - 6,896 verses with divine speech (toggleable)

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
- [x] Reading plans with progress tracking - DONE

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
- [x] Note tags/categories - DONE (with Supabase sync)
- [ ] Migrate notes from localStorage to IndexedDB
- [ ] Highlight colors
- [ ] Export notes

### Navigation
- [x] Book/chapter picker dropdown - DONE
- [ ] Reading history
- [ ] Bookmarks

### Reading Plans
- [x] Chronological Bible reading plan - DONE (365 days)
- [x] Combined "Read All Together" mode - DONE
- [x] URL state persistence - DONE
- [x] Supabase sync for progress - DONE
- [x] Completion indicator - DONE
- [ ] Additional reading plans (canonical, M'Cheyne, etc.)
- [ ] User-created custom reading plans

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
- [x] Database build tooling (`scripts/build_db.py` orchestrator, `scripts/setup_db.sh`, `Makefile`)
- [x] `DATABASE_PATH` env var support (all import scripts + `database.py`)

### Performance / Scaling
- [ ] **Add Cache-Control headers** to API responses — Bible text is immutable, set `Cache-Control: public, max-age=86400` on passage/commentary/cross-ref endpoints. Free scaling with Cloudflare.
- [ ] Consider LiteFS for multi-region read replicas if user base grows
- [ ] Consider adding `user_id` to `reading_plan_progress` table for faster RLS queries at scale
- [ ] Add index on `reading_plan_progress.day_number` if querying "who completed day X" becomes needed

### Commentary UX
- [ ] **Auto-scroll to current verse in commentary** — When viewing verse 20, commentary should scroll/jump to the section about verse 20 instead of showing from the top. Requires parsing `reference_start`/`reference_end` fields and anchoring to the closest section.
- [ ] **Collapsible commentary sections** — Long commentaries (especially Matthew Henry) should be broken into expandable sections by verse range, so users can quickly find and expand the relevant section.
- [ ] **Commentary source tabs** — When multiple commentaries exist for a passage (Matthew Henry + John Gill), show them as sub-tabs rather than concatenated, so users can switch between perspectives.
- [ ] Consider JSONB array for completed days if row count becomes a concern (365 rows per user per plan)

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

## Immersive / Distraction-Free Mode (HIGH PRIORITY)

- [ ] Full-screen verse view with swipe navigation (Alpine.js touch events)
- [ ] Toggles: Originals, cross-refs, commentary overlays
- [ ] Integrate as template "screen" type (e.g., optional in "Daily Reading")
- [ ] "No distraction" mode — clean, focused reading with large typography
- [ ] Ambient background options, minimal UI chrome
- [ ] Swipe between chapters/verses, tap to reveal controls

## Future Features (Roadmap)

### Parallel Translation View
- [ ] Side-by-side comparison of BSB/KJV/WEB for the same passage
- [ ] Highlight differences between translations
- [ ] Synchronized scrolling

### Scripture Memory Tool
- [ ] Spaced repetition flashcards for verse memorization
- [ ] Progressive word hiding (first letters → blanks → full recall)
- [ ] Track memorization progress per verse
- [ ] Daily memory review prompts

### Cross-Reference Graph Visualization
- [ ] Interactive D3.js force-directed graph showing verse connections
- [ ] Click a verse → see all 41,649 cross-references as a visual web
- [ ] Filter by relationship type, book, testament
- [ ] Zoomable, explorable — "wow factor" feature

### Word Study Dashboard
- [ ] Click a Strong's number → see full usage dashboard
- [ ] Occurrence frequency chart by book
- [ ] All different English translations of the word
- [ ] Context clusters showing usage patterns
- [ ] Already have the data (426K alignments + lexicon)

### Passage Comparison Diff
- [ ] Show highlighted diffs between translations for the same passage
- [ ] Color-code additions/removals/changes between BSB/KJV/WEB
- [ ] Pairs with source text transparency to show WHY translations differ

### Sermon Outline Builder
- [ ] Structured notes mode with headings, points, sub-points
- [ ] Drag-and-drop verse references into outline slots
- [ ] Export outline as formatted document
- [ ] Designed for pastor sermon prep workflow

### Topical Index (Nave's Topical Bible) — credit Orville James Nave
- [ ] Import Nave's Topical Bible (public domain, 1896, ~20K topics, ~100K refs)
- [ ] Data source: Open Scriptures project on GitHub (digitized, freely available)
- [ ] Add "Topics" as a sidebar tab option alongside Commentary/Notes/Cross-Refs
- [ ] Browse-by-topic UI with search
- [ ] Topic → verse list with previews, click to navigate
- [ ] Integrates with existing cross-reference system
- [ ] Credit Orville James Nave as the original compiler

### Audio Read-Along (Browser TTS) — Zero Cost
- [ ] Use `window.speechSynthesis` API (zero server cost, runs entirely client-side)
- [ ] Play button on passages — verses highlight as they're read aloud
- [ ] Adjustable speed, voice selection (OS/browser-dependent voices)
- [ ] Pairs perfectly with immersive/distraction-free mode
- [ ] No API costs — uses built-in browser text-to-speech engine
- [ ] Quality varies: iOS has excellent voices, Android decent, Chrome desktop good

### Export/Print Study Sessions
- [ ] Export notes + highlighted verses + commentary as PDF
- [ ] Clean formatting for sermon prep handouts
- [ ] Print-friendly stylesheet
- [ ] Depends on: Sermon Outline Builder for best results

### AI Study Assistant (Claude API)
- [ ] Ask questions about passages ("What does this Greek word mean in context?")
- [ ] Generate study questions for small groups
- [ ] Explain difficult texts with scholarly context
- [ ] Summarize commentary across sources
- [ ] Uses Claude API — consider usage limits/costs

### Study Group Sync
- [ ] Share a "study space" with small group members
- [ ] See each other's highlights/notes in real-time
- [ ] Supabase real-time for live sync
- [ ] Privacy controls — choose what to share

## User Feedback (Feb 2026 - from educated friend / Bible scholar)

### Critical: Original Language Source Text Accuracy
The interlinear/original language toggle currently shows the same Greek source text regardless of
which translation the user is reading. This is **misleading** because different translations use
different source texts:
- **KJV** → Textus Receptus (TR, Scrivener 1894)
- **WEB** → Majority Text
- **BSB** → Critical Text (SBLGNT for Greek, WLCM for Hebrew)

**Why this matters:** When a user reads the WEB or BSB and clicks "original language," they may see
Textus Receptus text, which is NOT the source their translation used. This reinforces the common
(incorrect) KJV-only argument that modern translations "removed" text. In reality, the extra text
in the TR (e.g., the Johannine Comma in 1 John 5:7-8) was most likely added later and corrected
in newer critical editions.

**Example:** 1 John 5:7 — KJV includes "the Father, the Word, and the Holy Ghost: and these three
are one" (from TR). Modern translations (NIV, NASB, BSB, WEB) correctly omit this because it's
not found in the earliest manuscripts.

**Current status:**
- BSB Hebrew mapping appears correct (uses WLCM)
- BSB/WEB Greek mapping appears to still show Textus Receptus in some cases
- The STEPBible TAGNT data DOES include variant markers (NKO system) showing which editions contain
  each word — we could potentially leverage this to show the correct source text per translation

**Recommendation from friend:** Don't try to solve this all at once. This is literally a lifetime
of scholarly work. Options:
1. Label the source text clearly (e.g., "Shown: SBLGNT" or "Shown: Textus Receptus")
2. Find existing translation→source mappings that scholars have already done


### Bug: Original Language Missing for Some Books/Chapters
- Reported: Original language not available at all for Psalms
- Reported: Toggle button not appearing in Genesis chapter 4
- Sporadic issues in Genesis 23-25 (worked later — may be data loading race condition)
- Need to audit interlinear data coverage across all 66 books

### Attribution: Share Jesus Without Fear
- Need to credit **William Fay** as the creator of the "Share Jesus Without Fear" method
- The current Share Jesus modal uses his 5 questions + 7 verses format

### Verse Sharing Feature Request
- Users want to select verses and share them:
  - As text (copy/paste formatted)
  - Overlaid on a pretty background image (like Other app's verse images)
  - Direct share to social media / messaging apps

### Offline Caching Bug
- Users report downloading a Bible version, getting success feedback, but:
  - Data disappears on page refresh
  - Going offline shows no cached content
- Root cause likely: `loadPassage()` doesn't fall back to IndexedDB when fetch fails

### Tablet Sidebar
- On tablets (768px-1024px), the resources sidebar takes up too much space
- Need a way to collapse/hide the sidebar on tablet-sized screens

---

Last updated: 2026-02-05
