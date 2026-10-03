# Resource License Review (2026-10)

Researched 2026-10-02 for Bible MVP (free PWA, SQLite, offline download, possibly donation-supported).
Test applied to each resource: can we store it in bulk, ship it inside a downloadable DB for offline use, and keep doing that if the site takes donations?

**Sources.** Each license was checked at the publisher's site or the repo's LICENSE/README where one could be reached. Where that wasn't possible, the row says what was used (CrossWire `mods.d` conf files, eBible.org detail pages, the HelloAO `available_*.json` metadata) and is marked **UNVERIFIED** when no primary source could be reached.

**Verdicts.**
- **ADD**: clean license, clean machine-readable source.
- **ADD-WITH-CARE**: usable, but has a share-alike, attribution, provenance, or completeness issue to handle first.
- **SKIP**: license blocks us, or no clean source exists.

**Not legal advice.**

## Corrections to the current repo (found while researching)

| Item | Current claim | Actual |
|---|---|---|
| BSB (`LICENSES.md`, `translations.license_info`) | "CC BY 4.0" | **Public domain (CC0) since 2023-04-30** per berean.bible/terms.htm. Attribution "appreciated but not required". If we change the text, we must not call the result "Berean". CrossWire's `bsb.conf` also says CC0. |
| Matthew Henry (`LICENSES.md`) | "Concise, from CCEL" | The DB holds the **Complete** commentary (avg entry ~8.4k chars), imported from **HelloAO** (`scripts/import_commentary.py`). HelloAO's `matthew-henry` set has 65 books, and **Song of Solomon is missing at the source**. |
| Cross-references (`LICENSES.md`) | "TSK, public domain" | The app uses OpenBible.info cross-references. They are **CC BY 4.0, attribution to OpenBible.info required** (openbible.info/labs/cross-references). They are derived from TSK, but the dataset itself is CC BY. |
| ASV | Task brief lists it as a candidate | **Already in the DB** (`translations` row `ASV`). |
| SBLGNT (`TRANSLATION_SOURCE_TEXT_RESEARCH.md`) | "non-commercial EULA" | **CC BY 4.0 since 2022-12-19** (LogosBible/SBLGNT README and LICENSE). |
| STEPBible TBESH (in use or planned) | CC BY 4.0 | See Traps #1: the file's own header asks you to get Online Bible's permission for the brief definitions. |

## Summary table

Abbreviations: PD = public domain; SA = share-alike; NC = non-commercial; HelloAO = `https://bible.helloao.org/api/...` (JSON); eBible = `https://ebible.org/find/details.php?id=<id>` (USFM, USFX, VPL, SWORD, etc.); CW = CrossWire SWORD module (`https://www.crosswire.org/sword/modules/ModInfo.jsp?modName=<mod>`).

### Translations

