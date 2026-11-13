# Commentary Library (2026-11)

Branch `v2/commentary` expanded the commentary library from 2 to 13 sources, added the
`commentary_sources` metadata table, and made every import reproducible through
`scripts/build_db.py`. On 2026-11-13 the library was cut to the **five sources** below
(`feat/commentary-trim`). Not legal advice.

**Removed 2026-11-13, at the owner's decision.** The site owner reviewed the commentators
against his church's doctrine (conservative, dispensational, Baptist-leaning) and had eight
removed outright, not hidden: **Matthew Henry, Keil & Delitzsch, Albert Barnes (Barnes'
Notes), John Calvin, John Wesley, Adam Clarke, People's New Testament (B. W. Johnson) and
Catena Aurea.** The reason is doctrinal fit, not licensing or data quality. They are gone from
the registry, the build, the database and the app; a build drops their rows from an older
database. Do not re-add them. Their import notes are in this file's git history (before
2026-11-13) if ever needed.

## How to rebuild

```bash
python scripts/build_db.py                      # incremental; runs the commentary_* steps
python scripts/build_db.py --step commentary_tyndale  # one source
python scripts/import_commentary.py --list      # registry keys
python scripts/check_commentary.py --samples 3  # quality report (exit 1 on failure)
```

- Metadata and loader settings for every source: `scripts/commentary_registry.py`.
- Loaders: HelloAO JSON, CrossWire SWORD modules (`scripts/sword_reader.py`, no third-party
  dependency), Tyndale XML. Downloads are cached in `data/sources/` (git-ignored): 
  `commentary-<id>/` (HelloAO), `crosswire/<Module>.zip`, `tyndale/`, `ccel/` (reference copies
  used for checking only). Once warm, a rebuild needs no network.
- Each step deletes and rewrites its own source's rows and its `commentary_sources` row, so
  it is idempotent.
- The `commentary_search` step (`scripts/migrate_commentary_search.py`, v1.1) runs after the
  imports. Besides the search-storage conversion (below) it drops every row of a source that
  is not in the registry (entries, `commentary_sources`, and their FTS index entries through
  the delete trigger), rewrites the kept sources' `commentary_sources` rows from the registry
  (`sort_order`, metadata, `size_bytes`), and runs FTS5 `optimize` + `integrity-check`.
  `build_db.py` also forgets `_build_meta` records of steps it no longer has, so the manifest
  lists only what the DB contains, and VACUUMs when the prune frees space.
- References are linked during import (validated against KJV versification), so the startup
  link migration in `backend/database.py` finds links and skips. This also removes the
  ~40 s boot cost noted in `docs/BUG_REVIEW_2026-10.md` item 8 for rebuilt DBs.

## Stored format (same for every source)

- `content`: plain text. Paragraphs are separated by `\n\n` (sometimes `\n`). The only markup
  is `<a href="#" class="commentary-ref" data-ref="Book C:V">...</a>` (also `Book C:V-W` and
  `Book C`). Everything else from the source is escaped. A bare `&` is left as is (`&c.`),
  so it reads correctly in both `x-html` and `x-text`.
- Search text: the same text without anchors, original case, no `<` or `>`, derived from
  `content` through a view (see "Search storage" below; `search_override` only where it differs).
- `book` matches `books.name`; `reference_start`/`reference_end` are verse numbers inside
  `chapter`; every range exists in KJV versification. Entries never span chapters.

## The library

Measured on 2026-11-13 with `scripts/check_commentary.py` on the trimmed database (release
`2026.11.13.1`, after VACUUM). **Coverage** = share of verses in the books the source covers
that have at least one entry (share of all 31,102 verses in brackets). **DB MB** = the source's
share of the space used by `commentary_entries` + the FTS index (128.6 MB together).
Whole DB: **535.7 MB with 13 sources, 286.4 MB with five** (bytes 535,650,304 -> 286,441,472).

