# Bible MVP — Full Code Review (2026-07-21)

Three-agent parallel review: backend (main.py/database.py), frontend JS (app.js + support files), CSS/HTML (style.css/index.html). All findings verified against the code and the live 385MB production database. No changes made — this is the findings doc.

**Headline numbers:**
- ~3,000–3,400 removable lines across the codebase (~12% of 27.7K)
- 20+ real bugs, several user-visible
- Perf wins that are one-liners (GZip) and structural (N+1 BFS queries, per-render note scans)

---

## PART 1 — BACKEND (main.py 2,393 lines, database.py, models.py)

### Architecture assessment

`main.py` mixes route handlers, a reference parser, book-name data tables, BFS graph algorithms, and seed-verse content data. Natural split: 4 routers (`passages`, `search`, `offline`, `crossref_map`/`topics`) plus `books.py` constants and a `refs.py` parser. The crossref-map BFS code alone is ~600 lines and duplicated internally. Realistic reduction: **500–650 lines (~25%)** from dedup + dead code, before any router split.

### Tier 1 — Code reduction / dead code / duplication

1. **`words` table is empty in production — two dead query paths.** Verified: `SELECT COUNT(*) FROM words` = 0.
   - `main.py:383-404` — Strong's-number branch of `/api/search` joins `words` → **always returns zero verse results** (also a bug: searching "H3068" gives lexicon info but no verses, even though `word_alignments` has 6,040 rows for it).
   - `main.py:592-607` — `/api/word` occurrence query on `words` always empty, falls through to the `word_alignments` fallback at 608-615 every time.
   - Fix: query `word_alignments` directly, delete the `words`-table paths (~45 lines), drop table/indexes from schema.

2. **Bidirectional cross-ref neighbor query duplicated 5×.** Identical `UNION ALL … GROUP BY … ORDER BY MAX(votes) DESC LIMIT ?` blocks at `main.py:1649-1664`, `1794-1809`, `1921-1936`, `2109-2125`, plus focus-books variant at `2086-2107`. Extract `_get_neighbors(conn, book, chapter, verse, limit, focus_list=None)`. ~80 lines.

3. **Two full BFS-to-seed implementations.** `find-path` mode inside `/api/crossref-map/christological` (`main.py:1603-1748`) and `/api/path-to-christ/{reference}` (`main.py:1845-2002`) are near-duplicate BFS to the same seed set with separate path reconstruction. One shared helper eliminates ~150 lines and the behavioral drift (see bug 5 below).

4. **`models.py` is 100% dead.** Nothing imports it (verified). Delete: 101 lines. Same for the `user_notes` table in `database.py:372-383` — the comment itself says notes live in IndexedDB.

5. **OT/NT book lists defined 3×, abbreviation maps 2×.** `OT_BOOKS`/`NT_BOOKS` at `main.py:336-353` and verbatim at `729-746`; canonical list a third time at `1006-1021`. `database.py:94-162` (`BOOK_ABBREVS`) duplicates `parse_reference`'s abbrevs at `main.py:939-1003`. The `books` table already stores this. ~90 lines.

6. **Strong's-number normalization CASE SQL pasted 5×.** `main.py:511-513`, `690-707` (twice in one query), `1132-1135`, `1252-1255`. Root cause: mixed `H0430`/`H430` formats in data (verified both exist). Best fix: one-time migration normalizing `word_alignments.strong_number` — deletes every CASE hack (~30 lines) and makes the lexicon JOIN sargable.

7. **Reading-plan loading duplicated.** `main.py:879-894` and `897-912` repeat sanitize/path/exists/load, including the magic `replace('chronological-year', 'chronological')` hack twice. Extract `_load_plan(plan_id)`: ~15 lines.

8. **Minor:** function-local `import re`/`import json` at `main.py:333, 401, 431, 790, 861, 880, 900`; dead `visited` set at `1785`; `get_speaker_verses` (`1086-1092`) selects `speaker` but returns only `row[0]`.

### Tier 2 — Bugs

