# Scripture-to-hymn index (2026-11)

From a passage, find hymns that quote it or are built on it, so a song leader
can pick Sunday's text and see hymns that fit. Build step `hymns`
(`scripts/import_hymns.py`, 8 s); API `backend/routers/hymns.py`; join keys
`backend/hymn_keys.py`; tests `tests/test_hymns.py`.

## Sources: what was checked, used and rejected

Checked at the primary source on 2026-11-13 (quotes are from the sites).

| Candidate | Verdict | Evidence |
|---|---|---|
| **Open Hymnal Project** (openhymnal.org), edition 2026.11, one ABC file | **Used** | openhymnal.org/copying.html: "All content produced specifically by the Open Hymnal which is not a part of a hymn is placed into the public domain. This includes compilation, indices, web pages (or parts thereof), scripts used to assemble the hymnal, and all other data files." Hymn words and music: "Specific copyright terms are listed on each score sheet and in each abc file." |
| Hymnary.org (texts, per-hymnal Scripture indexes, `/api/scripture`) | Rejected without permission | hymnary.org/copyright: "Hymnary.org website and special contents copyright 2007-present Harry Plantinga ... some are copyrighted with rights reserved." No open license on the copyright, FAQ or API pages; its CSV exports sit behind a bot check. By far the richest data (it even indexes the Scripture of individual hymnals such as *Praise! Our Songs and Hymns*, 1979); worth a written permission request |
| Cyber Hymnal (hymntime.com) Scripture pages | Rejected without permission | hymntime.com/tch/misc/copyrite.htm: "The design & HTML code of our Web pages are copyrighted, & may not be reproduced"; the Scripture pages carry "© 2000–2026 Richard W. Adams" |
| CCEL public-domain hymnals (e.g. Watts, *Psalms and Hymns*, with `scripCom` tags) | Not used | ccel.org/about/copyright.html: "These books may be used for personal, educational, or non-profit purposes ... Contact us for permission to republish CCEL works"; CCEL claims its markup. Mostly Watts texts evangelical hymnals rarely use |
| Internet Archive scans of pre-1928 hymnals | Not used | The ones checked (Methodist Hymnal 1905, Presbyterian *Hymnal* 1911, *Psalter* 1912, Gospel Hymns 1875) have no Scripture index, and the OCR is poor |
| Wikidata (CC0) | Not used for links | 3,497 hymn items; only 110 link to a Bible passage or event. Useful later for its Hymnary.org IDs |

The research on Hymnary.org, Cyber Hymnal, CCEL, Internet Archive and
Wikidata was done by fetching their terms pages and samples; the Open Hymnal
terms were re-read before use. Not legal advice.

## What is stored

