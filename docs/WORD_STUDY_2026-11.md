# Computed word studies (2026-11)

For any Hebrew or Greek lemma (Strong's number) the app can show a study page
built only from datasets: lexicon entries quoted from public-domain lexicons,
counts and parsing from the STEPBible source text, renderings from the word
alignments, associations computed from co-occurrence, topics from Nave's,
cross-references from OpenBible.info. Nothing is written by a model, and every
section of the payload names its dataset (`source`), which the `sources` map
describes with its license and credit line.

Build: steps `lexicons` (`scripts/import_lexicons.py`, 6 s) and `word_study`
(`scripts/build_word_study.py`, 15 s, 350 MB peak) in `scripts/build_db.py`.
API: `backend/routers/wordstudy.py`. Shared rules: `backend/word_study.py`.
Tests: `tests/test_word_study.py`.

## API

### `GET /api/word/{strong}/study`

`strong`: `G26`, `g0026`, `H2617`. 400 if malformed, 404 if the number is in
neither the lexicon nor the text. Cached per process (256 lemmas, invalidated
when the DB file changes).

```jsonc
{
  "strong_number": "G26", "language": "greek",            // or "hebrew"
  "lemma": {
    "original": "ἀγάπη", "transliteration": "agápē",
    "transliteration_source": "strongs",                   // Hebrew: "bdb" (OSHB lexical index)
    "pronunciation": "", "pos": {"code": "N", "label": "noun", "source": "stepbible"},
    "function_word": false                                 // true: no collocates computed
  },
  "lexicons": [                                            // fullest first; never merged
    {"source": "abbott-smith", "entries": [{
       "headword": "ἀγάπη, -ης, ἡ", "gloss": "love; goodwill; esteem",
       "definition": "love, goodwill, esteem. ...\n1. Of men's love:\n  (a) to one another, Jo 13:35; ...",
       "notes": "SYN.: φιλία. ...",                       // Abbott-Smith synonym notes, else null
       "source_key": "ἀγάπη|G26",
       "meta": {"nt_occurrences": 116, "etymology": "[in LXX for אַהֲבָה, ...]"}}]},
    {"source": "dodson", "entries": [{"headword": "ἀγάπη, ης, ἡ", "gloss": "love",
       "definition": "love, benevolence, good will, esteem; plur: love-feasts.", ...}]},
    // Hebrew: {"source": "bdb", "order": "<rule>", "entries": [ ... one per homograph,
    //   meta: {bdb_id, aug, xlit, homograph: "I", count, pos, status}, rendering_matches } ]
    {"source": "strongs", "entries": [{"headword": "ἀγάπη", "transliteration": "agápē",
       "pronunciation": "", "definition": "love, i.e. affection ...",
       "kjv_usage": "(feast of) charity(-ably), dear, love", "derivation": "from G25 (ἀγαπάω);"}]}
  ],
  "occurrences": {
    "source": "stepbible", "text": "Greek NT (SBLGNT, as in TAGNT)",
    "total": 116, "verses": 106, "by_testament": {"OT": 0, "NT": 116},
    "by_book": [{"book": "Matthew", "count": 1}, ...],     // canonical order
    "by_form": [{"form": "N-NS", "label": "nominative singular", "count": 36}, ...],
    "by_edition": {"SBL": 116, "TR": 116, "Byz": 116}      // NT only
  },
  "renderings": {
    "source": "alignments", "min_confidence": 0.5,
    "verses_url": "/api/word/G26/renderings?translation={translation}&rendering={rendering}",
    "translations": {"BSB": {"total": 115, "distinct": 7,
                             "renderings": [{"rendering": "love", "count": 109}, ...]}, // top 12
                     "KJV": {...}, "WEB": {...}}
  },
  "collocates": {
    "source": "stepbible", "text": "...", "method": {"unit": "verse", "measure": "...", "excluded": "..."},
    "items": [{"strong_number": "G4102", "original": "πίστις", "transliteration": "pístis",
               "gloss": "faith, belief, trust", "gloss_source": "dodson",
               "together": 24, "expected": 3.03, "g2": 64.1, "log_dice": 11.21,
               "verses_url": "/api/word/G26/verses?with=G4102"}],   // up to 15
    "note": null                                                     // or "Not computed for function words."
  },
  "related": {"items": [{"strong_number": "G25", "original": "ἀγαπάω", "transliteration": "agapáō",
                         "gloss": "I love", "gloss_source": "dodson",
                         "links": [{"relation": "derived_from", "source": "strongs", "detail": null}]}],
              "note": "Only relations a lexicon states; none are inferred."},
  "topics": {"source": "naves", "method": "...",
             "items": [{"topic_id": 3094, "topic": "LOVE", "section": "L", "hits": 35,
                        "topic_verses": 260, "g2": 206.4, "url": "/api/topics/3094"}]},   // up to 8
  "cross_references": {"source": "openbible-xrefs", "method": "...",
             "items": [{"from": {"book": "2 Timothy", "chapter": 1, "verse": 7},
                        "to": {"book": "1 John", "chapter": 4, "verse": 18}, "votes": 242}]}, // up to 8
  "samples": {"source": "alignments", "method": "<selection rule>", "all_occurrences": false,
              "items": [{"book": "John", "chapter": 15, "verse": 13, "word_position": 2,
                         "rendering": "love", "reason": "section: Gospels",
                         "bsb_text": "Greater love has no one than this, ...",
                         "bsb_word_positions": [2]}]},          // up to 12, canonical order
  "sources": {"abbott-smith": {"name": "...", "license": "Public domain", "attribution": "",
                               "url": "...", "note": "..."}, ...}
}
```

- `relation` is `derived_from`, `source_of` (the reverse), `compare` (Strong's
  "compare G…", or a number inside parentheses such as "in the sense of H…"),
  or `same_root` (BDB root family; `detail` is the root, e.g. `חָסַד`).
- `bsb_word_positions` are tappable-word positions in `bsb_text` (the same
  contract as `/api/word-alignment`), for highlighting.
- `by_form` keys can be passed to `/verses?form=`.
- Show the `sources[...].attribution` line wherever a CC BY section is shown
  (BDB: "Open Scriptures Hebrew Bible Project"; OpenBible.info; STEP Bible;
  Clear Bible).

### `GET /api/word/{strong}/verses`

Occurrences, one row per token, canonical order, 100 per page.
Query: `book`, `form` (a `by_form` key), `edition` (`SBL` default, `TR`,
`Byz`; NT only), `with` (another Strong's number: only verses that contain
both, i.e. the evidence behind a collocate), `offset`.

```json
{"strong_number": "G26", "text": "...", "filters": {...}, "total": 25, "verses": 24,
 "offset": 0, "occurrences": [{"book": "1 Corinthians", "chapter": 13, "verse": 2,
   "word_position": 23, "original_text": "ἀγάπην", "grammar": "N-ASF", "gloss": "love",
   "form": "N-AS", "form_label": "accusative singular"}]}
```

Renderings by verse stay at the existing
`GET /api/word/{strong}/renderings?translation=KJV&rendering=charity`.

### Sizes and speed (bridge, TestClient, data as built 2026-11-13)

| | median | p95 | max |
|---|---:|---:|---:|
| `/study`, 300 random lemmas, uncached | 10 ms | 18 ms | 48 ms |
| `/study` payload | 6.1 KB | 14.6 KB | 21.9 KB |

Heaviest: H3068 (YHWH, 6,522 occurrences) 135 ms uncached, 24.7 KB; the
article G3588 (19,738 occurrences) 257 ms uncached. Cached requests 5–25 ms.
`/verses` 9–13 ms. Gzip roughly thirds the payloads (the app has GZip middleware).

New tables (`dbstat`): `lexicon_entries` 6.4 MB, `lexicon_relations` 1.9 MB,
`lemma_samples` 1.7 MB, `lemma_collocates` 1.3 MB, `lemma_topics` 0.5 MB,
`lemma_xrefs` 0.5 MB, `lemma_profile` 0.3 MB: 12.6 MB in all.

## Sources and licenses

Checked at the primary source on 2026-11-13; files are pinned by commit and
cached under `data/sources/lexicons/` (`source_cache.cached_fetch_path`).

| Dataset | License (where it says so) | Used for |
|---|---|---|
| Dodson Greek Lexicon, github.com/biblicalhumanities/Dodson-Greek-Lexicon @74f7035 | `LICENSE`: CC0 1.0. `README-ulrikp.txt`: "This lexicon ... is in the Public Domain"; Dodson's note: "released by the copyright holder into the public domain ... personal, academic, non-commercial, and/or commercial purposes" | Greek brief and full glosses |
| Abbott-Smith, *Manual Greek Lexicon of the NT* (1922), github.com/translatable-exegetical-tools/Abbott-Smith @8c00cb2 | `README.md`: "The lexicon (abbott-smith.tei.xml), including the marked up version in this repository, is in the public domain." No LICENSE file. Its archive.org **PDF** "has restrictions": not downloaded, not used | Greek full entries, synonym notes, NT counts, derivations |
| OpenScriptures HebrewLexicon (BDB + LexicalIndex), github.com/openscriptures/HebrewLexicon @21c9add | `readme.md`: "released under the Creative Commons Attribution 4.0 International license. The actual text of Brown, Driver, Briggs and Strong's Hebrew dictionary remain in the public domain. For attribution purposes, credit the Open Scriptures Hebrew Bible Project." | Hebrew entries, homographs, root families, lemma transliteration |
| Strong's dictionaries (already in `lexicon`) | Public domain (1890) | brief definition, KJV usage, derivation lines |
| STEPBible TAHOT/TAGNT (already in `word_alignments`) | CC BY 4.0 | counts, parsing, editions, collocations |
| Word alignments (`english_alignment_verses`, `lemma_renderings`) | CC BY 4.0 (derived) | renderings, samples |
| Nave's Topical Bible (`naves_*`) | Public domain (1896) | topics |
| OpenBible.info cross-references | CC BY 4.0 | cross-references among occurrences |

Rejected: STEPBible TBESH (its header asks for Online Bible's permission for
the brief definitions), TBESG (mixes Middle Liddell, CC BY-SA, and Mounce,
unverified) and TFLSJ (LSJ, CC BY-SA) — Traps 1 of
`docs/RESOURCE_LICENSES_2026-10.md`; Thayer (no clean structured source).
The OpenScriptures BDB is CC BY: the credit line travels in `sources.bdb`.

## Method

**The text that is counted.** OT: every TAHOT token except LXX-reconstructed
words (`word_type` `X…`). NT: tokens in the SBL Greek NT (BSB's base text);
TR and Byzantine counts are given beside it. Edition membership is by exact
name, and TAGNT's displaced-word marks count (`TR«3` is in the TR).
442,690 tokens, 13,913 lemmas.

**Counts agree with the printed lexicons.** Greek totals equal Abbott-Smith's
printed NT counts for 89.8% of 5,198 lemmas and are within 5% for 96.3%
(Abbott-Smith counted a different Greek text). BDB prints a number after the
headword for 580 entries; ours is within 5% for 81.6% of them. That number is
usually but not always an occurrence count (H5379 prints 656 against 1
occurrence), so `meta.count` is labelled as "the number BDB prints".

**Forms.** Greek (Robinson codes): verbs by tense-voice-mood ("aorist active
indicative"), nouns, adjectives and pronouns by case and number. Hebrew and
Aramaic (OSHB codes as used by STEPBible): the word's own segment after
prefixes (ו, prepositions, article, interrogative ה, relative ש); verbs by
stem and conjugation ("Qal perfect", "Niphal participle"), nouns by number and
state. Labels are the standard grammatical names of the codes.

**Part of speech and function words.** A lemma's part of speech is the most
common one over its occurrences. Function words are everything except nouns,
verbs and adjectives (articles, conjunctions, prepositions, particles,
pronouns, adverbs), plus seven lemmas the parsing calls nouns or verbs but
which do grammatical work: kol "all", ʾayin "there is not", yesh "there is",
bayin "between", hayah "be", eimi "be", pas "all". 558 lemmas.

**Lexicons.** Each lexicon keeps its own rows (`lexicon_entries`), converted
from XML to plain text with one sense per line, indented by depth. Coverage of
lemmas that occur: Greek 5,388 lemmas, Dodson 5,293 (98.2%), Abbott-Smith
5,293 (98.2%); Hebrew 8,525 lemmas, BDB 8,511 (99.8%). (The Hebrew misses are
STEPBible-only numbers such as H9033, which no lexicon has.) BDB homographs
sharing a Strong's number (H2617 I "goodness, kindness", II "shame") are all
shown; their order is computed (see weaknesses).

**Renderings** come from `lemma_renderings` (links with calibrated confidence
≥ 0.5, the alignment doc's cut for content words) and the verses for one
rendering from the existing `/renderings` endpoint.

**Collocates ("words it travels with").** Unit: the verse, within one
testament (Hebrew/Aramaic with Hebrew, Greek with Greek); each lemma counted
once per verse; function words removed on both sides. For lemmas *a* and *b*
with verse counts R and C out of N verses, sharing O verses: kept when
O ≥ 3, O > expected (R·C/N) and Dunning's log-likelihood G² ≥ 15.13 (p < 0.0001,
1 df). Ranked by logDice = 14 + log2(2·O/(R+C)), which does not favour very
frequent words the way G² does. Top 15 stored. 4,524 lemmas have at least one.

**Related lemmas.** Only what a lexicon states: Strong's derivation lines
("from G25" → derived_from; numbers in parentheses or after "compare/like/see"
→ compare), Abbott-Smith's "< word" derivations (only the words right after
"<", so "v.s. ἀγάπη", *see under*, is not a source), BDB root families from the
OpenScriptures LexicalIndex (entries under the same root). 44,054 relations
for 13,009 lemmas.

**Nave's topics.** A topic's verse list (ranges expanded) against the lemma's
verses over all 31,102 verses: kept when they share ≥ 3 verses, more than
chance, G² ≥ 15.13; ranked by G² (ranking by the share of the topic's verses
favoured tiny topics: RAINBOW for nephesh). Top 8. 4,426 lemmas.

**Cross-references among occurrences.** OpenBible.info pairs whose two
verses both contain the lemma, positive votes, unordered pairs, by votes; top
8. 3,068 lemmas. Kept because real examples are meaningful: Exod 34:6 ↔ Ps
86:15, Joel 2:13, Ps 103:8 for ḥesed; John 1:1 ↔ Rev 19:13, John 1:14,
1 John 1:1 for logos; Isa 41:10 ↔ Isa 43:1, Deut 31:6 for yare.

**Sample verses** (lemmas with more than 12 occurrences; otherwise all of
them): one for each BSB rendering used in ≥ 5% of occurrences (at most 6),
then one for each part of the canon not yet represented (Law, History, Wisdom,
Prophets, Gospels, Acts, Paul, General Letters, Revelation; largest first),
then one for each book not yet represented (largest first), up to 12. Within
a choice: the least-represented part of the canon, then the verse with the
most OpenBible cross-reference votes (a data proxy for well-known verses);
part-of-canon and book picks prefer an occurrence rendered in one of the
frequent ways, so a stray alignment does not become the example. 2,984 lemmas.

## Hand check (2026-11-13)

Twelve words, read in full. "Right" means it matched the lexicons and what a
reader would expect; "wrong" lists every problem seen.

| Lemma | Count | Looks right | Looks wrong |
|---|---:|---|---|
| G26 agapē | 116 (A-S 116) | BSB love 109, KJV love 82 / charity 27; collocates pistis, gnōsis, hypomonē, agapaō, makrothymia, anypokritos; topics LOVE, GRACES, LONGSUFFERING; xrefs 2 Tim 1:7–1 John 4:18; samples John 15:13, Rom 5:8, 1 Cor 13:13 | BSB "faith 1", "it 1" (alignment errors); related shows only agapaō (Strong's); Abbott-Smith gives no derivation |
| G3056 logos | 328 (A-S 330) | word/words/message/account; collocates akouō, laleō, tēreō, speirō (sower); related logizomai, logikos, apologeomai…; xrefs John 1:1 ↔ Rev 19:13, John 1:14 | only 4 collocates (frequent word, strict cut); topics include MINISTER, PAUL, JESUS THE CHRIST (big topics) |
| G4102 pistis | 242 (243) | faith 224; collocates agapē, dikaiosynē, Christos, ergon, epangelia, nomos, dikaioō, Abraham; topics FAITH, JUSTIFICATION, WORKS; xref Heb 11:1 ↔ 2 Cor 5:7 | — |
| G1343 dikaiosynē | 91 (92) | righteousness 80, justice 2; collocates logizomai, pistis, diōkō, Abraham, hamartia, nomos; Matt 6:33 ↔ Matt 5:6 | — |
| G5485 charis | 155 (155) | grace/favor/thanks; collocates Christos, eirēnē (greetings), theos, kyrios, dōrea; topics BENEDICTIONS, GRACE OF GOD | topics TIMOTHY, ADAM; collocates reflect letter greetings more than theology |
| H2617 ḥesed | 247 (BDB 247) | BSB loving devotion 171, KJV mercy 135 / lovingkindness 25, WEB loving kindness 163; collocates ʾemet, ʿolam, yadah, raḥamim, ʾemunah, "slow (to anger)", raḥum, ḥanun; Exod 34:6 ↔ Ps 86:15; BDB I and II both shown | count includes 2 uses of BDB II "shame" (Lev 20:17, Prov 14:34; BSB "disgrace"); topic GOD (33 of 1,588) |
| H7965 shalom | 237 (237) | peace 119/160/163, safely, prosperity, welfare; related shalam root family; Isa 26:3 ↔ Isa 9:6 | collocates are greeting formulas (ask, send, say, come, Jehu); topics JORAM, MICAIAH, JEHU, CUSHI (2 Kgs 9 "Is it peace?"); BSB "have you come in peace" as one rendering (5) |
| H7307 ruaḥ | 378 (378) | spirit/wind/breath; "side" 4 is right (Ezek 42); collocates east wind, breath, waters, heart, storm; topic HOLY SPIRIT; Isa 44:3 ↔ Joel 2:28 | BSB rendering "a" 4 (alignment noise); topics LYING, MICAIAH (1 Kgs 22) |
| H3372 yare | 315 | afraid/fear/feared/awesome; collocates ḥatat ("be dismayed"), "very", God, great; Qal jussive 82 = "do not fear"; Isa 41:10 ↔ Isa 43:1 | — |
| H1285 berit | 284 (285) | covenant 255, treaty 14, KJV league 14; collocates karat (cut), ark, parar (break), ʿolam, zakar, shamar, oath; topics COVENANT, ALLIANCES, TREATY, RAINBOW | related bara "create" (now `compare`; was wrongly "derived" before the parenthesis rule) |
| H3519 kabod | 200 | glory/honor/glorious; collocates riches, cloud, fill, "give (glory)"; topics GLORY, CLOUD; Ps 57:5 ↔ Hab 2:14, Isa 6:3 | BDB root family includes "liver" (kabed): right per BDB, surprising to a reader |
| H5315 nephesh | 754 (756) | soul/life/person; collocates alive, seek, die, cut off, eat, heart, blood, love; Deut 6:5 ↔ Deut 10:12; samples Lev 17:11, Deut 6:5, Ps 19:7 | BSB "I 17", "me 17", "you 14" are BSB's own translation (nephesh as "self") but read oddly; topics are noise (ATONEMENT, SANITATION, MASSACRE, RAINBOW) |

## Known weaknesses

- **Nave's topics** are the weakest section: for narrative-heavy words they
  follow the stories the word occurs in (shalom → JORAM, JEHU), not its
  meaning. Shown with hits/topic size so a reader can judge; consider hiding
  topics with fewer than ~5 hits.
- **Collocates** reflect formulas (greetings with charis/eirēnē, "Is it
  peace?" with shalom) as much as ideas; for very frequent lemmas the strict cut
  leaves few (logos: 4). They are verse co-occurrence, not syntax.
- **BDB depth**: of the 8,673 primary BDB entries, 6,165 (71%) are "base" in
  the OpenScriptures edition: the sense outline without the references; 2,123
  ("ref") and 384 ("done") have references. `meta.status` says which.
- **Homographs**: counts cannot separate BDB homographs (STEPBible's lemma
  letters are not kept in `word_alignments`), so H2617 counts include ḥesed II.
  Homograph order uses the renderings, then the printed number, then article
  length; H1817's three "door" entries tie and the order is not meaningful.
- **Renderings** inherit alignment errors (function-word fragments such as "a",
  long phrases such as "have you come in peace"). The 0.5 confidence cut is
  the alignment doc's content-word rule; function-word lemmas would need 0.7.
- **Strong's numbering** does not always match a lexicon's lemma: the largest
  count disagreements with Abbott-Smith are G3700 (54 here, 1 there), G5552 and
  G3376; Strong's derivation lines sometimes cross languages (Salome G4539
  "from H7965").
- **Hebrew transliteration** is OSHB's lemma form (Strong's Hebrew has none);
  a few lemmas have none at all (H430 in collocate lists).
- The study does not cover the LXX (no clean morphology; license review Trap 7).

## Found while building (outside this work)

- `/api/passage/{ref}/interlinear` filters editions with `LIKE '%TR%'`, which
  SQLite matches case-insensitively against "Treg": the KJV interlinear shows
  5,194 Tregelles-only tokens in 260 chapters. Fix: the exact test in
  `backend.word_study.edition_sql`.
- The aligner's `SourceToken.in_edition` uses exact names, so 482 TR and 507
  Byzantine tokens marked as displaced (`TR«3`) are not candidates for KJV/WEB
  links.
