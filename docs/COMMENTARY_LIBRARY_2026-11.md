# Commentary Library (2026-11)

Branch `v2/commentary` expanded the commentary library from 2 to 13 sources, added the
`commentary_sources` metadata table, and made every import reproducible through
`scripts/build_db.py`. On 2026-11-13 the library was cut to the **five sources** below
(`feat/commentary-trim`), and the same day a first wave of public-domain **dispensational
sources** was added (`feat/disp-sources`; section "Dispensational sources" below). Not legal
advice.

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

## Dispensational sources (2026-11-13, `feat/disp-sources`)

The owner approved adding the free (public-domain) dispensational commentaries first. Six were
imported; Gray was left out (below). Build steps `commentary_gaebelein`, `commentary_ironside`,
`commentary_darby`, `commentary_brooks`, `commentary_mackintosh`, `commentary_larkin`; registry
entries in `scripts/commentary_registry.py`; SermonIndex repairs in
`scripts/commentary_repair.py`. Every download goes through `source_cache`
(`data/sources/sermonindex/`, `archive/`, `gutenberg/`), so a from-scratch build fetches the
same files from their real URLs.

| Order | Source (`source`) | Chip | Kind | Text shipped (edition, year) | Downloaded from | Entries | Books | Coverage | Text MB |
|---:|---|---|---|---|---|---:|---:|---|---:|
| 50 | Gaebelein Annotated Bible | Gaebelein | passage | A. C. Gaebelein, *The Annotated Bible*, 9 vols, Our Hope, New York, ©1913-1921; **Matthew** is his *The Gospel of Matthew: An Exposition* (vol. 1 1903; 2-vol. edition ©1910) | `https://sermonindex.net/modules/sword/siannbible.zip`; caps repair from archive.org `annotatedbibleho01gaeb`…`09gaeb`, `gospelofmatthewe01gaeb`, `gospelofmatthewe02gaeb` | 1,291 | 66 | 100% | 7.0 |
| 60 | Ironside Expositions | Ironside | passage | H. A. Ironside: Notes on Nehemiah (2nd ed. 1925), Esther (1921 rev. ed. of 1905), Jeremiah and Lamentations (1928 ed. of 1906), Minor Prophets (1909; 1928 printing), Lectures on Romans (1928), Colossians (Jan. 1929) | `https://sermonindex.net/modules/sword/siiron.zip`, books on `IRONSIDE_PRE1931` only; caps repair from archive.org `notesonbookofneh0000iron`, `notesonbookofest0000unse`, `notesonprophecyl0000hair`, `bwb_T5-CWQ-371`, `lecturesonepistl0000hair_u7v0`, `bwb_S0-BLY-002` | 184 (279 with the second group) | 18 (22) | 99.6% of those books | 1.8 (3.5) |
| 80 | Darby Synopsis | Darby | chapter | J. N. Darby, *Synopsis of the Books of the Bible*, New Testament (first ed. 1857-1867) | `https://sermonindex.net/modules/sword/sidarbysyn.zip` | 260 | 27 | NT 100% | 3.0 |
| 90 | Brooks Summarized Bible | Brooks | chapter | Keith L. Brooks, *The Summarized Bible*, Bible Institute of Los Angeles, ©1919 | `https://sermonindex.net/modules/sword/sitsb.zip` | 1,189 | 66 | 100% | 1.3 |
| 100 | Mackintosh Notes on the Pentateuch | Mackintosh | passage | C. H. Mackintosh, *Notes on Genesis … Deuteronomy* (1858-1880); PG transcribes Loizeaux reprints (e.g. Exodus "First edition 1880, 27th printing 1965") of the unchanged text | Project Gutenberg `https://www.gutenberg.org/cache/epub/<n>/pg<n>.txt`, n = 37915 Gen, 40596 Exod, 40610 Lev, 76552 Num, 41571 + 41584 Deut | 210 | 5 | 100% | 5.3 |
| 110 | Larkin on Revelation | Larkin | passage | Clarence Larkin, *The Book of Revelation*, ©1919 (charts not included) | `https://sermonindex.net/modules/sword/silarkinrev.zip`; caps repair from archive.org `bookofrevelation00lark` | 75 | 1 | 100% | 0.5 |

