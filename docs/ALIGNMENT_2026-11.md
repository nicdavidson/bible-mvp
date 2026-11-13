# Word alignment for every translation (2026-11)

Goal: tap any word in any translation and see the Hebrew or Greek word behind
it, and for any lemma see how each translation renders it. This document
covers the method, the data and licenses, the measured accuracy, known
weaknesses, and how to add a translation.

Build: `python scripts/build_alignments.py all` (or the `alignments` step of
`scripts/build_db.py`). Evaluate: `python scripts/build_alignments.py evaluate`
writes `docs/alignment-eval-2026-11.json`, which the tables below come from.

## Headline numbers

All on held-out books never used for training or tuning (Ruth, 2 Samuel, Job,
Song of Solomon, Lamentations, Hosea, Habakkuk, Zechariah, Mark, Galatians,
1 Peter, 1 John, Revelation). Token-level: a link is right when it names a
gold source word for that English word.

| Test | Precision | Recall | F1 | AER |
|---|---:|---:|---:|---:|
| BSB vs human gold (Clear-Bible), clean verses, all words incl. "the/of/and" | 81.9 | 80.7 | 81.3 | 21.7 |
| KJV aligned as if untagged, vs KJV Strong's tags (content words + italics) | 82.9 | 88.7 | 85.7 | 14.3 |
| — same, content words only (italic words excluded) | ≈90.0 | 88.7 | ≈89.4 | |
| YLT vs Clear-Bible manual alignment (independent second gold) | 81.7 | 85.6 | 83.6 | 16.8 |

The KJV row uses the production recipe (BSB gold + self-training on the KJV's
own text, no KJV tags). Without self-training it is 81.1 / 87.2 / 84.0.
With links below confidence 0.5 hidden: BSB precision 85.6 (recall 77.5),
KJV precision 86.0 (recall 86.8).

Shipped coverage (share of tappable words with a link) and confidence:

| Translation | Tappable words | Linked | conf ≥ 0.9 | 0.7–0.9 | 0.5–0.7 | < 0.5 | Source of links |
|---|---:|---:|---:|---:|---:|---:|---|
| BSB | 706,141 | 99.4% | 685,143 | 7,423 | 7,358 | 1,666 | 675,689 human gold (1.0); 25,901 aligner (627 shifted verses + ~11,300 isolated implausible gold links) |
| KJV | 787,634 | 95.4% | 516,985 | 118,544 | 91,882 | 23,617 | 352,464 from tags, 398,564 aligner (mostly function words the tagging skips) |
| WEB | 726,545 | 98.5% | 399,879 | 164,807 | 107,682 | 43,109 | aligner |

KJV words with no link: 26,988 italic supplied words (no source by design) and
about 9,600 words the aligner or the textual tradition leaves unlinked.

**Recommendation for the UI.** Show links with confidence ≥ 0.5 as is. Mark
0.5–0.8 as approximate if the design has room for it. Hide links below 0.5:
on BSB that drops 8% of links and lifts precision from 81.9 to 85.6. On KJV
the stated confidence runs 5 to 15 points higher than measured accuracy in the
0.5–0.95 band (calibration tables below), so treat a stated 0.7 on KJV or WEB
as roughly 0.6. The `lemma_renderings` index uses the same 0.5 cut.

Is the unsupervised aligner good enough to show? For WEB, yes behind the 0.5
threshold, with the caveat that a tap is wrong roughly one time in seven, more
often on "the", "of", "and" and pronouns than on nouns and verbs. Content
words are where users look, and there the KJV proxy measures about 90%
precision. For KJV, most content words come from human tags, so it is better
than that.

## What was wrong before this work

Found while building the gold set. All four affected what users see today.

1. **The BSB alignment rows pointed at the wrong words in ~18% of taps.**
   `import_bsb.py` numbered English words by its own rule (any token with a
   letter), but the reader numbers *tappable* words (`formatVerseText` in
   `app.js`: whitespace pieces matching `[a-zA-Z'-]+` with straight
   punctuation around them). A word with a curly quote (`“Let`, `light,”`) is
   not tappable, so every later word in the verse was off by one or more.
   It also stored Clear-Bible's source numbering (WLCM/SBLGNT, Hebrew
   versification) in `original_word_position`, which the API joins to
   STEPBible's numbering (TAHOT/TAGNT, English versification). Of 724,050
   BSB rows, 125,329 disagreed with the gold once both sides were re-keyed.
