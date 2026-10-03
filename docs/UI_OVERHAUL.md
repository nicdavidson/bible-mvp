# UI Overhaul: audit findings and task list

Audit date: 2026-10-02. Source state: working tree on `infra/dev-prod`, which is `9365950` plus uncommitted infra changes. None of those changes touch the UI code reviewed here.
Method: I ran the app from a scratch copy with Supabase disabled (`SUPABASE_URL` empty, so no account or sync calls). I drove it with headless Chromium through Playwright at phone size (390x844, touch) and desktop size (1440x900). I also read the code. Every repro below was observed in the browser unless it is marked *(code)*.
Screenshots are in `docs/ui-audit/`.

Size key: **S** is under half a day, **M** is 1 to 2 days, **L** is 3 days or more.

---

## TL;DR: top 5

1. **The browser Back button is a trap.** Pressing Back reloads the previous chapter and pushes it again as a *new* history entry. A second Back lands on the same chapter, and the history list grows with every press. You cannot back out of the app. (P0-1)
2. **With a verse highlighted, navigation loads the wrong passage.** Tapping a cross-ref, a commentary link, a search result or `Ch →` while a verse is selected reloads the *current* chapter. This is a race between `clearVerseSelection()` and an `await` inside `loadPassage()`. It hits every deep link like `/John/3/16`. (P0-2)
3. **On phones the verse action bar can't be tapped.** The "Study" peek row covers all six buttons (Highlight/Note/Study/Memorize/Copy/Dismiss), and a tap on any of them just clears the selection. (P0-3)
4. **Reading plans break.** Tapping a day's reading such as "Genesis 1-3" gives a 404 and a misleading "not cached for offline use" error. That error then sticks and hides the text of plan reading. `← Ch` / `Ch →` in plan mode load `"null 1"` and blank the screen. (P0-4, P0-5)
5. **There are three book/chapter pickers and they behave differently.** The home screen, with Recent and Bookmarks, can't be reached again once a chapter is open. (P1-1, P1-2)

---

## P0: broken core flows

### P0-1. Browser Back re-pushes history, so Back can never leave the current chapter
- **Repro (phone or desktop):** open `/`, pick John → 3, tap `Ch →` (John 4), then tap `Ch →` again or follow any reference. Press browser Back 5 times.
  Observed: every Back lands on the same chapter. The URL stays put and `history.length` grows by 1 per press (measured 5→6→7→8→9→10). Each press also refetches the chapter.
- **Root cause:**
  - `frontend/static/js/app.js:654-669`: the `popstate` handler calls `loadPassage()`.
  - `loadPassage()` always calls `updateURL(true)` (`app.js:1233` cache path, `app.js:1292` network path, `app.js:1363` offline path).
  - `updateURL(true)` runs `history.pushState` (`frontend/static/js/modules/selection.js:120-121`). Restoring an entry therefore creates a new entry and wipes the forward stack.
  - Plan mode does the same thing: `startPlanReading()` → `updateURL()` → `selection.js:107-110` *always* `pushState`s for plan URLs, even when the call came from `popstate` → `restorePlanFromURL()`.
  - The first page load pushes too, so a fresh deep link like `/John/4` has two identical entries (measured `history.length` 3 from `about:blank`). The first Back does nothing.
- **Fix:** add a `source` parameter to navigation: `'user' | 'pop' | 'init'`. Only `'user'` pushes. `'init'` and `'pop'` use `replaceState`, or don't touch history at all. Details are in the [Navigation model](#navigation-model-proposal) section. **S** for the minimal fix (thread a `{ push }` flag through `loadPassage`/`startPlanReading`). **M** with the full nav model.

### P0-2. Navigating while a verse is highlighted loads the current chapter instead
- **Repro A (desktop):** open `/John/4`, click verse 10, then click "Exodus 17:6" in the Study → Links grid.
  Observed: John 4 reloads. Exodus is never requested; the network log shows only `GET /api/passage/John 4`.
