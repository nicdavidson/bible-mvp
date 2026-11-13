# Commentary Library (2026-11)

Branch `v2/commentary`. This expands the commentary library from 2 to 13 sources, adds the
`commentary_sources` metadata table, and makes every import reproducible through
`scripts/build_db.py`. Not legal advice.

## How to rebuild

```bash
python scripts/build_db.py                      # incremental; runs the commentary_* steps
python scripts/build_db.py --step commentary_kd # one source
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
- References are linked during import (validated against KJV versification), so the startup
  link migration in `backend/database.py` finds links and skips. This also removes the
  ~40 s boot cost noted in `docs/BUG_REVIEW_2026-10.md` item 8 for rebuilt DBs.

## Stored format (same for every source)

- `content`: plain text. Paragraphs are separated by `\n\n` (sometimes `\n`). The only markup
  is `<a href="#" class="commentary-ref" data-ref="Book C:V">...</a>` (also `Book C:V-W` and
  `Book C`). Everything else from the source is escaped. A bare `&` is left as is (`&c.`),
  so it reads correctly in both `x-html` and `x-text`.
- `searchable_text`: the same text without anchors, original case, no `<` or `>`. FTS5
  is case-insensitive, so search behaves as before; snippets now keep capitals.
- `book` matches `books.name`; `reference_start`/`reference_end` are verse numbers inside
  `chapter`; every range exists in KJV versification. Entries never span chapters.

## The library

Measured on 2026-11-12 with `scripts/check_commentary.py` against a full build (after VACUUM).
**Coverage** = share of verses in the books the source covers that have at least one entry
(share of all 31,102 verses in brackets). **DB MB** = the source's share of the space used by
`commentary_entries` + the FTS index. Each entry is stored twice (HTML `content` plus plain
`searchable_text`) and indexed, so the DB cost is about 1.37x the text bytes. Whole DB:
**385 MB before, 755 MB after (+370 MB)**. No single source is over the 150 MB flag.

| Source (`source`) | Chip | Kind | License basis | Came from | Entries | Books | Coverage | DB MB | Reader should know |
|---|---|---|---|---|---:|---:|---|---:|---|
| Matthew Henry | Henry | passage | PD (1708-10; d. 1714) | HelloAO; Song of Solomon from CrossWire `MHC` | 4,182 | 66 | 98.2% | 96.0 | Was 65 books with no ranges; now 66, with `reference_end` set (e.g. John 3 = 1-21, 22-36). Chapter outlines (previously dropped) are now at the top of each chapter's first entry. 253 entries over 20 KB (max 42 KB). HelloAO 404s on its phantom Isaiah 67 (harmless) |
| John Gill | Gill | verse | PD (1746-63; d. 1771) | HelloAO | 29,707 | 66 | 95.5% | 128.5 | Re-imported: the old rows were shifted by one or two verses in many chapters (see below). Now includes Song of Solomon (was missing) |
| Jamieson-Fausset-Brown | JFB | verse | PD (1871) | HelloAO, checked against CCEL | 18,214 | 66 | 58.6% | 32.4 | Brief notes; skips verses it has nothing to say on. HelloAO is missing Ps 146 and Mark 15 (404 upstream). Mojibake ("Ã†non") repaired |
| Keil & Delitzsch | K&D | passage | PD (Eng. 1864-78; d. 1888/1890) | HelloAO; Song of Solomon from CrossWire `KD` | 6,752 | 39 | 98.1% (73.0%) | 70.4 | OT only. Section-level; 153 entries over 20 KB (max 60 KB; the Song of Solomon 1:1 entry starts with K&D's introduction to the book). HelloAO has no text for Exod 37-38, Num 17, Job 25, Ps 101, 117, 131, 133, Ezek 4-5, 36 (404 upstream). Footnotes kept inline as "(Note: ...)" |
| John Calvin | Calvin | passage | PD (Eng. 1843-55) | HelloAO (CCEL text) | 7,327 | 48 | 95.1% (67.2%) | 106.6 | Calvin wrote nothing on Judges-Song (except Psalms), 2-3 John, Revelation. The verse text Calvin prints before each section (English + Latin) is removed in 4,148 sections; about 4% of entries, mostly the Harmony of the Law (Exodus-Deuteronomy), still contain it. Translator footnotes removed. Some "?" in Latin/Greek words (lost characters upstream). Lev 12 missing upstream |
| Adam Clarke | Clarke | verse | PD (1810-26; d. 1832) | CrossWire `Clarke` (Wikisource) | 21,051 | 66 | 67.7% | 56.9 | Each entry starts "Verse N". 24 book introductions removed from verse-1 entries; a few remain (Ezra 1:1 is 62 KB) |
| Barnes' Notes | Barnes | verse | PD (1832-51; d. 1870) | CrossWire `Barnes` | 7,322 | 27 | 92.3% (23.6%) | 42.7 | NT only. E-text quirks: chapter-1 verse-1 entries often start with Barnes's book introduction (14 removed; e.g. 1 Cor 1:1 still 33 KB); a few very long notes spill into the next verse with a "Continued" marker (2 Cor 4:18, 5:21; Rev 9). Matthew 1 re-keyed (the Gospels preface sat in 1:1-2); 107 "No specific Barnes text" placeholders dropped |
| John Wesley | Wesley | verse | PD (1755/1765; d. 1791) | CrossWire `Wesley` | 16,927 | 64 | 59.7% | 13.6 | Short notes. **Module has no 1 Kings or Philemon.** 3 misplaced 2 Samuel entries dropped |
| People's New Testament | PNT | verse | PD (1889-91; d. 1894) | CrossWire `PNT` | 6,068 | 26 | 76.5% | 6.3 | NT only; module has no Philemon |
| Scofield Notes (1917) | Scofield | notes | PD (1917; d. 1921) | CrossWire `Scofield` (Wikisource) | 3,207 | 65 | 10.3% | 2.9 | Occasional notes keyed to a word in the verse (first line is the headword); a few long topical notes (Heb 1:4 11 KB). No 3 John |
| Treasury of David | Spurgeon | verse | PD (1869-85; d. 1892) | CrossWire `TDavid` (Spurgeon Archive) | 2,547 | 1 | 100% of Psalms | 10.0 | Spurgeon's exposition split by his "Verse N." markers, plus one whole-psalm entry per psalm (his overview, range 1-last). The collected quotations and sermon hints (10.9 MB) are left out. Ps 18 and 22 have exposition without verse markers, so those are whole-psalm entries |
| Catena Aurea | Catena | passage | PD (Newman trans. 1841-45) | CrossWire `Catena` (lemtom/catena, CC0) | 821 | 4 | 100% of Gospels | 16.3 | Gospels only. Each entry quotes the verses, then the Fathers by name ("Augustine: ..."). Ranges inferred from the next section (726) |
| Tyndale Study Notes | Tyndale | notes | **CC BY-SA 4.0** (C) 2022 Tyndale House | tyndaleopenresources.com ZIP | 16,920 | 66 | 91.6% | 16.8 | Modern English, NLT wording in lemmas. Notes overlap: a passage note (e.g. 3:16-21) plus verse notes. 222 notes spanning chapters are truncated to their first chapter. Share-alike: keep the attribution string visible |

Totals: 141,045 entries (was 32,424). Commentary text payload 437 MB, DB space 599 MB.

### Verse alignment (shift) check, all sources

`check_commentary.py` tests every entry it can. A **lemma** test checks that the quoted KJV words
open the entry's own verse range. A **marker** test checks the "Verse N" / "C:V" / "N." the
entry prints. A **selfref** test checks the first link back into the same chapter. It reports
entries that match the next or previous verse instead. Result: every source is at or under 2.7%
(lemma noise). Gill went from **20.7% shifted (old DB) to 0.0%**.

K&D has few markers, so it was also cross-checked against the separately numbered CrossWire KD
text: 94.7% of locatable HelloAO entries overlap the CrossWire range. The rest trace back to
CrossWire's own lossy linking or to HelloAO merging adjacent sections (e.g. Gen 7:1-16).

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

## Notes for the study view (UI)

- Read `commentary_sources` for chips (`short_name`), ordering (`sort_order`), `kind`, `coverage`,
  `license` and `attribution`. Every `commentary_entries.source` has exactly one row (tested).
- `reference_end` is filled for every row in every source (0 NULLs). Passage sources (Henry, K&D,
  Calvin, Catena) carry real ranges, so there is no need to infer them from the next entry. Ranges
  never cross a chapter.
- Entries can overlap within one source: Tyndale (passage note + verse notes), Treasury of David
  (whole-psalm overview + verse exposition), Henry/K&D (an intro that became the verse-1 entry).
  For a verse, expect several rows from one source and order them by `reference_start`, then
  range length.
- Granularity: `verse` = mostly one verse per entry (some small ranges). `passage` = sections of
  several verses (Henry median about 8 KB, up to 42 KB). `notes` = sparse notes on selected
  verses (Scofield 10% coverage). A verse with no entry from a source is normal for JFB, Wesley,
  Clarke, PNT and Scofield.
- Very long entries: 602 entries over 20 KB (Henry 253, K&D 153, Calvin 124, Barnes 37, Clarke 29,
  Catena 5, Gill 1); the longest is 74 KB (Calvin). Show a preview and expand on tap.
- Paragraphs are separated by `\n\n`, but `.commentary-content` has no `white-space: pre-line`,
  so today every entry (old and new) renders as one block. Adding `white-space: pre-line` (or
  splitting into `<p>` client-side) fixes it for all sources.
- `getCommentaryEntryPreview()` strips tags but doesn't decode entities: a rare `&lt;`, `&gt;` or
  `&amp;` will show literally in the preview.
- **Offline size:** `/api/offline/chapter` and `/api/offline/commentary` return every source. The
  average chapter's commentary went from 70 KB (Henry + Gill) to 190 KB (max 1.2 MB). John 3 alone
  is 485 KB. The offline download should take a source list. A natural "optional download" split
  is a default set (e.g. Henry or JFB + Tyndale, about 50 MB in DB terms) with the big sources
  (Gill 129, Calvin 107, Henry 96, K&D 70, Clarke 57 MB) as per-source add-ons.
- Tyndale is CC BY-SA. Wherever it is shown or exported, show the `attribution` string.

## Upstream problems found

- **CrossWire `JFB`, `KD`, `CalvinCommentaries`:** text stored in the module that no verse slot
  points to (9.6%, 8.1%, 23.7% of bytes). No SWORD front end can show it. Calvin is worst: 166
  entries for all of Psalms. Worth a CrossWire tracker report.
- **CrossWire `Wesley`:** 1 Kings and Philemon empty; the first 1 Kings notes sit in 2 Samuel 24.
- **CrossWire `Barnes`:** book introductions in verse slots, notes that spill into the next verse,
  and the Gospels preface in Matthew 1:1-2.
- **HelloAO:** chapter 404s listed above. Henry's book list claims Isaiah has 67 chapters. K&D lists
  Song of Solomon with 0 chapters. JFB's verse-1 notes are filed under the chapter `introduction`
  field. The Gill data was misnumbered at the February import and has since been corrected.
- 404s are cached as `<key>.404` so rebuilds stay offline. Delete those files to retry.

## What was verified by running vs reasoned

Run: every number in the tables above; FTS hits per source (`check_commentary.py`) and through
`/api/search`; `/api/passage/John 3:16/commentary` returning 11 sources with ranges; `pytest
tests/` (91 passed, including the new `tests/test_commentary_data.py`); a full `build_db.py` run
of all 13 commentary steps from cache (4 min, 560 MB peak RSS); comparisons against independent
copies: HelloAO JFB vs CCEL Genesis (98.5%), CrossWire MHC Song of Solomon vs CCEL `mhc3.xml`
(100% of ours found), Treasury of David Ps 23 vs the Spurgeon Archive (identical), Clarke Romans 8
vs HelloAO (99.9%), K&D HelloAO vs CrossWire numbering (94.7% overlap).

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
| Matthew Henry | 1708-1710 (vols 1-5; Romans-Revelation finished from his notes by other ministers, 1710s); d. 1714 | HelloAO API: "no copyright restrictions whatsoever", per-commentary PD Mark. Song of Solomon from CrossWire `MHC` (DistributionLicense=Public Domain; "prepared from CCEL"). CCEL `mhc3.xml` header: `DC.Rights` "Public domain. May be copied and distributed freely." Our Song of Solomon text is 100% contained in CCEL's |
| John Gill | 1746-1763; d. 1771 | HelloAO API (as above) |
| Jamieson-Fausset-Brown | 1871 (*Commentary Critical and Explanatory*); Jamieson d. 1880, Brown d. 1897, Fausset d. 1910 | HelloAO API. Checked against CCEL `jfb.txt` ("Rights: Public Domain"): HelloAO covers 98.5% of CCEL's Genesis words |
| Keil & Delitzsch | German 1861-1875; English (T. & T. Clark, Foreign Theological Library) 1864-1878; Keil d. 1888, Delitzsch d. 1890 | HelloAO API (PD Mark). HelloAO credits worthy.bible, whose site has only a generic "(C) 1999-2026" footer and terms of use with no reuse clause; no claim on this text found. Treated as clear on the faithful-transcription rule |
| John Calvin | Latin/French 1540-1565; English: Calvin Translation Society, Edinburgh 1843-1855; d. 1564 | HelloAO API; its notes cite CCEL ("public domain and usable for any purpose"). Translator footnotes dropped |
| Adam Clarke | 1810-1826; d. 1832 | CrossWire `Clarke` v2.0 (DistributionLicense=Public Domain; TextSource Wikisource). Wikisource hosts public-domain texts without adding terms |
| Barnes' Notes | NT 1832-1851; d. 1870 | CrossWire `Barnes` (DistributionLicense=Public Domain; no TextSource given). No rights claim anywhere in the module text |
| John Wesley | NT 1755, OT 1765; d. 1791 | CrossWire `Wesley` (DistributionLicense=Public Domain; Kelley/Brown e-text, "Please share this work with a friend") |
| People's New Testament | 1889-1891; B. W. Johnson d. 1894 | CrossWire `PNT` (DistributionLicense=Public Domain) |
| Scofield Notes (1917) | 1917 edition (first edition 1909); Scofield d. 1921 | CrossWire `Scofield` v2.1 (Public Domain; TextSource Wikisource). Only the 1917 notes: the 1967 *New Scofield* notes are still copyrighted. Oxford University Press uses "Scofield" as a product name, so the label is descriptive ("Scofield Notes (1917)") |
| Treasury of David | 1869-1885; Spurgeon d. 1892 | CrossWire `TDavid` v2.1 (Public Domain; TextSource archive.spurgeon.org). The Spurgeon Archive page states no rights or terms. Spot-checked Psalm 23 against the archive: identical |
| Catena Aurea | Compiled c. 1262-1264; English translation ed. J. H. Newman, Oxford 1841-1845; Newman d. 1890 | CrossWire `Catena` (Public Domain; TextSource github.com/lemtom/catena, which is CC0: "compiled from various public domain sources, including the CCEL rawtext") |
| Tyndale Study Notes | 2022 | **CC BY-SA 4.0.** Primary download from tyndaleopenresources.com; the ZIP's `_README.txt` states the license and the required credit. Not public domain: keep attribution and share-alike (see LICENSES.md) |

Trap from the earlier review still applies: CCEL's site-wide policy limits commercial reuse of its
editions even though its file headers say "Public domain". The app is free; if it ever charges,
re-check the CCEL-derived sources (JFB check copy, Henry's Song of Solomon, Calvin via HelloAO).

## Rejected or unverified

| Candidate | Status | Reason / what is missing |
|---|---|---|
| Matthew Henry **Concise** (CrossWire `MHCC`, CCEL `mhcc`) | Unverified | It is an abridgement, and nobody names the abridger or its date. CrossWire cites "the printed edition as published by Moody Press, 28th printing, no Copyright displayed" (ISBN 0-8024-5190-X). That could be PD for lack of notice, but the printing date and notice status can't be confirmed. Need a dated 19th-century edition, or the Moody edition's details |
| Geneva Bible notes (CrossWire `Geneva`) | Unverified | The 1560/1599 notes are PD, but the module conf has no DistributionLicense and no TextSource, so the edition and its digitizer are unknown. Need the provenance of the e-text |
| Family Bible Notes (CrossWire `Family`) | Unverified | No DistributionLicense. Source is a defunct nnc.edu page; edition/date not stated |
| Matthew Poole (sermonindex.net) | Rejected | Poole's only structured source says "may never be sold or used commercially" (review Trap 5). No other source found |
| Robertson's Word Pictures (`RWP`) | Rejected | Vols 5-6 renewed (clear 2028/2029, review Trap 3); CrossWire terms are non-commercial |
| NET Bible notes (`NETnotesfree`), KingComments (`KingComments`) | Rejected | Copyrighted; non-commercial or no-bundling terms |
| Luther (CrossWire `Luther`) | Rejected | Mixes the Lenker edition (1905-1909) with Holman vols up to 1933 and Graebner's 1949 Galatians translation. Can't separate the post-1930 parts per entry |
| HistoricalChristianFaith Commentaries-Database (church fathers) | Rejected | Its LICENSE says some entries are "limited excerpts from works still under copyright… under the fair use doctrine", and there is no per-entry flag |
| CrossWire `JFB`, `KD`, `CalvinCommentaries` modules | Rejected as sources (works imported from HelloAO) | Their verse indexes leave text unreferenced: 9.6%, 8.1% and 23.7% of stored bytes. Confirmed losses: JFB John 3:16 and 3:18-21 notes missing (present in CCEL); K&D's Gen 1:3 comment missing; Calvin has 166 entries for all of Psalms and none for Psalm 23. Worth reporting to CrossWire |
| HelloAO `adam-clarke` | Not used | 63 books (review Trap 6); CrossWire `Clarke` has all 66 |
| Pulpit Commentary, Ellicott, Cambridge Bible for Schools, Expositor's Bible | Not imported | PD by date (1870s-1910s), but no clean verse-keyed source was found (not on CrossWire or HelloAO; BibleHub is off-limits). CCEL has the Expositor's Bible as chapter-length essays, which would need manual keying |
| Darby's Synopsis | Not imported | Only HTML (e.g. stempublishing.com), not verse-keyed. CrossWire `DTN` holds Darby's translation notes, which is a different work |
| Burkitt (1700-1703), Abbott Illustrated NT (1878), Lightfoot (1658-1674), McGarvey & Pendleton Fourfold Gospel (c. 1914) | PD, deferred | CrossWire modules marked Public Domain and old enough. Left out to keep size and scope down; add with a registry entry each if wanted |

