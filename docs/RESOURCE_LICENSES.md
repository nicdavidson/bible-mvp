# Candidate Resource Licenses

> License research for free resources we might add to Bible MVP. Each entry
> was checked at its source (repo LICENSE file, file header, or publisher
> page) in Oct 2026. Scope: a free, open-source, non-commercial, publicly
> hosted web app.
>
> This file covers **new candidates only**. Resources already shipping are
> tracked in [`LICENSES.md`](../LICENSES.md). When a candidate is adopted,
> add it there too.

## Summary

| Resource | License (as verified) | Attribution | Share-alike / ND / NC | OK for public web app? | Best machine-readable source | Confidence |
|---|---|---|---|---|---|---|
| **STEPBible TBESG** (brief Greek lexicon) | CC BY 4.0 | "STEP Bible" linked to STEPBible.org | None (see LSJ / Mounce note) | Yes | `STEPBible-Data/Lexicons/TBESG …txt` (TSV) | High |
| **STEPBible TBESH** (brief Hebrew lexicon) | CC BY 4.0 on the file, **but** the definitions are Online Bible's Abridged BDB | STEP Bible + Larry Pierce / OnlineBible.net | None stated | ⚠️ **Glosses yes. Definitions need Online Bible permission** | `STEPBible-Data/Lexicons/TBESH …txt` (TSV) | Medium |
| **STEPBible TFLSJ** (full LSJ lexicon) | Labelled CC BY 4.0, but derived from Perseus LSJ, which is **CC BY-SA 4.0** | STEP Bible + Perseus Project (Tufts) | ⚠️ **Treat as share-alike** | Yes, under CC BY-SA terms | `STEPBible-Data/Lexicons/TFLSJ …txt` (2 files, TSV) | Medium |
| **Jamieson-Fausset-Brown (JFB)** | Public domain (1871; all authors d. by 1910) | None required (courtesy credit) | None | Yes | CrossWire SWORD module `JFB` v3.0 (OSIS, verse-keyed) | High |
| **ASV** (1901) | Public domain | None required | None | Yes | eBible.org `eng-asv` (USFM/USFX/VPL) | High |
| **YLT** (Young's Literal) | Public domain (1862/1898; Young d. 1888) | None required | None | Yes | eBible.org `engylt` (USFM/USFX/VPL) | High |
| **LSV** (Literal Standard Version) | **CC BY-SA 4.0**, © 2020 Covenant Press | Copyright line + source | **Share-alike** | Yes (verbatim, or with marked changes, under BY-SA) | eBible.org `englsv` (USFM/USFX/VPL) | High |
| **Vincent's Word Studies** | Public domain (1887–1900; Vincent d. 1922) | None required | None | Yes (the text) | ⚠️ **No clean open verse-keyed dataset found.** Internet Archive scans/OCR | High on PD, Low on source |
| **Theographic Bible Metadata** | **CC BY-SA 4.0** (repo LICENSE) | Theographic / Robert Rouse + OpenBible.info for coordinates | **Share-alike** | Yes, under BY-SA terms | `robertrouse/theographic-bible-metadata/json/*.json` | High (license), Medium (provenance) |

**Share-alike (BY-SA) in practice.** The MIT-licensed app code is not
affected: the database content is a separate work that the app reads, not
code compiled into it. But any dataset we build from BY-SA sources must be
released under CC BY-SA 4.0. That covers LSV text, TFLSJ entries, and
Theographic-derived tables, including our edits to them. Credit each one in
the UI and in `LICENSES.md`.

---

## Per-Resource Notes

### 1. STEPBible lexicons (TBESH, TBESG, TFLSJ)

**Sources checked**
- Repo README: <https://github.com/STEPBible/STEPBible-Data> (heading: "STEPBible Data Repository **CC BY 4.0**")
- Lexicon folder: <https://github.com/STEPBible/STEPBible-Data/tree/master/Lexicons>
  - `TBESH - Translators Brief lexicon of Extended Strongs for Hebrew - STEPBible.org CC BY.txt`
  - `TBESG - Translators Brief lexicon of Extended Strongs for Greek - STEPBible.org CC BY.txt`
  - `TFLSJ  0-5624 - Translators Formatted full LSJ Bible lexicon - STEPBible.org CC BY.txt`
  - `TFLSJ extra - Translators Formatted full LSJ Bible lexicon - STEPBible.org CC BY.txt`
- STEP copyrights page: <https://stepweb.atlassian.net/wiki/spaces/SUG/pages/12484619>
- Perseus LSJ repo: <https://github.com/PerseusDL/lexica> (GitHub license: CC-BY-SA-4.0)

**License:** CC BY 4.0. Credit it to "STEP Bible" linked to www.STEPBible.org,
which is the README's exact wording. Suggested UI credit: *"Lexicon data from
STEPBible.org (Tyndale House, Cambridge), CC BY 4.0."*

**Format:** tab-separated text with a long header block. Rows are keyed by
eStrong, dStrong, and uStrong. These are the same extended Strong's numbers
our TAGNT/TAHOT alignment data already uses, so the join is easy.

**⚠️ Flags**

1. **The README and the file headers disagree on redistribution.**
   - The README says you may include any part of the data "without requesting
     permission" and may "make a mirror, so long as it is kept up-to-date and
     has a link back here."
   - Each file header instead says "Download the data and reformat it for your
     application, *without changing the data*" and "*Please do not
     redistribute it yourself.*"

   CC BY 4.0 itself allows redistribution and adaptation, and those header
   lines read as requests rather than extra terms. Showing entries inside the
   app is clearly fine. To respect the request:
   - Don't offer a bulk download of the raw files.
   - If we correct anything, keep a public change note. Both texts ask for
     this.
2. **TBESH definitions are not STEP's to license.**
   - The TBESH header says: "The Brief lexicon is based on Abridged BDB by
     Online Bible … *Permission should be gained from Online Bible before
     these definitions are applied in any project.*"
   - The STEP copyrights page lists "Abridged … Brown-Driver-Briggs: © Larry
     Pierce of OnlineBible.net".
   - The Tyndale-made fields in the same file (gloss, morph, Strong's
     mapping) are CC BY.
   - **Recommendation:** import only the TBESH glosses and mappings. Keep
     using our existing Strong's (openscriptures, public domain) definitions
     for Hebrew. Use the abridged-BDB definitions only if Online Bible grants
     permission by email. **Do not ship TBESH definitions without that
     permission.**
3. **TFLSJ inherits Perseus's ShareAlike.**
   - TFLSJ is "edited from the Full LSJ." STEP's own copyrights page says the
     electronic LSJ is "under CC-BY-SA by the Perseus Project of Tufts
     University (who must be offered all modifications)."
   - The Perseus repo confirms CC BY-SA 4.0 and adds: "You must offer Perseus
     any modifications you make."
   - STEP's "CC BY" file label is therefore probably understated.
   - **Treat TFLSJ as CC BY-SA 4.0** and credit both STEP Bible and Perseus.
4. **TBESG is mostly clean.**
   - Its definitions come from Abbott-Smith (1922; author d. 1947), which is
     public domain in the US and also under life+70 rules.
   - A few gaps are filled from Middle Liddell, which is Perseus and so CC
     BY-SA, and from Mounce's Teknia dictionary on billmounce.com, which
     carries its own copyright. The header names the source per entry ("MD"
     or "Teknia").
   - **Low risk.** Optionally drop or flag the Teknia-sourced entries.

**Confidence:**
- TBESG: High.
- TBESH: Medium, because of the Online Bible permission note.
- TFLSJ: Medium, because the label conflicts with the upstream ShareAlike.

---

### 2. Jamieson-Fausset-Brown Commentary (JFB)

**Sources checked**
- CrossWire module page: <https://www.crosswire.org/sword/modules/ModInfo.jsp?modName=JFB>
- Module conf, from <https://www.crosswire.org/ftpmirror/pub/sword/packages/rawzip/JFB.zip>:
  `DistributionLicense=Public Domain`, `Version=3.0 (2021-02-15)`,
  `TextSource=https://ccel.org/ccel/j/jamieson/jfb/cache/jfb.txt`,
  `SourceType=OSIS`, `Versification=KJV`
- CCEL work page: <https://www.ccel.org/ccel/jamieson/jfb.html> (formats: TXT, ThML XML, PDF, ePub)
- CCEL copyright policy: <https://www.ccel.org/about/copyright.html>

**License:** public domain. The work was published in 1871. Jamieson died in
1880, Brown in 1897, and Fausset in 1910, so it is PD worldwide. No
attribution is required. Credit it as a courtesy.

**Best source:** the CrossWire SWORD module `JFB` (zCom4, OSIS, KJV
versification, about 5.7 MB zipped). It is already verse-keyed, and it can be
extracted with `pysword` or `diatheke`. The fallback is CCEL ThML XML or TXT,
which would need our own verse parsing.

**⚠️ Note on CCEL as a source:**
- CCEL's policy says: "These books may be used for personal, educational, or
  non-profit purposes. Contact us for permission to republish CCEL works or
  to use them commercially."
- CCEL also claims copyright on its "special contents": introductions, cover
  art, and the like.
- Our non-profit use fits the permission. The underlying PD text is free in
  any case.
- Strip any CCEL-authored front matter. This applies equally to the existing
  Henry, Spurgeon, and Gill imports listed in `LICENSES.md`.

**Confidence:** High.

---

### 3. ASV (American Standard Version, 1901)

**Sources checked**
- eBible.org: <https://ebible.org/find/details.php?id=eng-asv> ("public domain"; formats include USFM, USFX, VPL+SQL, OSIS/SWORD)
- open-bibles: <https://github.com/seven1m/open-bibles> (README lists `eng-asv.zefania.xml`, "Public Domain")

**License:** public domain. It was published in 1901, before 1929, so it is
PD in the US. No attribution is required.

**Best source:** eBible.org `eng-asv_usfm.zip` or `eng-asv_vpl.zip`. The VPL
format is one verse per line and the easiest to import. `eng-asv.zefania.xml`
from open-bibles also works, and it matches the repo we already use for WEB.

**Note:** ASV is **already listed** in `LICENSES.md`, and it is registered in
the `translations` table (`backend/database.py:388`). But `data/bible.db` has
**0 ASV verses**: only BSB, KJV, and WEB are loaded. The text still needs to
be imported.

**Confidence:** High.

---

### 4. YLT (Young's Literal Translation)

**Sources checked**
- eBible.org: <https://ebible.org/find/details.php?id=engylt> ("public domain … Translation by: Robert Young"; full OT+NT; USFM, USFX, VPL, SWORD)
- open-bibles README: `eng-ylt.zefania.xml` "Young's Literal Translation (**NT only**)", Public Domain

**License:** public domain. It was first published in 1862 and revised in
1887 and 1898. Robert Young died in 1888. No attribution is required.

**Best source:** eBible.org `engylt_usfm.zip` or `engylt_vpl.zip`.
**⚠️ Don't use the open-bibles copy:** it is NT only.

**Confidence:** High.

---

### 5. LSV (Literal Standard Version)

**Sources checked**
- eBible.org: <https://ebible.org/find/details.php?id=englsv> and <https://ebible.org/englsv/copyright.htm>
- Publisher: <https://www.lsvbible.com/> (footer: "© 2020– The LSV Bible, a CC BY-SA translation by Covenant Press, official publisher of the CCC", linking to creativecommons.org/licenses/by-sa/4.0/)

**License:** CC BY-SA 4.0, © 2020 Covenant Press (Covenant Christian
Coalition). The license text on eBible says: "You have permission to share
and redistribute this Bible translation in any format and to make reasonable
revisions and adaptations … provided that:
- You include the above copyright and source information.
- If you make any changes to the text, you must indicate that you did so …
- If you redistribute this text, you must distribute your contributions
  under the same license as the original."

**Attribution (suggested):** *"Literal Standard Version (LSV) © 2020 Covenant
Press. Licensed under CC BY-SA 4.0. lsvbible.com"*. Show it wherever LSV text
is displayed, the same way we handle BSB.

**Constraints:**
- Share-alike applies to the LSV text and to any edits we make to it, but
  not to our MIT code.
- There are no NC or ND restrictions.

**Best source:** eBible.org `englsv_usfm.zip` or `englsv_vpl.zip`. **Note:**
the eBible page spells the publisher "Covanet Press", which is a typo on
their page. Use "Covenant Press".

**Confidence:** High.

---

### 6. Vincent's Word Studies in the New Testament

**Sources checked**
- Internet Archive scans:
  - <https://archive.org/details/wordstudiesinnew0001vinc_j2z6>
  - <https://archive.org/details/cu31924092322522> (Cornell)
  - <https://archive.org/details/wordstudiesinnew0003marv>
- CrossWire: `ModInfo.jsp?modName=Vincent` returns "No module found". There
  is no SWORD module. The commentary list has RWP (Robertson) but no
  Vincent.
- CCEL: there is an author page (<https://ccel.org/ccel/vincent>), but no
  Word Studies text was found (the work URL returns 404).
- sacred-texts.com has `bib/cmt/vws/`, but it sits behind a Cloudflare
  challenge (403), so its terms could not be verified.
- e-Sword and theWord module sites list a Vincent module. Each module
  packager has its own terms, which were not verified.

**License:** public domain. It was published in 4 volumes between 1887 and
1900. Marvin R. Vincent died in 1922 (life+70 means PD since 1992), and the
work is pre-1929 in the US. No attribution is required.

**⚠️ Flag: source, not license.**
- No clean, open, verse-keyed digital edition was found.
- Options, in order of preference:
  1. Find a vetted transcription with a clear license, such as an e-Sword
     module whose packager states PD.
  2. Build one from Internet Archive OCR. That is high effort, and the Greek
     words in the OCR will need cleanup.
  3. Defer.
- Do **not** scrape BibleHub or StudyLight. That matches existing policy.

**Confidence:** High that the text is PD. Low on having a usable source.

---

### 7. Theographic Bible Metadata (viz.bible)

**Sources checked**
- Repo: <https://github.com/robertrouse/theographic-bible-metadata>. The
  `LICENSE` file is the full CC BY-SA 4.0 legal code. The GitHub API reports
  `CC-BY-SA-4.0`. The README says: "This work is free to use and copy under
  a Creative Commons Attribution Share-Alike 4.0 License." The repo was last
  pushed on 2026-04-21.
- Bibliography: <https://github.com/robertrouse/theographic-bible-metadata/blob/master/docs/data-source-bibliography.md>
- OpenBible.info geodata: <https://www.openbible.info/geo/> ("licensed under the Creative Commons Attribution license … as long as you credit OpenBible.info")

**License:** CC BY-SA 4.0.
- **Attribution (suggested):** *"Theographic Bible Metadata by Robert Rouse
  (viz.bible), CC BY-SA 4.0."*
- Place coordinates (the `openBibleLat`/`openBibleLong` fields) also need
  credit to OpenBible.info.

**Constraints:** share-alike applies to the metadata and to any tables we
derive from it. There are no NC or ND restrictions.

**Best source:** the `json/` folder (`people.json`, `places.json`,
`events.json`, `peopleGroups.json`, `books.json`, `chapters.json`,
`verses.json`, `easton.json`). These are Airtable exports with record-ID
links. The README calls JSON "the preferred source", and CSV and Neo4j
versions are also available. `verses.json` carries KJV text (PD), and
`easton.json` is Easton's Bible Dictionary from 1897 (PD, sourced from CCEL
XML).

**⚠️ Flags (provenance):**
1. The bibliography says the people data was built partly from **TIPNR,
   labelled at the time "CC BY-NC"**. STEPBible has since relicensed TIPNR
   as **CC BY**: the current file is
   `Proper Nouns/TIPNR - … - STEPBible.org CC BY.txt`. So the NC taint is
   most likely moot, but this is not airtight.
2. Place research cites the Holman Bible Atlas, the Rand McNally Bible
   Atlas, and others. Facts and coordinates are generally not copyrightable,
   and Theographic does not reproduce atlas text, so the risk is low.
3. Places carry `esvName` fields. These are just place names, so the risk is
   negligible.
4. Dating follows Floyd Nolen Jones's chronology, which is one interpretive
   view. That is a content note, not a license issue. Label the dates as
   "per Theographic / Jones chronology".

**Confidence:** High on the license itself. Medium on clean provenance.

---

## Recommended Next Steps

1. **Adopt now, low risk:** ASV (it's registered, just needs import), YLT,
   JFB, and TBESG.
2. **Adopt with BY-SA labelling:** LSV, TFLSJ, and Theographic. Mark each
   dataset's license in `LICENSES.md` and next to the content in the UI.
3. **Hold:** TBESH *definitions* until Online Bible grants permission. The
   glosses can go in now.
4. **Defer:** Vincent's Word Studies, until a clean verse-keyed source turns
   up.

---

*Last updated: 2026-10-02*
*Research conducted by Claude for the Bible MVP project*
