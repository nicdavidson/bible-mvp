# Translation Source Text Research

> Deep research into mapping English Bible translations to their correct
> original language source texts. Conducted Feb 2026 for the Bible MVP project.

## Table of Contents
1. [The Problem](#the-problem)
2. [Greek NT Edition → Translation Mapping](#greek-nt-editions)
3. [Hebrew OT Editions](#hebrew-ot-editions)
4. [STEPBible NKO Variant System](#stepbible-nko-variant-system)
5. [Current Codebase State](#current-codebase-state)
6. [Available Public-Domain Digital Source Texts](#available-datasets)
7. [Key Divergent Passages](#key-divergent-passages)
8. [Implementation Plan](#implementation-plan)

---

## The Problem

When a user reads the KJV and toggles "original language," they should see the
**Textus Receptus** (the Greek text the KJV translators actually used). When
reading BSB, they should see the **SBLGNT/Critical Text**. Currently, the app
shows the same source text regardless of translation — this is misleading and
can reinforce the incorrect "KJV-only" argument that modern translations
"removed" text, when in reality those passages were later additions to the TR.

**Friend's key insight (Feb 2026):** "Don't try to solve this all at once.
This is literally a lifetime of scholarly work." Start with clear labeling,
then progressively add filtering.

---

## Greek NT Editions

### Edition → Translation Mapping

| Greek Edition | Key Translations | Digital Availability | License |
|---|---|---|---|
| **Textus Receptus** (Scrivener 1894) | KJV, NKJV, MEV | GitHub: `byztxt/scrivener-tr` | Public domain |
| **Byzantine/Majority Text** (Robinson-Pierpont 2018) | WEB, NKJV (footnotes) | GitHub: `byztxt/byzantine-majority-text` | Public domain |
| **NA27** (Nestle-Aland 27th) | NIV (1984), NASB (1995), ESV (2001), HCSB | **NOT freely available** (copyrighted by Deutsche Bibelgesellschaft) | Copyrighted |
| **NA28** (Nestle-Aland 28th) | NIV (2011), NASB (2020), CSB, NLT, LSB | **NOT freely available** | Copyrighted |
| **UBS5** | Same text as NA28, different apparatus | **NOT freely available** | Copyrighted |
| **SBLGNT** (SBL Greek NT, Holmes 2010) | BSB | GitHub: `morphgnt/sblgnt` | Free for non-commercial use (SBLGNT EULA) |
| **Tyndale House GNT** (2017) | LSB (consulted), Tyndale editions | Available via STEPBible data | CC BY 4.0 |

### How the Editions Relate

The major "families" for practical purposes:

```
                    ┌─ Textus Receptus (TR, 1500s-1894)
                    │   └─ KJV, NKJV, MEV
  Greek NT ─────────┤
  Editions          ├─ Byzantine/Majority Text (Byz, Robinson-Pierpont)
                    │   └─ WEB
                    │
                    └─ Critical Text (eclectic, manuscript-based)
                        ├─ NA27/NA28/UBS5 (standard scholarly)
                        │   └─ NIV, ESV, NASB, CSB, NLT, NRSV
                        ├─ SBLGNT (Holmes 2010, slightly different from NA)
                        │   └─ BSB
                        └─ Tyndale House GNT (2017)
                            └─ LSB (consulted)
```

**Key insight:** NA27 and NA28 text is nearly identical for 99%+ of the NT.
The differences between NA27 and NA28 only affect the Catholic Epistles
(James through Jude) and are minor. For our purposes, **treating all Critical
Text translations as one group ("N" in TAGNT) is accurate enough.**

### Simplified Mapping for Our Three Translations

| Our Translation | Source Text | TAGNT NKO Filter | Source Label |
|---|---|---|---|
| **BSB** | SBLGNT (Critical Text) | Show words with `N` | "SBL Greek New Testament" |
| **KJV** | Textus Receptus (Scrivener 1894) | Show words with `K` | "Textus Receptus (Scrivener 1894)" |
| **WEB** | Majority Text | Show words where `Byz` in editions | "Byzantine Majority Text (RP 2018)" |

---

## Hebrew OT Editions

### The Good News: OT is Much Simpler

Unlike the Greek NT, virtually **all** modern English translations use the same
Hebrew source text: the **Masoretic Text (MT)**, specifically based on the
**Leningrad Codex** (oldest complete MT manuscript, c. 1008 CE).

| Hebrew Edition | Description | Used By |
|---|---|---|
| **BHS** (Biblia Hebraica Stuttgartensia) | Standard scholarly edition of Leningrad Codex | Nearly all modern translations |
| **BHQ** (Biblia Hebraica Quinta) | Successor to BHS, still in progress | Newer translations |
| **WLC/WLCM** (Westminster Leningrad Codex) | Digital encoding of Leningrad Codex | Our app (via Clear-Bible & Open Scriptures) |

**Differences are minimal.** The TAHOT data does track some variants:
- **Q** (Qere) vs **K** (Ketiv) — scribal corrections vs original text
- **D** — Dead Sea Scrolls readings
- **A** — Aleppo Codex differences
- **X** — LXX-based reconstructions

But these are scholarly edge cases. **For our purposes, showing WLCM for all
translations with a "Westminster Leningrad Codex" label is correct and
sufficient.** No filtering needed for Hebrew.

---

## STEPBible NKO Variant System

### What NKO Means

The STEPBible TAGNT data (which we already have locally in `data/alignment/`)
encodes **every word** with a type marker indicating which manuscript
traditions contain it:

```
N = "Ancient" = found in Nestle-Aland (NA27/28), used by most modern Bibles
K = "Traditional" = found in KJV's Textus Receptus (Scrivener 1894)
O = "Other" = found in other major editions but rarely translated
```

**Case matters:**
- **Uppercase** = the variant changes the translation (significant)
- **Lowercase** = minor difference (spelling, word order) that doesn't
  affect translation

**Parentheses** = the letter is a variant (not the main reading for that
tradition).

### NKO Type Examples

| Type | Meaning | Example |
|---|---|---|
| `NKO` | All editions agree (94% of words) | Most NT words |
| `N(k)O` | Ancient + Other agree; Traditional has a minor difference | |
| `K` | **Only in TR** (not in Critical Text) | 1 John 5:7 "Johannine Comma" |
| `KO` | In Traditional + Other, but NOT in Ancient manuscripts | Mark 16:9-20 |
| `N(K)O` | All have it, but TR version differs significantly | |
| `NO` | In Ancient + Other, but NOT in TR | |
| `N` or `n` | Only in Ancient manuscripts | |
| `O` or `o` | Only in Other editions | |

### Quantitative Breakdown (Entire NT)

From our actual TAGNT data files:

| Category | Count | % | Meaning |
|---|---|---|---|
| **NKO** (all agree) | ~133,000 | 94% | No filtering needed |
| **K-only** (K, k, ko, KO, K(o)...) | ~3,500 | 2.5% | TR words absent from Critical Text |
| **N-only** (N, n, no, NO, n(o)...) | ~800 | 0.5% | Critical Text words absent from TR |
| **Variant forms** (N(k)O, N(K)O...) | ~3,500 | 2.5% | Same word, different form |
| **O-only** (O, o) | ~300 | 0.2% | Rare, in neither standard edition |

### Editions Column (More Granular)

Each TAGNT word also has an editions column listing exactly which editions
include it:

```
NA28+NA27+Tyn+SBL+WH+Treg+TR+Byz    (= NKO, all editions)
TR                                     (= K, only in Textus Receptus)
NA28+NA27+Tyn+SBL+WH+Treg             (= N, only Critical Text editions)
NA28+NA27+Tyn+WH+Treg+TR+Byz          (= NKO minus SBL)
```

Available editions in the data:
- **NA28** — Nestle-Aland 28th
- **NA27** — Nestle-Aland 27th
- **Tyn** — Tyndale House GNT 2017
- **SBL** — SBLGNT (Holmes 2010)
- **WH** — Westcott & Hort 1881
- **Treg** — Tregelles 1879
- **TR** — Textus Receptus (Scrivener 1894)
- **Byz** — Byzantine (Robinson-Pierpont 2005)

### Filtering Logic

**For BSB** (SBLGNT): Show words where `SBL` appears in editions column
(or simpler: where NKO type contains `N`)

**For KJV** (TR): Show words where `TR` appears in editions column
(or simpler: where NKO type contains `K`, case-insensitive)

**For WEB** (Majority/Byzantine): Show words where `Byz` appears in
editions column (NKO type doesn't distinguish Byz from TR under `K`)

**Important:** The `K` marker in NKO covers BOTH TR and Byz. For WEB,
which uses Byzantine/Majority Text (not identical to TR), we MUST use the
editions column rather than just the NKO type marker. TR and Byz agree
most of the time but diverge in ~160 places.

---

## Current Codebase State

### What We Have

1. **TAGNT data files** with full NKO markers: `data/alignment/TAGNT_Mat-Jhn.txt`
   and `TAGNT_Act-Rev.txt` — **the data is there, we just don't use it**

2. **TAHOT data files** for Hebrew: `data/alignment/TAHOT_*.txt`

3. **SBLGNT source**: `data/clear-bible/data/sources/SBLGNT.tsv` (10.9 MB)

4. **WLCM source**: `data/clear-bible/data/sources/WLCM.tsv` (28.7 MB)

5. **BGNT** (Bunning Greek NT): `data/clear-bible/data/sources/BGNT.tsv` (8.6 MB)

### What's Broken

1. **`import_stepbible_alignment.py` line 69**: `parse_reference()` regex
   extracts `Book.Ch.Vs#Pos` but **discards** the `=NKO` type marker entirely:
   ```python
   match = re.match(r'([A-Za-z0-9]+)\.(\d+)\.(\d+)#(\d+)', ref_str)
   # The '=NKO' or '=K' part is completely lost
   ```

2. **`word_alignments` table** has no columns for `word_type` or `editions`

3. **`/api/passage/{ref}/interlinear` endpoint** (main.py:593-598) hardcodes
   source text labels without considering translation:
   ```python
   if language == 'hebrew':
       source_text = 'Westminster Leningrad Codex'
   elif language == 'greek':
       source_text = 'SBL Greek New Testament'
   ```

4. **Frontend** (`app.js`) displays interlinear data identically regardless of
   which translation is active

### The `words` Table (Legacy)

The older `words` table uses **OpenGNT** data (Critical Text only) imported via
`import_interlinear.py`. This is separate from the `word_alignments` table
(STEPBible data). The `words` table has no variant info at all.

---

## Available Datasets

### Already in Our Repo

| Dataset | Path | Size | Content |
|---|---|---|---|
| STEPBible TAGNT (Greek) | `data/alignment/TAGNT_*.txt` | ~15 MB | Full NT with NKO markers |
| STEPBible TAHOT (Hebrew) | `data/alignment/TAHOT_*.txt` | ~25 MB | Full OT |
| Clear-Bible SBLGNT | `data/clear-bible/data/sources/SBLGNT.tsv` | 11 MB | SBL Greek text |
| Clear-Bible WLCM | `data/clear-bible/data/sources/WLCM.tsv` | 29 MB | Hebrew text |
| Clear-Bible BGNT | `data/clear-bible/data/sources/BGNT.tsv` | 8.6 MB | Bunning Greek NT |
| OpenGNT | `data/OpenGNT_version3_3.csv` | ~30 MB | Critical Text Greek |

### Available on GitHub (Public Domain / CC BY)

| Dataset | Source | License | Notes |
|---|---|---|---|
| Robinson-Pierpont Byzantine | `byztxt/byzantine-majority-text` | Public domain | For WEB source text |
| Scrivener TR | `byztxt/scrivener-tr` | Public domain | For KJV source text |
| SBLGNT | `morphgnt/sblgnt` | SBLGNT EULA (free use) | Already have via Clear-Bible |
| Open Scriptures Hebrew | `openscriptures/morphhb` | CC BY 4.0 | WLC with morphology |
| STEPBible Data | `STEPBible/STEPBible-Data` | CC BY 4.0 | Our primary source |

### NOT Available (Copyrighted)

| Dataset | Why Not | Workaround |
|---|---|---|
| NA28 text | Deutsche Bibelgesellschaft copyright | Use SBLGNT (nearly identical) + NKO filtering |
| UBS5 text | Same copyright as NA28 | Same workaround |
| BHQ (Hebrew) | Still in progress, copyrighted | WLC/WLCM is sufficient |

---

## Key Divergent Passages

### The "Big Three" Greek Variants

These are the passages most likely to confuse users if shown incorrectly:

#### 1. Johannine Comma — 1 John 5:7-8

**TR/KJV adds:** "in heaven, the Father, the Word, and the Holy Ghost: and
these three are one. And there are three that bear witness in earth:"

**Critical Text/BSB:** Omits the entire Trinitarian formula. Only reads
"For there are three that testify: the Spirit, the water, and the blood."

**TAGNT encoding:** All TR-only words marked `=K` with editions `TR` only.
Lines 106958-106997 in `TAGNT_Act-Rev.txt`.

**Why it matters:** This is the #1 passage cited by KJV-only advocates. If
our app shows the Johannine Comma when someone reads BSB, it's actively
misleading.

#### 2. Long Ending of Mark — Mark 16:9-20

**Status:** Most scholars believe Mark originally ended at 16:8. Verses 9-20
are a later addition found in most but not all manuscripts.

**TAGNT encoding:** All words marked `=KO` (in Traditional + Other, but the
`[[` double brackets indicate disputed status). Editions column still lists
all editions because NA28 includes it in double brackets.

**How translations handle it:**
- KJV: includes without note
- BSB: includes but marks as disputed
- WEB: includes but marks as disputed
- NIV: includes with note that earliest manuscripts lack it

**For our app:** Show for all translations but visually indicate disputed
status (e.g., lighter text, bracketed, with a note).

#### 3. Woman Caught in Adultery — John 7:53-8:11 (Pericope Adulterae)

Similar to Mark 16:9-20. Not in earliest manuscripts. Most translations
include it with a note. TAGNT marks these words appropriately.

#### 4. Acts 8:37 (Philip & the Eunuch)

**TR/KJV has:** Philip asks the eunuch to confess faith before baptism.

**Critical Text/BSB:** Verse entirely absent. Goes from 8:36 to 8:38.

**TAGNT encoding:** All words marked `=K` with editions `TR` only.

#### 5. Other Notable Variants

| Passage | TR/KJV | Critical Text | Impact |
|---|---|---|---|
| Matt 17:21 | Includes verse about prayer & fasting | Omits | Moderate |
| Matt 18:11 | "Son of Man came to save the lost" | Omits | Low (in Luke 19:10) |
| Matt 23:14 | Woe to scribes (devouring widows) | Omits | Low (in Mark 12:40) |
| Luke 17:36 | "Two men in the field" | Omits | Low (in Matt 24:40) |
| Acts 15:34 | Silas stayed in Antioch | Omits | Low |
| Rom 16:24 | Grace benediction | Omits | Low (in 16:20) |

---

## Implementation Plan

### Phase 1: Quick Win — Source Text Labeling (1-2 hours)

**Goal:** Show correct source text name based on active translation.

**Changes:**
1. In `backend/main.py` interlinear endpoint (~line 593-598), change source
   text label based on `translation` parameter:
   ```python
   GREEK_SOURCE_LABELS = {
       'BSB': 'SBL Greek New Testament',
       'KJV': 'Textus Receptus (Scrivener 1894)',
       'WEB': 'Byzantine Majority Text (Robinson-Pierpont)',
   }
   ```
2. In frontend, display the `source_text` label prominently in the
   interlinear header.

**No data changes needed.** Just labeling.

### Phase 2: Database Schema + Re-import (2-3 hours)

**Goal:** Preserve NKO markers and editions in the database.

**Changes:**
1. Add columns to `word_alignments`:
   ```sql
   ALTER TABLE word_alignments ADD COLUMN word_type TEXT;  -- 'NKO', 'K', 'KO', etc.
   ALTER TABLE word_alignments ADD COLUMN editions TEXT;   -- 'NA28+NA27+Tyn+SBL+WH+Treg+TR+Byz'
   ```
2. Update `import_stepbible_alignment.py`:
   - Modify `parse_reference()` to capture `=NKO` type marker
   - Extract editions column (column 5 for Greek TAGNT data)
   - Store both in the new columns
3. Re-import TAGNT data (the TAHOT Hebrew data doesn't need this since
   Hebrew variants are minimal and not edition-based)

### Phase 3: API Filtering (2-3 hours)

**Goal:** Filter interlinear words based on translation.

**Changes:**
1. Update `/api/passage/{ref}/interlinear` to accept `translation` param
   and filter results:
   - **BSB**: `WHERE word_type LIKE '%N%' OR word_type = 'NKO'` (or more
     precisely: `WHERE editions LIKE '%SBL%'`)
   - **KJV**: `WHERE editions LIKE '%TR%'`
   - **WEB**: `WHERE editions LIKE '%Byz%'`
2. For words that exist in all editions but differ (types like `N(K)O`),
   show them but potentially flag the variant.
3. Add a `variant_info` field to the API response for words that have
   variants (the meaning variants and variant notes columns from TAGNT).

### Phase 4: Frontend Variant Display (3-4 hours)

**Goal:** Visual indication of textual variants.

**Changes:**
1. Words only in the active translation's source → normal display
2. Words in all editions → normal display
3. Disputed passages (Mark 16:9-20, John 7:53-8:11) → show with visual
   indicator (lighter text, brackets, or a banner)
4. Words NOT in the active translation's source → hide by default, but
   optionally show with strike-through or different color if user enables
   "show all manuscripts" mode
5. Source text badge/label always visible in interlinear header

### Phase 5: Advanced Features (Future)

- **Manuscript comparison mode:** Side-by-side view of how the same verse
  reads in different source texts
- **Variant note popups:** Click a flagged word to see which manuscripts
  include/exclude it and why
- **Per-edition word counts:** Show stats like "This verse has 3 words
  unique to the TR" in a verse info panel
- **Integration with Passage Comparison Diff:** Combine source text
  differences with English translation differences

### Data Flow Summary

```
TAGNT files (with NKO + editions) ──→ import_stepbible_alignment.py
                                         │
                                         ▼
                                    word_alignments table
                                    (+ word_type, editions columns)
                                         │
                                         ▼
                            /api/passage/{ref}/interlinear?translation=BSB
                                         │
                                    Filter by editions
                                         │
                                         ▼
                                    Frontend display
                                    (with source label + variant indicators)
```

---

## Quick Reference: NKO Filtering Cheatsheet

### "Should I show this word for [translation]?"

```
BSB (Critical Text / SBLGNT):
  ✅ Show if: word_type contains 'N' (uppercase or lowercase)
  ✅ Show if: editions contains 'SBL'
  ❌ Hide if: word_type is K-only (K, k, ko, KO) with no N

KJV (Textus Receptus):
  ✅ Show if: word_type contains 'K' (uppercase or lowercase)
  ✅ Show if: editions contains 'TR'
  ❌ Hide if: word_type is N-only (N, n, no, NO) with no K

WEB (Byzantine/Majority Text):
  ✅ Show if: editions contains 'Byz'
  ❌ Hide if: editions does NOT contain 'Byz'
  ⚠️  Cannot rely on NKO type alone (K covers both TR and Byz)
```

### For the ~94% NKO words: Show for everyone, no filtering needed.

---

*Last updated: 2026-02-06*
*Research conducted by Claude for the Bible MVP project*