2. **22,310 STEPBible words were missing from `word_alignments`**, including
   all of Psalm 3 and Malachi 4: references with an alternative versification
   (`Psa.3.1(3.2)#01`, `Mat.17.15[17.14]#01`) failed the importer's regex.
   Fixed in `import_stepbible_alignment.py` (step `interlinear` v1.1).
3. **The WEB text was truncated.** The USFX importer only read the text
   directly after `<v>`: poetry verses kept their first line (Psalm 23:4 ended
   at "the shadow of death,") and verses that start inside `<q>` or `<wj>`
   (words of Jesus) were dropped. Matthew had 566 of 1,071 verses. Fixed in
   `import_web_xml.py` (step `web` v1.1): 29,684 → 31,098 verses.
4. **About 2% of Clear-Bible's BSB alignment is shifted** (627 verses): links
   land on the neighbouring words, apparently because BSB text revisions moved
   the target token ids after the manual alignment was made. Example, John
   10:36: "Father" is linked to ὃν ("whom"), "sanctified" to ὁ. These verses
   are detected automatically (below), left out of training and of the clean
   evaluation, and their shipped BSB rows come from the aligner instead.

## Data model

`english_word_alignments` (one row per tappable English word that has a source word):

| Column | Meaning |
|---|---|
| translation_id, book, chapter, verse | verse, English versification (as in `verses`) |
| english_word_position | 1-based index among the verse's tappable words (the UI contract, `scripts/aligner/text.py`) |
| english_word | the word as displayed |
| original_word_position | `word_alignments.word_position` in the same verse |
| confidence | calibrated: roughly the probability the link is right (see calibration tables) |
| method | 0 = human alignment (Clear-Bible BSB), 1 = resolved from a human Strong's tag (KJV), 2 = statistical aligner |

The table is now `WITHOUT ROWID` with the primary key on
(translation, book, chapter, verse, position); the old `id` column and its
separate unique index are gone (no code read `id`). Words with no source word
(KJV italics, a word the aligner leaves unlinked, verses whose source text
lacks the words) simply have no row: `/api/word-alignment` returns
`found: false`, which the UI already handles.

`lemma_renderings (strong_number, translation_id, rendering, count)`: for each
lemma and translation, the English renderings with counts. A rendering is the
English words in one verse linked to the same source word ("in the beginning";
gaps shown as "did … go"). Only links with confidence ≥ 0.5 are counted.
Occurrences are listed on demand by `GET /api/word/{strong}/renderings`
(`?translation=KJV&rendering=love`), which re-groups the alignment rows with
the same rule, so the index stays small.

## Method

### Source tokens and textual traditions

Source words are the STEPBible TAHOT/TAGNT tokens already in `word_alignments`
(same positions). For the NT each translation is aligned only to the words of
its own Greek edition, using TAGNT's editions column: BSB → SBL, KJV → TR
(Scrivener 1894), WEB → Byz (Robinson-Pierpont). So a KJV word can never be
linked to a Greek word the Textus Receptus lacks, and WEB/BSB words can never
be linked to TR-only words. Verses that exist in one tradition only follow:

- 1 John 5:7 (Johannine Comma): the KJV words "in heaven, the Father, the
  Word, and the Holy Ghost" link to the TR-only Greek words; WEB's "For there
  are three who testify:" links only to Byzantine words.
- Acts 8:37: KJV links to the TR-only words; WEB and BSB have no verse text.
- Matthew 6:13 doxology: KJV and WEB link to the TR/Byz words; BSB has no doxology.
- Mark 16:9-20: in all three source editions, so all three translations link.

Hebrew: one Masoretic text for all three; LXX-reconstructed rows (`=X`) are excluded.

### Gold sets