- **Repro B (any size):** open the deep link `/John/3/16`, which highlights v16, then tap `Ch →`.
  Observed: you stay on John 3 and the highlight is cleared. You need a second tap to reach John 4.
  The same thing happens with typed references: "rom 8:28" + Go, then `Ch →`, stays on Romans 8.
- **Root cause:** the verse action bar has `@click.outside="... clearVerseSelection()"` (`frontend/index.html:541`). Every click outside the bar runs `clearVerseSelection()`, and that writes `this.referenceInput = "${currentBook} ${currentChapter}"` (`app.js:2140-2142`).
  `loadPassage()` sets `referenceInput` from the click, but then `await`s the IndexedDB cache check (`app.js:1207`). While it waits, the outside-click handler overwrites `referenceInput`. The fetch then reads the clobbered value: ``fetch(`/api/passage/${encodeURIComponent(this.referenceInput)}`)`` (`app.js:1266`).
  `autoCacheEnabled` defaults to `true` (`app.js:495`), so the `await` always happens.
- **Fix:**
  1. `loadPassage(ref)` should take the reference as an argument. Capture it once at the top and never re-read `this.referenceInput` after an `await`. **S**
  2. `clearVerseSelection()` should not write `referenceInput`. That field belongs to the text input; derive the displayed text from `currentReference`. **S**

### P0-3. Phone: the verse action bar is covered by the "Study" peek row and can't be used
- **Repro (390x844):** open `/John/3` and tap verse 16. Then tap Highlight, Note, Study, Copy or ✕.
  `elementFromPoint` at the centre of every button returns `.study-peek`. The tap goes to the peek row, counts as an "outside" click, and clears the selection. Nothing opens.
  Screenshot: `ui-audit/01-phone-action-bar-covered.png`, where the icon row is hidden behind "STUDY Commentary 36 · Cross-refs 40 · Topics 24".
- **Root cause:** at ≤600px the action bar sits at `bottom: 60px` ("Above collapsed resources panel (48px peek…)", `frontend/static/css/style.css:6761`). The `.peeking` sheet state added later lifts the sheet to `translateY(calc(100% - 96px))` (`style.css:8749-8751`), so it now covers the bar.
  It only happens when the verse has commentary, cross-refs, topics or notes (`index.html:581`, the `peeking` class condition). That is almost every verse, so the bug looks intermittent.
- **Fix:** merge the two rows. When a verse is selected on mobile, show one bottom bar: actions on top, peek chips under them, inside the sheet. Quick patch: set `bottom: calc(96px + 8px)` while peeking, and add the peek row to the click-outside exclusion. **S** (patch) / **M** (merge).

### P0-4. Reading plan: tapping a day's reading gives a 404, then a stale error hides the plan text
- **Repro (phone):** open ☰ → Reading Plans → Start Plan → Today. Tap "Genesis 1-3" under Main Reading.
  You get the error *"Genesis 1 is not cached for offline use. Read it while online first…"* even though you are online.
  Then open ☰ → Reading Plans → Start Reading. The plan bar loads and 92 verses are in state, but the page shows only the old error and no text (`ui-audit/02-phone-plan-stale-error.png`).
- **Root cause:**
  - `goToPlanPassage(ref)` (`modules/plans.js:715-720`) passes a chapter *range* ("Genesis 1-3") to `loadPassage()`. The passage API doesn't support ranges and returns 404.
  - `loadPassage`'s catch block falls back to `_loadFromCache()`. That replaces the real error with the "not cached" text whenever the cache misses (`app.js:1385`), even when the network is up and the server said 404.
  - `startPlanReading()` (`modules/plans.js:460+`) never resets `this.error`. The verse list is gated on `!error` (`index.html:456`), so the stale error hides everything.
- **Fix:**
  - Route plan-modal reading links through `startPlanReading()` scrolled to that section, or load the first chapter with the range highlighted.
  - Set `this.error = null` at the start of every navigation.
  - Only show the "not cached" message when `!navigator.onLine || forcedOffline`; otherwise show the server's detail ("Passage not found: …").
  **S**

