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

Eleven sources, in this display order. Full license reasoning, sources and per-source notes:
[docs/COMMENTARY_LIBRARY_2026-11.md](docs/COMMENTARY_LIBRARY_2026-11.md).
The same metadata ships in the `commentary_sources` table. US public-domain status is argued from
first publication (before 1931) and the author's death, not from a website's label.

| Commentary (`source`) | Status | Source used | Notes |
|------------|--------|--------|-------|
| Scofield Notes (1917) | Public Domain | CrossWire `Scofield` (Wikisource text) | 1917 edition only; the 1967 New Scofield notes are copyrighted. "Scofield" is used descriptively |
| John Gill | Public Domain | HelloAO API | Published 1746-1763; Gill d. 1771 |
| Jamieson-Fausset-Brown | Public Domain | HelloAO API (matches CCEL) | Published 1871; authors d. 1880, 1897, 1910 |
| Tyndale Study Notes | **CC BY-SA 4.0**, (C) 2022 Tyndale House Publishers | tyndaleopenresources.com ZIP | Short credit (`commentary_sources.attribution_short`): "Adapted from Tyndale Open Study Notes © 2022 Tyndale House Publishers, CC BY-SA 4.0", linked to the full credit. Share-alike: credit "Adapted from Tyndale Open Study Notes. The original work by Tyndale House Publishers is available for free at http://www.tyndaleopenresources.com." Changes: XML converted to plain text with reference links; wording unchanged. Any published DB slice containing these rows stays CC BY-SA for these rows |
| Gaebelein Annotated Bible | Public Domain (first published before 1931) | SermonIndex SWORD module `siannbible`, repaired against archive.org scans | *The Annotated Bible*, 9 vols, Our Hope, ©1913-1921 (two volumes undated, internal evidence 1919-22). Matthew is Gaebelein's *Gospel of Matthew: An Exposition* (1903; ©1910), which the module ships in place of the Annotated Bible's Matthew |
| Ironside Expositions | Public Domain (first published before 1931) | SermonIndex SWORD module `siiron`, **allow-listed books only** | Nehemiah (1925 ed.), Esther (1921 ed. of 1905), Jeremiah and Lamentations (1928 ed. of 1906), Minor Prophets (1909/1928), Romans (1928), Colossians (1929), each matched to an archive.org scan of that edition. Later works the module appends (Hosea 3:4-, part of Jeremiah 30, Romans 11:25-) left out. The module's other books (later volumes, edited texts, "Copyright @ 1952") are not imported |
| Darby Synopsis | Public Domain (first published 1857-1867; Darby d. 1882) | SermonIndex SWORD module `sidarbysyn` | New Testament only. The Old Testament text was not taken from STEM Publishing or CCEL (both ask for permission) |
| Brooks Summarized Bible | Public Domain (©1919) | SermonIndex SWORD module `sitsb` | Matches the 1919 Bible Institute of Los Angeles edition (archive.org scans); three short readings follow BIOLA's undated "Second Edition", which carries only the 1919 notice |
| Mackintosh Notes on the Pentateuch | Public Domain (1858-1880; Mackintosh d. 1896) | Project Gutenberg #37915, #40596, #40610, #76552, #41571, #41584 | PG license: only the text is used, nothing of PG's is stored |
| Larkin on Revelation | Public Domain (©1919; Larkin d. 1924) | SermonIndex SWORD module `silarkinrev`, repaired against archive.org `bookofrevelation00lark` | Charts not included |
| Treasury of David | Public Domain | CrossWire `TDavid` (Spurgeon Archive text) | Published 1869-1885; Spurgeon d. 1892. Spurgeon's own exposition only |

