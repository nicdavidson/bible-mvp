# app.js Module Split — Execution Plan (prepped 2026-07-23)

Status: PLANNED, not started. Execute on branch `appjs-split`, keep master
deployable (master currently holds the un-deployed offline rate-limit fix
`6790da9` — deploy that first or keep the branch rebased over it).

## Current shape

`frontend/static/js/app.js` (~6,065 lines): one `function bibleApp()`
returning a single Alpine data object (~227 methods), plus module-scope
helpers above it (lines 1–261: book lists, normalizeBookName, memo caches).
Loaded as a plain script tag (no bundler, no ESM).

## Split strategy (no bundler — keep script tags)

Extract feature clusters into `frontend/static/js/modules/<name>.js`, each
defining `window.BibleModules.<name> = { ...methods }`. `bibleApp()` becomes
core state + `Object.assign(this-shape)` merge of the modules:

```js
return Object.assign(
    { /* core state + navigation */ },
    BibleModules.tts, BibleModules.offline, BibleModules.plans, ...
);
```

Alpine binds `this` per component instance, so plain-object merge preserves
behavior. Load order in index.html: modules first, app.js last — all with the
`?v=__SW_VERSION__` stamp (added 027d9bb) and appended to the SW precache list.

## Module map (by existing section markers, ~line ranges pre-split)

| Module | Lines (approx) | Contents |
|---|---|---|
| core (stays in app.js) | 1–2945 minus extractions | state, navigation, passage loading, verse selection, word study, commentary/crossrefs/topics panels |
| tts.js | 2946–3136 | Text-to-speech read-along |
| menus.js | 3137–3309 | Side menu + single-verse view |
| share.js | 3310–3346 + 4296–4511 | Share Jesus + verse sharing |
| feedback.js | 3347–3943 | Feedback/bug report (large — check for dead weight while moving) |
| tags.js | 3944–4142 + 5668–5790 | Tag methods + tag-based highlighting |
| selection.js | 4143–4295 | Multi-verse selection |
| offline.js | 4512–4933 | Offline download/manage (incl. word-study fallback helpers) |
| plans.js | 4934–5667 | Reading plans + combined plan reading |
| study-extras.js | 5791–6065 | Export notes, scripture memory, reading history, bookmarks |

## Order of extraction (safest first)

1. tts.js (self-contained, easy verify)
2. study-extras.js
3. tags.js + selection.js
4. share.js, feedback.js
5. offline.js
6. plans.js (biggest, most cross-coupled — last)

After each: `node --check` all files, pytest (69), then headless playwright
smoke against local `make dev` (John/3 renders, plan day loads, verse tap
opens sheet). Commit per module.

## Gotchas noted during prep

- Module-scope helpers (lines 1–261) are referenced by many methods — leave
  in app.js, loaded last works only if modules don't call them at *load*
  time (they don't; methods run post-merge). Verify per module.
- `sw.js` STATIC_ASSETS should gain the module files.
- index.html script tags need the `?v=__SW_VERSION__` stamp on each new file
  (Dockerfile sed already substitutes index.html).
- `_loadGeneration`, `_highlightInterlinearWord` etc. cross modules — merge
  order doesn't matter for methods, but avoid two modules defining the same
  key (grep for duplicate method names after extraction).
