"""
Registry of commentary sources: metadata for the `commentary_sources` table plus the
loader configuration used by scripts/import_commentary.py.

`source` must equal commentary_entries.source; the study view's slugs and deep links
(?study=john-gill) are derived from it, so don't rename a source.

The library is these five sources, chosen by the site owner for doctrinal fit. Eight others
(Matthew Henry, Keil & Delitzsch, Albert Barnes, John Calvin, John Wesley, Adam Clarke,
People's New Testament, Catena Aurea) were removed on 2026-11-13 at the owner's decision;
don't re-add them. A build drops rows of any source not listed here
(scripts/migrate_commentary_search.py, prune_sources).

License reasoning for every entry is in docs/COMMENTARY_LIBRARY_2026-11.md; keep the two
in sync when adding a source.
"""

CW_RAWZIP = "https://www.crosswire.org/ftpmirror/pub/sword/packages/rawzip/{module}.zip"
HELLOAO = "https://bible.helloao.org/api/c/{id}"

PD = "Public domain"

COMMENTARIES = {
    "john-gill": {
        "source": "John Gill",
        "short_name": "Gill",
        "author": "John Gill (1697-1771)",
        "year": 1746,
        "tradition": "Baptist (Particular Baptist)",
        "kind": "verse",
        "coverage": "66 books",
        "license": PD,
        "attribution": "John Gill, Exposition of the Old and New Testaments (1746-1763). "
                       "Text from the HelloAO Free Use Bible API.",
        "source_url": "https://bible.helloao.org/api/c/john-gill/books.json",
        "description": "A London Baptist pastor's verse-by-verse exposition, notable for its use of "
                       "Jewish rabbinic sources and its strongly Calvinist theology.",
        "loader": "helloao",
        "helloao_id": "john-gill",
    },
    "jamieson-fausset-brown": {
        "source": "Jamieson-Fausset-Brown",
        "short_name": "JFB",
        "author": "Robert Jamieson, A. R. Fausset, David Brown",
        "year": 1871,
        "tradition": "Presbyterian/Anglican",
        "kind": "verse",
        "coverage": "66 books",
        "license": PD,
        "attribution": "Jamieson, Fausset and Brown, Commentary Critical and Explanatory on the "
                       "Whole Bible (1871). Text from the HelloAO Free Use Bible API (matches the "
                       "CCEL edition).",
        "source_url": "https://bible.helloao.org/api/c/jamieson-fausset-brown/books.json",
        "description": "A compact, phrase-by-phrase commentary by two Scottish Presbyterian "
                       "ministers and an Anglican scholar; brief notes on wording, history and "
                       "meaning.",
        "loader": "helloao",
        "helloao_id": "jamieson-fausset-brown",
    },
    "scofield": {
        "source": "Scofield Notes (1917)",
        "short_name": "Scofield",
        "author": "C. I. Scofield (1843-1921)",
        "year": 1917,
        "tradition": "Dispensational",
        "kind": "notes",
        "coverage": "65 books",
        "license": PD,
        "attribution": "C. I. Scofield, Scofield Reference Bible notes, 1917 edition. CrossWire "
                       "Scofield module, from the Wikisource transcription.",
        "source_url": "https://www.crosswire.org/sword/modules/ModInfo.jsp?modName=Scofield",
        "description": "The study notes of the 1917 Scofield Reference Bible, which spread "
                       "dispensational premillennial teaching; notes are occasional, not on "
                       "every verse.",
        "loader": "sword",
        "module": "Scofield",
    },
    "treasury-of-david": {
        "source": "Treasury of David",
        "short_name": "Spurgeon",
        "author": "C. H. Spurgeon (1834-1892)",
        "year": 1869,
        "tradition": "Baptist",
        "kind": "verse",
        "coverage": "Psalms",
        "license": PD,
        "attribution": "C. H. Spurgeon, The Treasury of David (1869-1885). CrossWire TDavid "
                       "module, from the Spurgeon Archive text. Spurgeon's own exposition only.",
        "source_url": "https://www.crosswire.org/sword/modules/ModInfo.jsp?modName=TDavid",
        "description": "The London Baptist preacher's devotional exposition of the Psalms. Only "
                       "Spurgeon's own overview and verse exposition are included, not the "
                       "collected quotations or sermon hints.",
        "loader": "tdavid",
        "module": "TDavid",
    },
    "tyndale": {
        "source": "Tyndale Study Notes",
        "short_name": "Tyndale",
        "author": "Tyndale House Publishers",
        "year": 2022,
        "tradition": "Evangelical",
        "kind": "notes",
        "coverage": "66 books",
        "license": "CC BY-SA 4.0",
        # CC BY-SA 4.0 s.3(a)(1): creator, copyright notice, license, modification notice;
        # s.3(a)(2) allows the rest (license URI, full credit) one link away, e.g. the info
        # sheet showing `attribution`. Wording follows Tyndale's README ("Adapted from ...").
        "attribution_short": "Adapted from Tyndale Open Study Notes \u00a9 2022 Tyndale House "
                             "Publishers, CC BY-SA 4.0",
        "requires_attribution": 1,
        "attribution": "Adapted from Tyndale Open Study Notes. The original work by Tyndale House "
                       "Publishers is available for free at http://www.tyndaleopenresources.com. "
                       "Copyright (C) 2022 by Tyndale House Publishers, CC BY-SA 4.0. Changes: "
                       "converted from XML to plain text with reference links; wording unchanged.",
        "source_url": "https://tyndaleopenresources.com/",
        "description": "Modern evangelical study-Bible notes in clear contemporary English, on "
                       "verses and passages, covering background and meaning.",
        "loader": "tyndale",
        "url": "https://tyndaleopenresources.com/wp-content/themes/tyndale-openresources/files/"
               "tyndale_open-studynotes.zip",
    },
}

SOURCE_COLUMNS = ["source", "short_name", "author", "year", "tradition", "kind", "coverage",
                  "license", "attribution", "source_url", "sort_order", "description",
                  "attribution_short", "size_bytes", "requires_attribution"]

# Display order, set by the site owner (2026-11-13). The study view opens on the first
# source in this order that has something on the selection, so sparse Scofield first is
# fine. Keep frontend/static/js/modules/study.js DEFAULT_ORDER (slugs) in step.
DEFAULT_ORDER = ["scofield", "john-gill", "jamieson-fausset-brown", "tyndale",
                 "treasury-of-david"]
assert sorted(DEFAULT_ORDER) == sorted(COMMENTARIES)
for _i, _key in enumerate(DEFAULT_ORDER):
    _c = COMMENTARIES[_key]
    _c["sort_order"] = (_i + 1) * 10
    _c.setdefault("requires_attribution", 0)
    _c.setdefault("attribution_short", None)
