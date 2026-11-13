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
