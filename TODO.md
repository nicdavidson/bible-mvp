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

---

Last updated: 2026-01-16
