# Reference Autocomplete & Verse Highlighting Design

## Overview

Two UX improvements to the Bible reference input:
1. **Autocomplete** - Type "Gen" → suggests "Genesis"
2. **Chapter context with verse highlighting** - "Genesis 1:2" shows full chapter with verse 2 highlighted

## Feature 1: Reference Autocomplete

### Behavior
- User types in reference input → dropdown shows matching books
- Case-insensitive prefix matching (e.g., "gen" matches "Genesis")
- Handles numbered books (e.g., "1 c" matches "1 Chronicles", "1 Corinthians")
- Click or Tab/Enter to select suggestion
- After book selected, user continues typing chapter:verse

### Implementation
- Frontend only (no API needed - fixed 66 book list)
- Add `bookSuggestions` array and `showSuggestions` boolean to app state
- Add `BIBLE_BOOKS` constant with all book names
- Filter on input change, show dropdown when matches exist
- Keyboard navigation: Arrow keys to select, Enter/Tab to confirm

## Feature 2: Chapter Context with Verse Highlighting

### Behavior
- "Genesis 1:2" loads full chapter 1, highlights verse 2
- "Genesis 1:2-5" loads full chapter 1, highlights verses 2-5
- "Genesis 1" loads chapter with no highlighting (current behavior)
- Auto-scroll to first highlighted verse

### Implementation

**Backend changes:**
- Modify `/api/passage/{reference}` to always return full chapter
- Add `highlighted_verses` array to response (empty if no specific verse requested)

**Frontend changes:**
- Track `highlightedVerses` array in state
- Add `.verse-highlighted` CSS class
- Auto-scroll to first highlighted verse after render

## Files to Modify

1. `backend/main.py` - Update `get_passage()` to return full chapter + highlighted_verses
2. `frontend/static/js/app.js` - Add autocomplete logic and highlight handling
3. `frontend/index.html` - Add autocomplete dropdown markup
4. `frontend/static/css/style.css` - Add highlight and dropdown styles