1. **FTS search matches metadata columns — wrong results.** `verses_fts` indexes `book`, `chapter`, `verse` as regular FTS columns (`database.py:245-252`); `/api/search` does bare `MATCH ?` (`main.py:461-468`). Verified live: `MATCH 'john'` → **3,098 rows** vs `MATCH 'text:john'` → **396 rows**. Searching "john" returns every verse in the books of John. Same flaw in `commentary_fts`. Fix: prefix queries with `text:` (one line), or rebuild FTS with `book UNINDEXED`.

2. **Rate-limit bypass via spoofable X-Forwarded-For.** `main.py:49-54` keys on `forwarded.split(",")[0]` — leftmost XFF is client-controlled; Fly appends the real IP at the end. Fix: take last entry, or use `Fly-Client-IP`.

3. **Async handlers doing blocking SQLite.** Every endpoint is `async def` running sync `sqlite3` — one slow request (offline Psalms, deep BFS) freezes the event loop for everyone. Fix: plain `def` → FastAPI threadpool. Mechanical, biggest single reliability win.

4. **Devotional caching serves stale "today".** `/api/devotional` no-date resolves date server-side (`main.py:792-795`, UTC) but gets `Cache-Control: max-age=3600` (`main.py:75, 108`). Cache key has no date → up to an hour into a new day everyone gets yesterday's devotional; "today" is UTC regardless of user TZ. Fix: only cache when explicit `date` param present.

