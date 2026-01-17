# BibleMVP - TODO

## Current Status

**Working:**
- [x] Bible text (61,303 verses - WEB + KJV)
- [x] Search autocomplete for book names
- [x] Chapter context with verse highlighting
- [x] Prev/next chapter and verse navigation
- [x] Clickable verse boxes for commentary
- [x] Cross-references (41,649 entries) with hover previews
- [x] Commentary display (4,124 entries - Matthew Henry, all 66 books)
- [x] Dark mode
- [x] Notes (localStorage)
- [x] Book-only reference defaults to chapter 1
- [x] Hebrew interlinear for entire OT (304,400 words)
- [x] Greek interlinear for entire NT (122,286 words)
- [x] Word click shows Greek/Hebrew details with Strong's definitions
- [x] Loading states & empty state messaging
- [x] Mobile touch support for word study
- [x] "Original Language" toggle in header (always visible)
- [x] Expandable word occurrence list ("and xxx more" clickable)
- [x] PWA manifest for installability
- [x] Service worker for offline caching
- [x] Book/chapter picker dropdown
- [x] Mobile-optimized header with hamburger menu
- [x] Resource tab indicators (shows when commentary/notes/cross-refs available)
- [x] Clickable Bible references in commentary (56,228 links auto-parsed)

## High Priority

### Data Import
- [x] Import remaining Matthew Henry commentary (all 66 books - DONE)
- [x] Import Strong's lexicon for word studies (DONE)
- [ ] Add second commentary source (John Gill or Adam Clarke)

### UI/UX
- [ ] **Draggable/resizable panels** - VSCode-style layout where Word details, Notes, Commentary, Cross-refs can all be visible simultaneously and rearranged. Consider using Golden Layout or split.js library.

### Core Features (from spec)
- [x] Interlinear data import (OpenGNT, OpenHebrewBible) - DONE for all 66 books
- [x] Word click shows Greek/Hebrew details - DONE
- [x] Service worker + offline caching - DONE
- [x] PWA manifest + install prompt - DONE

## Medium Priority

### Search Improvements
- [ ] Better search result snippets
- [ ] Search within current book/chapter

### Notes System
- [ ] Migrate from localStorage to IndexedDB
- [ ] Note tags/categories
- [ ] Highlight colors
- [ ] Export notes

### Navigation
- [x] Book/chapter picker dropdown - DONE
- [ ] Reading history
- [ ] Bookmarks

## Lower Priority

### Content
- [ ] Spurgeon Morning/Evening devotionals
- [ ] Additional translations (ASV already in dropdown but may need import)

### Polish
- [ ] Keyboard shortcuts
- [ ] Print-friendly styles
- [ ] Share verse functionality

## Technical Debt
- [ ] Add tests
- [ ] Error handling improvements
- [x] Loading states/skeletons - DONE

## Word-by-Word Reorganization (Original-Language Anchoring)

**Goal:** Shift core data model to treat words as rich objects anchored to original Greek/Hebrew (lemmas + Strong's/morphology) instead of English-only positions. This enables accurate multi-translation support, word studies, pronoun/entity resolution, and deep features without breaking on translation variances.

### High Priority (Foundation for Word-Level Features)
- [ ] Research & select primary data sources for originals:
  - NT Greek: MorphGNT or OpenGNT (SBLGNT/NA28 with Strong's + morphology)
  - OT Hebrew: Open Scriptures Hebrew Bible (OSHB) or Westminster Leningrad Codex tagged (Strong's + morphology)
  - Strong's lexicon (Greek & Hebrew definitions) – public domain XML/JSON imports
- [ ] Design & create new SQLite tables for word-level data:
  - `original_words` (id, book, chapter, verse, word_seq, language, text, lemma, strongs, morphology, gloss)
  - `strongs_lexicon` (strongs_id TEXT PRIMARY KEY, language, lemma, definition, pronunciation)
  - `word_alignments` (original_word_id, translation TEXT, verse_ref TEXT, word_index INT, text) – for mapping English words to originals
  - Add indexes: ON original_words(verse_ref), (lemma), (strongs)
- [ ] Write Python import script for NT Greek interlinear (start with Gospel of John for prototyping):
  - Parse MorphGNT/OpenGNT data → populate `original_words` & `strongs_lexicon`
  - Limit to 1-2 books initially to test performance
- [ ] Prototype word click handler:
  - On frontend: Click English word → query alignments → fetch original details + Strong's definition
  - Display in side panel (leverage draggable panels when ready)

### Medium Priority (Integration & Expansion)
- [ ] Add OT Hebrew word-level import (modular, user-downloadable pack)
- [ ] Implement basic word study view:
  - Search by lemma/Strong's → list all occurrences across books with context snippets
  - Show translation variants (e.g., "love" → agapē in different English renderings)
- [ ] Prototype pronoun/entity resolution (start simple):
  - Add optional `antecedent_id` field to `original_words` for pronouns
  - Manual tagging for key ambiguous cases (e.g., "he" in John 1 referring to John the Baptist)
  - Future: Integrate lightweight rule-based or LLM-assisted chains
- [ ] Performance & storage audit:
  - Benchmark chapter load with word data (target <200ms)
  - Estimate full NT Greek + Strong's size (~30-60 MB?) → plan modular downloads
  - Test on low-end devices (SQLite + FTS5 should handle it well)

### Lower Priority / Future
- [ ] Full multi-translation alignments (KJV/WEB/NIV/ESV → originals)
- [ ] Advanced word features: Morphology breakdown, usage stats, lexicon popups
- [ ] User-contributed word notes/tags linked to original_word_id

**Notes on this epic:**
- Anchor to originals (lemma + strongs + verse context) as primary key for stability across translations.
- Keep verse-level text as-is for quick reading; word-level is optional/on-demand.
- Sources: MorphGNT (GitHub), Open Scriptures Hebrew Bible, public-domain Strong's.
- This ties directly into interlinear import (already high-priority) and commentary (verse-level is fine, link to words optionally).

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

Last updated: 2026-01-17
