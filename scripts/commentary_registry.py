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

# ---------------------------------------------------------------------------
# Dispensational sources, first wave (2026-11-13): public domain because first published
# before 1931. SermonIndex modules are rebuilt by the importer from
# https://sermonindex.net/modules/sword/<module>.zip; their conversion damage is repaired
# at import (scripts/commentary_repair.py). Evidence per text: docs/COMMENTARY_LIBRARY_2026-11.md.
# ---------------------------------------------------------------------------

PD_PRE1931 = "Public domain (US: first published before 1931)"

# H. A. Ironside: SermonIndex's siiron module mixes volumes of every date (its Isaiah prints
# "Copyright @ 1952") and later edited versions. Only books whose module text was matched
# against an archive.org scan of a pre-1931 edition are imported (docs, "Ironside"):
IRONSIDE_PRE1931 = [
    "Nehemiah",          # Notes on Nehemiah, 2nd ed. 1925 (first 1918/19)
    "Esther",            # Notes on Esther, 1905; module = 1921 revised edition
    "Jeremiah",          # Notes on Jeremiah and Lamentations, 1906; module = 1928 new edition
    "Lamentations",
    "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
    "Zephaniah", "Haggai", "Zechariah", "Malachi",   # Notes on the Minor Prophets, 1909/1928
    "Romans",            # Lectures on Romans, 1928
    "Colossians",        # Lectures on Colossians, January 1929
]
# Not imported, though first published before 1931: Proverbs, Revelation and Philippians
# (the module has later edited wording), Daniel (the module is the 1996 edited text, and
# Daniel 9 includes The Great Parenthesis, 1943).