### P0-5. `← Ch` / `Ch →` in plan reading mode load "null 1" and blank the page
- **Repro:** open `/plan/chronological-year/1` and tap `Ch →`.
  Result: `referenceInput = "null 1"`, a 404, the "null 1 is not cached for offline use" error, and zero verses.
- **Root cause:** combined plan mode sets `currentBook = null` (`modules/plans.js`, and `app.js:2134-2137` on deselect). The chapter nav buttons are only gated on `currentReference` (`index.html:252-256`), and `nextChapter()`/`previousChapter()` (`app.js:1787-1823`) have no plan guard.
- **Fix:** in plan mode, hide the chapter buttons or turn them into plan Prev/Next day (`immersivePlanPrev/Next` already exist at `app.js:2897-2910`). Also guard both functions on `currentBook`. **S**

---

## P1: confusing or partly broken

### P1-1. Three book/chapter pickers that disagree
| | Header 📖 dropdown (`index.html:130,173-217`; `app.js:1015-1032`) | Home grid (`index.html:378-410`; `app.js:1034-1048`) | Title tap → chapter jump (`index.html:261-267`; `app.js:1050-1057`) |
|---|---|---|---|
| Single-chapter books (Obadiah, Jude…) | Forces a 1-button chapter grid | Loads chapter 1 immediately | n/a |
| Opens at | Always the book list, even when you're reading John | Book list | Current book's chapters |
| Marks current book/chapter | No | No | Yes (`current-chapter`) |
| Translation selector | Hidden inside it on mobile (`.picker-translation-mobile`) | No | No |
| Esc closes | **No** (`showBookPicker` is missing from `closeTopmostModal`, `app.js:761-772`) | n/a | **No** |
| Discoverability | 📖 icon | Only before the first chapter loads | Hidden: the title is the button, with only a `title` tooltip |

- **Repro:** from the home grid, tap Obadiah: it loads. From the header 📖, tap Obadiah: a grid with one "1" button appears. Reopen 📖 while reading John 3: it starts at the full book list with nothing marked. Press Esc: the dropdown stays open.
  Screenshots: `ui-audit/03-phone-header-picker.png`, `04-phone-home-picker.png`, `05-desktop-header-picker.png`.
