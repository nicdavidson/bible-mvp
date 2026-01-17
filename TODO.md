# BibleMVP - TODO

## Current Status

**Working:**
- [x] Bible text (61,303 verses - WEB + KJV)
- [x] Search autocomplete for book names
- [x] Chapter context with verse highlighting
- [x] Prev/next chapter and verse navigation
- [x] Clickable verse boxes for commentary
- [x] Cross-references (41,649 entries) with hover previews
- [x] Commentary display (463 entries - Matthew Henry, 3 books)
- [x] Dark mode
- [x] Notes (localStorage)
- [x] Book-only reference defaults to chapter 1

## High Priority

### Data Import
- [ ] Import remaining Matthew Henry commentary (63 more books)
- [ ] Import Strong's lexicon for word studies
- [ ] Add second commentary source (John Gill or Adam Clarke)

### UI/UX
- [ ] **Draggable/resizable panels** - VSCode-style layout where Word details, Notes, Commentary, Cross-refs can all be visible simultaneously and rearranged. Consider using Golden Layout or split.js library.

### Core Features (from spec)
- [ ] Interlinear data import (OpenGNT, OpenHebrewBible)
- [ ] Word click shows Greek/Hebrew details (currently placeholder)
- [ ] Service worker + offline caching
- [ ] PWA manifest + install prompt

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
- [ ] Book/chapter picker dropdown
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
- [ ] Loading states/skeletons

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

---

Last updated: 2026-01-16
