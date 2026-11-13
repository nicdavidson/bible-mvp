# Content Licenses

This document tracks the licensing status of all content included in BibleMVP.

## Code License

The BibleMVP source code is licensed under the **MIT License**.

---

## Bible Translations

| Translation | Status | Source | Notes |
|-------------|--------|--------|-------|
| BSB (Berean Standard Bible) | Public Domain (CC0, since 2023-04-30) | [berean.bible](https://berean.bible/terms.htm) | Modern translation, default. Attribution appreciated, not required; a modified text must not be called "Berean" |
| WEB (World English Bible) | Public Domain | [open-bibles](https://github.com/seven1m/open-bibles) | Explicitly released to public domain |
| KJV (King James Version) | Public Domain | Various | 1611, public domain worldwide |
| ASV (American Standard Version) | Public Domain | Various | 1901, public domain |

---

## Lexicons & Reference

| Resource | Status | Source | Notes |
|----------|--------|--------|-------|
| Strong's Concordance | Public Domain | [openscriptures](https://github.com/openscriptures/strongs) | Original 1890 work |
| Dodson Greek Lexicon | Public Domain / CC0 1.0 | [biblicalhumanities/Dodson-Greek-Lexicon](https://github.com/biblicalhumanities/Dodson-Greek-Lexicon) | Repo LICENSE is CC0; Dodson's own note releases it into the public domain. Kept as its own rows in `lexicon_entries` |
| Abbott-Smith, *Manual Greek Lexicon of the NT* (1922) | Public Domain | [translatable-exegetical-tools/Abbott-Smith](https://github.com/translatable-exegetical-tools/Abbott-Smith) | README: the TEI file "including the marked up version ... is in the public domain". The repo's archive.org PDF has restrictions and is not used |
| Brown-Driver-Briggs + Lexical Index (OpenScriptures) | **CC BY 4.0** (markup); BDB text public domain | [openscriptures/HebrewLexicon](https://github.com/openscriptures/HebrewLexicon) | Credit "Open Scriptures Hebrew Bible Project" wherever BDB entries or BDB root families are shown (`word_study_sources.attribution`). Abridged edition: most entries carry the sense outline only |
| Nave's Topical Bible (1896) | Public Domain | `data/naves/` | Topic verse lists |
| Derived word-study tables (`lemma_*`) | CC BY 4.0 | this project, `scripts/build_word_study.py` | Computed from STEPBible data, the alignments, Nave's and OpenBible.info cross-references; see docs/WORD_STUDY_2026-11.md |

STEPBible's own lexicons (TBESH, TBESG, TFLSJ) are **not** used: see Traps 1 in
docs/RESOURCE_LICENSES_2026-10.md.

---

## Commentaries

Full license reasoning, sources and per-source notes: [docs/COMMENTARY_LIBRARY_2026-11.md](docs/COMMENTARY_LIBRARY_2026-11.md).
The same metadata ships in the `commentary_sources` table. US public-domain status is argued from
first publication (before 1931) and the author's death, not from a website's label.

| Commentary (`source`) | Status | Source used | Notes |
|------------|--------|--------|-------|
| Matthew Henry (Complete) | Public Domain | CrossWire `MHC` (CCEL text). Not HelloAO, which cuts long entries at 32,767 bytes | Published 1708-1710; Henry d. 1714. Earlier listed here as "Concise, CCEL", which was wrong |
| John Gill | Public Domain | HelloAO API | Published 1746-1763; Gill d. 1771 |
| Jamieson-Fausset-Brown | Public Domain | HelloAO API (matches CCEL) | Published 1871; authors d. 1880, 1897, 1910 |
| Keil & Delitzsch | Public Domain | HelloAO API; 1 Chronicles, Song of Solomon and the ends of 17 length-capped entries from CrossWire `KD` (Wikisource text) | English translation T. & T. Clark 1864-1878; authors d. 1888, 1890 |
| John Calvin | Public Domain | HelloAO API (CCEL text) | Calvin Translation Society English, 1843-1855 |
| Adam Clarke | Public Domain | CrossWire `Clarke` (Wikisource text) | Published 1810-1826; Clarke d. 1832 |
| Barnes' Notes (NT) | Public Domain | CrossWire `Barnes` | Published 1832-1851; Barnes d. 1870 |
| John Wesley | Public Domain | CrossWire `Wesley` (Kelley/Brown e-text) | Published 1755 (NT), 1765 (OT); Wesley d. 1791 |
| People's New Testament | Public Domain | CrossWire `PNT` | Published 1889-1891; B. W. Johnson d. 1894 |
| Scofield Notes (1917) | Public Domain | CrossWire `Scofield` (Wikisource text) | 1917 edition only; the 1967 New Scofield notes are copyrighted. "Scofield" is used descriptively |
| Treasury of David | Public Domain | CrossWire `TDavid` (Spurgeon Archive text) | Published 1869-1885; Spurgeon d. 1892. Spurgeon's own exposition only |
| Catena Aurea | Public Domain | CrossWire `Catena` (github.com/lemtom/catena, CC0) | Newman's English translation, Oxford 1841-1845 |
| Tyndale Study Notes | **CC BY-SA 4.0**, (C) 2022 Tyndale House Publishers | tyndaleopenresources.com ZIP | Short credit (`commentary_sources.attribution_short`): "Adapted from Tyndale Open Study Notes © 2022 Tyndale House Publishers, CC BY-SA 4.0", linked to the full credit. Share-alike: credit "Adapted from Tyndale Open Study Notes. The original work by Tyndale House Publishers is available for free at http://www.tyndaleopenresources.com." Changes: XML converted to plain text with reference links; wording unchanged. Any published DB slice containing these rows stays CC BY-SA for these rows |

Not imported (see the library doc for reasons): Matthew Henry Concise (abridger and date unverified),
Geneva Bible notes and Family Bible Notes (provenance unverified), Robertson's Word Pictures (vols 5-6
still under renewed copyright), NET Bible notes and KingComments (copyrighted, non-commercial terms),
Luther (CrossWire module mixes in translations from 1915-1949), Matthew Poole (only source is
non-commercial), HistoricalChristianFaith Commentaries-Database (mixes in copyrighted "fair use"
excerpts), Pulpit, Ellicott, Expositor's, Cambridge Bible (no clean verse-keyed source found).

## Hymns

Full reasoning and the sources that were rejected: [docs/HYMN_INDEX_2026-11.md](docs/HYMN_INDEX_2026-11.md).

| Resource | Status | Source | Notes |
|----------|--------|--------|-------|
| Open Hymnal Project, edition 2026.11 (metadata, topical and Scripture indexes) | Public Domain | [openhymnal.org](http://openhymnal.org/copying.html) | "All content produced specifically by the Open Hymnal which is not a part of a hymn is placed into the public domain ... compilation, indices ... and all other data files." Hymn words and music have per-hymn terms (`hymns.copyright`); we store a hymn's first line only when its words are public domain (`hymns.words_public_domain`) |
| Computed hymn-to-KJV quotation links | Public Domain inputs | this project, `scripts/import_hymns.py` | Shared word runs between public-domain hymn words and the KJV |

Not used without written permission: Hymnary.org (all rights reserved), the Cyber Hymnal
(hymntime.com page code copyrighted). CCEL hymnals: not used (non-profit-only wording,
markup claimed by CCEL).

## Devotionals

| Devotional | Status | Source | Notes |
|------------|--------|--------|-------|
| Spurgeon's Morning & Evening | Public Domain | CCEL | Author died 1892 |

---

## Cross-References

| Resource | Status | Source | Notes |
|----------|--------|--------|-------|
| OpenBible.info cross-references | CC BY 4.0 | [openbible.info](https://www.openbible.info/labs/cross-references/) | Attribution to OpenBible.info required. Derived from the Treasury of Scripture Knowledge (1836, public domain), but the dataset itself is CC BY |

---

## Interlinear & Alignment Data

| Resource | Status | Source | Notes |
|----------|--------|--------|-------|
| Clear-Bible Alignments | CC BY 4.0 | [Clear-Bible/Alignments](https://github.com/Clear-Bible/Alignments) | BSB word-level Hebrew/Greek alignments |
| STEPBible Data | CC BY 4.0 | [STEPBible/STEPBible-Data](https://github.com/STEPBible/STEPBible-Data) | Hebrew/Greek interlinear with Strong's |
| KJV with Strong's numbers (eng-kjv2006) | Public Domain | [eBible.org](https://ebible.org/find/details.php?id=eng-kjv2006) | Strong's tags and italic (supplied) words used to build KJV word alignments; text courtesy of CrossWire and eBible.org |
| Derived alignments (KJV, WEB, BSB re-keyed) | CC BY 4.0 | this project, `scripts/build_alignments.py` | Derived from Clear-Bible alignments and STEPBible data (both CC BY 4.0); see docs/ALIGNMENT_2026-11.md |
| OpenGNT | CC BY-SA 4.0 | [OpenGNT](https://github.com/eliranwong/OpenGNT) | Greek NT data |
| OpenHebrewBible | CC BY 4.0 | [OpenHebrewBible](https://github.com/eliranwong/OpenHebrewBible) | Hebrew OT data |

---

## DO NOT USE (Copyrighted)

The following translations and resources are **copyrighted** and must NOT be used without licensing:

- NIV (Biblica)
- ESV (Crossway)
- NASB (Lockman Foundation)
- NKJV (Thomas Nelson)
- NLT (Tyndale)
- Any modern commentary (assume copyrighted unless verified)
- BibleHub data (do not scrape)

---

## Adding New Content

Before adding any new content:

1. Verify the license/copyright status
2. Document the source
3. Add an entry to this file
4. If uncertain, do not use