- **Fix:** build one `<passage-picker>` (a single Alpine component/partial) used in all three places. See [Navigation model](#navigation-model-proposal). **M**

### P1-2. The home screen (Recent, Bookmarks, book grid) can't be reached once a chapter is open
- **Repro:** load any chapter, then open ☰ → "Get in the Word". You stay on the chapter. Reloading `/` works, but every chapter load rewrites the URL to `/Book/N`, so a reload just shows the chapter again.
- **Root cause:** the home view is just `verses.length === 0` (`index.html:342`). `navigateTo('reader')` → `exitPlanReading()` only clears `verses` when `!currentBook` (`modules/menus.js:31-33`). Bookmarks have no other entry point that I could find.
- **Fix:** make Home a real route (`/`) with a 🏠 entry in the header or menu that clears the passage state. Or put Recent and Bookmarks into the unified picker sheet as tabs. **S**

### P1-3. A verse reference with an abbreviated or lowercase book corrupts state (prev/next, URL, Recent)
- **Repro:** type `rom 8:28` and press Go. The URL becomes `/rom/8/28`, the title is "rom 8:28" and `currentBook = "rom"`. Recent stores "rom 8:28". The chapter buttons misbehave: `BOOK_CHAPTERS["rom"]` is undefined, so `nextChapter()` treats the book as one chapter long and `BIBLE_BOOKS.indexOf` is -1.
  `jn 3` without a verse works, because that path is normalised.
- **Root cause:** `backend/routers/passages.py:65` returns `"reference": f"{book} {chapter}" if not has_verse else reference`, which echoes the raw user string whenever a verse is present.
- **Fix:** always return the canonical form: `f"{book} {chapter}:{vs}"` or `f"{book} {chapter}:{vs}-{ve}"`. Also make the cache-first path canonicalise `inputBook` (`app.js:1191-1192`) through `normalizeBookName`. **S**

### P1-4. `Jude 5` / `Obadiah 3` and similar don't resolve; the error text is misleading
- **Repro:** type `Jude 5`. You get "Jude 5 is not cached for offline use…" (the API returns 404 "Passage not found").
- **Root cause:** `backend/core.py:42` `parse_reference` reads "5" as the chapter. Then the offline-message masking described in P0-4 (`app.js:1385`) hides the real error.
- **Fix:** in the parser, treat `<single-chapter book> N` as `1:N`, and fix the error-message masking. **S**

### P1-5. Mobile header: the reference box is about 60px wide, and the translation switch is hidden
- **Repro (390px):** the header holds ☰ · status dot · ▶ · ⛶ · 🔍 · 📖 · [input] · Go. The input shows "Joh" / "Ge" (`ui-audit/07-phone-after-xref-jump.png`). The translation `<select>` is hidden on mobile, and the only copy is inside the 📖 dropdown.
- **Fix:** on mobile, swap the input for a large tappable **reference title** ("John 3 · BSB ▾") that opens the unified picker. Move ▶ and ⛶ into the overflow menu. The search sheet should accept typed references (see P1-7). **M**

### P1-6. Peek chips and cross-refs lose their verse context
- **Repro (phone):** tap v16, then tap the "Cross-refs 40" peek chip. The sheet opens and the selection is cleared by `click.outside`, so the title goes back to "John 3". The list still shows v16's 40 refs, with no label saying which verse they belong to (`ui-audit/07…` shows the same pattern after a jump).
- **Root cause:** the peek chips are outside `.verse-action-bar`, so its `@click.outside` (`index.html:541`) clears the selection. `clearVerseSelection()` doesn't reload cross-refs.
- **Fix:** exclude `.panel-resources` and `.study-peek` from the outside-click rule. Show "Cross-refs for John 3:16" as a header in the tab. **S**

### P1-7. Search: duplicate hits across translations, no translation label, no reference lookup, results lost after a jump
- **Repro:** search "living water" and you get Jeremiah 2:13 twice and John 7:38 twice. These are the BSB/WEB/KJV hits, but nothing says which is which (`ui-audit/06-phone-search-duplicates.png`). Tapping a KJV-worded hit opens the passage in the *current* translation, so the snippet doesn't match.
  Searching `John 3:16` returns nothing, and Enter does nothing.
  After tapping a result, the modal closes and the query and results are wiped (`modules/feedback.js:212-222`). Going back to the results means retyping.
- **Fix:**
  - Group or deduplicate by verse and show a translation badge, or filter to the current translation by default (an API param).
  - If the query parses as a reference, show a "Go to John 3:16" row at the top.
  - Keep the last query and results; the "return" chip below can reopen search. **M**

### P1-8. Back from plan reading does nothing visible
- **Repro:** start plan reading from the plan modal, so the URL becomes `/plan/chronological-year/1`, then press Back. The URL becomes `/` but the plan view stays, and the next Back leaves the site.
- **Root cause:** in the `popstate` handler (`app.js:654-669`), a URL that is neither a plan nor a path reference falls through with no else branch.
- **Fix:** handle `/` as Home (P1-2). This is covered by the nav model. **S**

### P1-9. Guest notes vanish from view after signing in *(code)*
- `loadNotes()` reads Supabase when signed in and localStorage otherwise (`modules/feedback.js:352-369`). Nothing uploads guest notes (`synced: false`) on sign-in.
  I didn't test the signed-in path (no account was created). The signed-out notes UI works.
- **Fix:** on `SIGNED_IN`, offer "Import N notes from this device" (and the same for highlights and tags). **M**

### P1-10. After a jump on mobile, the sheet stays half-open over the destination verse
- **Repro (phone):** open the Cross-refs sheet and tap "Genesis 22:2". Genesis 22 loads and v2 is highlighted, but the sheet still covers the bottom half, partly hiding the verse you jumped to (`ui-audit/07-phone-after-xref-jump.png`).
- **Fix:** on any reference jump, collapse the sheet to peek and show the return chip, described below. **S**

---

## P2: polish

| # | Issue | Where | Fix | Size |
|---|---|---|---|---|
| P2-1 | The desktop sidebar collapse button "‹" overlaps the "Study" tab label (renders "tudy") | `index.html:583-590` (sidebar toggle), tab bar at `index.html:619-640` | Move the toggle out of the tab strip, or add padding-left to the tabs | S |
| P2-2 | The mobile sheet tab bar overflows ("Topics (2" is clipped next to ✕) | sheet tabs, ≤600px | Drop counts on mobile, or scroll the tabs | S |
| P2-3 | Scroll position isn't restored on Back | `loadPassage` | Store `scrollTop` and the verse anchor in `history.state` (nav model) | S |
| P2-4 | Recent (reading history) only records network loads, so chapters served from the cache never appear | `app.js:1289` (no `addToHistory` in the cache path at `app.js:1206-1256`) | Call `addToHistory` in one place, after any successful load | S |
| P2-5 | The home book grid shows the empty Study/Commentary/Notes tab bar on mobile before anything is loaded | `ui-audit/04-phone-home-picker.png` | Hide the sheet when `verses.length === 0` | S |
| P2-6 | Red-letter colouring is per verse, so narration inside a speaking verse is also red (e.g. Gen 22:1 "Some time later God tested Abraham") | `isRedLetterVerse` `app.js:2840` | Long term: word-level speaker spans. Short term: accept | L |
| P2-7 | Plan start: the date picker renders *below* the plan card, so on a phone "Start Plan" looks like it did nothing until you scroll | `index.html:2413-2455` | Make the picker a step that replaces the list, or scroll it into view | S |
| P2-8 | Two different "exit plan" functions with different behaviour (`exitPlanReading` in menus.js:20 keeps the chapter, `exitPlanReadingMode` in plans.js:677 reopens the plan modal or loads Genesis 1) | modules | Keep one | S |
| P2-9 | Alpine is loaded unpinned (`alpinejs@3.x.x` from unpkg) | `index.html:19` | Pin an exact version (or vendor it) | S |
| P2-10 | Dead Alpine v2 API `document.querySelector('[x-data]').__x.$data` | `index.html:2902` | Use `Alpine.$data(document.body)` | S |
| P2-11 | Note mode: "Done Selecting / Click verses to select them" is shown before the user has typed anything; "Click" on touch | `ui-audit` (note sheet) | Copy tweak: "Tap verses to extend this note" | S |
| P2-12 | Every chapter load fetches `/api/passage/X` twice when auto-cache is on (cache hit + `_backgroundRefresh`) | `app.js:1252`, `_backgroundRefresh` | Skip the background refresh if the cached copy is fresh (ETag or timestamp) | S |

---

## Navigation model (proposal)

### Goals
1. **One picker.** The same component everywhere (header, home and title tap), with the same behaviour.
2. **A real back stack.** Every *user* navigation pushes exactly one entry. Back and Forward restore the passage, the highlight and the scroll position, and never push.
3. **A "Return to where I was" chip** after any *jump*: a cross-ref, a commentary link, a search hit, a topic, a word occurrence or a note link. Chapter-to-chapter reading doesn't show it.

### 1. Single navigation entry point

Today there are at least 8 ways in, each setting `referenceInput` and calling `loadPassage()` or `loadReference()` directly. They include `previousChapter`/`nextChapter` (`app.js:1787-1823`), `selectPickerChapter`, `selectHomeChapter`, `jumpToChapter`, `handleCommentaryClick`, the cross-ref anchors (`index.html:736,1067`), `goToSearchResult`, `goToTopicRef`, `navigateFromPath` and `goToVerseFromModal`. Replace all of them with one function:

```js
// app.js (core) — the only function that changes the passage
async navigate(ref, { kind = 'read', source = 'user' } = {}) {
  // kind:   'read' (prev/next, picker)  |  'jump' (xref, commentary, search, topic, note, word occurrence)
  // source: 'user' (push) | 'pop' (from popstate, never push) | 'init' (first load, replace)
  const from = this.snapshotLocation();          // {ref, book, chapter, verses, scrollTop, translation, plan?}
  const ok = await this.loadPassage(ref);        // loadPassage(ref) takes the ref as an ARG (fixes P0-2)
  if (!ok) return;
  const state = this.snapshotLocation();
  if (source === 'user') history.pushState(state, '', this.pathFor(state));
  else if (source === 'init') history.replaceState(state, '', this.pathFor(state));
  // source === 'pop': URL is already correct; do nothing
  if (kind === 'jump' && source === 'user') this.returnTo = from;   // show chip
  if (kind === 'read') this.returnTo = null;                         // reading on clears it
}
```

- `loadPassage()` stops touching history. Delete the `updateURL(true)` calls at `app.js:1233,1292,1363`. `updateURL()` without push stays only for in-chapter verse selection (`replaceState`), and it should write `history.state` too.
- `startPlanReading()` goes through the same function with a plan location, and `selection.js:107-110` no longer always pushes.
- `popstate`: `navigate(e.state?.ref ?? parseFromURL(), { source: 'pop' })`, then restore `e.state.scrollTop`. Handle `/` by clearing to Home (fixes P1-8).

### 2. Return chip

- State: `returnTo: null | {ref, scrollTop, label}`. When it is non-null after a `jump`, show a pill pinned under the passage header: **"← Back to John 4:10"**.
  This generalises the existing "Return to Plan Reading" bar (`index.html:290-294`, `wasInPlanReading`), which should become the same chip with the label "← Back to Day 12 reading".
- Tapping the chip calls `history.back()` when the previous entry is that location (track `history.state.idx`). Otherwise it calls `navigate(returnTo.ref, {kind:'read'})` and restores `scrollTop`. Either way it clears the chip.
- The chip clears on a `read` navigation (prev/next chapter, picker) and on dismiss (✕).
- Chained jumps (xref → xref → xref) keep the chip pointing at the *original* location, so one tap returns to where you were reading. Browser Back still walks every hop.
- Search jumps set `returnTo.search = {query, results}`, so the chip can offer "Back to results" (fixes the result loss in P1-7).
- Mobile: on a jump, collapse the sheet to peek (P1-10) so both the chip and the destination verse are visible.

### 3. Unified picker

- Make one Alpine partial `passagePicker` with its own state: `{open, step: 'book'|'chapter', book}`. Use it as:
  - the header 📖 button and, on mobile, the tappable title "John 3 · BSB ▾" (replaces the cramped input; P1-5);
  - the Home screen, rendered inline (`open` always true, no overlay);
  - title tap, which opens straight at `step:'chapter'` for the current book (replaces `chapter-jump-grid`).
- Shared rules:
  - Opening while reading starts at the *current book's chapters*, with "← All books" one tap away.
  - Highlight the current book and chapter.
  - Single-chapter books load directly.
  - Esc and outside-click close it (add it to `closeTopmostModal`).
  - Include a "type a reference" field at the top that accepts `jn 3:16`, plus a translation switch and a tabs row: **Books · Recent · Bookmarks** (fixes P1-2 without needing the home screen).
- Delete `selectPickerBook/selectPickerChapter/selectHomeBook/selectHomeChapter/jumpToChapter`, `homePickerBook`, `pickerSelectedBook` and `showChapterJump` (`app.js:1015-1057`), and the three markup blocks (`index.html:173-217, 261-267, 378-410`).

### Rough sequencing
1. P0-2 (`loadPassage(ref)` arg, stop clobbering) plus P0-1 minimal (no push on pop/init). **S, ship first.**
2. P0-3, P0-4, P0-5. **S each.**
3. `navigate()` and `history.state` with the return chip. **M**
4. The unified picker and mobile header. **M–L**
5. P1 and P2 polish.

Add a Playwright regression test for each P0 (the audit scripts can be turned into `tests/e2e/`). The back-stack and race bugs are easy to reintroduce.