| Order | Source (`source`) | Chip | Kind | License basis | Came from | Entries | Books | Coverage | DB MB | Reader should know |
|---:|---|---|---|---|---|---:|---:|---|---:|---|
| 10 | Scofield Notes (1917) | Scofield | notes | PD (1917; d. 1921) | CrossWire `Scofield` (Wikisource) | 3,207 | 65 | 10.3% | 2.9 | Occasional notes keyed to a word in the verse (first line is the headword); a few long topical notes (Heb 1:4 11 KB). No 3 John. First in the order, but sparse: the study view opens on the first source that has something on the selection, so a verse without a Scofield note opens on Gill (or the next source with a note), never on an empty pane |
| 20 | John Gill | Gill | verse | PD (1746-63; d. 1771) | HelloAO | 29,699 | 66 | 95.5% | 82.6 | Re-imported in 2026-11: the old rows were shifted by one or two verses in many chapters (see below). Includes Song of Solomon. 8 rows holding only "See Chapter Introduction" dropped. Ends with a comma are Gill's own lead-ins ("it follows,") |
| 30 | Jamieson-Fausset-Brown | JFB | verse | PD (1871) | HelloAO, checked against CCEL | 18,214 | 66 | 58.6% | 23.0 | Brief notes; skips verses it has nothing to say on. HelloAO is missing Ps 146 and Mark 15 (404 upstream). Mojibake ("Ã†non") repaired; 1,085 "Next: … Chapter N" page-navigation lines removed |
| 40 | Tyndale Study Notes | Tyndale | notes | **CC BY-SA 4.0** (C) 2022 Tyndale House | tyndaleopenresources.com ZIP | 17,301 | 66 | 93.0% | 13.9 | Modern English, NLT wording in lemmas. Notes overlap: a passage note (e.g. 3:16-21) plus verse notes. 222 notes on chapter groups ("Pss 23–28 ...") are attached to every chapter they cover (+381 rows), each with the verses it covers there; the note text names the full span. **Show `attribution_short` wherever its text is shown** |
| 50 | Treasury of David | Spurgeon | verse | PD (1869-85; d. 1892) | CrossWire `TDavid` (Spurgeon Archive) | 2,547 | 1 | 100% of Psalms (7.9%) | 6.2 | Spurgeon's exposition split by his "Verse N." markers, plus one whole-psalm entry per psalm (his overview, range 1-last). The collected quotations and sermon hints (10.9 MB) are left out. Ps 18 and 22 have exposition without verse markers, so those are whole-psalm entries |

Totals: 70,968 entries (141,380 with 13 sources). Commentary text payload 75.3 MB.
`commentary_sources.size_bytes` holds each source's `content` size in UTF-8 bytes (what an offline
download of that source transfers before compression).

**Coverage after the trim.** Every one of the 1,189 chapters still has commentary from at least
one kept source (of the 929 Old Testament chapters, 106 have all five, 618 four, 202
three, 3 two; none rely on one source). 119 verses (of 31,102) now have no entry from any source, all
in the historical books, mostly 2 Chronicles passages that repeat Kings (before the trim only
removed sources covered them): 2 Kings 18:36, 19:5, 19:7; 1 Chronicles 25:10-31, 26:3; 88
verses across 2 Chronicles 3-36 (e.g. 2 Chr 6:3-20, 9:5-31, 18:3-27, 25:18-28); Nehemiah 7:63-69.
For such a selection the study view says "No commentary on ... yet" and each source chip offers
where it comments nearby.

### Verse alignment (shift) check, all sources

`check_commentary.py` tests every entry it can. A **lemma** test checks that the quoted KJV words
open the entry's own verse range. A **marker** test checks the "Verse N" / "C:V" the entry
prints. It reports entries that match the next or previous verse instead. Result (2026-11-13):
Scofield 0.2%, Gill 0.0%, JFB 0.6%, Tyndale 0.0%, Treasury of David 0.0%. Gill went from
**20.7% shifted (old DB) to 0.0%**.

### John Gill: what was wrong and what changed

- Symptom (reported by the study-view agent): John 3:1 held verse 2's comment, John 1 started at
  verse 2, and so on.
- Extent in the old DB: of 28,300 Gill rows, 16,267 sat at the right verse. 8,938 (32%) belonged to
  a different verse: 5,773 one verse later, 1,591 two later, 1,571 elsewhere. The rest had text
  that upstream has since revised. 1,104 chapters in 65 books had at least one moved or changed row, and Song of Solomon
  was missing. The lemma check scored the old data 20.7% shifted.
- Cause: `import_commentary.py` copied HelloAO's `number` field straight into `reference_start`
  with no check. The HelloAO Gill data fetched on 2026-02-06 was misnumbered in those chapters.
  The same code on today's HelloAO data gives correctly aligned rows, and HelloAO has also
  revised the text (e.g. "Gen 6:13" is now "Genesis 6:13"). So the defect was upstream, and
  nothing in the importer caught it.