- **BSB (Clear-Bible manual alignment, CC BY 4.0).** Clear numbers source words
  in WLCM/SBLGNT. We map every Clear word to a STEPBible token by aligning the
  two word streams per chapter on their unpointed, unaccented spelling
  (`difflib`, then Strong's numbers inside unequal blocks): 99.7% of OT and
  99.5% of NT words map. English side: the BSB tokens are laid back into the
  verse text (identical to `verses.text` for all 31,202 verses) and each
  tappable word takes the links of the tokens it overlaps. 526 links that
  cross a verse boundary are dropped (the table keys both sides on one verse).
- **Shifted-gold detection.** A content-word gold link is implausible when the
  model's lemma table gives that English word probability < 0.002 for that
  lemma and the word is not in STEPBible's gloss of that token. A verse with
  ≥ 2 implausible links that are ≥ 30% of its content-word links is flagged:
  627 verses.
- **KJV (eBible.org `eng-kjv2006`, public domain).** The USFM tags content
  words with a Strong's number and marks italic supplied words (`\add`). We
  project eBible's words onto our KJV text (sequence alignment on letters) and
  resolve each tag to a STEPBible position among the verse's TR/MT tokens:
  *unique* when the lemma occurs once, *ordered* when the verse has as many
  tagged spans as occurrences, otherwise *ambiguous*. Strong's 1890 gives some
  inflected forms their own numbers (ὑμῖν G5213, ἐστί G2076); 20 lemma classes
  map these to STEPBible's lemma (from the lexicon's own "dative case of
  G4771" derivations and from data). Of 787,634 tappable KJV words: 283,021
  unique, 61,814 ordered, 7,629 ambiguous, 6,629 unresolvable, 26,988 italic,
  401,553 untagged (mostly function words: the KJV tagging skips "the", "of",
  "unto"...).
- **YLT (Clear-Bible manual alignment).** Used only as a second evaluation set
  (YLT is not in the app).

### The aligner (`scripts/aligner/model.py`)

Each English word is aligned to one source token or to nothing.

- **Emission** p(English word | source token) is a mixture over the token's
  features: its lemma (Strong's), Hebrew function morphemes from the dStrongs
  (ו and, ה the, ב in, pronoun suffixes...), grammar (Hebrew verb
  person/conjugation, construct state; Greek case, tense/mood, person), the
  STEPBible gloss of that very token (exact match after normalization), and a
  uniform floor. Which feature produced each gold word is latent; tables and
  mixture weights are fitted by EM on the gold links (6 iterations). The gloss
  component carries about half the weight and is what handles rare lemmas.
- **English normalization**: lowercase, a light stemmer, a lemma map for
  pronouns and irregular verbs, and Early Modern English handling (thou/thee/ye,
  hath, unto, and -eth/-est endings stripped only when the result is a word in
  the BSB/WEB vocabulary, so *beast* and *midst* survive).
- **Order model**: a first-order HMM over source positions (Vogel-style) with a
  "no link, remember position" state per position (Och & Ney). The jump
  distribution is estimated from BSB gold, separately for Hebrew and Greek, and
  conditioned on the previous English word for the 80 most frequent words
  (after "the" or "of" the next word usually links to the same Hebrew word or
  the next Greek one). A mild diagonal prior is multiplied in. Posterior
  marginals come from forward-backward; each word takes its most probable
  source and that posterior is its raw confidence.
- **Constraints**: for the KJV, a tagged word may only link to positions of its
  lemma and an italic word may not link; the HMM propagates these to the
  untagged neighbours ("the", "of", "unto").
- **Self-training** (for every translation except BSB): align the
  translation's own text, add the links with posterior ≥ 0.7 as extra training
  pairs, retrain once. No gold of that translation is used. This teaches the
  model that translation's vocabulary (archaic forms, its spelling of names).
- **Calibration**: an isotonic map from raw posterior to accuracy, fitted on
  the dev books (Joshua, Ecclesiastes, Micah, Philippians, James, 2 Peter) with
  a model trained without them.

Rows written:

- BSB: the human gold (confidence 1.0, method 0) except in the 627 shifted
  verses, which get aligner links (method 2). When gold links one English word
  to several source words, the row keeps the one the model finds most likely
  to produce that word ("one" in "the evil one" → πονηροῦ, not τοῦ).
- KJV: constrained aligner output. Words with a uniquely resolved tag get
  confidence 1.0 and order-resolved tags 0.9 (both method 1; these are stated,
  not measured); ambiguous tags get the calibrated posterior among that
  lemma's positions (method 1); untagged words get the calibrated posterior
  (method 2); italic words get no row.
- WEB: aligner output, calibrated (method 2).

No large model and no randomness: `build_alignments.py all` on this N100 box
takes about 30 minutes and peaks under 2 GB RAM. The local model router was
not used; nothing in the error analysis called for it yet (see Next steps).

## Evaluation

Splits are by whole book. Test books (above) and dev books (Joshua,
Ecclesiastes, Micah, Philippians, James, 2 Peter) are excluded from training
when evaluating; the shipped models include them. "Clean" excludes the 627
verses with shifted gold (103 of them in test books). AER uses the standard
definition with S = P = gold pairs; because the table stores one link per
English word, AER cannot reach 0 when gold links a word to two source words
(the floor is 3.7% on BSB). "Unlinked-when-gold-has-none" is the share of
words that have no gold source that we also left unlinked (KJV italics, a few
BSB words).

**BSB held-out books (clean gold)**

| Slice | Words scored | Precision | Recall | F1 | AER | Unlinked-when-gold-has-none |
|---|---:|---:|---:|---:|---:|---:|
| all | 83,719 | 81.9 | 80.7 | 81.3 | 21.7 | 38.8 |
| OT | 52,476 | 80.1 | 78.7 | 79.4 | 22.9 | 5.2 |
| NT | 31,243 | 85.0 | 84.2 | 84.6 | 19.7 | 48.4 |
| OT narrative | 19,464 | 81.5 | 80.7 | 81.1 | 22.0 | 0.0 |
| OT poetry | 21,450 | 78.0 | 76.1 | 77.0 | 24.6 | 8.3 |
| OT prophecy | 11,562 | 81.4 | 80.2 | 80.8 | 21.1 | 7.7 |
| NT narrative | 12,982 | 85.2 | 84.2 | 84.7 | 20.8 | 80.4 |
| NT epistle | 7,545 | 84.0 | 83.6 | 83.8 | 20.4 | 2.9 |
| NT prophecy | 10,716 | 85.3 | 84.6 | 85.0 | 17.9 | 5.4 |

With the shifted verses left in: 81.0 / 79.8 / 80.4 (AER 22.6).

**KJV aligned as if untagged, scored against the KJV Strong's tags**

Gold here is the uniquely resolved tags (content words) plus italic words as
"no source"; untagged function words are not scored, which is why recall is
higher than on BSB. Test books only.

| Slice | Words scored | P (BSB only) | R | F1 | P (+ self-training) | R | F1 | AER |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all | 39,550 | 81.1 | 87.2 | 84.0 | 82.9 | 88.7 | 85.7 | 14.3 |
| OT | 21,031 | 79.0 | 88.6 | 83.5 | 81.0 | 90.5 | 85.5 | 14.5 |
| NT | 18,519 | 83.5 | 85.6 | 84.5 | 85.0 | 86.7 | 85.8 | 14.2 |
| OT narrative | 7,478 | 82.4 | 90.9 | 86.5 | 84.3 | 92.7 | 88.3 | 11.7 |
| OT poetry | 9,285 | 75.5 | 86.1 | 80.5 | 77.7 | 87.9 | 82.5 | 17.5 |
| OT prophecy | 4,268 | 80.3 | 89.9 | 84.8 | 82.3 | 92.1 | 87.0 | 13.0 |
| NT narrative | 8,716 | 82.3 | 83.7 | 83.0 | 83.7 | 84.7 | 84.2 | 15.8 |
| NT epistle | 4,102 | 84.4 | 87.9 | 86.2 | 86.5 | 89.6 | 88.0 | 12.0 |
| NT prophecy | 5,701 | 84.7 | 86.9 | 85.8 | 85.9 | 87.7 | 86.8 | 13.2 |

Most of the precision loss is italic words: the BSB-trained aligner links
about 90% of KJV italic words, because BSB gold links almost every word
(no-link rate 0.6%). Excluding italic words, precision is about 90%.

**YLT held-out books vs Clear-Bible manual alignment** (BSB-trained, no self-training)

| Slice | Words scored | Precision | Recall | F1 | AER |
|---|---:|---:|---:|---:|---:|
| all | 92,853 | 81.7 | 85.6 | 83.6 | 16.8 |
| OT | 56,616 | 81.3 | 85.7 | 83.5 | 17.0 |
| NT | 36,237 | 82.4 | 85.5 | 83.9 | 16.4 |

**Model ablations on BSB dev books, F1** (from the development runs; the first
two rows were measured before shifted-gold filtering, on all dev gold)

| Model | Dev gold | F1 |
|---|---|---:|
| Independent per-word choice, diagonal prior (fast_align-like) | all | 71.8 |
| + first-order HMM with jump model | all | 75.8 |
| same | clean | 76.7 |
| + jumps conditioned on the previous English word | clean | 79.6 |
| + KJV tag data in training | clean | 79.7 (no gain; not used) |
| + self-training on KJV text | clean | 79.5 (neutral on BSB; +1.7 F1 on KJV test) |

### Calibration (stated confidence vs measured accuracy)

| Stated | BSB links | BSB accuracy | KJV links | KJV accuracy (production recipe) |
|---|---:|---:|---:|---:|
| 0.00–0.30 | 1,047 | 29.6 | 498 | 21.3 |
| 0.30–0.50 | 5,611 | 42.6 | 1,679 | 33.8 |
| 0.50–0.60 | 8,116 | 56.1 | 2,003 | 42.7 |
| 0.60–0.70 | 6,062 | 66.5 | 2,073 | 49.6 |
| 0.70–0.80 | 6,137 | 75.9 | 1,869 | 64.7 |
| 0.80–0.90 | 13,743 | 85.9 | 3,103 | 77.0 |
| 0.90–0.95 | 20,501 | 93.7 | 10,668 | 87.4 |
| 0.95–1.00 | 20,631 | 97.3 | 16,788 | 98.8 |

Calibrated on BSB dev, it holds on BSB test. On KJV it is optimistic in the
middle bands (archaic English, different gold conventions). WEB is modern
English like BSB, so expect it between the two columns; there is no WEB gold
to check.

### Thresholds

| Hide links below | BSB precision | BSB recall | KJV precision | KJV recall |
|---:|---:|---:|---:|---:|
| 0.0 | 81.9 | 80.7 | 82.9 | 88.7 |
| 0.3 | 82.6 | 80.4 | 83.7 | 88.4 |
| 0.5 | 85.6 | 77.5 | 86.0 | 86.8 |
| 0.7 | 91.4 | 67.1 | 91.0 | 81.6 |
| 0.9 | 95.5 | 47.3 | 94.3 | 71.6 |

### Error classes

BSB test, wrong or missing links (16,421): adjacent source word 7,834 · other
wrong source word 5,932 · missed (no link, gold has one) 1,599 · same lemma,
wrong occurrence 627 · spurious (gold has none) 429. By English word, the
most frequent errors are "of", "the", "and", "be", "to", pronouns.

- **Adjacent source word (the biggest class).** Mostly function words where
  conventions differ: "the sole *of* your foot" (gold: "of" → the following
  noun רַגְלְכֶם; we pick the construct noun כַּף), "*The* man" (gold: the noun;
  we pick the preceding וְשֵׁם), KJV "seen *with* our eyes" (tag on the verb).
- **Wrong source word.** Free renderings in BSB: Ruth 1:1 "when the judges
  *ruled*" (gold שְׁפֹט, we pick וַיְהִי); words BSB supplies for clarity
  ("Naomi" for a pronoun suffix).
- **Same lemma, wrong occurrence.** Repeated words: Ruth 1:1 has וַיְהִי twice
  ("In the days… *there was* a famine"); we pick the second.
- **Spurious (KJV).** Italic words linked: 1 John 2:2 "*the sins* of the whole
  world" linked to ἁμαρτιῶν. Shipped KJV rows avoid this via the tags.
- **Missed.** Low-posterior words the HMM sends to "no link": Ruth 1:5 "sons"
  (gold יְלָדֶיהָ "her children").

Gold noise also counts as error: Ruth 1:1 "a certain man" has no gold link in
Clear's data at all. On KJV, phrase tags put the content word's number on
neighbouring words ("seen *with*"), which our scorer counts against us.

## Data sources and licenses

| Data | Used for | License | Notes |
|---|---|---|---|
| Clear-Bible/Alignments (`data/clear-bible`, commit `4b47c05`, 2025-12-03) | BSB gold; YLT gold (eval only); WLCM/SBLGNT/WLC token lists | Data CC BY 4.0 (alignments © Biblica / Clear Bible); BSB text CC0; YLT PD | Attribution in LICENSES.md. `build_db.py` clones HEAD; re-run `evaluate` after an update. |
| STEPBible TAHOT/TAGNT (`data/alignment`, in git) | source tokens, editions, glosses, dStrongs | CC BY 4.0 | Only the TAHOT/TAGNT files; none of the lexicon files from Trap 1 of the license review (TBESH/TBESG/TFLSJ) are used. Their header asks that the data not be redistributed separately; we ship derived alignments inside the app DB with attribution, which the license allows. |
| eBible.org `eng-kjv2006` USFM (cached at `data/sources/kjv-strongs/`, sha256 prefix `dce1ec3ea45a155a`) | KJV Strong's tags and italics | Public domain ("You may copy the King James Version of the Holy Bible freely", copr.htm in the zip; checked at ebible.org/find/details.php?id=eng-kjv2006) | Crown patent applies only to printing in the UK. eBible regenerates the file; the cached zip pins it. |
| seven1m/open-bibles `eng-web.usfx.xml` | WEB text (re-imported) | Public domain; "World English Bible" is a trademark | Text unchanged except whitespace. |

The derived tables (`english_word_alignments` for KJV and WEB, the re-keyed BSB
rows and `lemma_renderings`) derive from CC BY 4.0 data and carry its
attribution requirement (LICENSES.md now lists them).

Candidates checked but not used: CrossWire KJV/ASV SWORD modules (binary
format, and eBible's USFM carries the same KJV tagging); STEPBible tagged
English Bibles (the only one in that repo is the ESV, CC BY-NC, Trap 1).

## Known weaknesses

- **Function words.** "the", "of", "and", pronouns and auxiliaries make up
  most errors. Their right answer depends on convention (does "of" belong to
  the construct noun or the genitive?); our convention is Clear-Bible's.
- **Poetry** is the weakest genre (BSB OT poetry F1 77.0, KJV 82.5): freer
  word order and rare vocabulary.
- **KJV/WEB confidence is optimistic** in the 0.5–0.95 range (calibration was
  fitted on BSB).
- **Cross-verse links are impossible** in this schema. Where KJV and NRSV
  versification split a verse differently (Matthew 17:14/15, Acts 4:5/6,
  3 John 14/15, Revelation 12:18/13:1, about 40 places in the NT), words that
  TAGNT files under the neighbouring verse have no link. 526 BSB gold links
  were dropped for the same reason.
- **Gold quality.** Beyond the 627 shifted verses, Clear-Bible gold has
  isolated errors (Genesis 1:3). Implausible single links are replaced by the
  aligner only when it is confident (calibrated ≥ 0.5); others are kept.
  Evaluation scores count gold errors against the model, so true accuracy is
  somewhat higher than measured.
- **Tokenization contract.** 2.6% of BSB and 3.0% of WEB words are not
  tappable today because the UI's tokenizer rejects curly quotes and
  apostrophes (“Let, God’s). They get no row. If the UI's tokenizer changes,
  `scripts/aligner/text.py` must change with it and the build must be re-run;
  otherwise positions drift.
- **Interlinear highlight in the NT.** `_highlightInterlinearWord` in `app.js`
  highlights by index in the rendered (edition-filtered) list, but
  `original_word_position` is the STEPBible position. In verses with words
  outside the active edition, the wrong interlinear word lights up. The tap
  popup itself is right. A frontend fix: match on `position`, not index.
- **KJV tag confidence** (1.0 unique, 0.9 by order) is assigned, not measured.
- **Strong's lemma classes** (20 sets) cover the frequent 1890-vs-STEPBible
  numbering splits; about 6,600 KJV tags (0.8%) still match no source word
  and fall back to the aligner.

## Storage

Measured with `dbstat` on a `VACUUM INTO` copy:

| | Before | After |
|---|---:|---:|
| `english_word_alignments` | 44.2 MB (BSB only, 724,050 rows: 23.8 table + 20.4 unique index) | 75.3 MB (2,168,095 rows, ~36 B/row, no separate index) |
| — per translation (by row share) | BSB 44.2 | BSB ≈24.4, KJV ≈26.1, WEB ≈24.8 |
| `lemma_renderings` | — | 5.3 MB (214,006 rows) |
| `word_alignments` (+22,310 recovered words) | 33.9 MB | 36.4 MB |
| WEB text (+1,414 verses, full poetry/words of Jesus), incl. FTS | | ≈ +3 MB |
| Whole DB file | 384.9 MB | 422.5 MB (+37.6 MB) |

So each additional aligned translation costs about 25 MB in the server DB. The
offline download is unaffected until the client fetches a translation's
chapters (`/api/offline/...` already includes alignments per translation).
Packed storage (Next steps) would cut ~25 MB to ~2–3 MB per translation.

## How to add a translation

1. Import its text into `verses` (one row per verse, English versification,
   the text exactly as the reader shows it).
2. Pick its Greek edition in `TRANSLATION_EDITION`
   (`scripts/aligner/sources.py`): `TR` for KJV-family texts, `Byz` for
   Majority-text ones, `SBL`/`WH`/`NA28` for critical-text ones. Hebrew needs
   nothing.
3. If it is Early Modern English, check `ARCHAIC` in `scripts/aligner/text.py`
   covers its forms.
4. Add a step in `scripts/build_alignments.py` like `step_web`:
   `production_model(ctx, "YLT")` then `write_rows(... model_rows(...))`.
   This self-trains on the new text automatically.
5. If it has human Strong's tags (ASV and Darby do, in CrossWire OSIS), write a
   loader that yields per-verse words with tags and italics like
   `scripts/aligner/kjv.py`, and reuse `resolve_tags` and `kjv_rows` with its
   edition.
6. Add an evaluation if any gold exists, re-run `build_alignments.py index`,
   and bump the `alignments` step version in `scripts/build_db.py`.

## Next steps to raise accuracy

1. **Fix the UI tokenizer** to accept curly quotes and apostrophes: +2.6–3%
   tappable words at no accuracy cost (needs a coordinated rebuild).
2. **Function-word attachment model**: a small classifier for "the/of/to/and"
   deciding between the neighbouring content words' sources, trained on BSB
   gold. These words are about half of all errors.
3. **Second-order or syntax-aware jumps** for poetry (a phrase-level
   reordering model, or Hebrew clause boundaries from the cantillation marks
   that TAHOT keeps).
4. **Bidirectional agreement**: train a Hebrew/Greek → English model too and
   keep links both directions agree on (classic symmetrization). Typically a
   few points of precision.
5. **KJV-specific calibration** using the tags (we have measured accuracy per
   confidence bin; fit a second calibrator for archaic translations).
6. **Use the GPU box** for an embedding-based similarity feature (e.g. a
   multilingual model scoring English word vs. gloss in context). Job: embed
   ~450K source tokens (gloss + lemma) and ~2.2M English tokens in context
   once, store a compact cosine table per verse, add as an emission feature;
   about one GPU-hour. Justify it by the BSB dev F1 like the ablations above.
7. **Packed storage**: one row per verse with the links as a compact string
   (`3,1,1,2,…`) would cut `english_word_alignments` from ~39 to ~3 bytes per
   word, at the cost of a small change in `words.py` and `offline.py`.