With the second group (below) the library holds 74,659 entries. Database (release
`2026.11.13.2`, sha256 `07e6e218…f012`): 286,441,472 → 326,320,128 bytes (+39.9 MB; commentary
tables + FTS 128.6 → 163.8 MB; 1.4% free pages, under the 5% VACUUM threshold). Every one of the 31,102 verses has at least one entry
(the 119 verses left uncovered by the trim are all covered again: Brooks and Gaebelein cover
every chapter). Treasury of David moved to `sort_order` 120.

**Order.** Verse-level whole-Bible sources first (Scofield, Gill, JFB, Tyndale), then the
chapter-level ones (Gaebelein, Ironside, Newell, Darby, Brooks, Mackintosh, Larkin), Treasury of David
last, as the owner proposed. Brooks is whole-Bible but a short digest, so it sits after the
expositions; Ironside sits high although it covers 18 books because the view skips a source
with nothing on the selection.

### How they are stored

- SermonIndex modules store each section at the verse it starts on (whole-chapter notes at
  verse 1). The importer stores each section with its real range: it runs until the next section
  of the same book starts. A section that runs on into chapters with no section of their own
  (Gaebelein's Genesis 1:1-2:3, Mackintosh's Joseph essay on Genesis 39-50, Darby's Acts 24-25)
  is stored once per chapter it covers, with the verses it covers there, exactly as Tyndale's
  chapter-group notes are. The schema has no way to point one row at another, so the text is
  repeated: 173 extra rows, 2.3 MB (Mackintosh 72 rows/1.6 MB, Gaebelein 98/0.7 MB, Darby 3). Entries never cross a
  chapter.
- `kind`: Brooks and Darby `chapter` (exactly one note per chapter, enforced at import);
  Gaebelein, Ironside, Mackintosh, Larkin `passage` with explicit ends. The study view's
  "find my verses inside a passage note" works as for Tyndale: Gaebelein and Larkin open their
  sub-sections with a reference ("Revelation 20:4-6.", "Genesis 2:4-6"), which the importer
  links, and a link into the chapter at the start of a paragraph is a verse marker for the view.
- Mackintosh: essays start at the volume's "CHAPTER XII." / "CHAPTERS VII.-XI." / "CHAPTER
  V. 14-VI. 7" headings; an essay covers what its heading names and, where the next heading
  starts later, the chapters in between (Lev 6:8-7:38, Gen 46-50). Footnotes ("[3] …") move to
  the end of the essay that cites them (108); PG front matter and transcriber notes are dropped.

### SermonIndex conversion damage, and the repairs

1. **Every ALL-CAPS word of 8+ letters was deleted.** No SermonIndex module holds a single
   all-caps word of that length while 7-letter ones are common (Larkin: 399), so the rule is
   exact. Example: "THE REVELATION OF JESUS CHRIST" became "THE OF JESUS CHRIST", "companion in
   TRIBULATION" became "companion in .". Repair (`restore_caps`): align the module with an
   archive.org OCR of the same edition on 5-word sequences that occur once in each, diff the
   stretches between, and insert only words the scan has, the module lacks, and that are
   themselves 8+ letters and ALL-CAPS (or small capitals inside an all-caps heading).
   Restored: Larkin 526 words in 59 sections, plus 12 section headings read off the scan by hand
   (`patches` in the registry; the import fails if one stops applying); Gaebelein 111;
   Ironside 13. Visible traces left (`check_commentary.py` reports them): Gaebelein 27, Larkin 12,
   Ironside 5, Darby 1, Brooks 0 — mostly section headings, e.g. Gaebelein "II. THE OF THE
   HEAVENS AND THE EARTH" (GENERATIONS). There are surely others with no visible trace;
   Larkin, with caps on most pages, was the worst hit and is now close to the printed text.
2. **"is" became "Isaiah"** before numbers. Rule (`fix_is_isaiah`): "Isaiah N" with no ":verse"
   is "is N" when N has a thousands separator, decimal or fraction, or N > 66; when the next
   word is a quantity ("6 cubits", "8 times", "3 x 6", "766 to 679"); or when the word before is
   a number or date ("30 A. D. Isaiah 34"); and "Isaiah" directly before another book's
   reference is "is". Never after a label colon (Brooks: "Writer of the Book: Isaiah 766 to
   679 B. C." is left as it is, ambiguous). Changed: Larkin 9, Gaebelein 6, Brooks 2,
   Ironside 0, Darby 0. Examples: "(Daniel 9:25) Isaiah 476 years" → "is 476 years"; "30 A. D.
   Isaiah 34." → "is 34."; "the specific gravity of gold Isaiah 19.5" → "is 19.5"; "which
   Isaiah 6 times 7" → "is 6 times 7"; "This Exodus of the Psalms Isaiah 72, the great Kingdom
   Psalm" → "is 72". Real references ("(Isaiah 4)", "read Isaiah 53") are untouched; the test
   suite fails if any text the rule would still change is stored.
3. **Spacing**: "God’ s" → "God’s", "“ Elohim”" → "“Elohim”", "Israel , as" → "Israel, as".
4. **Entries over 64 KB**: the module index cuts them; `recover_orphans=True` restores the text
   from the compressed blocks (Gaebelein Matthew 13, 24, 26 grew from ~6 KB to ~70 KB). Those
   three Gaebelein entries still end with SermonIndex's own note "This entry is longer than a
   Bible module can hold. The rest is at …": the rest of those chapters is not in the module.
   They end with " […]" (counted as marked-incomplete). Ironside's three such notes are in
   books not imported.
5. Debris removed: "Submitted by H A Ironside on Tue, 03/11/2008", "~ end of chapter 16 ~",
   Markdown "**", Larkin's stray page digit at the start of every section ("62. THE THRONE").
   Brooks's James 5 entry carried a second copy of 1 Peter 1; it is cut.

Truncation check after import: mid-sentence endings Gaebelein 1, Ironside 1, Darby 1, Brooks
0, Mackintosh 0, Larkin 1 (all authentic or a closing quotation), none cap-truncated.

### Licence evidence, per source (what was checked, what remains unverified)

US rule as above: first published before 1931 = public domain. SermonIndex's module pages say
"Free to copy and pass on" and label the modules "Public Domain"; that label was **not** relied
on. Checked means compared on 2026-11-13 by word similarity against archive.org scans.

- **Gaebelein.** Checked: the module's books match *The Annotated Bible* volumes (Genesis 0.87,
  Job 0.92, Psalms 0.87, Daniel 0.91, Romans 0.91, Revelation 0.91; next-best volume always under
  0.11). Volume title pages: OT I ©1913, OT II ©1915, OT III ©1916, OT IV ©1921, NT I ©1913,
  NT II ©1916, NT III ©1917. Matthew: 92% of the module's Matthew is *The Gospel of Matthew: An
  Exposition* (scans `thegospelofmatth00gaebuoft`, title pages "Copyright 1910"; vol. 1 first
  printed 1903), only 33% of the Annotated Bible's own Matthew. Unverified: OT V (Daniel-Malachi)
  and NT IV (James-Revelation) carry no date in any scan; internal evidence ("the late great war",
  "parlor-bolshevists") and the same Our Hope imprint put them 1919-1922, and University of
  Wisconsin copies bear a 7 Nov 1928 accession stamp. The module also leaves out each book's
  introduction (e.g. Genesis "Revelation or Myth?"): what it has is 66-81% of each volume.
- **Ironside.** Checked per book against scans (5-word overlap / aligned share): Esther .94/.99
  (1921 revised ed.), Nehemiah .95/.99 (1925 ed.), Jeremiah .92/.99 and Lamentations .92/.99 (1928
  ed.), Minor Prophets .95-.97/≥.99 (1928 printing of 1909), Romans .96/.99 (1928), Colossians
  .94/.93 (1929; light editorial touches: "King James Version" for "Authorized", "(author's
  translation)" tags). Left out inside allowed books, because SermonIndex appended later works:
  Jeremiah 30 from about its middle and Hosea 3:4- ("Not Wrath But Rapture", in *Miscellaneous
  Papers*, 1941), Romans 11:25- (*The Great Parenthesis*, 1943, ch. VIII). Unverified: no 1905
  Esther, 1906 Jeremiah or 1909 Minor Prophets first edition is on archive.org; the scans are the
  pre-1931 revised editions named above, and the module matches those.
- **Darby.** First published 1857-1867, Darby d. 1882; nothing later could be in copyright.
  Unverified: the module conf names no printed source, and its text was not compared with a
  scan (it reads as the standard Morrish text).
- **Brooks.** Checked: 99.7% of module words match the first edition (archive.org
  `summarizedbible00broorich` OT and `summarizedbiblec00broorich` NT, title pages "Copyright 1919
  Keith L. Brooks", BIOLA); 1,121 of 1,189 chapters ≥0.95 similarity (the rest OCR splits). Three
  readings (1 Sam 27 Striking Facts, a sentence in Rev 17, "Promise: 20:6" in Rev 20) follow
  BIOLA's undated "Second Edition", which carries only the 1919 notice; the 1966 revision was
  not used. Unverified: the Second Edition's printing date (any US publication before 1978
  without a notice for new matter left that matter in the public domain).
- **Mackintosh.** Published 1858-1880, Mackintosh d. 1896. Project Gutenberg cleared the
  ebooks as US public domain; PG's licence is honoured by using only the text.
- **Larkin.** Scan `bookofrevelation00lark`: "Copyrighted 1919 By Clarence Larkin" (a later
  printing by the Rev. Clarence Larkin Estate, Glenside, Pa.). The module's text matches it apart
  from the deleted caps (above). Larkin d. 1924. The Estate still sells the books and charts;
  the 1919 text is public domain, the charts are not included.

### Not imported, and why

| Work | Why |
|---|---|
| James M. Gray, *Christian Workers' Commentary* (1915), SermonIndex `siconcise` | The module is an edited later version: book introductions and citations of other authors removed, phrasing modernised, and some new sentences added (e.g. Acts 2, Matt 1, Gen 12:10 "Group leaders may want to review…", 2 Kgs 15 "Local librarians will give further help"); about 98% of its words are Gray's but the added text is not 1915 and its date is unknown. The 1915 text exists only as archive.org OCR (`christianworkers00gray`, two columns, diagrams as garbage); keying it to lessons is a separate job |
| Darby, Synopsis, Old Testament | STEM Publishing and CCEL ask for permission; Project Gutenberg and Wikisource have nothing; SermonIndex has the NT only. archive.org has Morrish printings (`synopsisofbookso01darb`, `02darb`) but the OCR has no chapter divisions and 1-2% word errors: days of keying |
| Ironside, Daniel | The module's Daniel is the 1996 edited Loizeaux text (no chapter matches the 1911/1920 *Lectures on Daniel*), and Daniel 9 includes *The Great Parenthesis* (1943). The 1920 edition exists as OCR (`lecturesondaniel0000hair_d9x0`) with reference misreadings ("Mark 18" for 13) and page furniture; not imported from it in this wave |
| Ironside, Proverbs, Revelation, Philippians | Pre-1931 books, but the module has later edited wording (Revelation mentions "World War I"; Philippians cites a 1976 book) |
| Ironside, all other books in `siiron` | Later volumes; some renewed (Isaiah "Copyright @ 1952") |
| Gaebelein's book introductions; Matthew 13, 24, 26 after ~70 KB | Not in the module |

### Takedown

Policy: if a rights holder believes something here should not be published, we review the
claim promptly and remove the text if it holds. The app says so under About > Sources and
rights (direct link `/?about=sources`), which lists every commentary source with its author,
year and `license` line from `/api/commentary/sources`, links to LICENSES.md, and gives a
contact that needs no sign-in: a prefilled GitHub issue ("Rights enquiry: <work>"; fields for
work, claimant, basis, contact). The contact is defined once, `RIGHTS_CONTACT` in
`frontend/static/js/modules/menus.js`; setting its `email` shows a mailto link first. LICENSES.md
opens with the same paragraph. Removing a source: delete its registry entry and build step; the
`commentary_search` step drops its rows (see "How to rebuild").

## Second group: "public domain (no renewal found)" (2026-11-13)

Imported after the first wave, as its own registry entry and build step (Newell,
`commentary_newell`) and its own book list (`IRONSIDE_1931_47_NOT_RENEWED` inside the one
Ironside source), so the whole group can be dropped again by deleting the `newell` registry
entry and build step and that one list, then running the `commentary_ironside` and
`commentary_search` steps. **These works were first published 1932-1940, after the 1930
cut-off.** They are public domain in the US only if their copyright was not renewed in its
28th year (works published 1928-1963 needed a renewal; unrenewed ones fell into the public
domain). Their `license` reads **"Public domain (no renewal found)"**, and that basis rests
entirely on the transcribed renewal records below: a renewal the transcription missed would
mean the work is still in copyright (until 95 years after publication: 2030-2035).

| Source | Text shipped | Downloaded from | Entries | Books | Text MB |
|---|---|---|---:|---:|---:|
| Newell Verse by Verse (`newell`, order 70) | William R. Newell, *Romans Verse by Verse* (Grace Publications / Moody, 1938) and *The Book of the Revelation* (1935) | `https://sermonindex.net/modules/sword/sinewell.zip` | 387 | 2 | 3.4 |
| Ironside Expositions, second list | H. A. Ironside, *Studies in Hebrews and Titus* (1932; Hebrews only), *Addresses on the First Epistle to the Corinthians* (1938), *Addresses on the Second Epistle to the Corinthians* (1939), *Expository Messages on the Epistle to the Galatians* (1940) | `siiron.zip` as above | 95 of Ironside's 279 | 4 of 22 | 1.7 |

Newell's Romans is keyed by verse: each section (as SermonIndex stores it) is split at Newell's
"Verse 24:" / "Verses 3 and 4:" markers into one row per marked verse or verses (310 rows), and
the section's opening (his translation of the passage and headings) is a row over the whole
section. Ten of Newell's sections were cut by SermonIndex at ~70 KB ("This entry is longer than a
Bible module can hold"); they end with " […]" (Romans 1:1-7, 3:21-31, 4:18-25, 5:1-11, 5:12-21,
6:1-11, 7:7-25, 8:1-11, 8:31-39, 11:11-24 and Revelation 1 are the affected sections; the rest
of those sections is not in the module). The module's Romans 1:1 entry opened with a second copy
of the 1:24-27 notes; it is dropped. The module has no Hebrews (Newell's *Hebrews Verse by Verse*,
1947, renewed 1975, is excluded; a test fails if a Newell Hebrews row appears).

