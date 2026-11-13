# Scripture-to-hymn index (2026-11)

From a passage, find hymns that quote it or are built on it, so a song leader
can pick Sunday's text and see hymns that fit. Build step `hymns`
(`scripts/import_hymns.py`, 8 s); API `backend/routers/hymns.py`; join keys
`backend/hymn_keys.py`; tests `tests/test_hymns.py`.

## Sources: what was checked, used and rejected

Checked at the primary source on 2026-11-13 (quotes are from the sites or the
files themselves). Round two (2026-11-13) added five sources whose Scripture
basis is in their own structure: metrical psalters (each text is a psalm by
construction) and hymnals that print a text under each hymn.

| Source | Verdict | Evidence | Used for |
|---|---|---|---|
| **Open Hymnal Project** (openhymnal.org), edition 2026.11, one ABC file | **Used** | openhymnal.org/copying.html: "All content produced specifically by the Open Hymnal which is not a part of a hymn is placed into the public domain. This includes compilation, indices, web pages (or parts thereof), scripts used to assemble the hymnal, and all other data files." Hymn words and music: "Specific copyright terms are listed on each score sheet and in each abc file." | 346 scores, its Scripture index, credit lines, quotations from public-domain words |
| **Watts, *The Psalms of David Imitated*** (1719), 1818 printing, Project Gutenberg #13166 | **Used** | gutenberg.org/policy/license.html: "If you strip the Project Gutenberg license and all references to Project Gutenberg from the text, you are left with a text unrestricted by U.S. intellectual property law." Only the text between the START/END markers is read; nothing of Project Gutenberg's is stored | 290 psalm versions; heading gives psalm and verses ("Psalm 90:2. 1-5. First Part. C. M."); quotations |
| **Watts, *Hymns and Spiritual Songs*** (1707), 1818 printing, Project Gutenberg #13341 | **Used** | as above | 360 hymns; 140 with the text printed under the title ("Crucifixion to the world by the cross of Christ, Gal. 6. 14."); quotations |
| **Tate and Brady, *A New Version of the Psalms*** (1696), EEBO-TCP A27952 (commit 8211195) | **Used** | the file's `<availability>`: "This Phase I text is available for reuse, according to the terms of Creative Commons 0 1.0 Universal. The text can be copied, modified, distributed and performed, even for commercial purposes, all without asking permission." | 237 psalm versions (psalm-level); quotations |
| **Scottish Psalter (1650) and Paraphrases (1781)**, CCEL ThML | **Facts only** | The works are public domain and the file says `<DC.Rights>Public Domain</DC.Rights>`, but ccel.org/about/copyright.html: "These books may be used for personal, educational, or non-profit purposes. Contact us for permission to republish CCEL works or to use them commercially", and CCEL claims its markup. Bible MVP is free and non-commercial, but "republish" is not defined, so only facts are taken: first line, the psalm or passage, author, metre. No text is stored and no quotations are computed from it. `hymn_sources.ENABLE_CCEL = False` removes both CCEL sources | 251 items, psalm or passage for each |
| **Olney Hymns** (Newton and Cowper, 1779), CCEL ThML | **Facts only** | as above (`<DC.Rights>Public Domain</DC.Rights>`) | 348 hymns; 157 with the text printed under the hymn (Book I: 133 of 141), e.g. "Amazing grace!" → 1 Chr 17:16-17 |
| Hymnary.org (texts, per-hymnal Scripture indexes, `/api/scripture`) | Not used without permission | hymnary.org/copyright: "Hymnary.org website and special contents copyright 2007-present Harry Plantinga ... some are copyrighted with rights reserved." No open license on the copyright, FAQ or API pages. By far the richest data (it indexes the Scripture of individual hymnals such as *Praise! Our Songs and Hymns*, 1979). A request is drafted below | — |
| Cyber Hymnal (hymntime.com) | Not used without permission | "The design & HTML code of our Web pages are copyrighted, & may not be reproduced"; the Scripture pages carry "© 2000–2026 Richard W. Adams" | — |
| CCEL Watts, *Psalms and Hymns* (ThML with `scripCom`) | Not used | Same CCEL terms; the Project Gutenberg copies of both Watts books carry the same Scripture headings with a clean status | — |
| *The Psalter* (1912), Internet Archive OCR | Not yet | Public domain (1912), but stanza 1 is OCR'd under the music and is mostly noise; psalm-level only. Worth doing later from its Index of First Lines | — |
| Internet Archive scans of other pre-1928 hymnals | Not used | Methodist Hymnal 1905, Presbyterian *Hymnal* 1911, Gospel Hymns 1875: no Scripture index; poor OCR | — |
| Wikidata (CC0) | Not used for links | 3,497 hymn items; only 110 link to a Bible passage or event | — |
| Doddridge, *Hymns founded on Various Texts* (1755); Sternhold & Hopkins (EEBO-TCP) | Leads, not checked | Every Doddridge hymn has a text heading; the ECCO-TCP record could not be reached | — |