`hymns` (346 rows, one per Open Hymnal score; 332 distinct texts, since some
texts have several tunes): `title`, `alt_titles` ("also known as"),
`first_line`, `author` (as the source writes it, "Newton, John
(1725-1807)"), `translator`, `words_year` (1146–2024), `words_credit`,
`tune`, `composer`, `meter`, `topics` (the hymnal's topical index),
`category`, `words_public_domain` (328 of 346), `copyright` (the source's
line, verbatim), `title_key`, `keys`, `text_key`, `source`, `source_url`.

Hymn text: only the **first line**, and only when the words are public domain
(319 hymns; 9 public-domain scores have no lyric line under the notes). It is
cut from the first verse by the metre's first number of syllables
("8 6 8 6" → "Amazing grace! How sweet the sound"). Full lyrics are not
stored: reconstructing them from the ABC syllables is error-prone, and a
congregation sings from its own hymnal.

`words_public_domain` is false when the copyright line says the words or
lyrics are under copyright ("music and setting public domain. Words:
Copyright 2005, …") or the whole hymn is licensed ("This hymn (lyrics, music,
and setting) may be freely reproduced …"); otherwise true when it says
"public domain".

`hymn_scripture` (1,560 links): `hymn_id`, `book`, `chapter`, `verse_start`,
`verse_end` (NULL = whole chapter), `kind`, `source`, `ref_text` (as written),
`evidence`. Kinds, as far as the sources say:

| kind | source | count | meaning |
|---|---|---:|---|
| `reference` | `openhymnal` | 1,513 (346 hymns) | the hymnal's own Scripture line. The source does not say whether a reference is quoted, paraphrased or topical |
| `paraphrase` | `openhymnal-credit` | 3 | the hymn's credit line names the passage as its source: "Words: Psalm 146 …", "Psalm 23 from the Scottish Psalter", "after Is 6:1-4" |
| `quotes` | `kjv-overlap` | 44 (35 hymns) | computed: a line of the public-domain words shares a run of words with one to three KJV verses; `evidence` holds the shared words |

Quotation rule: 5-word sequences (lowercased words) that occur in at most 3
KJV verses and contain at least 2 words outside a short function-word list;
a hymn line matching one counts when the shared run is at least 6 words long,
or 5 words with one word found in fewer than 100 KJV verses. This keeps "holy
holy holy lord god almighty" (Rev 4:8), "i know that my redeemer" (Job 19:25),
"with healing in his wings" (Mal 4:2), and drops chance runs of common words
("that we may live and", "the son of man in"). By reading all 44: about 37 are
real quotations or close allusions; about 7 are chance ("that he may live with
thee" → Lev 25:35; "happy is the man that" → three Proverbs/Psalms verses;
"for we know not what we" → Rom 8:26).

References are parsed from the Open Hymnal's own abbreviations (`Lv`, `Ez`
= Ezekiel, `So`, `1Pt`); a reference without a book takes the previous one's
("Is 41:10, 43:2-5"); "5:7b" is read as 5:7; a range across chapters
("Lk 1:67-2:10") becomes one row per chapter.

Coverage: 52 books, 419 of 1,189 chapters (NT 1,094 links, OT 466; Psalms
213, John 166, Luke 135, Matthew 130). Of 300 random chapters, 110 have at
least one hymn.

## API

### `GET /api/hymns/for-passage`

`ref=Psalm 23` / `ref=John 3:16-21`, or `book`, `chapter`, `verse_start`,
`verse_end`. `include_chapter` (default true): also hymns linked to other
verses of the same chapter, after the others. `limit` (default 30, max 100).
400 for a bad reference, 404 for a chapter that does not exist.

```jsonc
{
  "passage": {"book": "Psalms", "chapter": 23, "verse_start": 1, "verse_end": 6},
  "ranking": "1) hymns linked to verses inside the passage before ... 5) title",
  "total": 10,
  "hymns": [{
    "id": "oh-332", "title": "The Lord's My Shepherd", "alt_titles": [],
    "first_line": "The Lord's my shepherd I'll not want",
    "author": "from the Scottish Psalter, 1650", "translator": null, "words_year": 1650,
    "words_credit": "Psalm 23 from the Scottish Psalter, 1650 alt. by ...",
    "tune": "Marosa, Brother James` Air", "composer": "...", "meter": "8 6 8 6 8 6 8 6",
    "topics": ["..."], "category": "...", "words_public_domain": true,
    "copyright": "public domain. ...", "keys": ["lordsmyshepherd", "..."],
    "text_key": "...", "source": "openhymnal", "source_url": "http://openhymnal.org/",
    "match": "passage",                                  // or "chapter"
    "links": [{"reference": "Psalms 23", "book": "Psalms", "chapter": 23,
               "verse_start": null, "verse_end": null, "kind": "paraphrase",
               "source": "openhymnal-credit", "as_written": "Psalm 23",
               "evidence": "Psalm 23 from the Scottish Psalter, ..."}],   // best first
    "settings": [{"id": "oh-332", "tune": "...", "meter": "..."}]        // all tunes of this text
  }],
  "sources": {"openhymnal": {"name": "...", "license": "...", "attribution": "...",
                             "url": "...", "note": "..."}, ...}
}
```

Ranking: (1) hymns linked to verses inside the passage before hymns linked
only elsewhere in the chapter; (2) a quotation or paraphrase before a plain
reference; (3) the share of the hymn's linked verses that fall inside the
passage (a hymn on Ps 23:4 fits a reading of Ps 23:1-6 fully; one on
Ps 23–24 only half); (4) the share of all the hymn's links that touch the
passage (a hymn citing 3 passages is more about each of them than one citing
12); (5) title. Several tunes of one text are one result (`settings`).

### `GET /api/hymns/{id}`

The hymn, `passages` (every link, canonical order), `other_settings`
(other tunes of the same text), `sources`. 404 if unknown.

### `GET /api/hymns?q=…` / `?key=…`

`q`: words that must all appear in the title, alternate titles or first line.
`key`: a title or first line from another hymnal, matched by join key (below).
Each result carries `scripture_links` (its link count). `limit` default 50.

Speed (bridge, 300 random chapters): median 22 ms, p95 47 ms, max 79 ms;
payload median 1.4 KB, p95 8.9 KB, max 27 KB (Luke 2). Tables: 0.5 MB.

## Joining another hymnal

`backend/hymn_keys.py` `title_key()`: lowercase, drop text in parentheses,
drop a leading "the", "a" or "an", keep letters and digits. Every hymn stores
`keys`: the keys of its title, each alternate title and its first line. A
client computes the same key for its own titles (and for the text inside any
parentheses) and intersects, so a hymnal's own title list can be joined
locally, without sending it anywhere.

Measured against *Praise! Our Songs and Hymns* (1979, 572 numbers, 562
distinct songs; its title list is public on hymnary.org): **104 of its 562
songs match** a hymn here, all of them with Scripture links (on average about
4 each). The rest are mostly 20th-century gospel songs and choruses still
under copyright, plus some public-domain classics the Open Hymnal does not
have ("O Worship the King", "Love Divine, All Loves Excelling", "This Is My
Father's World", "When Morning Gilds the Skies").

## Known weaknesses

- **Coverage** is the Open Hymnal's: 332 texts, chosen for being freely
  distributable. Many hymns a typical evangelical church sings are not there.
  The only richer source (Hymnary.org) needs permission.
- **The source's references are curated, not exhaustive, and not typed.**
  "All People That on Earth Do Dwell" (Kethe's paraphrase of Psalm 100) is
  linked to Ps 33, 1 Chr 16, Ps 5 and Ps 9, not Ps 100; Psalm 100 finds only
  two other hymns. Some links look odd ("God Rest Ye Merry Gentlemen" → Ps
  46:10). They are shown as the source gives them.
- **Paraphrase links are rare** (3): few credit lines name the psalm.
- **Computed quotations** are about 85% right (above) and only see the KJV
  wording; a hymn quoting another translation, or paraphrasing, is missed.
- **Ids** are the Open Hymnal's X: numbers (`oh-219`); five scores all
  numbered X:1 get `oh-1`, `oh-1-2`, ... Ids are stable within one edition; a
  new edition may renumber. Join by `keys`, not by id, across editions.
- The ABC file is cached by edition (`data/sources/hymns/OpenHymnal2026.11.abc`);
  the site replaces it when a new edition appears, so a fresh build without the
  cache needs `OH_EDITION` updated.

## Next steps

1. Ask Hymnary.org for written permission to use its Scripture data
   (`/api/scripture`, the texts CSV, and per-hymnal Scripture indexes) in a
   free, donation-supported app; with it, coverage of a hymnal such as
   *Praise! Our Songs and Hymns* would go from 104 songs to most of them. Ask
   the Cyber Hymnal as a second.
2. A small curated file of "the words are a paraphrase of" links, each row with
   a citation to a public-domain hymnal that prints the heading (e.g. the 1561
   Anglo-Genevan psalter's "Psalm C" for "All People That on Earth Do
   Dwell"), loaded with `kind = paraphrase` and the citation as `evidence`.