### Renewal search (what was searched, what was found)

Data: NYPL's transcription of the Catalog of Copyright Entries renewal volumes 1950-1977 plus
the Copyright Office renewal records 1978-2001 (github.com/NYPL/cce-renewals, `data/*.tsv`,
445,386 rows; copy in the research scratch directory). Every field of every row was searched
case-insensitively for "ironside", "koppin" (Ironside's daughter, Lillian Ironside Koppin, who
renewed his books from 1975) and "newell" (claimant Philip/Phillip R. Newell), and for each title
below; publisher names (Loizeaux, Moody, Our Hope, Bible Institute Colportage) were also swept.
**The search finds the known renewals**, so a miss means something:

- found: Newell, *Hebrews verse by verse* (©13Aug47, A15063; renewed 11Aug75, R611479, Phillip R.
  Newell) and *Famous messages* (1951; RE26853);
- found: Ironside, *The lamp of prophecy* (1940; R428751, 1968), *The great parenthesis* (1943;
  R499630, 1971), *What's the answer* (1944), *Divine priorities* (1945), *Addresses of the First
  and Second Epistles of Thessalonians* (1947; R609276), *Timothy, Titus and Philemon* (1947;
  R609277), *Expository notes on the Gospel of Mark* (1948), *… Matthew* (1948), *The daily
  sacrifice* (1948), *Expository notes on Ezekiel* (1949), *Addresses on the Book of Joshua*
  (1950; RE4643), *Studies on book one of the Psalms* (1952), *Expository notes on the prophet
  Isaiah* (1952; RE67098), *Doctor Ironside's Bible* (1955).