- Fix: re-imported Gill (29,707 rows, 66 books, 0.0% shifted). The alignment check is now part of
  `check_commentary.py` and fails above 3%, so a regression upstream would be caught.

### Truncation check, all sources

Rule, chosen from the data: in every source over 97% of entries end with sentence-final
punctuation (`. ! ? ) " '` etc.). An entry that ends on a lowercase letter or a comma stopped
mid-sentence. If it is also 30,000+ characters, that is the signature of a length cap.
`check_commentary.py` now fails on: any cap-truncated entry, any source with more than 2% of
entries ending mid-sentence, and any leftover page-navigation line. Entries we could not
complete end with " […]" and are counted separately.

| Source | Ends mid-sentence | Cap-truncated | Marked " […]" | What the mid-sentence endings are |
|---|---:|---:|---:|---|
| Tyndale | 2 (0.01%) | 0 | 0 | Authentic |
| JFB | 19 (0.10%) | 0 | 0 | Quotation attributions |
| Treasury of David | 4 (0.16%) | 0 | 0 | Authentic (no closing stop in source) |
| Gill | 167 (0.56%) | 0 | 0 | 80 end "it follows,": Gill's own lead-in to the next verse; 63 footnote lines ("(c) In voce"); a few "see Gill on" whose target was dropped upstream |
| Scofield | 1 (0.03%) | 0 | 0 | Authentic |

## Notes for the study view (UI)

- Read `commentary_sources` for chips (`short_name`), ordering (`sort_order`), `kind`, `coverage`,
  `license` and `attribution`. Every `commentary_entries.source` has exactly one row (tested).
- `attribution_short` (one line; set only where the license requires credit, i.e. Tyndale, NULL
  elsewhere), `requires_attribution` (1/0), `size_bytes` (UTF-8 bytes of the source's `content`,
  written by the build; tested to match). Under CC BY-SA 4.0 s.3(a)(2) the short line may stand
  in for the full credit if the full one (`attribution`, which also names the license and states
  the changes) is a tap away, e.g. on the info sheet.
- Default order (`sort_order` 10..50, set by the owner): Scofield, Gill, JFB, Tyndale, Treasury
  of David. The same order is `DEFAULT_ORDER` in `scripts/commentary_registry.py` (keys) and
  `frontend/static/js/modules/study.js` (slugs); keep them in step.
- Which source the view opens on: the one asked for (deep link `?study=`, or the reader's last
  choice) if it has something on the selection, else the first source in the order that does.
  So a verse without a Scofield note opens on Gill, and an old link to a removed source
  (`/John/3/16?study=matthew-henry`, shared before 2026-11-13) opens on the first available
  source and the address is rewritten to it (tested in `tests/e2e/test_study_flow.py`).
- Offline: commentary a device saved from a removed source is not shown once the app has seen
  the current library online (`studySourceMeta`); `/api/offline/commentary?sources=` ignores
  unknown or removed names. Default offline set: Tyndale + JFB.
- `reference_end` is filled for every row in every source (0 NULLs). Ranges never cross a chapter.
- Entries can overlap within one source: Tyndale (passage note + verse notes), Treasury of David
  (whole-psalm overview + verse exposition). For a verse, expect several rows from one source
  and order them by `reference_start`, then range length.
- Granularity: `verse` = mostly one verse per entry (some small ranges). `notes` = sparse notes on
  selected verses (Scofield 10% coverage). A verse with no entry from a source is normal for JFB
  and Scofield.
- Long entries: one entry over 20 KB (Gill, 21 KB); the longest Scofield note is 11 KB.
- Tyndale is CC BY-SA. Wherever it is shown or exported, show `attribution_short`, linked to the full
  `attribution`.

## Upstream problems found

- **CrossWire `JFB`:** 9.6% of the module's stored bytes are text no verse slot points to (no
  SWORD front end can show it; e.g. the John 3:16 and 3:18-21 notes). JFB is imported from
  HelloAO instead. Worth a CrossWire tracker report.
- **HelloAO navigation debris:** "Next: Genesis Chapter 2" lines in JFB (1,085) and Gill rows
  holding only "See Chapter Introduction". Removed at import.
- **HelloAO:** chapter 404s listed above. JFB's verse-1 notes are filed under the chapter
  `introduction` field. The Gill data was misnumbered at the February import and has since been
  corrected.