| Resource | License | Offline OK? | Attribution | Restrictions | Source + format | Verdict |
|---|---|---|---|---|---|---|
| BSB | PD / CC0 (2023-04-30) | Yes | Optional | Can't call a modified text "Berean" | berean.bible/downloads.htm: USFM, USX, USJ, txt, xlsx, `bsb_tables.tsv` (interlinear tables); HelloAO `BSB` | Already in; fix the license label |
| Berean Literal Bible (BLB) | PD / CC0 (same declaration) | Yes | Optional | Same naming rule; **NT only** | berean.bible/downloads.htm: txt, xlsx, docx | ADD |
| ASV 1901 | PD | Yes | None | None | eBible `eng-asv`; HelloAO `eng_asv`; CW `ASV` (OSIS, with Strong's) | Already in |
| YLT (1898) | PD | Yes | None | None | eBible `engylt`; HelloAO `eng_ylt`; CW `YLT` | ADD |
| Darby (1889) | PD | Yes | None | None | HelloAO `eng_dby` (eBible `engDBY`); CW `Darby` (OSIS, with Strong's) | ADD |
| Geneva 1599 | PD | Yes | None | Original spelling, not modernized | eBible `enggnv`; HelloAO `eng_gnv`; CW `Geneva1599` ("electronic edition edited by Mark Langley", marked PD) | ADD |
| Douay-Rheims (1899 American / Challoner) | PD | Yes | None | Includes deuterocanon; we need a policy for non-66-book canons | eBible `engDRA`; HelloAO `eng_dra`; CW `DRC` | ADD-WITH-CARE (canon handling) |
| Literal Standard Version (LSV) | **CC BY-SA 4.0**, © 2020 Covenant Press | Yes | Required: copyright line plus a note of any changes | SA applies to adaptations | eBible `englsv` (USFM, USFX, VPL+SQL); HelloAO `eng_lsv` | ADD-WITH-CARE (SA) |
| unfoldingWord ULT / UST | **CC BY-SA 4.0** (unfoldingword.org/ult) | Yes | Required. If modified, **remove the unfoldingWord® trademark** and credit "The original work by unfoldingWord is available from unfoldingword.org/ult" | SA; trademark rule; both texts are "In Progress v85" (not complete) | git.door43.org `unfoldingWord/en_ult`, `en_ust` (USFM; the door43 fetch was bot-blocked, **UNVERIFIED** download path); mirror at github.com/BibleAquifer/unfoldingWordLiteral | ADD-WITH-CARE (incomplete, SA) |
| Free Bible Version (FBV) | **CC BY-SA 4.0**, © 2018 Jonathan Gallagher (per eBible) | Yes | Required | SA. eBible text says "NT and Psalms" but HelloAO `eng_fbv` reports 66 books. Primary site freebibleversion.org **not checked (UNVERIFIED)** | eBible `engfbv`; HelloAO `eng_fbv` | ADD-WITH-CARE |
| Open English Bible (OEB) | **CC0** (openenglishbible.org) | Yes | None | **Incomplete OT**: NT, Psalms and some OT books (Genesis added Dec 2025) | openenglishbible.org (USFM); eBible `engoebus`; CW `OEB` | ADD-WITH-CARE (gaps) |
| Lexham English Bible (LEB) | Copyright Logos. CW conf: "Copyrighted; Free non-commercial distribution". The full license URL (lexhamenglishbible.com/license) is **dead (DNS fails)**; lexhampress.com/LEB-License redirects to a Baker store search | Unclear | Required | NC per CW; the full terms can't currently be read | CW `LEB` | SKIP (**UNVERIFIED** terms) |
| NET Bible | © Biblical Studies Press, all rights reserved (netbible.com/copyright) | Free apps may quote with "(NET)" hyperlinked to netbible.org | Required notice | Free copies "**cannot be bundled with anything sold, used as a gift to solicit donations**". Commercial use goes through HarperCollins | eBible `engnet`; HelloAO `eng_net`; CW `NETfree` (all marked "Copyrighted") | SKIP (donation clause; whole-text bundling needs written permission) |
| KJV | PD in the US | Yes | None | Crown patent in the UK (see Traps) | Already in | Already in |
| WEB | PD; "World English Bible" is a trademark | Yes | None | Can't call a modified text "WEB" | Already in | Already in |

### Commentaries

| Resource | License | Offline OK? | Attribution | Restrictions | Source + format | Verdict |
|---|---|---|---|---|---|---|
| Matthew Henry Complete: **Song of Solomon** | PD. CCEL ThML `<DC.Rights>` says "Public domain. May be copied and distributed freely." | Yes | Courtesy credit to CCEL | CCEL's site-wide policy (see Traps #4) | **https://ccel.org/ccel/henry/mhc3.xml** (ThML). Has `div2 id="Song.i"` (intro) through `Song.ix` (ch. 1–8). Also CW `MHC` (PD, "prepared from CCEL"). Both cover SNG | ADD (fills the gap) |
| Jamieson-Fausset-Brown | PD | Yes | None | None | HelloAO `jamieson-fausset-brown` (66 books, JSON); CW `JFB` (OSIS, from CCEL) | ADD |
| Keil & Delitzsch (OT) | PD | Yes | None | None | HelloAO `keil-delitzsch` (39 books); CW `KD` (OSIS, from Wikisource) | ADD |
| Calvin's Commentaries | PD (CCEL: "usable for any purpose", quoted in HelloAO notes) | Yes | None | Calvin wrote no commentary on Judges–Song or Revelation; HelloAO has 48 books | HelloAO `john-calvin`; CW `CalvinCommentaries` | ADD |
| Adam Clarke | PD | Yes | None | **HelloAO is missing DEU, JDG, PSA, PRO, ECC, JER, JOL, MAL, MAT** (57 books) | Use CW `Clarke` (OSIS, from Wikisource) for the full set; HelloAO `adam-clarke` is partial | ADD-WITH-CARE (pick the complete source) |
| Barnes' Notes | PD | Yes | None | CW `Barnes` is **NT only**; no clean OT source verified | CW `Barnes` (ThML) | ADD (NT) |
| Wesley's Notes | PD | Yes | None | None | CW `Wesley` (ThML, Kelley/Brown e-text) | ADD |
| Matthew Poole | PD (1680s) | Yes for the text | — | The only structured source found (sermonindex.net SWORD/MyBible) says "**may never be sold or used commercially**" | sermonindex.net/commentary/poole | SKIP until a clean source exists |
| Pulpit Commentary | PD (1880–1919) | — | — | No clean structured source. Copies are in e-Sword/SwordSearcher (vendor-converted) or BibleHub (do not scrape) | none verified | SKIP |
| Ellicott | PD (1878–84) | — | — | Same problem as the Pulpit Commentary | none verified | SKIP |
| Vincent's Word Studies (1887) | PD | — | — | Only archive.org scans/OCR; no SWORD/OSIS edition found | archive.org (OCR) | SKIP (effort) |
| A.T. Robertson, Word Pictures | **Mixed.** Vols 1–4 (1930–31) PD per CW. **Vol 5 (1932) and vol 6 (1933) were renewed in 1960 by Broadman** | No, for vols 5–6 | — | CW conf says "Copyrighted; Free non-commercial distribution". See Traps #3 for when it clears | CW `RWP` (OSIS) | SKIP now. Revisit 2029 (vols 1–4 earlier, if the renewal status is confirmed) |
| Geneva Bible notes (1599) | PD text | Yes | — | CW `Geneva` conf has **no DistributionLicense field**; provenance **UNVERIFIED** | CW `Geneva` (ThML) | ADD-WITH-CARE |
| Tyndale Open Study Notes (bonus) | **CC BY-SA 4.0** (tyndaleopenresources.com) | Yes | Required | SA | HelloAO `tyndale` (JSON: notes, intros, profiles); ZIP downloads at tyndaleopenresources.com | ADD-WITH-CARE (SA) |

### Lexicons and dictionaries

| Resource | License | Offline OK? | Attribution | Restrictions | Source + format | Verdict |
|---|---|---|---|---|---|---|
| STEPBible TBESH | Labeled CC BY 4.0 | See Traps | "STEP Bible" linked to STEPBible.org | **File header says the brief defs come from Online Bible's Abridged BDB and that "Permission should be gained from Online Bible"** | github.com/STEPBible/STEPBible-Data `/Lexicons` (TSV) | ADD-WITH-CARE (use BDB below instead, or get permission) |
| STEPBible TBESG | Labeled CC BY 4.0 | Yes | As above | Mostly Abbott-Smith (PD). Gaps are filled from Middle Liddell (Perseus, **CC BY-SA**) and **Mounce's Teknia (license UNVERIFIED)**. G6100+ entries come from the Apostolic Bible Polyglot (copyrighted) | same repo, TSV | ADD-WITH-CARE (filter `(ML)`/Mounce rows, or treat as SA) |
| STEPBible TFLSJ | Labeled CC BY 4.0 | Yes | As above | **Built on Perseus LSJ, which is CC BY-SA 4.0** (PerseusDL/lexica). Treat it as SA | same repo, TSV (two files) | ADD-WITH-CARE (SA) |
| Abbott-Smith (1922) | PD, markup included (repo README); markup is complete | Yes | Courtesy | **Don't ship the repo's archive.org PDF**: "certain restrictions apply" to it | github.com/translatable-exegetical-tools/Abbott-Smith `abbott-smith.tei.xml` (TEI); CW `AbbottSmith` | ADD |
| Dodson Greek | PD; repo license CC0 | Yes | None | Glosses are brief | github.com/biblicalhumanities/Dodson-Greek-Lexicon (XML, Strong's-keyed); CW `Dodson` | ADD |
| Thayer's (1889) | PD text | — | — | No clean structured source verified. Strong's-coded print editions (Hendrickson/Baker) are later, copyrighted works | archive.org scans only (**UNVERIFIED** digital source) | SKIP (use Abbott-Smith + Dodson) |
| Brown-Driver-Briggs | Text PD; OpenScriptures markup **CC BY 4.0**, credit "Open Scriptures Hebrew Bible Project" | Yes | Required | Completeness of the BDB XML **UNVERIFIED** (check before import) | github.com/openscriptures/HebrewLexicon `BrownDriverBriggs.xml` + `LexicalIndex.xml` + `HebrewStrong.xml` (Strong's ↔ BDB map) | ADD |
| Easton's (1897) | PD | Yes | None | — | CW `Easton` (TEI); also `json/easton.json` in the Theographic repo (but that repo is CC BY-SA) | ADD |
| Smith's (1863) | PD | Yes | None | — | CW `Smith` (ThML) | ADD |
| ISBE 1915 | PD | Yes | None | Large | CW `ISBE` (TEI) | ADD (lower priority) |
| Torrey's Topical Textbook | PD | Yes | None | Overlaps Nave's | CW `Torrey` (ThML) | ADD (low priority) |
| Tyndale Open Bible Dictionary (bonus) | CC BY-SA 4.0 | Yes | Required | SA | tyndaleopenresources.com (ZIP) | ADD-WITH-CARE |

### Structured data

| Resource | License | Offline OK? | Attribution | Restrictions | Source + format | Verdict |
|---|---|---|---|---|---|---|
| Theographic Bible Metadata | **CC BY-SA 4.0** (repo LICENSE) | Yes | Required | SA | github.com/robertrouse/theographic-bible-metadata `json/` (people, places, events, peopleGroups, easton) and `CSV/`; also HelloAO dataset `theographic` | ADD-WITH-CARE (SA) |
| OpenBible.info geocoding | **CC BY 4.0** (repo license.txt). Embedded OpenStreetMap geometry is **ODbL**; image licenses vary | Yes | "OpenBible.info" | Drop OSM geometry and images, or comply with ODbL | github.com/openbibleinfo/Bible-Geocoding-Data `data/*.jsonl` (ancient, modern, geometry, image, source) | ADD |
| OpenBible cross-refs | CC BY 4.0 | Yes | OpenBible.info | — | a.openbible.info/data/cross-references.zip (TSV) | Already in; fix attribution |
| LXX: Rahlfs / CCAT morphology | **CC BY-NC-SA** (eliranwong/LXX-Rahlfs-1935). CCAT also requires a signed user declaration | No (NC) | — | NC + CCAT declaration | — | SKIP |
| LXX: CW `LXX` module | "Copyrighted; Free non-commercial distribution" | No | — | NC | — | SKIP |
| LXX: Swete (First1KGreek) text | **CC BY-SA 4.0** (nathans/lxx-swete, from OpenGreekAndLatin) | Yes | Required | SA; **text only, no morphology** | github.com/nathans/lxx-swete | ADD-WITH-CARE (text only) |
| LXX: eliranwong/LXX-Swete-1930 (Tauber morphology) | Repo is GPL-3.0; licensing of the morphology layer is an **open question** (issue #4) | Unclear | — | Provenance unresolved | — | SKIP for now |
| LXX: STEPBible TAGOT | Would be CC BY when released | — | — | **Not released** ("still being finished"). Its morphology is "based on CCAT", so watch for inherited NC terms | — | Watch |
| LXX English: Brenton | PD | Yes | None | — | eBible `eng-Brenton`; HelloAO `eng_bre` | ADD (cheap substitute) |
| Tyndale House GNT (THGNT) | **© Tyndale House 2017, published by Crossway; not open** | No | — | — | — | SKIP as a standalone text. Its readings are already marked per word in TAGNT (CC BY) |
| Robinson-Pierpont Byzantine (2018) | **PD**; repo is The Unlicense | Yes | Courtesy | — | github.com/byztxt/byzantine-majority-text `csv-unicode/` (with parsing and Strong's), BETA, TEI | ADD |
| SBLGNT | CC BY 4.0 | Yes | Required | — | github.com/LogosBible/SBLGNT | ADD (if a CT Greek text is needed) |
| MACULA Greek | CC BY 4.0 (Biblica); bundles MARBLE word senses "used with permission" | Yes | "MACULA Greek Linguistic Datasets…" | Check the MARBLE `@ln`/`@domain` fields separately | github.com/Clear-Bible/macula-greek (TSV/XML) | ADD-WITH-CARE |

### Audio (brief)

| Resource | License | Offline OK? | Notes | Verdict |
|---|---|---|---|---|
| BSB audio (Souer; also Hays, Gilbert) | Described as CC0 by archive.org and podcast listings. **Not confirmed on berean.bible (UNVERIFIED at primary)** | Probably | MP3 at `openbible.com/audio/souer/BSB_<nn>_<Abc>_<ccc>.mp3`; whole-OT zip is 4.2 GB, NT 921 MB | ADD-WITH-CARE (confirm in writing; stream rather than bundle) |
| WEB audio (Michael Paul Johnson) | PD: "not copyrighted… download, copy, mirror, and share" (ebible.org/webaudio) | Yes | MP3 and OGG | ADD |
| WEB audio (FCBH NT, Henson, others) | No explicit license on the page | — | — | SKIP (UNVERIFIED) |
| KJV audio | LibriVox recordings are PD; not checked individually | — | — | UNVERIFIED |

## Recommended next 6 imports

Ranked by study value per unit of effort, with weight on mobile word study and the existing schema (`lexicon`, `commentary_entries`, `translations`/`verses`).

1. **Matthew Henry Song of Solomon gap.** Parse the `Song.ii`–`Song.ix` divs from `ccel.org/ccel/henry/mhc3.xml` into `commentary_entries` (source "Matthew Henry"). Hours of work; closes a visible hole. While there, correct the BSB, Henry and cross-ref entries in `LICENSES.md` and `translations.license_info`.
2. **Greek lexicon depth: Dodson (CC0) + Abbott-Smith (PD).** Both are Strong's-keyed or Strong's-mappable. They fit `lexicon.definition` and `extended_definition` (or a small `lexicon_sources` side table) with no license strings attached. This is the biggest gain for tap-a-word study on a phone.
3. **Hebrew lexicon depth: OpenScriptures BDB (CC BY 4.0).** Join `HebrewStrong.xml` to `LexicalIndex.xml` to `BrownDriverBriggs.xml`. This replaces any reliance on TBESH brief defs (Traps #1). Effort is moderate (XML) and the value is high.
4. **More commentaries via the existing HelloAO importer: JFB (66 books), Keil & Delitzsch (39), Calvin (48).** About zero new code; just add the IDs to `import_commentary.py`. Take Clarke, Wesley and Barnes NT later from CrossWire OSIS/ThML. Watch DB size, since offline download is the product.
5. **Literal translations pack: YLT + Darby (PD, HelloAO), BLB NT (PD, berean.bible txt).** These fit the existing `translations` table, and literal renderings help word study. LSV is a good fourth if you accept SA.
6. **Places and people: OpenBible geocoding (CC BY) + Theographic people/events (CC BY-SA).** New tables are needed, so the effort is higher. Value is high for "who/where is this" taps. Start with geocoding (cleaner license, JSONL), then add Theographic.

Next in line: Robinson-Pierpont Byzantine CSV (gives KJV/WEB readers a fitting Greek text; see `TRANSLATION_SOURCE_TEXT_RESEARCH.md`), Tyndale Open Study Notes, and Easton's dictionary.

## Traps

1. **STEPBible's "CC BY" label is not uniform underneath.**
   - The TBESH header says its brief definitions are "based on Abridged BDB by Online Bible… Permission should be gained from Online Bible before these definitions are applied in any project."
   - TBESG fills gaps from Middle Liddell (Perseus, CC BY-SA) and Mounce's Teknia (license unverified), and draws G6100+ entries from the Apostolic Bible Polyglot (copyrighted).
   - TFLSJ is built on Perseus LSJ (CC BY-SA 4.0).
   - The same repo also contains `TTESV … CC BY-NC.txt` (ESV tags, non-commercial). Never bulk-import that directory.
   - The headers also ask: "Please do not redistribute it yourself." CC BY allows redistribution, but this is a stated preference worth honoring by linking back.
2. **NET Bible's free terms exclude donation contexts.** Free copies "cannot be bundled with anything sold, used as a gift to solicit donations". Its app wording covers quotations, not whole-text bundling.
3. **RWP's "copyright expired 2006/2007" note is wrong under current US law.** The CrossWire note predates the 1998 term extension. Renewed 1932 and 1933 works run 95 years, so vol 5 (John, Hebrews) should clear 2028-01-01 and vol 6 (James–Revelation) 2029-01-01. Renewal facts come from the CW conf, not checked against Copyright Office records.
4. **CCEL's site policy vs. its file headers.** The site policy says works "may be used for personal, educational, or non-profit purposes" and commercial reuse needs permission; CCEL also claims its markup and editorial additions. The ThML file header says "Public domain. May be copied and distributed freely." A free app with donations is probably fine, but if the app ever charges, prefer CrossWire or HelloAO derivatives or re-key from scans.
5. **Poole via sermonindex has a non-commercial condition** on a PD text. The PD status of the work does not override the terms on someone's digitization.
6. **HelloAO coverage gaps.** Matthew Henry has no SNG. Adam Clarke is missing 9 books, including Psalms and Matthew. Calvin has 48 books (expected). Always diff the book lists after import.
7. **Septuagint.** Almost every morph-tagged LXX traces back to CCAT/Rahlfs (NC plus a signed declaration). Rahlfs' Greek text itself is © Deutsche Bibelgesellschaft. The only clearly open option today is Swete text (CC BY-SA) with no morphology.
8. **THGNT is not open.** It is © Tyndale House, published by Crossway. Only its *readings* reach us, via TAGNT edition flags.
9. **Share-alike resources** (LSV, ULT/UST, FBV, Theographic, Tyndale Open, TFLSJ, Swete). Keep each in its own clearly attributed tables or rows, and record any changes made. Any adapted version we publish (including the downloadable DB slice) must stay CC BY-SA. App code (MIT) is unaffected.
10. **Trademark and name clauses.** WEB, Berean and unfoldingWord® all forbid using their name on a modified text. Normalizing whitespace and markup is fine; editing words is not.
11. **KJV is under Crown patent in the UK.** It is PD in the US, but printing and distribution rights in the UK belong to the Crown (via Cambridge University Press). This is low risk for a web app, but worth knowing if the app is ever distributed through a UK store.
12. **OSM data inside OpenBible geocoding is ODbL,** not CC BY. Strip `geometry` and OSM-derived fields, or carry ODbL attribution and share-alike.
13. **The LEB license page is gone** (DNS failure; the old URL now redirects to a bookstore search). Don't rely on remembered "free LEB" terms.
14. **Theographic bundles Easton's** under its CC BY-SA repo license. Take Easton's from CrossWire (PD) to avoid SA on PD content.