COMMENTARIES.update({
    "ironside": {
        "source": "Ironside Expositions",
        "short_name": "Ironside",
        "author": "H. A. Ironside (1876-1951)",
        "year": 1905,
        "tradition": "Dispensational",
        "kind": "passage",
        "coverage": "Nehemiah, Esther, Jeremiah, Lamentations, Minor Prophets, Romans, "
                    "Colossians",
        "license": PD_PRE1931,
        "attribution": "H. A. Ironside, Notes and Lectures (Loizeaux, 1905-1929). Text from "
                       "the SermonIndex SWORD module siiron, books matched to the pre-1931 "
                       "editions only.",
        "source_url": "https://www.sermonindex.net/commentary/iron/",
        "description": "Plain-spoken expository lectures by the Bible teacher who later "
                       "pastored Moody Church in Chicago; strongly dispensational, with much "
                       "on prophecy and Israel's future.",
        "loader": "sermonindex",
        "module": "siiron",
        "books": IRONSIDE_PRE1931,
        # archive.org scans of those editions (Nehemiah 1925, Esther 1921, Jeremiah 1928,
        # Minor Prophets 1928 printing, Romans 1928, Colossians 1929)
        "caps_from_scans": ["notesonbookofneh0000iron", "notesonbookofest0000unse",
                            "notesonprophecyl0000hair", "bwb_T5-CWQ-371",
                            "lecturesonepistl0000hair_u7v0", "bwb_S0-BLY-002"],
        # SermonIndex appended later works to three chapters; those parts are left out:
        # Hosea 3:4- and Jeremiah 30 (from about its middle) are "Not Wrath But Rapture",
        # Romans 11:25- is The Great Parenthesis (1943), chapter VIII.
        "drop_sections": [("Hosea", 3, 4), ("Romans", 11, 25)],
        "patches": [("Jeremiah", 30, 1, "NOT WRATH BUT RAPTURE", None)],
    },
    "gaebelein": {
        "source": "Gaebelein Annotated Bible",
        "short_name": "Gaebelein",
        "author": "Arno C. Gaebelein (1861-1945)",
        "year": 1913,
        "tradition": "Dispensational",
        "kind": "passage",
        "coverage": "66 books",
        "license": PD_PRE1931,
        "attribution": "A. C. Gaebelein, The Annotated Bible (Our Hope, 1913-1922). Text from "
                       "the SermonIndex SWORD module siannbible, repaired against archive.org "
                       "scans.",
        "source_url": "https://www.sermonindex.net/commentary/annotated-bible/",
        "description": "A dispensational survey of every book of the Bible by the editor of "
                       "Our Hope: an outline of each section followed by annotations on its "
                       "meaning, with much attention to prophecy and to Israel's future.",
        "loader": "sermonindex",
        "module": "siannbible",
        # The Annotated Bible, 9 vols (Wellesley College scans), and for Matthew the
        # module's actual text, The Gospel of Matthew: An Exposition (1903; 1910 edition)
        "caps_from_scans": [f"annotatedbibleho0{n}gaeb" for n in range(1, 10)]
        + ["gospelofmatthewe01gaeb", "gospelofmatthewe02gaeb"],
    },
    "darby": {
        "source": "Darby Synopsis",
        "short_name": "Darby",
        "author": "J. N. Darby (1800-1882)",
        "year": 1857,
        "tradition": "Plymouth Brethren",
        "kind": "chapter",
        "coverage": "New Testament",
        "license": PD_PRE1931,
        "attribution": "J. N. Darby, Synopsis of the Books of the Bible (1857-1867). Text from "
                       "the SermonIndex SWORD module sidarbysyn.",
        "source_url": "https://www.sermonindex.net/commentary/darby-s-n-t-synopsis/",
        "description": "A chapter-by-chapter survey by the leading early Brethren teacher, "
                       "who first systematised dispensationalism. It also reflects the "
                       "Plymouth Brethren view of church order (no ordained clergy).",
        "loader": "sermonindex",
        "module": "sidarbysyn",
    },
    "brooks": {
        "source": "Brooks Summarized Bible",
        "short_name": "Brooks",
        "author": "Keith L. Brooks (1888-1954)",
        "year": 1919,
        "tradition": "Dispensational",
        "kind": "chapter",
        "coverage": "66 books",
        "license": PD_PRE1931,
        "attribution": "Keith L. Brooks, The Summarized Bible (Bible Institute of Los Angeles, "
                       "1919). Text from the SermonIndex SWORD module sitsb.",
        "source_url": "https://www.sermonindex.net/commentary/summarized-bible/",
        "description": "A short digest of every chapter: contents, characters, a one-sentence "
                       "conclusion, key word, strong verses and striking facts.",
        "loader": "sermonindex",
        "module": "sitsb",
        # the module's James 5 entry has a second copy of 1 Peter 1 appended to it
        "patches": [("James", 5, 1, "\n\n**1 Peter 1:1-25", None)],
    },
    "mackintosh": {
        "source": "Mackintosh Notes on the Pentateuch",
        "short_name": "Mackintosh",
        "author": "C. H. Mackintosh (1820-1896)",
        "year": 1858,
        "tradition": "Plymouth Brethren",
        "kind": "passage",
        "coverage": "Genesis-Deuteronomy",
        "license": PD_PRE1931,
        "attribution": "C. H. Mackintosh, Notes on the Pentateuch (1858-1880). Text from "
                       "Project Gutenberg ebooks 37915, 40596, 40610, 76552, 41571 and 41584.",
        "source_url": "https://www.gutenberg.org/ebooks/author/41226",
        "description": "Devotional essays on the five books of Moses, reading their history and "
                       "ritual as types of Christ. Mackintosh was a Plymouth Brethren writer, "
                       "and his view of church order shows in places.",
        "loader": "gutenberg_mackintosh",
        "volumes": [("Genesis", [37915]), ("Exodus", [40596]), ("Leviticus", [40610]),
                    ("Numbers", [76552]), ("Deuteronomy", [41571, 41584])],
    },
    "larkin": {
        "source": "Larkin on Revelation",
        "short_name": "Larkin",
        "author": "Clarence Larkin (1850-1924)",
        "year": 1919,
        "tradition": "Dispensational Baptist",
        "kind": "passage",
        "coverage": "Revelation",
        "license": PD_PRE1931,
        "attribution": "Clarence Larkin, The Book of Revelation (1919). Text from the "
                       "SermonIndex SWORD module silarkinrev, repaired against the archive.org "
                       "scan bookofrevelation00lark; the charts are not included.",
        "source_url": "https://www.sermonindex.net/commentary/larkin-rev/",
        "description": "A dispensational, premillennial study of Revelation by the Baptist "
                       "pastor known for his prophecy charts. Larkin also taught the gap theory "
                       "and speculated about a pre-Adamite world.",
        "loader": "sermonindex",
        "module": "silarkinrev",
        "strip_lead_digit": True,
        "caps_from_scans": ["bookofrevelation00lark"],
        # Section headings whose deleted words the automatic repair could not place
        # (the scan prints them in small capitals next to a running head); each one read
        # off the scan by hand: (book, chapter, verse, module text, restored text)
        "patches": [
            ("Revelation", 7, 1, "THE BETWEEN THE SIXTH AND SEVENTH SEALS",
             "THE INTERVAL BETWEEN THE SIXTH AND SEVENTH SEALS"),
            ("Revelation", 8, 6, "THE SEVEN\n(", "THE SEVEN TRUMPETS\n("),
            ("Revelation", 10, 1, "THE BETWEEN THE SIXTH AND SEVENTH.",
             "THE INTERVAL BETWEEN THE SIXTH AND SEVENTH TRUMPETS."),
            ("Revelation", 11, 1, "2. THE TWO.", "2. THE TWO WITNESSES."),
            ("Revelation", 12, 7, "4. THE.", "4. THE ARCHANGEL."),
            ("Revelation", 14, 6, "2. THE THREE ANGEL.", "2. THE THREE ANGEL MESSENGERS."),
            ("Revelation", 14, 9, "THE DOOM OF 'S.", "THE DOOM OF ANTICHRIST'S FOLLOWERS."),
            ("Revelation", 15, 1, "OR VIAL.", "OR VIAL JUDGMENTS."),
            ("Revelation", 15, 5, "THE TABERNACLE OF.", "THE TABERNACLE OF TESTIMONY."),
            ("Revelation", 16, 13, "THE BETWEEN", "THE INTERVAL BETWEEN"),
            ("Revelation", 19, 11, "3. THE BATTLE OF.", "3. THE BATTLE OF ARMAGEDDON."),
            ("Revelation", 20, 4, "3. THE.", "3. THE MILLENNIUM."),
        ],
    },
})

SOURCE_COLUMNS = ["source", "short_name", "author", "year", "tradition", "kind", "coverage",
                  "license", "attribution", "source_url", "sort_order", "description",
                  "attribution_short", "size_bytes", "requires_attribution"]

# Display order, set by the site owner (2026-11-13). The study view opens on the first
# source in this order that has something on the selection, so sparse Scofield first is
# fine. Keep frontend/static/js/modules/study.js DEFAULT_ORDER (slugs) in step.
DEFAULT_ORDER = ["scofield", "john-gill", "jamieson-fausset-brown", "tyndale",
                 "gaebelein", "ironside", "darby", "brooks", "mackintosh", "larkin",
                 "treasury-of-david"]
assert sorted(DEFAULT_ORDER) == sorted(COMMENTARIES)
for _i, _key in enumerate(DEFAULT_ORDER):
    _c = COMMENTARIES[_key]
    _c["sort_order"] = (_i + 1) * 10
    _c.setdefault("requires_attribution", 0)
    _c.setdefault("attribution_short", None)