The SermonIndex modules (https://sermonindex.net/modules/sword/) say "Free to copy and pass on".
Their "Public Domain" labels were not relied on: the basis above is the first publication of
the text actually shipped, checked against scans. Their conversion deleted every ALL-CAPS word of
8+ letters and turned some "is" into "Isaiah"; both are repaired at import
(`scripts/commentary_repair.py`), and the remaining known gaps are listed in the library doc.

Not imported in this wave (see the library doc): Gray's *Christian Workers' Commentary* (the only
structured text, SermonIndex `siconcise`, is a later edited version with modern additions; the 1915
text exists only as OCR), Darby's Old Testament synopsis (no clean source we may use), Ironside's
Daniel, Proverbs, Revelation and Philippians (the module has later edited wording; Daniel 9 includes
*The Great Parenthesis*, 1943).

**Removed 2026-11-13.** At the site owner's decision, after reviewing the commentators against
his church's doctrine (conservative, dispensational, Baptist-leaning), eight sources were removed
from the library and the database: Matthew Henry, Keil & Delitzsch, Albert Barnes (Barnes' Notes),
John Calvin, John Wesley, Adam Clarke, People's New Testament (B. W. Johnson) and Catena Aurea.
Their licensing was fine; the reason is doctrinal fit. Do not re-add them.

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
| Watts, *Psalms of David Imitated* (1719) and *Hymns and Spiritual Songs* (1707), 1818 printing | Public Domain | Project Gutenberg #13166, #13341 | PG license: with its license and references stripped the text is "unrestricted by U.S. intellectual property law"; only the text is used, nothing of PG's is stored |
| Tate and Brady, *New Version of the Psalms* (1696) | Public Domain; TCP encoding CC0 1.0 | EEBO-TCP A27952 | CC0 statement in the file's `<availability>` |
| Scottish Psalter (1650) + Paraphrases (1781); Olney Hymns (1779) | Public Domain works; CCEL site terms | CCEL ThML (`scotpsalter`, `olneyhymns`) | **Facts only** (first line, the printed Scripture reference, author, metre); no text stored. CCEL: "may be used for personal, educational, or non-profit purposes" and claims its markup. `hymn_sources.ENABLE_CCEL = False` removes them |
| Computed hymn-to-KJV quotation links | Public Domain inputs | this project, `scripts/import_hymns.py` | Shared word runs between public-domain hymn words (Open Hymnal, Project Gutenberg, TCP) and the KJV |

Not used without written permission: Hymnary.org (all rights reserved), the Cyber Hymnal
(hymntime.com page code copyrighted). CCEL: facts only, as above.

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

## Meaning Search (models and libraries)

Meaning search (docs/SEMANTIC_SEARCH_2026-11.md) ranks existing verses; it generates no text.
The model is a file we run, not content we show, but it ships in the image and may be
downloaded by browsers, so its license is listed here.

| Component | License | Source | Notes |
|-----------|---------|--------|-------|
| gte-small, quantized ONNX export (shipped model) | MIT | [thenlper/gte-small](https://huggingface.co/thenlper/gte-small) (Alibaba DAMO), ONNX by [Xenova/gte-small](https://huggingface.co/Xenova/gte-small) @ `5927d1727bb1` | Copied to `data/models/gte-small@5927d1727bb1/` at build time (not in git). Keep the MIT notice if redistributed. The Xenova repo card has no license field; the weights are a format conversion of the MIT model |
| Verse vectors (`semantic_vectors` table) | Same as the BSB text (public domain) + model output | this project, `scripts/build_embeddings.py` | Numbers derived from BSB verse text |
| ONNX Runtime (server inference) | MIT | [microsoft/onnxruntime](https://github.com/microsoft/onnxruntime) | Python wheel, runtime dependency |
| Hugging Face tokenizers | Apache-2.0 | [huggingface/tokenizers](https://github.com/huggingface/tokenizers) | Python wheel, runtime dependency |
| NumPy | BSD-3-Clause | [numpy/numpy](https://github.com/numpy/numpy) | Runtime dependency |
| transformers.js 3.8.1 (browser proof only, `tests/browser/`) | Apache-2.0 | [huggingface/transformers.js](https://github.com/huggingface/transformers.js) | Not shipped in the app yet; bundles onnxruntime-web (MIT) |
| Models evaluated but not shipped | MIT (bge-small-en-v1.5, e5-small-v2, potion-*), Apache-2.0 (all-MiniLM-L6-v2, snowflake-arctic-embed-xs, mxbai-embed-xsmall-v1) | Hugging Face, revisions pinned in `backend/semantic.py` | Evaluation only. qwen3-embedding:0.6b (Apache-2.0) was used as a quality ceiling via Ollama and is never on the request path |

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