Not legal advice.

## What is stored

`hymns` (1,832 rows: 346 Open Hymnal scores, 290 Watts psalm versions, 360
Watts hymns, 237 Tate and Brady psalm versions, 251 Scottish Psalter items, 348
Olney hymns; **1,787 distinct texts**, 25 of them found in more than one
source): `title`, `alt_titles`, `first_line`, `author` (as the source writes
it), `translator`, `words_year`, `words_credit`, `tune`, `composer`, `meter`,
`topics`, `category`, `words_public_domain`, `copyright` (the source's line),
`title_key`, `keys`, `text_key`, `source`, `source_url`.

**One text, several sources.** Items are merged by `text_key`, the letters and
digits of the first line, lowercased ("Amazing grace! (how sweet the sound)"
in Olney = "Amazing grace! How sweet the sound" in the Open Hymnal). Every
item keeps its own row and its own Scripture links with their `source`; the
API merges them per text. Examples: "Our God, our help in ages past", "Joy to
the world", "Jesus shall reign", "When I survey the wondrous cross" (Open
Hymnal + Watts); "Amazing grace" (Open Hymnal + Olney); "All people that on
earth do dwell" and "The Lord's my shepherd" (Open Hymnal + Scottish Psalter).
Altered texts do not merge ("O God, our help" vs Watts' "Our God, our help").

Hymn text: only the **first line** (1,805 items). Full words are read only to
compute quotations, and only from public-domain copies with a clean status
(Open Hymnal public-domain words, Project Gutenberg, TCP), never from CCEL.
Open Hymnal first lines are cut from the first verse by the metre's first
number of syllables ("8 6 8 6" → "Amazing grace! How sweet the sound"); the
psalters and hymnals print them. `words_public_domain` (Open Hymnal) is false
when the copyright line says the words are under copyright; true for every
item from the older sources.

`hymn_scripture` (2,769 links): `hymn_id`, `book`, `chapter`, `verse_start`,
`verse_end` (NULL = whole chapter), `kind`, `source`, `ref_text` (as written),
`evidence`. Every reference is checked against the KJV's chapters and verse
counts; a misprint is dropped, not guessed (Watts "Col. 9. 16", Olney "Isa
33:27,28" for "Glorious things": Isaiah 33 has 24 verses).

| kind | source | links (items) | meaning |
|---|---|---:|---|
| `paraphrase` | `pg-watts-psalms` | 351 (290) | a metrical version of the psalm, with the verses when the heading gives them |
| `paraphrase` | `tcp-tate-brady` | 237 (237) | a metrical version of the psalm (psalm-level) |
| `paraphrase` | `ccel-scottish-psalter` | 253 (251) | a metrical psalm or a paraphrase of the passage |
| `paraphrase` | `openhymnal-credit` | 3 (3) | the credit line names the source: "Words: Psalm 146 …" |
| `based_on` | `pg-watts-hss` | 220 (140) | the text printed under the hymn's title |
| `based_on` | `ccel-olney` | 163 (157) | the text printed with the hymn |
| `reference` | `openhymnal` | 1,513 (346) | the Open Hymnal's Scripture line; the source does not say whether quoted, paraphrased or topical |
| `quotes` | `kjv-overlap` | 29 (29) | computed (below); `evidence` holds the shared words |

### Quotations

A hymn line counts as quoting a KJV verse when it shares a run of **at least 6
words** with **exactly one** KJV verse (every 5-word window of the run occurs
in that verse only, and has at least 2 words outside a short function-word
list) and the run holds **a word found in fewer than 100 KJV verses**.

How the threshold was chosen. Metrical psalms give a check with a known
answer: a quotation inside the item's own psalm is real; one pointing
elsewhere is mostly chance (or a parallel passage). Over Watts' psalms and
Tate and Brady (222 candidate runs, 83 in their own psalm):

| Rule | kept | outside own psalm |
|---|---:|---:|
| round one: ≥ 6 words, or 5 with a rare word; n-gram in ≤ 3 verses | 100 | 47 (47%) |
| ≥ 7 words, or 2 rare words | 23 | 10 (43%) |
| ≥ 7 words or a rare word, n-gram in 1 verse | 74 | 29 (39%) |
| **≥ 6 words, a rare word, n-gram in 1 verse (used)** | **13** | **3 (23%)** |

Of those 3, one is real (Watts' Psalm 32 quotes Rom 4:8, which is Paul quoting
Psalm 32). Over every source, the rule gives 29 links; reading all 29, about
27 are real quotations or close allusions ("holy holy holy lord god almighty"
Rev 4:8, "not dismayed for i am thy" Isa 41:10, "when i am weak then am i
strong" 2 Cor 12:10, "i shall be whiter than snow" Ps 51:7) and 2 are doubtful
(Tate and Brady's Psalm 118 → Ps 20:6 "saving strength of his right hand";
Watts → Ps 38:6 "i go mourning all the day"): about 93% precision, against
about 84% in round one. The price is recall: the round-one rule found 44
links in the Open Hymnal alone; this one finds 9 there, and misses real
5-word quotations ("with healing in his wings" Mal 4:2, "i know that my
redeemer" Job 19:25, "here am i send me" Isa 6:8).

Coverage: 58 books, 571 of 1,189 chapters. Every psalm has at least three
versions.

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
    "sources_for_text": ["ccel-scottish-psalter", "openhymnal"],  // every source holding the text
    "links": [{"reference": "Psalms 23", "hymn_id": "oh-332", "book": "Psalms", "chapter": 23,
               "verse_start": null, "verse_end": null, "kind": "paraphrase",
               "source": "openhymnal-credit", "as_written": "Psalm 23",
               "evidence": "Psalm 23 from the Scottish Psalter, ..."}],   // best first
    "settings": [{"id": "oh-332", "source": "openhymnal", "title": "...", "tune": "...",
                  "meter": "..."}, {"id": "sp-p24", "source": "ccel-scottish-psalter", ...}]
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

The item, `passages` (every link of every item with the same text, canonical
order, each with `source` and `hymn_id`), `other_settings` (the other items of
the text, with their source), `sources`. 404 if unknown.

### `GET /api/hymns?q=…` / `?key=…`

`q`: words that must all appear in the title, alternate titles or first line.
`key`: a title or first line from another hymnal, matched by join key
(below); a title of 12 letters or more also matches a first line it begins
("Joy to the World" → "Joy to the world; the Lord is come").
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
distinct songs; its title list is public on hymnary.org): **118 of its 562
songs match** (round one: 104), all with Scripture links. The new ones come
from Watts and Olney ("There Is a Fountain Filled with Blood", "God Moves in a
Mysterious Way", "How Sweet the Name of Jesus Sounds", "O for a Closer Walk
with God", "Join All the Glorious Names", "Come, We That Love the Lord").
Most of the rest are 20th-century gospel songs and choruses still under
copyright, which no public-domain source can supply.

Well-known hymns in the index that still lack their most obvious passage (the
"obvious" passage is a judgment, not data, so nothing was added):
"A Mighty Fortress Is Our God" (Ps 46), "Nearer, My God, to Thee" (Gen
28:10-22), "Praise to the Lord, the Almighty" (Ps 103 / 150), "It Is Well
with My Soul" (2 Kgs 4:26), "O Sacred Head, Now Wounded" (Matt 27:29), "Rock
of Ages" (Isa 26:4 margin), "Praise God from Whom All Blessings Flow" (Ps
150). Not in any source used: "How Great Thou Art", "O Worship the King",
"Love Divine, All Loves Excelling", "This Is My Father's World", "When
Morning Gilds the Skies", "Come, Thou Almighty King".

## Known weaknesses

- **Coverage** of a modern evangelical hymnal stays low (118 of 562 songs in
  the hymnal measured): the clean sources are pre-1930, and gospel songs and
  choruses after that are under copyright. Hymnary.org is the only richer
  source, and it needs permission.
- **The Open Hymnal's references are curated, not exhaustive, and untyped**
  ("All People That on Earth Do Dwell" carries Ps 33, 1 Chr 16, Ps 5, Ps 9;
  Ps 100 now comes from the Scottish Psalter). Some look odd ("God Rest Ye
  Merry Gentlemen" → Ps 46:10). They are shown as the source gives them.
- **CCEL items are facts only** and depend on CCEL's terms (above); turning
  them off removes "Amazing grace" → 1 Chr 17:16-17 and the Scottish Psalter.
- **Psalm-level links** (Tate and Brady, most Scottish Psalter items, Watts
  psalms without a verse list) say nothing about which verses a part covers.
- **Merging is by exact first line**: altered texts stay apart ("Our God, our
  help" / "O God, our help"), and two different texts with the same first line
  would merge (none seen).
- **Computed quotations** are about 93% right but find only long, distinctive
  runs of KJV wording.
- **Ids** are per source and stable within one edition of the source; join by
  `keys`, not by id, across editions.


## Next steps

1. The owner decides whether to send the Hymnary.org request below; with that
   data, coverage of a hymnal like *Praise! Our Songs and Hymns* would go from
   118 songs to most of them.
2. *The Psalter* (1912) from its Index of First Lines (OCR), psalm-level.
3. Doddridge's *Hymns founded on Various Texts* (1755), if a clean TCP copy can
   be reached: every hymn is headed by its text.
4. Verse ranges for psalm parts (Tate and Brady, Scottish Psalter) from the
   verse numbers the Scottish Psalter prints in its lines.

## Draft: request to Hymnary.org (for the owner to send, or not)

> Subject: Permission request: Scripture references for a free Bible study app
>
> Hello,
>
> I run Bible MVP (study.inthewordproject.org), a free Bible study web app with
> no ads, no paid tier and no sales. It can be downloaded for offline use as a
> single database. I lead singing at a small church and would like the app to
> show, for a Bible passage, hymns that are based on it.
>
> May we use, and include in the app's downloadable database, the following
> Hymnary.org data?
>
> - For hymn texts: text ID, title, first line, author name, year, and the
>   Scripture references you list for each text.
> - For the hymnal *Praise! Our Songs and Hymns* (1979): hymn number and the
>   text ID it prints (so we can join our church's hymnal to the above).
>
> We would not copy hymn words, tunes, scores, images or any copyrighted text,
> would credit Hymnary.org (with a link) wherever the data is shown, and would
> refresh it only as often as you allow. If an export or the scripture API is
> the preferred way to get it, we will use that, at whatever rate you set.
>
> If you would rather not, that is fine; thank you for considering it.
>
> [name, contact]

(Not sent. The same request, without the hymnal line, would suit the Cyber
Hymnal; CCEL could be asked to confirm that taking first lines and printed
references from its Scottish Psalter and Olney Hymns files is acceptable.)
