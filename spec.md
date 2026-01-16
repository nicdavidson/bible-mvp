# BibleMVP

**Working title for a free, open-source Bible study platform.**

## The Problem

Logos Bible Software costs $500-$2000+ and locks churches into expensive subscriptions. Free alternatives (e-Sword, YouVersion, BibleGateway) are either:
- Desktop-only and dated (e-Sword)
- Read-only with no real study tools (YouVersion)
- Online-only with no offline capability (BibleGateway)

None of them do the one thing that makes Logos valuable: **cross-resource linking**. The ability to click a word and instantly see lexicon entries, commentary notes, cross-references, and your own annotations—all connected.

## The Goal

Build a free Bible study tool that's actually useful for sermon prep and deep study—not just another Bible reader with search.

**Target user:** A pastor preparing Sunday's sermon, or a small group leader doing word studies. Someone who would benefit from Logos but can't justify the cost.

**Success criteria:** My pastor uses this instead of Logos for weekly sermon prep.

## Core Value Proposition

**One workspace, everything linked.**

When you open Romans 3:25:
- See the verse in your preferred translation
- Click any word → Greek/Hebrew, parsing, definition, everywhere else it appears
- Commentary notes from multiple sources in a sidebar (not separate tabs)
- Your personal notes attached to this verse from previous studies
- Cross-references to related passages

This is what Logos does well. This is what free tools don't do at all.

## Design Principles

1. **Offline-first** — Core content lives locally. Internet optional after initial load.
2. **Link everything** — Notes, highlights, bookmarks connect to verses/words. Search spans all content.
3. **Fast and simple** — No bloat. Opens instantly. Works on old laptops and phones.
4. **Privacy by default** — No accounts required. No tracking. Your data stays yours.
5. **Free forever** — MIT licensed. No paywalls. Donations welcome but never required.

---

## MVP Features (Phase 1)

The minimum to be useful for actual sermon prep.

### 1. Unified Passage Workspace

The core interface. Enter a reference, get everything in one view:

```
┌─────────────────────────────────────────────────────────────┐
│  [Romans 3:25 ▼]                            [KJV ▼] [⚙️]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Bible Text                    │  Resources                 │
│  ─────────────                 │  ─────────                 │
│  25 Whom God hath set forth    │  ▼ Matthew Henry           │
│  to be a propitiation through  │    "Justification is the   │
│  faith in his blood...         │    great privilege of      │
│                                │    those who believe..."   │
│  [propitiation] ← clickable    │                            │
│                                │  ▼ Your Notes              │
│                                │    "Key verse for atonement│
│                                │    theology - revisit"     │
│                                │                            │
│                                │  ▼ Cross-References        │
│                                │    • 1 John 2:2            │
│                                │    • 1 John 4:10           │
│                                │    • Heb 9:5 (mercy seat)  │
├─────────────────────────────────────────────────────────────┤
│  Word Details (on click)                                    │
│  ─────────────────────                                      │
│  propitiation (ἱλαστήριον, hilastērion)                    │
│  Strong's G2435 | Noun, Accusative, Singular, Neuter       │
│  Definition: an expiatory sacrifice; the mercy seat        │
│  Appears 2x in NT: Romans 3:25, Hebrews 9:5                │
└─────────────────────────────────────────────────────────────┘
```

### 2. Greek/Hebrew Word Tools (Without Requiring Seminary)

Click any word in the text:
- See original language word + transliteration
- Grammatical parsing (tense, voice, mood, case, etc.)
- Short definition from Strong's/Thayer
- List of every occurrence in Scripture (clickable)
- Reverse interlinear: English aligned with Greek/Hebrew

This is the #1 feature that makes Logos worth money. We need to nail this.

### 3. Commentary Integration

Not just "here's a commentary." Commentary that's **wired to the text**:
- Select a verse → see what commentaries say about that verse
- Commentary panel stays synced as you navigate
- Start with public domain: Matthew Henry, Spurgeon, Gill, Calvin
- Searchable across all commentaries

### 4. Personal Notes & Annotations