- 404s are cached as `<key>.404` so rebuilds stay offline. Delete those files to retry.

## What was verified by running vs reasoned

Run (2026-11-13 trim): the prune on the full 13-source database (70,412 rows of the eight
sources removed; FTS5 `integrity-check` passes; a full-text search for the removed sources'
names in the `source` column finds nothing); the kept sources' rows are byte-identical before
and after; a fresh re-import of all five with the trimmed importer reproduces exactly the same
rows and `commentary_sources` rows; the prune run a second time removes nothing;
`check_commentary.py` passes (it now also fails on any source not in the registry); the full
`pytest` suite.

Run (2026-11 rounds one and two, still true for the kept sources): the shift and truncation
checks; comparisons against independent copies: HelloAO JFB vs CCEL Genesis (98.5%), Treasury of
David Ps 23 vs the Spurgeon Archive (identical); FTS hits per source and through `/api/search`.

Reasoned, not run: public-domain status (from publication dates and death dates above), and the
reading that faithful transcriptions carry no new copyright. Not checked against Copyright Office
records. Not legal advice.

## License basis, per source

US rule used: works first published before 1931 are in the US public domain (the 1930 class
entered it on 2026-01-01). Every public-domain item below was published before 1931 (all but
Scofield's 1917 notes before 1900), and every author died before 1930. A faithful transcription of a public-domain text adds no new US
copyright (no originality), so the remaining question for each digital edition is whether its
publisher imposes terms. "Checked" means the page or file was read on 2026-11-12.

| Source | Original publication; author death | Digital edition used; terms checked |
|---|---|---|
| John Gill | 1746-1763; d. 1771 | HelloAO Free Use Bible API (bible.helloao.org) |
| Jamieson-Fausset-Brown | 1871 (*Commentary Critical and Explanatory*); Jamieson d. 1880, Brown d. 1897, Fausset d. 1910 | HelloAO API. Checked against CCEL `jfb.txt` ("Rights: Public Domain"): HelloAO covers 98.5% of CCEL's Genesis words |
| Scofield Notes (1917) | 1917 edition (first edition 1909); Scofield d. 1921 | CrossWire `Scofield` v2.1 (Public Domain; TextSource Wikisource). Only the 1917 notes: the 1967 *New Scofield* notes are still copyrighted. Oxford University Press uses "Scofield" as a product name, so the label is descriptive ("Scofield Notes (1917)") |
| Treasury of David | 1869-1885; Spurgeon d. 1892 | CrossWire `TDavid` v2.1 (Public Domain; TextSource archive.spurgeon.org). The Spurgeon Archive page states no rights or terms. Spot-checked Psalm 23 against the archive: identical |
| Tyndale Study Notes | 2022 | **CC BY-SA 4.0.** Primary download from tyndaleopenresources.com; the ZIP's `_README.txt` states the license and the required credit. Not public domain: keep attribution and share-alike (see LICENSES.md) |

Trap from the earlier review still applies: CCEL's site-wide policy limits commercial reuse of its
editions even though its file headers say "Public domain". The app is free; if it ever charges,
re-check JFB (HelloAO text, checked against CCEL's edition).

## Rejected or unverified

| Candidate | Status | Reason / what is missing |
|---|---|---|
| Matthew Henry **Concise** (CrossWire `MHCC`, CCEL `mhcc`) | Rejected (Henry removed 2026-11-13; before that unverified) | It is an abridgement, and nobody names the abridger or its date. CrossWire cites "the printed edition as published by Moody Press, 28th printing, no Copyright displayed" (ISBN 0-8024-5190-X). That could be PD for lack of notice, but the printing date and notice status can't be confirmed. Need a dated 19th-century edition, or the Moody edition's details |
| Geneva Bible notes (CrossWire `Geneva`) | Unverified | The 1560/1599 notes are PD, but the module conf has no DistributionLicense and no TextSource, so the edition and its digitizer are unknown. Need the provenance of the e-text |
| Family Bible Notes (CrossWire `Family`) | Unverified | No DistributionLicense. Source is a defunct nnc.edu page; edition/date not stated |
| Matthew Poole (sermonindex.net) | Rejected | Poole's only structured source says "may never be sold or used commercially" (review Trap 5). No other source found |
| Robertson's Word Pictures (`RWP`) | Rejected | Vols 5-6 renewed (clear 2028/2029, review Trap 3); CrossWire terms are non-commercial |
| NET Bible notes (`NETnotesfree`), KingComments (`KingComments`) | Rejected | Copyrighted; non-commercial or no-bundling terms |
| Luther (CrossWire `Luther`) | Rejected | Mixes the Lenker edition (1905-1909) with Holman vols up to 1933 and Graebner's 1949 Galatians translation. Can't separate the post-1930 parts per entry |
| HistoricalChristianFaith Commentaries-Database (church fathers) | Rejected | Its LICENSE says some entries are "limited excerpts from works still under copyright… under the fair use doctrine", and there is no per-entry flag |
| CrossWire `JFB` module | Rejected as primary source (JFB imported from HelloAO) | Its verse index leaves 9.6% of stored bytes unreferenced; JFB John 3:16 and 3:18-21 notes missing (present in CCEL). Worth reporting to CrossWire |
| Pulpit Commentary, Ellicott, Cambridge Bible for Schools, Expositor's Bible | Not imported | PD by date (1870s-1910s), but no clean verse-keyed source was found (not on CrossWire or HelloAO; BibleHub is off-limits). CCEL has the Expositor's Bible as chapter-length essays, which would need manual keying |
| Darby's Synopsis | Not imported | Only HTML (e.g. stempublishing.com), not verse-keyed. CrossWire `DTN` holds Darby's translation notes, which is a different work |
| Burkitt (1700-1703), Abbott Illustrated NT (1878), Lightfoot (1658-1674), McGarvey & Pendleton Fourfold Gospel (c. 1914) | PD, deferred | CrossWire modules marked Public Domain and old enough. Left out to keep size and scope down. Any addition now needs the owner's doctrinal review first |
| Matthew Henry, Keil & Delitzsch, Barnes' Notes, John Calvin, John Wesley, Adam Clarke, People's New Testament, Catena Aurea | **Removed 2026-11-13** | Were in the library (licensing fine); removed at the owner's decision for doctrinal fit. Do not re-add |


## Search storage (2026-11-13, `v2/wordstudy`)

(Written for the 13-source library; the numbers below are from then. The mechanism is unchanged
after the trim: 383 of the 70,968 remaining entries carry a `search_override`.)

Each entry used to be stored twice: `content` (HTML with reference anchors) and
`searchable_text` (the same text without anchors, 207.6 MB of text), which fed the
external-content FTS5 table `commentary_fts`. Now FTS5 reads the text through a view:

    commentary_search(id, searchable_text, source, book, chapter)
      searchable_text = COALESCE(search_override, commentary_plain(content))

`commentary_plain` (`backend/commentary_search.py`) unwraps the anchors and reads
`&lt;`/`&gt;` as spaces and `&amp;` as `&`, the importer's own rule. For 668 of 141,380
entries the stored text differed from that by whitespace the HTML lost ("the result
thata great" in `content`, "that a great" in the old searchable text; also Wesley,
Scofield, Barnes); `search_override` keeps the old text for exactly those, so the index
and snippets see the same text as before.

What reads it: the FTS triggers (insert, delete, and a new update trigger), `snippet()`
in `/api/search`, and `scripts/check_commentary.py`. The SQL function must be registered
on every connection that inserts, updates or deletes commentary or asks FTS5 for text
(`snippet`, `highlight`, the column): `backend/database.py` does it for both app
connections; the importer and the checker do it too. **Deploy code and database
together**: older code against this database gets "no such function" from `snippet()`,
which `/api/search` turns into empty results.

Proof: 2,591 searches sampled from the corpus (single words in three frequency bands,
quoted 2-3 word phrases, last-word prefixes, two-word queries; scopes commentary and
all) return byte-identical responses (results, order, snippets) before and after;
FTS5's `integrity-check` passes; `check_commentary.py` passes. Median search 27 → 19 ms.

Size (after VACUUM): 742,858,752 → 514,818,048 bytes (−228.0 MB, −30.7%);
`commentary_entries` 507.3 → 279.3 MB; the FTS index is unchanged (92.7 MB).
Build: step `commentary_search` (`scripts/migrate_commentary_search.py`, 89 s, 20 MB
RAM) converts an older database; new imports store `search_override` only where needed.

Found while doing this: those 668 entries display with the missing spaces ("thata",
"2:25and"); worth fixing in the importers' HTML, separately.