| Work | Published | Renewal due (27th-28th year) | Searched | Result |
|---|---|---|---|---|
| Newell, *The Book of the Revelation* | 1935 | 1962-1963 | "newell", "book of the revelation", "revelation" + verse/lectures | no renewal found |
| Newell, *Romans Verse by Verse* | 1938 | 1965-1966 | "newell", "romans verse by verse", "verse by verse" | no renewal found |
| Ironside, *Studies in Hebrews and Titus* (Hebrews) | 1932 | 1959-1960 | "ironside", "koppin", "hebrews and titus", "epistle to the hebrews" | no renewal found |
| Ironside, *Addresses on the First Epistle to the Corinthians* | 1938 | 1965-1966 | "ironside", "koppin", "first epistle to the corinthians" | no renewal found |
| Ironside, *Addresses on the Second Epistle to the Corinthians* | 1939 | 1966-1967 | as above, "second epistle…" | no renewal found |
| Ironside, *Expository Messages on the Epistle to the Galatians* | 1940 | 1967-1968 | "ironside", "koppin", "epistle to the galatians" | no renewal found |
| Ironside, *Addresses on the Epistles of John and Jude* | 1931 | 1958-1959 | "epistles of john" | no renewal found, **but not imported**: the module's text could not be confirmed as the 1931 volume (1 John 5 ends with *Full Assurance*, 1937) |
| Ironside, *In the Heavenlies* (Ephesians) | 1937 | 1964-1965 | "in the heavenlies" | no renewal found, **not imported**: the module is a modern e-text with added wording ("this sermon was delivered in 1936") |
| Ironside, *Addresses on the Gospel of John* | 1942 | 1969-1970 | "gospel of john" | no renewal found, **not imported**: partly edited text |
| Ironside, *Lectures on the Book of Acts* | 1943 | 1970-1971 | "book of acts", "acts of the apostles" | no renewal found, **not imported**: heavily edited ("During World War II"; 21 of 48 sampled phrases in no edition) |
| Ironside, *Expository Notes on James and Peter* | 1947 | 1974-1975 | "epistle of james", "epistles of peter" | no renewal found, **not imported**: not confirmed against the 1947 text; 2 Peter 3 ends with an essay from *Miscellaneous Papers* |
| Ironside, Titus (in *Hebrews and Titus*, 1932) | 1932 | 1959-1960 | | **not imported**: the same lectures are reprinted in *Timothy, Titus and Philemon* (1947), renewed 1975 (R609277); which printing the module copied can't be told |