- Highlight verses (multiple colors)
- Add notes to any verse (rich text)
- Notes persist and sync across sessions
- **Critical:** Notes are searchable alongside Bible text and commentaries
- Tag system for organizing (sermon series, topics, etc.)

### 5. Cross-Resource Search

One search box. Results from everywhere:
- Bible text (with FTS)
- Your notes
- Commentaries
- Original language words (search by Strong's number or Greek/Hebrew)

Example: Search "propitiation" → get Romans 3:25, 1 John 2:2, plus Matthew Henry's comments, plus your note from last month.

### 6. Daily Devotionals

Simple date-based devotional reader:
- Spurgeon's Morning & Evening (public domain)
- Shows today's reading by default
- Browse by date
- Can add notes to devotional entries

### 7. Dark Mode & Responsive Design

- Clean, readable typography (this is for reading long-form text)
- Dark mode toggle (essential for evening study)
- Works on desktop, tablet, and phone
- Keyboard navigation for power users

---

## Non-MVP (Later Phases)

Features that matter but aren't needed for initial usefulness.

### Phase 2: Reading Plans & Sharing
- Create custom reading plans
- Share reading plans with church members
- Track reading progress
- Pre-built plans (chronological, M'Cheyne, etc.)

### Phase 3: Deeper Language Tools
- Full lexicon entries (BDAG-style, from public domain sources)
- Word frequency analysis
- Hebrew/Greek sentence diagrams
- Morphology search (find all aorist passive verbs in Paul's letters)

### Phase 4: More Content
- Additional commentaries
- Systematic theology references
- Bible dictionaries and encyclopedias
- Maps and timelines

### Phase 5: Sync & Collaboration
- Optional account creation
- Sync notes/highlights across devices
- Share notes with study group
- Export sermon research

### Phase 6: Modern Translations
- NIV, ESV, NASB via official APIs (requires licensing agreements)
- Parallel translation view

### Phase 7: Mobile Apps
- Android app (Capacitor or TWA wrapper)
- iOS app (if demand exists)

---

## Tech Stack

### Frontend
- **Vanilla JavaScript** — No framework. Keep it simple and fast.
- **Alpine.js** — Lightweight reactivity where needed.
- **Tailwind CSS** — Utility-first styling.
- Static HTML files served directly.

### Backend
- **FastAPI (Python)** — Serves API endpoints and static files.
- **SQLite** — Single database file with all content.
- **SQLite FTS5** — Full-text search.

### Offline
- **Service Worker** — Cache static assets and Bible data.
- **IndexedDB** — Store user notes, highlights, bookmarks locally.
- Offline-first: works without internet after initial load.

### Deployment
- Vercel / Render / Railway (free tier)
- Static export option for self-hosting

---

## Data Architecture

### Core Entities

```
verses
├── book, chapter, verse
├── text (translation-specific)
├── translation_id
└── word_ids[] (links to interlinear)

words (interlinear data)
├── strong_number
├── original (Greek/Hebrew)
├── transliteration
├── parsing (morphology)
├── definition (short)
├── translation_id
└── position (word order)

commentary_entries
├── reference (book/chapter/verse or range)
├── source (matthew_henry, spurgeon, etc.)
├── content (HTML or Markdown)
└── searchable_text (FTS indexed)

user_notes
├── reference (verse or verse range)
├── content
├── tags[]
├── color (for highlights)
├── created_at, updated_at
└── [synced locally via IndexedDB]

cross_references
├── source_reference
├── target_reference
└── relationship_type

devotionals
├── date (month-day)
├── source (spurgeon_morning, spurgeon_evening)
├── title
├── content
└── scripture_refs[]
```

### Content Sources (Public Domain)

| Content | Source | Format |
|---------|--------|--------|
| Bible text (WEB, KJV) | seven1m/open-bibles | JSON/XML |
| Greek NT interlinear | OpenGNT | XML |
| Hebrew OT interlinear | OpenHebrewBible | XML |
| Strong's definitions | Public domain | Various |
| Matthew Henry Concise | CCEL | HTML |
| Spurgeon Treasury of David | CCEL | HTML |
| Gill's Exposition | CCEL | HTML |
| Spurgeon Morning/Evening | CCEL | HTML |
| Cross-references | Treasury of Scripture Knowledge | XML |

---

## API Design

### Core Endpoints

```
GET  /api/passage/{reference}
     → Returns verse(s) + interlinear data + cross-refs

GET  /api/passage/{reference}/commentary
     → Returns commentary entries for passage

GET  /api/search?q={query}&scope={bible|notes|commentary|all}
     → Full-text search across specified scope

GET  /api/word/{strong_number}
     → Lexicon entry + all occurrences

GET  /api/devotional/{date?}
     → Today's devotional (or specified date)

POST /api/notes
GET  /api/notes/{reference}
PUT  /api/notes/{id}
     → CRUD for user notes (initially local-only)
```

### Reference Format

Standard Bible reference parsing:
- `John 3:16` → single verse
- `John 3:16-18` → verse range
- `John 3` → full chapter
- `Rom 3:25` → abbreviations supported

---

## Development Phases

### Phase 1: Foundation (Current)
- [ ] Project structure (FastAPI + static frontend)
- [ ] SQLite schema + data import scripts
- [ ] WEB Bible text import
- [ ] Basic verse lookup API + UI
- [ ] Chapter navigation

### Phase 2: Core Study Features
- [ ] Interlinear data import (OpenGNT, OpenHebrewBible)
- [ ] Word click → Greek/Hebrew details
- [ ] Matthew Henry commentary import + display
- [ ] Unified passage workspace UI

### Phase 3: Personal Tools
- [ ] Notes system (IndexedDB)
- [ ] Highlights with colors
- [ ] Cross-resource search
- [ ] Bookmarks

### Phase 4: Polish & Offline
- [ ] Service worker + offline caching
- [ ] Dark mode
- [ ] Responsive mobile layout
- [ ] PWA manifest + install prompt

### Phase 5: Devotionals & Launch
- [ ] Spurgeon Morning/Evening import
- [ ] Devotional UI
- [ ] Deploy to production
- [ ] Pastor feedback session

---

## Success Metrics

**For MVP:**
1. Pastor can prepare a sermon without opening Logos
2. Word studies take <30 seconds to access Greek/Hebrew details
3. Works offline after first visit
4. Page loads in <2 seconds on average hardware

**Long-term:**
1. Used weekly by at least 5 people at church
2. Zero ongoing cost (free hosting tier sufficient)
3. Other churches asking to use it

---

## What This Is NOT

- Not a Bible reader app (YouVersion already exists)
- Not a devotional app (plenty of those)
- Not trying to replace Logos for seminary professors
- Not aiming for every feature—aiming for useful features done well

---

## License & Content Rights

**Code:** MIT License

**Content:** We must be careful here. Strategy:

### Safe to Use (Public Domain)
- **KJV** — Public domain worldwide
- **WEB (World English Bible)** — Explicitly public domain, no restrictions
- **ASV (1901)** — Public domain
- **Strong's Concordance** — Public domain (original 1890 work)
- **Matthew Henry Commentary** — Public domain (died 1714)
- **Spurgeon's works** — Public domain (died 1892)
- **John Gill's Exposition** — Public domain (died 1771)
- **Treasury of Scripture Knowledge** — Public domain (1836)

### Requires Licensing (DO NOT USE without agreement)
- **NIV** — Biblica copyright, strict licensing
- **ESV** — Crossway copyright, API available but terms apply
- **NASB** — Lockman Foundation copyright
- **NKJV** — Thomas Nelson copyright
- **Any modern commentary** — Assume copyrighted unless verified

### Gray Area (Verify Before Using)
- **OpenGNT / OpenHebrewBible** — Check specific licenses (likely CC or open)
- **CCEL exports** — Most are PD but verify each resource
- **BibleHub data** — Do NOT scrape; unclear licensing

### Our Approach
1. MVP uses only verified public domain content
2. Document the source and license for every piece of content we import
3. Keep a `LICENSES.md` file tracking all content rights
4. Modern translations only via official APIs with proper attribution

---

## Contributing

Currently a solo project for my local church. If this proves useful, may open to contributions later.

Questions? Feedback? This is being built to solve a real problem for real people—input welcome.
