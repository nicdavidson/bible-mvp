"""
Registry of commentary sources: metadata for the `commentary_sources` table plus the
loader configuration used by scripts/import_commentary.py.

`source` must equal commentary_entries.source. Existing names ("Matthew Henry",
"John Gill") are kept so saved user state keeps working.

License reasoning for every entry is in docs/COMMENTARY_LIBRARY_2026-11.md; keep the two
in sync when adding a source.
"""

CW_RAWZIP = "https://www.crosswire.org/ftpmirror/pub/sword/packages/rawzip/{module}.zip"
HELLOAO = "https://bible.helloao.org/api/c/{id}"

PD = "Public domain"

COMMENTARIES = {
    "matthew-henry": {
        "source": "Matthew Henry",
        "short_name": "Henry",
        "author": "Matthew Henry (1662-1714)",
        "year": 1708,
        "tradition": "Presbyterian (English Nonconformist)",
        "kind": "passage",
        "coverage": "66 books",
        "license": PD,
        "attribution": "Matthew Henry, An Exposition of the Old and New Testaments (1708-1710). "
                       "Text from the HelloAO Free Use Bible API; Song of Solomon from the "
                       "CrossWire MHC module (prepared from CCEL).",
        "source_url": "https://bible.helloao.org/api/c/matthew-henry/books.json",
        "sort_order": 10,
        "description": "The complete devotional commentary by the English Nonconformist minister, "
                       "written passage by passage with practical application; Romans to "
                       "Revelation were finished from his notes by other ministers after his death.",
        "loader": "helloao",
        "helloao_id": "matthew-henry",
        "infer_ranges": True,
        "supplement": {"module": "MHC", "books": ["Song of Solomon"]},
    },
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
        "sort_order": 20,
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
        "sort_order": 30,
        "description": "A compact, phrase-by-phrase commentary by two Scottish Presbyterian "
                       "ministers and an Anglican scholar; brief notes on wording, history and "
                       "meaning.",
        "loader": "helloao",
        "helloao_id": "jamieson-fausset-brown",
    },
    "keil-delitzsch": {
        "source": "Keil & Delitzsch",
        "short_name": "K&D",
        "author": "C. F. Keil (1807-1888), Franz Delitzsch (1813-1890)",
        "year": 1861,
        "tradition": "Lutheran",
        "kind": "passage",
        "coverage": "OT only",
        "license": PD,
        "attribution": "Keil and Delitzsch, Biblical Commentary on the Old Testament "
                       "(English translation, T. & T. Clark, 1864-1878). Text from the HelloAO "
                       "Free Use Bible API; Song of Solomon from the CrossWire KD module "
                       "(Wikisource transcription).",
        "source_url": "https://bible.helloao.org/api/c/keil-delitzsch/books.json",
        "sort_order": 40,
        "description": "A detailed scholarly commentary on the Hebrew text of the Old Testament "
                       "by two German Lutheran professors; strong on language, history and "
                       "structure, usually by section rather than single verse.",
        "loader": "helloao",
        "helloao_id": "keil-delitzsch",
        "infer_ranges": True,
        # HelloAO lists Song of Solomon with 0 chapters; CrossWire KD's Song block is intact
        "supplement": {"module": "KD", "books": ["Song of Solomon"], "strip_book_intros": True},
    },
    "john-calvin": {
        "source": "John Calvin",
        "short_name": "Calvin",
        "author": "John Calvin (1509-1564)",
        "year": 1540,
        "tradition": "Reformed",
        "kind": "passage",
        "coverage": "48 books",
        "license": PD,
        "attribution": "John Calvin, Commentaries (Latin/French 1540-1565; English translation, "
                       "Calvin Translation Society, 1843-1855). Text from the HelloAO Free Use "
                       "Bible API (CCEL edition); inline verse text and translator footnotes removed.",
        "source_url": "https://bible.helloao.org/api/c/john-calvin/books.json",
        "sort_order": 50,
        "description": "The Geneva Reformer's own commentaries, explaining the plain sense of the "
                       "text with doctrinal and pastoral application. Calvin wrote none on Judges "
                       "to Song of Solomon (except Psalms), 2-3 John or Revelation.",
        "loader": "helloao",
        "helloao_id": "john-calvin",
        "clean": "calvin",
        "infer_ranges": True,
    },
    "adam-clarke": {
        "source": "Adam Clarke",
        "short_name": "Clarke",
        "author": "Adam Clarke (1762-1832)",
        "year": 1810,
        "tradition": "Methodist",
        "kind": "verse",
        "coverage": "66 books",
        "license": PD,
        "attribution": "Adam Clarke, The Holy Bible ... with a Commentary and Critical Notes "
                       "(1810-1826). CrossWire Clarke module, from the Wikisource transcription.",
        "source_url": "https://www.crosswire.org/sword/modules/ModInfo.jsp?modName=Clarke",
        "sort_order": 60,
        "description": "A Methodist scholar's verse-by-verse commentary, written over forty years, "
                       "with much on languages, customs and natural history alongside "
                       "Wesleyan theology.",
        "loader": "sword",
        "module": "Clarke",
        "strip_book_intros": True,
    },
    "albert-barnes": {
        "source": "Barnes' Notes",
        "short_name": "Barnes",
        "author": "Albert Barnes (1798-1870)",
        "year": 1832,
        "tradition": "Presbyterian",
        "kind": "verse",
        "coverage": "NT only",
        "license": PD,
        "attribution": "Albert Barnes, Notes, Explanatory and Practical, on the New Testament "
                       "(1832-1851). CrossWire Barnes module.",
        "source_url": "https://www.crosswire.org/sword/modules/ModInfo.jsp?modName=Barnes",
        "sort_order": 70,
        "description": "Notes by a Philadelphia Presbyterian pastor written for Sunday-school "
                       "teachers and families: clear, verse-by-verse explanation of words, "
                       "background and meaning.",
        "loader": "sword",
        "module": "Barnes",
        "strip_book_intros": True,
        "fixup": "barnes",
    },
    "john-wesley": {
        "source": "John Wesley",
        "short_name": "Wesley",
        "author": "John Wesley (1703-1791)",
        "year": 1755,
        "tradition": "Methodist",
        "kind": "verse",
        "coverage": "64 books",
        "license": PD,
        "attribution": "John Wesley, Explanatory Notes upon the New Testament (1755) and upon "
                       "the Old Testament (1765). CrossWire Wesley module (electronic edition by "
                       "Sulu Kelley and Bill Brown).",
        "source_url": "https://www.crosswire.org/sword/modules/ModInfo.jsp?modName=Wesley",
        "sort_order": 80,
        "description": "Short, plain notes by the founder of Methodism, written for ordinary "
                       "readers; often a sentence or two per verse.",
        "loader": "sword",
        "module": "Wesley",
        "fixup": "wesley",
    },
    "peoples-nt": {
        "source": "People's New Testament",
        "short_name": "PNT",
        "author": "B. W. Johnson (1833-1894)",
        "year": 1889,
        "tradition": "Restoration Movement",
        "kind": "verse",
        "coverage": "NT only",
        "license": PD,
        "attribution": "B. W. Johnson, The People's New Testament with Explanatory Notes "
                       "(1889-1891). CrossWire PNT module.",
        "source_url": "https://www.crosswire.org/sword/modules/ModInfo.jsp?modName=PNT",
        "sort_order": 90,
        "description": "Brief popular notes on the New Testament by a teacher in the Disciples of "
                       "Christ (Stone-Campbell) movement.",
        "loader": "sword",
        "module": "PNT",
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
        "sort_order": 100,
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
        "sort_order": 110,
        "description": "The London Baptist preacher's devotional exposition of the Psalms. Only "
                       "Spurgeon's own overview and verse exposition are included, not the "
                       "collected quotations or sermon hints.",
        "loader": "tdavid",
        "module": "TDavid",
    },
    "catena-aurea": {
        "source": "Catena Aurea",
        "short_name": "Catena",
        "author": "Thomas Aquinas (compiler, c. 1225-1274)",
        "year": 1264,
        "tradition": "Church Fathers (Catholic)",
        "kind": "passage",
        "coverage": "Gospels",
        "license": PD,
        "attribution": "Thomas Aquinas, Catena Aurea, English translation edited by J. H. Newman "
                       "(Oxford, 1841-1845). CrossWire Catena module, from github.com/lemtom/catena "
                       "(CC0).",
        "source_url": "https://www.crosswire.org/sword/modules/ModInfo.jsp?modName=Catena",
        "sort_order": 120,
        "description": "A 'golden chain' of quotations from the Church Fathers (Augustine, "
                       "Chrysostom, Jerome and others) arranged passage by passage through the "
                       "four Gospels.",
        "loader": "sword",
        "module": "Catena",
        "infer_ranges": True,
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
        "attribution": "Adapted from Tyndale Open Study Notes. The original work by Tyndale House "
                       "Publishers is available for free at http://www.tyndaleopenresources.com. "
                       "Copyright (C) 2022 by Tyndale House Publishers, CC BY-SA 4.0. Changes: "
                       "converted from XML to plain text with reference links; wording unchanged.",
        "source_url": "https://tyndaleopenresources.com/",
        "sort_order": 130,
        "description": "Modern evangelical study-Bible notes in clear contemporary English, on "
                       "verses and passages, covering background and meaning.",
        "loader": "tyndale",
        "url": "https://tyndaleopenresources.com/wp-content/themes/tyndale-openresources/files/"
               "tyndale_open-studynotes.zip",
    },
}

SOURCE_COLUMNS = ["source", "short_name", "author", "year", "tradition", "kind", "coverage",
                  "license", "attribution", "source_url", "sort_order", "description"]