Still excluded because renewed: Ironside's Isaiah, Psalms, Ezekiel, Matthew, Mark, Joshua,
Thessalonians, Timothy/Titus/Philemon, *The Great Parenthesis*, *The Lamp of Prophecy*; Newell's
Hebrews.

**Is the module text that volume?** Ironside's four books were checked by sampling 9-word phrases
from every chapter and running them through archive.org's full-text search, which covers the
borrow-only scans of the original editions (their text cannot be downloaded): Galatians 13 of
14 phrases found in the 1940 book, 2 Corinthians 27/31 (1939), 1 Corinthians 33/39 (1938),
Hebrews 27/36 (1932; 5 phrases found nowhere, so light editing is possible). A word-for-word
control (Esther) scored 14/17 the same way. This is weaker evidence than the full-text
comparisons of the first wave. Newell's text was **not** compared with the 1935/1938 editions
(none is downloadable); it is unverified whether SermonIndex's text is the first edition or a
later Moody printing (new matter in a later printing, if any, would have its own date).

## Notes for the study view (UI)

- Read `commentary_sources` for chips (`short_name`), ordering (`sort_order`), `kind`, `coverage`,
  `license` and `attribution`. Every `commentary_entries.source` has exactly one row (tested).
- `attribution_short` (one line; set only where the license requires credit, i.e. Tyndale, NULL
  elsewhere), `requires_attribution` (1/0), `size_bytes` (UTF-8 bytes of the source's `content`,
  written by the build; tested to match). Under CC BY-SA 4.0 s.3(a)(2) the short line may stand
  in for the full credit if the full one (`attribution`, which also names the license and states
  the changes) is a tap away, e.g. on the info sheet.
- Default order (`sort_order` 10..120, set by the owner): Scofield, Gill, JFB, Tyndale,
  Gaebelein, Ironside, Newell, Darby, Brooks, Mackintosh, Larkin, Treasury of David. The same order is `DEFAULT_ORDER` in `scripts/commentary_registry.py` (keys) and
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