5. **BFS path reconstruction can produce a false path.** In find-path mode, `parent[tgt_key]` only recorded when `tgt_key not in nodes` (`main.py:1677-1684`); if seed first reached as an already-known node, the loop silently emits `[seed, start]` as a "path" even when not adjacent. The `/api/path-to-christ` variant records parents defensively (`1945-1946`) — the two copies have drifted. Unify (Tier-1 #3).

6. **Verse-range edge cases in `parse_reference`.** `main.py:1048`: reversed ranges ("John 3:18-16") accepted, silently return nothing; "Ps 119:1-999" collides with the `verse_end == 999` full-chapter sentinel at `258`; "1john 3" (no space) 404s via `.title()` at `1043`. Fix: swap reversed bounds, use `None` sentinel, add `1john`-style keys.

7. **Commentary-link migration mis-links "2 Peter" and mutates data.** `database.py:161` maps bare `'Peter': '1 Peter'`; `'2 Peter'` isn't in the map — commentary text "2 Peter 1:4" gets linked to 1 Peter. Migration permanently rewrites `content` with presentation HTML at startup; corrupted links can't regenerate without reimport. Fix map; longer-term, decorate links at render time.

8. **Strong's search returns zero verses** — see Tier-1 #1; user-visible.

### Tier 3 — Performance

1. **No GZip middleware.** `/api/offline/lexicon` (`main.py:1183-1198`) and `/api/offline/book` ship multi-MB JSON that compresses 5–8×. One line: `app.add_middleware(GZipMiddleware, minimum_size=1000)`. Highest ROI in the file.
2. **`_enrich_nodes` is a textbook N+1.** `main.py:1466-1499`: one `SELECT` per node — up to 500 queries per crossref-map request, inside a blocking async handler. Batch with `WHERE (book, chapter, verse) IN (...)`. Same in `/api/crossref-map/presets` (`1546-1554`, ~46 q/req) and `get_topic` previews (`2337-2349`).
3. **BFS: one SQL round-trip per dequeued node.** `main.py:2068-2153` and three other loops: up to 500 queries/request. Batch the frontier per depth level.
4. **`/api/offline/book` runs 5 queries × chapters.** `main.py:1232-1287`: Psalms = ~750 queries. Run 5 whole-book queries, group in Python.
5. **Unbounded `/api/word` payloads.** `main.py:607-615`: H3068 = 6,040 occurrences, all returned. Paginate or cap with a `total`.
6. **Connection settings.** `database.py:17-21`: fresh default-mode connection per request for read-only workload. Use `mode=ro` URI + `PRAGMA mmap_size`/`cache_size`.

Indexes are in good shape (verified); `idx_crossref_target` created at startup (`main.py:32-36`) belongs in the schema.

### Tests

`tests/test_api.py` is smoke-level. It would not catch a single Tier-2 bug: no search-correctness assertions, no Strong's verse assertions, and `test_search_with_scope` (line 139-141) passes `scope=Genesis` which the handler doesn't recognize (valid form is `book:Genesis`) — test passes while exercising nothing.

---

## PART 2 — FRONTEND JS (app.js 6,128 lines, supabase-client.js, offline-storage.js, sw.js)

### Overall assessment

`app.js` is one giant Alpine component: ~120 state properties, ~200 methods (reader, search, auth, notes, tags, highlights, TTS, plans, offline, memory, sharing, feedback). Workable for Alpine (one instance), but past the ceiling. Cheap split, no build step: feature modules (`tts.js`, `plans.js`, `offline-downloads.js`, `notes-tags.js`, `share.js`, `memory.js`) each exporting a plain object, composed with `return { ...coreState, ...ttsModule, ... }`. The map page already uses this pattern.

Realistic reduction: **~700–900 lines (12–15%)** — ~450 confirmed dead, ~250–400 dedup.

### Code reduction

- **R1. Dead: old download system.** `app.js:458-461` (`downloadOptions`), `4402-4430` (`startDownload`), `4456-4507` (`downloadBook`). Zero template references; superseded by `downloadSelections`/`startOfflineDownload` (4547). ~110 lines.
- **R2. Dead: devotional reader.** `app.js:420-424`, `4819-4867` (`loadDevotional` etc.). No template references. ~55 lines. The "kept for offline downloads" comment is wrong — downloads use `downloadDevotionals()`.
- **R3. Dead misc:** `getGroupedCommentary` (1873-1883), `getCommentaryPreview` (1947-1959), `saveDarkMode` (2626-2630), `canUseNetwork` (4813-4815), `getCurrentVerse` (1634-1636, dup of `getNoteStartVerse` 3562). ~40 lines.
- **R4. Dead offline-storage.js + product gap:** `getWordAlignment` (152-162), `hasChapterVerses`, `hasChapterAlignments`, `getLexiconEntry` (187-197), `hasLexicon`, `clearStore` never called. **The downloadable lexicon is write-only** — `saveLexiconEntries` stores it, nothing reads it; word lookups always hit the network. Same for alignments (`saveChapterAlignments` called at 4482/4628, `getWordAlignment` never reads). **Offline word study silently doesn't work.** Either wire the read path into the word-click fallback or drop the download feature.
- **R5. Dead supabase-client.js exports:** `syncLocalNotesToSupabase` (148-178), `fetchNoteTagIds` (315-337), `setNoteTagIds` (372-405), `fetchPlanProgress` (479-491), `fetchUserBugReports` (687-699). ~120 lines.
- **R6. Book-abbreviation tables ×4.** `BOOK_ABBREVS` (app.js:50-123), `bookMap` in `formatTopicEntry` (1483-1500), the 120-line `normalizeBookName` map (5321-5442), reversed map in map-data.js:5-25. One canonical table + normalize helper: ~200 lines, ends drift (`normalizeBookName` handles trailing periods, `BOOK_ABBREVS` doesn't).
- **R7. Duplicate cross-ref loaders.** `loadCrossRefsForVerse` (1697-1724) and `loadCrossRefs` (2160-2190) are the same function. Collapse to `loadCrossRefs(ref, verseNum?)`. ~30 lines.
- **R8. Fetch-then-cache-fallback hand-rolled 6×.** `_loadFromCache` (1161), `loadCommentary` (1320), `loadCrossRefsForVerse`, `loadCrossRefs`, `loadInterlinearData` (2274). One `fetchOrCache(url, cacheGetter, mapFn)` removes ~80 lines and fixes an inconsistency: `loadCrossRefs` does NOT check `forcedOffline` (the monkey-patched fetch in index.html:2741 saves it by accident).
- **R9. Plan-start triplication.** `confirmStartPlan` (5031), `confirmStartPlanWithCatchUp` (5103), `startPlan` (5156) → one `startPlan(planId, startDate, catchUpDays=[])`. ~60 lines.
- **R10. Supabase-or-localStorage branching ~10×.** Every notes/tags CRUD repeats `if (this.authUser && window.SupabaseAuth) {...} else {...}`. Small storage adapter removes ~100 lines and a bug class (`saveNote` 3661-3679 and `quickHighlight` 5818-5835 duplicate the identical create-note block).
- **R11. SW double-caching.** SW `CACHE_DATA` → index.html handler (2779-2867) re-implements `_autoCacheCurrentChapter` (app.js:4365). Two independent writers to the same IndexedDB stores, one partially broken (B1). Delete the SW postMessage machinery (`notifyClientToCache`, sw.js:183-234 + handler). ~150 lines.

### Bugs

- **B1 HIGH — Alpine v2 API in SW cache handler; silent no-op.** `index.html:2864`: `.__x?.$data` is Alpine v2; page loads v3 → always undefined. `updateOfflineStats()` never fires from SW caching. Fix: `Alpine.$data(...)` — or just delete the path (R11).
- **B2 HIGH — cache-first path drops verse highlighting.** `app.js:1063-1085`: cache hit sets `highlightedVerses = []` and `currentReference = "Book Ch"` regardless of input. Cross-ref click "John 3:16" on a cached chapter → no highlight, no scroll. Fix: parse verse from `referenceInput` (regex exists at 1046) in the cached branch.
- **B3 HIGH — shared range links 404.** `getShareLink` (4131-4137) makes `/{Book}/{ch}/{first}-{last}`, but `parsePathReference` (791-802) only matches `(\d+)` → recipient lands on blank welcome screen. Fix: `(\d+)(?:-(\d+))?`.
- **B4 MED — `_backgroundRefresh` race.** `app.js:1208-1232`: after cache hit, resolves later and unconditionally writes `crossRefs`/`speakerVerses` — wrong chapter's data after fast navigation. No loader carries a request-generation token; `if (this.loading) return` guards (1597/1616) are defeated by the cache path setting `loading=false` early (1073). Fix: capture ref, bail if current book/chapter changed; ideally a generation token for all loaders.
- **B5 MED — bare `JSON.parse` at construction can brick the app.** `app.js:495, 498, 502`: `readingHistory`, `bookmarks`, `memoryVerses` parsed with no try/catch in the data literal. One corrupt value → Alpine init throws → blank app until storage cleared. Fix: 3-line `safeParse(key, fallback)`.
- **B6 MED — offline-storage awaits non-promises.** `offline-storage.js:89-98` (also 135, 176, 211, 257, 304): `await store.put(...)` — IDBRequest isn't thenable; per-put errors (QuotaExceeded) never observed. `setMeta` marks `cached: true` even if the verses transaction aborts. Fix: wrap in transaction `oncomplete/onerror` promise; set meta in same transaction.
- **B7 MED — hover preview no cancellation.** `previewVerse` (2231-2263): debounced but in-flight fetches not aborted; last to *resolve* wins — tooltip can show wrong verse or appear after `hidePreview`. Fix: AbortController/token.
- **B8 LOW — SW static cache unbounded.** sw.js:94-120: every navigation URL (`/John/3`… up to 1,189 chapter URLs × ~100KB shell) cached individually; `limitCacheSize` only runs on CONTENT_CACHE (153). Fix: serve cached `'/'` shell for `request.mode === 'navigate'`.
- **B9 LOW — SW revalidation not in `waitUntil`.** sw.js:103-108: background `fetch().then(cache.put)` can be killed before completing.
- **B10 LOW — global keydown fires under modals.** `setupKeyboardShortcuts` (700-788): with modals open, `d` cycles theme, `f` fullscreens, arrows navigate behind the modal. Add `anyModalOpen()` early return.
- **B11 LOW — toast id collision.** `showToast` (4348): `Date.now()` id; same-ms toasts share ids, cleanup removes both. Incrementing counter. (Also `memorizeSelected` at 2054 should toast once, not per verse.)
- **B12 LOW — `_sheetDragging` never resets on `touchcancel`.** app.js:952-1002: OS-interrupted gesture leaves drag state + `transition:none` stuck. Bind `touchcancel`.

### Performance

- **P1 HIGH — O(verses × notes) per render.** index.html:469-517 calls `getVerseHighlightColor` 3-4×/verse and `getVerseTagColors` (app.js:3927, scans ALL notes+tags) per verse in `x-for` over up to 176 verses. Any state change (toast, tab switch, TTS advance) → thousands of scans. Fix: precompute `verseColorMap` on notes/chapter change. Same for `getRelevantNotes()` — called 10+ places per render; cache it.
- **P2 HIGH — verse tap refetches full-chapter commentary.** `selectVerse` (2153-2154) awaits `loadCrossRefs()` then `loadCommentary()` per tap; commentary is chapter-scoped and already loaded by `loadPassage` (1120). Drop the call; unserialize the rest.
- **P3 MED — interlinear payload fetched even when feature off.** `loadPassage` → `loadInterlinearData` (1123-1127) unconditional; ~50KB/chapter, default-off feature. Fetch lazily on first toggle.
- **P4 MED — plan-day loading fully serial.** `startPlanReading` (5489-5670): 4-chapter day = up to 12 serial round-trips. `Promise.all` passages (ordered concat) + parallel commentary/interlinear: 3–5× wall-clock win.
- **P5 LOW — `formatVerseText` per render via `x-html`.** index.html:487. Compute once when `verses` assigned (store `verse.html`).
- **P6 LOW — tag toggle = 3 round-trips.** supabase-client.js:268-313: ownership-verify select + getUser + mutation; RLS already enforces ownership. `saveNote` loops `toggleNoteTag` per tag → 3N requests; batch.
- **P7 LOW — SW logs every request.** sw.js:81, 147, 187, 219. Gate behind debug flag.

Map-page files (force-graph.js, map-app.js, map-data.js) are in good shape; only note: window-level mousemove/mouseup listeners (force-graph.js:81-82) never detach — harmless while the map page owns the graph.

---

## PART 3 — CSS/HTML (style.css 9,363 lines, index.html 2,875 lines, map.*)

Method: CSS parsed programmatically (1,409 rules), every class cross-referenced against HTML + JS (including dynamically-built classes), rule bodies hashed for exact dupes, Jaccard-clustered near-dupes. Numbers measured, not guessed.

### Code reduction (ranked by savings)

**1.1 Dead CSS — ~630 lines, zero risk.** 75 rules whose classes appear nowhere:

| Lines | What | ~Lines |
|---|---|---|
| 4449–4552 | Old offline-manager UI (`.btn-download`, `.cached-chapter-*`) | 133 |
| 4705–4786 | Entire "DEVOTIONAL STYLES" section (no markup renders them) | 107 |
| 2924–2993 + 3350–3364 | `.help-modal`/`.shortcuts-grid` (superseded by guide modal) | 84 |
| 4390–4410 + 4658–4674 + 4045–4071 | `.offline-option-*`, `.stat-card`, `.connection-status` | 66 |
| 185–202 + 3025–3037 | `.logo*` (defined twice, used zero times) | 41 |
| 8720–8742, 9274–9296, 8637–8649 | `.btn-highlight-toggle`, `.btn-memorize`, `.btn-bookmark` (replaced by floating action bar) | 70 |
| Scattered | `.toggle-checkbox`, `.verse-link-btn`, `.btn-search`, `.btn-copy`, `.commentary-chapter-ref`, `.commentary-preview`, etc. | ~130 |

**1.2 Button family consolidation — ~400–450 lines.** 154 `.btn-*` rule blocks (~998 lines, 76 classes) when `.btn-primary/.btn-secondary/.btn-icon/.btn-danger` already exist. The identical 3-prop "active" state is copy-pasted **16×** (lines 427, 521, 659, 732, 852, 1082, 1300, 2030, 2242, 4848, 5476, 6243, 7135, 7913, 8309, 8314); a 2-prop hover 8×; a focus ring 5×. Fix: `.btn-solid`/`.btn-ghost`/`.btn-danger-text` + shared `.is-active` + global `:focus-visible`.

**1.3 Theme-override scatter — ~200–250 lines.** 138 lines of `.dark` + 282 of `.parchment` overrides re-tinting identical surfaces per component instead of extending the custom-property system (lines 4–90). E.g., 8678–8716 and 9309–9356 apply the same background/border pair to six components — collapses to one `--color-inset-surface`.

**1.4 Fullscreen-overlay pattern — ~150 lines.** `.single-verse-overlay` (6839–7048), `.plan-reading-overlay` (5630–5765), `.immersive-overlay` (7592–7895) each redefine the same fixed-overlay + header + exit + footer. One `.fullscreen-overlay` family.

**1.5 Patch-over duplicate selectors — ~30 lines + correctness.** `.header-center` (204/338), `.verse-box` (762/929), `.panel-body` (706/8217), `.search-result` (2740/8222), `.crossref-item` (2288/8227), `.immersive-controls-bottom` (7786/7850), `.search-result.selected` twice back-to-back (2748/2752). The "SELECTION & UTILITY POLISH" section (8200–8240) exists purely to patch rules defined thousands of lines earlier.

**1.6 Media-query fragmentation.** Nine separate `@media (max-width: 768px)` blocks (4658, 5766, 6140, 6348, 6576, 6998, 7057, 7571, 8003).

**Realistic CSS shrink: ~1,500–1,900 lines (16–20%) mechanical/low-risk; ~2,400 with the shared-component refactor (touches HTML, needs visual regression checking).**

### Bugs

- **2.1 Dead `[data-theme]` selectors — Topics theming broken.** Themes are body classes (index.html:20), never a `data-theme` attribute — all six rules at 8458–8477 never match. Symptom: `<mark>` in topic search snippets is browser-default bright yellow with dark text on dark background. One-line fixes: `[data-theme="dark"]` → `.dark`.
- **2.2 Modal accessibility — systemic.** 12 `modal-overlay` instances: zero `role="dialog"`/`aria-modal`/focus trapping. 3 `aria-label`s in the whole file. Every "×" close button unlabeled. Escape only closes 3 of 12 modals (app.js:745-753). No `prefers-reduced-motion` despite 6 `@keyframes` + smooth scroll.
- **2.3 z-index conflicts.** `.modal-overlay` z=200 (2568) vs side menu z=999/1000 (6368/6380): About/Guide/Feedback/Reading-Plan modals launched FROM the side menu render UNDER it. `.verse-preview-tooltip` z=300 above modals. Four systems tie at z=1000 (toasts + 3 overlays) — stacking is DOM-order luck. Fix: `--z-*` ladder.
- **2.4 Mobile viewport.** `100vh` on fixed overlays (6377, 5771, 7671), no `100dvh` fallback → iOS Safari URL-bar clipping. No `env(safe-area-inset-*)`; viewport meta lacks `viewport-fit=cover` despite standalone PWA mode → notch overlap.
- **2.5 PWA/manifest.** `background_color: #ffffff` → white flash for dark users; static `theme-color` with no dark media variant; SVG-only icon — iOS ignores SVG `apple-touch-icon` (index.html:14) → generic screenshot icon on installs; no `maskable` for Android.
- **2.6 Breakpoint inconsistency.** Core mobile layout at 600px (3014–3426), nine feature sections at 768px, one-offs at 380/480/900. 600–768px widths get feature-mobile styles without core mobile layout.
- **2.7 map.html divergence.** Hardcoded dark-only palette, ignores app theme; no manifest/icon links; 101 inline `style=""` attributes in 548 lines.

### Structure (index.html)

1. **Two parallel book/chapter pickers** (header 171–233 vs home 337–404): same data, same genre coloring, different class families + duplicated CSS. Merge with a `mode` flag: ~50 HTML + ~80–100 CSS lines.
2. **OT/NT template duplication** inside each picker (189/197, 391/399): loop over `[['Old Testament', otBooks], ['New Testament', ntBooks]]`.
3. **Modal scaffolding is actually well-factored** — win there is a11y, not lines.
4. **Inline bootstrap script** (2740+, SW registration/messaging) belongs in app.js: ~130 lines out of HTML.

---

## FEATURE SUGGESTIONS (after reduction + bugs)

The reviews surfaced features that are already half-built or newly cheap:

1. **Finish offline word study** — data is already downloaded; wire `getLexiconEntry`/`getWordAlignment` into the word-click fallback. Turns a dead feature into a real one.
2. **Fix + polish verse sharing** — B3 fix makes range links work; the TODO's user-requested "share as image/social" builds on that.
3. **KJV word alignments** — TODO item, data available (kaiserlik/kjv), and the alignment pipeline already exists.
4. **Audio read-along** (browser TTS) — TODO item, zero server cost; TTS state already exists in app.js.
5. **Word Study Dashboard** — TODO item; data (426K alignments + lexicon) already imported, backend endpoint additions are small once main.py is split.
6. **Modal a11y pass** — not a "feature" but user-facing quality: role/aria/focus/Escape-everywhere.

---

## ADDENDUM — Combined plan-reading mode: selection keyed by verse number (Captain-reported, root-caused 2026-07-21)

**Symptom:** in "Read All Together" plan mode, selecting a verse in one chapter selects the same verse number in every chapter of the day's reading.

**Root cause:** all per-verse UI state is keyed by verse *number* alone. In combined mode, `startPlanReading` (app.js:5497+) concatenates multiple chapters into one `this.verses` array (each verse tagged with `_book`/`_chapter` at ~5574), but the templates still test by bare number:

- `isVerseHighlighted(verse.verse)` / `highlightedVerses: [16]` — index.html:464, app.js:2099-2118. Verse 16 exists in every chapter → all light up.
- Same class of bug in every number-keyed feature in combined mode:
  - Note selection: `isVerseSelectedForNote(verse.verse)` (index.html:467)
  - Share selection: `shareSelectedVerses.includes(verse.verse)` (index.html:468)
  - Highlight color picker: `showHighlightPicker === verse.verse` (index.html:505) — opens the picker on every chapter's verse N
  - Color highlights: `getVerseHighlightColor(verse.verse)` (index.html:469/471/511/517) — looks up against `currentBook`/`currentChapter`, which in combined mode is whatever was last selected, so saved highlights paint the wrong chapters
- `selectVerse` (app.js:2097-2143) already receives `verseIdx` and correctly resolves `_book`/`_chapter` for the side panels — only the selection *state* ignores it. The multi-select add/remove branches (2105-2115) don't even reach the combined-mode context block, so shift/multi-select in combined mode also updates panels for the wrong chapter.

**Suggested fix (minimal):** when `combinedPlanReading`, store selection as the unique array index (or composite `_book|_chapter|verse` key) instead of the bare number, and have the five template checks compare against that. Normal single-chapter mode keeps numbers. One helper `verseKey(verse, idx)` used everywhere kills the whole class in one pass.

**Related plan-mode cleanup (already in this review):** serial loading of plan-day passages/commentary/interlinear (P4, 3-5× wall-clock win), plan-start triplication (R9), `.plan-reading-overlay` CSS duplicating the other two fullscreen overlays (§1.4).

## RECOMMENDED ATTACK ORDER

**Phase 1 — one-line/mechanical fixes with user-visible impact (half a day):**
1. FTS `text:` prefix (search correctness)
2. GZip middleware
3. `async def` → `def` (event-loop fix)
4. `[data-theme]` → `.dark` (Topics dark mode)
5. `safeParse` for the three bare JSON.parse calls
6. XFF rate-limit fix
7. Share-link range regex

**Phase 2 — dead code purge (~1,200 lines, zero behavior change):**
dead CSS (~630), models.py (101), old download system + devotional reader + misc JS (~250), unused supabase/offline-storage exports (~170), `words`-table query paths.

**Phase 3 — dedup (~1,200–1,500 lines, low risk):**
neighbor-query + BFS unification (kills false-path bug), book lists/abbrevs consolidation (both ends), button CSS consolidation, fetch-or-cache helper, plan-start merge, storage adapter.

**Phase 4 — perf + correctness structural work:**
N+1 batching (enrich/BFS/offline-book), verseColorMap precompute, drop redundant commentary fetch, lazy interlinear, background-refresh generation tokens, IDB transaction fix, z-index ladder, modal a11y.

**Phase 5 — features** (list above), ideally after main.py router split and app.js module split so additions don't grow the monoliths.
