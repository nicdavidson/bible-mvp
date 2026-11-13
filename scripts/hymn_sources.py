"""Public-domain hymn sources whose Scripture basis is in their own structure.

Each parser yields dicts:
    source, source_ref, title, first_line, author, words_year, meter, tune, copyright,
    words_public_domain, refs [(book, chapter, v1, v2, as_written, kind)],
    text [lines]   -- the words, used only to compute quotations; stored only when
                      `store_text` is true for the source (see SOURCES)

Licenses (checked 2026-11-13; docs/HYMN_INDEX_2026-11.md has the quotes):
    pg-watts-psalms, pg-watts-hss  Project Gutenberg #13166, #13341 (Watts, 1818 printing):
        PG license: with the PG license and references stripped, "you are left with a
        text unrestricted by U.S. intellectual property law". Only the text is used.
    tcp-tate-brady  EEBO-TCP A27952 (Tate & Brady, New Version, 1696): CC0 1.0 in the file.
    ccel-scottish-psalter, ccel-olney  CCEL ThML (Scottish Psalter 1650 + Paraphrases 1781;
        Olney Hymns 1779). Works public domain (<DC.Rights>Public Domain</DC.Rights>), but
        CCEL's site terms ("may be used for personal, educational, or non-profit purposes")
        and its claim on markup are not an open license: only facts are taken (first
        line, the reference printed with each item, author, metre), never the text, and
        quotations are not computed from it. Set ENABLE_CCEL = False to leave them out.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ENABLE_CCEL = True

PG_WATTS_PSALMS = ("hymns/pg13166.txt", "https://www.gutenberg.org/cache/epub/13166/pg13166.txt")
PG_WATTS_HSS = ("hymns/pg13341.txt", "https://www.gutenberg.org/cache/epub/13341/pg13341.txt")
TCP_SHA = "82111954dd2cda853c235c71a885ae143bfa3cf4"
TCP_TATE_BRADY = (f"hymns/tcp-A27952-{TCP_SHA[:7]}.xml",
                  f"https://raw.githubusercontent.com/textcreationpartnership/A27952/{TCP_SHA}/"
                  "A27952.xml")
CCEL_SCOTTISH = ("hymns/ccel-scotpsalter.xml", "https://www.ccel.org/ccel/anonymous/scotpsalter.xml")
CCEL_OLNEY = ("hymns/ccel-olneyhymns.xml", "https://www.ccel.org/ccel/newton/olneyhymns.xml")

SOURCES = [
    # (source, name, license, attribution, url, note)
    ("pg-watts-psalms", "Isaac Watts, The Psalms of David Imitated (1719), 1818 printing, "
     "Project Gutenberg #13166", "Public domain", "", "https://www.gutenberg.org/ebooks/13166",
     "Each psalm or part is headed by its psalm and verses ('Psalm 90:2. 1-5.')"),
    ("pg-watts-hss", "Isaac Watts, Hymns and Spiritual Songs (1707), 1818 printing, "
     "Project Gutenberg #13341", "Public domain", "", "https://www.gutenberg.org/ebooks/13341",
     "Book I is 'collected from the Holy Scriptures': a text under each hymn title"),
    ("tcp-tate-brady", "Tate and Brady, A New Version of the Psalms of David (1696), "
     "EEBO-TCP A27952", "CC0 1.0 (TCP encoding); text public domain",
     "Text Creation Partnership", "https://github.com/textcreationpartnership/A27952",
     "One metrical version per psalm (psalm-level links)"),
    ("ccel-scottish-psalter", "The Scottish Psalter (1650) and Paraphrases (1781), CCEL edition",
     "Works public domain (file: 'Public Domain'); CCEL site terms: personal, educational or "
     "non-profit use. Facts only: first lines and printed references, no text",
     "Christian Classics Ethereal Library", "https://www.ccel.org/ccel/anonymous/scotpsalter",
     "Psalm or passage for every item"),
    ("ccel-olney", "Newton and Cowper, Olney Hymns (1779), CCEL edition",
     "Works public domain (file: 'Public Domain'); CCEL site terms: personal, educational or "
     "non-profit use. Facts only: first lines and printed references, no text",
     "Christian Classics Ethereal Library", "https://www.ccel.org/ccel/newton/olneyhymns",
     "Book I hymns are headed by the text they are on"),
]

ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
METRE = {"C. M.": "8 6 8 6", "L. M.": "8 8 8 8", "S. M.": "6 6 8 6"}


def roman(s: str) -> int:
    total = 0
    for a, b in zip(s, s[1:] + " "):
        v = ROMAN[a]
        total += -v if b in ROMAN and ROMAN[b] > v else v
    return total


def _pg_body(path) -> list[str]:
    lines = Path(path).read_text(encoding="utf-8", errors="replace").replace("\r", "").split("\n")
    start = next(i for i, x in enumerate(lines) if x.startswith("*** START OF"))
    end = next(i for i, x in enumerate(lines) if x.startswith("*** END OF"))
    return lines[start + 1:end]


def _stanza_lines(lines) -> list[str]:
    """Hymn text lines after the heading: '1 Thro' every age...' -> without the number."""
    out = []
    for x in lines:
        x = x.replace("[", "").replace("]", "").strip()   # brackets mark optional stanzas
        if not x:
            continue
        out.append(re.sub(r"^\d+\s*", "", x))
    return out


def _verse_ranges(tokens: str, max_verse: int):
    """'1-5' / '8 11 9 10 12' / '13 &c.' -> merged [(v1, v2)] within the chapter."""
    vs = set()
    for a, b, etc in re.findall(r"(\d+)(?:-(\d+))?(?![a-z\d])(\s*&c)?", tokens):
        lo = int(a)
        hi = max_verse if etc else int(b or a)
        vs.update(range(lo, min(hi, max_verse) + 1))
    out = []
    for v in sorted(vs):
        if out and v == out[-1][1] + 1:
            out[-1][1] = v
        else:
            out.append([v, v])
    return [tuple(r) for r in out]


def watts_psalms(path, max_verse):
    body = _pg_body(path)
    heads = [i for i, x in enumerate(body) if re.match(r"^Psalm \d+:\d+\.", x)]
    for k, i in enumerate(heads):
        end = heads[k + 1] if k + 1 < len(heads) else len(body)
        head = body[i].strip()
        m = re.match(r"^Psalm (\d+):(\d+)\.\s*(.*)$", head)
        ps, part, rest = int(m.group(1)), int(m.group(2)), m.group(3)
        rest_clean = re.sub(r"As the \d+\w* Psalm\.?", "", rest)      # metre/tune note
        rest_clean = re.sub(rf"\bPsalm {ps}\.", "", rest_clean)
        verses = re.match(r"^\s*((?:\d+(?:-\d+)?(?![a-z\d])(?:\s*&c\.?)?[\s.,]*)+)", rest_clean)
        mv = max_verse.get(("Psalms", ps), 999)
        text_start = i + 1
        while text_start < end and not re.match(r"^\s*\[?1\s", body[text_start]):
            text_start += 1
        text = _stanza_lines(body[text_start:end])
        if not text:
            continue
        refs = [("Psalms", ps, a, b, head, "paraphrase")
                for a, b in (_verse_ranges(verses.group(1), mv) if verses else [])]
        if not refs:
            refs = [("Psalms", ps, None, None, head, "paraphrase")]
        meter = next((v for k2, v in METRE.items() if k2 in rest), None)
        yield {"source": "pg-watts-psalms", "source_ref": f"Psalm {ps}:{part}",
               "title": f"Psalm {ps}" + (f", part {part}" if part > 1 or "Part" in rest else ""),
               "first_line": text[0].rstrip(",;:"), "author": "Watts, Isaac (1674-1748)",
               "words_year": 1719, "meter": meter, "tune": None, "words_public_domain": True,
               "copyright": "Public domain", "refs": refs, "text": text}


HSS_REF = re.compile(r"((?:[123] )?[A-Z][a-z]+)\.? (\d+)[.,] ((?:(?:\d+(?:-\d+)?|&c\.?)\s*)+)")


def watts_hss(path, max_verse, resolve_book):
    body = _pg_body(path)
    heads = [i for i, x in enumerate(body) if re.match(r"^Hymn \d+:\d+\.", x)]
    for k, i in enumerate(heads):
        end = heads[k + 1] if k + 1 < len(heads) else len(body)
        m = re.match(r"^Hymn (\d+):(\d+)\.", body[i])
        book_no, num = int(m.group(1)), int(m.group(2))
        j = i + 1
        title_lines = []
        while j < end and body[j].strip():   # the title block ends at a blank line
            title_lines.append(body[j].strip())
            j += 1
        title = " ".join(title_lines)
        text = _stanza_lines(body[j:end])
        if not text:
            continue
        refs = []
        for bk, ch, vs in HSS_REF.findall(title):
            book = resolve_book(bk)
            ch = int(ch)
            mv = max_verse.get((book, ch)) if book else None
            if not mv:
                continue  # unknown book or chapter ('Col. 9. 16' is a misprint for 1:16)
            for a, b in _verse_ranges(vs, mv):
                refs.append((book, ch, a, b, f"{bk}. {ch}. {vs.strip()}", "based_on"))
        yield {"source": "pg-watts-hss", "source_ref": f"Hymn {book_no}:{num}",
               "title": re.sub(r"[,.]?\s*((?:[123] )?[A-Z][a-z]+\.? \d+[.,] .*)$", "",
                               title).strip(" ,.") or f"Hymn {book_no}:{num}",
               "first_line": text[0].rstrip(",;:"), "author": "Watts, Isaac (1674-1748)",
               "words_year": 1707, "meter": None, "tune": None, "words_public_domain": True,
               "copyright": "Public domain", "refs": refs, "text": text}


TEI = "{http://www.tei-c.org/ns/1.0}"


def _tcp_line(el) -> str:
    s = "".join(el.itertext()) if el is not None else ""
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^[\d,\s]+\.\s*", "", s)                 # stanza numbers '1. ', '1, 2. '
    first, _, rest = s.partition(" ")                        # drop capitals 'SInce', 'AT'
    if len(first) > 1 and first[:2].isupper():
        first = first[0] + first[1:].lower()
    return f"{first} {rest}".strip()


def tate_brady(path):
    root = ET.parse(path).getroot()
    ns = TEI if root.tag.startswith(TEI) else ""
    for div in root.iter(f"{ns}div"):
        if div.get("type") != "Psalm":
            continue
        ps = int(div.get("n")) if (div.get("n") or "").isdigit() else None
        head = div.find(f"{ns}head")
        if ps is None and head is not None:
            m = re.search(r"PSALM ([IVXLC]+)", "".join(head.itertext()))
            ps = roman(m.group(1)) if m else None
        if not ps:
            continue
        parts = [p for p in div.findall(f"{ns}div") if p.get("type") == "part"] or [div]
        for n, part in enumerate(parts, 1):
            lines = [_tcp_line(l) for l in part.iter(f"{ns}l")]
            lines = [x for x in lines if x]
            if not lines:
                continue
            yield {"source": "tcp-tate-brady", "source_ref": f"Psalm {ps}" +
                   (f" part {n}" if len(parts) > 1 else ""),
                   "title": f"Psalm {ps}" + (f", part {n}" if len(parts) > 1 else ""),
                   "first_line": lines[0].rstrip(",;:"),
                   "author": "Tate, Nahum (1652-1715); Brady, Nicholas (1659-1726)",
                   "words_year": 1696, "meter": None, "tune": None, "words_public_domain": True,
                   "copyright": "Public domain (1696); TCP encoding CC0 1.0",
                   "refs": [("Psalms", ps, None, None, f"PSALM {ps}", "paraphrase")],
                   "text": lines}


def _osis_refs(osis: str, book_of_osis, max_verse):
    """'Bible:Ps.23' / 'Bible:Gen.28.20-Gen.28.22' / 'Bible:1Chr.17.16-1Chr.17.17'."""
    out = []
    for piece in (osis or "").split():
        piece = piece.replace("Bible:", "")
        a, _, b = piece.partition("-")
        pa, pb = a.split("."), (b.split(".") if b else a.split("."))
        book = book_of_osis(pa[0])
        if not book or len(pa) < 2:
            continue
        ch = int(pa[1])
        mv = max_verse.get((book, ch))
        if not mv or (len(pa) > 2 and int(pa[2]) > mv):
            continue  # a misprint in the source (Olney 'Isa 33:27,28': Isaiah 33 has 24)
        if len(pa) == 2:
            out.append((book, ch, None, None))
        elif int(pb[1]) == ch:
            out.append((book, ch, int(pa[2]), int(pb[2]) if len(pb) > 2 else int(pa[2])))
        else:  # across chapters
            out.append((book, ch, int(pa[2]), max_verse.get((book, ch), 999)))
            out.append((book, int(pb[1]), 1, int(pb[2]) if len(pb) > 2 else 999))
    return out


def scottish_psalter(path, book_of_osis, max_verse):
    root = ET.parse(path).getroot()
    for h in root.iter("hymn"):
        n = h.get("n") or ""
        first = (h.get("firstline") or "").replace("’", "'")
        sc = h.find("scripCom")
        if not first or sc is None or n[:1] not in "PR":
            continue
        refs = [(*r, sc.get("passage") or "", "paraphrase")
                for r in _osis_refs(sc.get("osisRef"), book_of_osis, max_verse)]
        meter = h.find("meter")
        yield {"source": "ccel-scottish-psalter", "source_ref": n,
               "title": (h.get("title") or "").split(":")[0] if n.startswith("P") else
               f"Paraphrase {n[1:]}", "first_line": first.rstrip(",;:"),
               "author": "Scottish Psalter (1650)" if n.startswith("P")
               else "Scottish Paraphrases (1781)",
               "words_year": 1650 if n.startswith("P") else 1781,
               "meter": meter.text.strip() if meter is not None and meter.text else None,
               "tune": None, "words_public_domain": True, "copyright": "Public domain",
               "refs": refs, "text": None}


def olney(path, book_of_osis, max_verse):
    root = ET.parse(path).getroot()
    for div in root.iter("div3"):
        if div.get("type") != "Hymn":
            continue
        hymn = div.find("hymn")
        if hymn is None:
            continue
        refs, first = [], None
        for el in hymn:
            if el.tag == "verse":
                ln = el.find("l")
                first = re.sub(r"\s+", " ", "".join(ln.itertext())).strip() if ln is not None else None
                break
            # the text the hymn is on: after the argument or inside it (not the
            # references inside the verses)
            for ref in ([el] if el.tag in ("scripRef", "scripCom") else el.iter("scripRef")):
                refs += [(*r, ref.get("passage") or "", "based_on")
                         for r in _osis_refs(ref.get("osisRef"), book_of_osis, max_verse)]
        if not first:
            continue
        book_no = (div.get("id") or "Book1").split(".")[0].replace("Book", "")
        author = hymn.find("author")
        meter = hymn.find("meter")
        yield {"source": "ccel-olney", "source_ref": f"Book {book_no}, Hymn {div.get('n')}",
               "title": f"Olney Hymns {book_no}.{div.get('n')}",
               "first_line": first.replace("’", "'").rstrip(",;:"),
               "author": author.text.strip() if author is not None and author.text else None,
               "words_year": 1779,
               "meter": meter.text.replace(",", " ").strip() if meter is not None and meter.text
               else None,
               "tune": None, "words_public_domain": True, "copyright": "Public domain",
               "refs": refs, "text": None}


OSIS_BOOKS = {
    "Gen": "Genesis", "Exod": "Exodus", "Lev": "Leviticus", "Num": "Numbers",
    "Deut": "Deuteronomy", "Josh": "Joshua", "Judg": "Judges", "Ruth": "Ruth",
    "1Sam": "1 Samuel", "2Sam": "2 Samuel", "1Kgs": "1 Kings", "2Kgs": "2 Kings",
    "1Chr": "1 Chronicles", "2Chr": "2 Chronicles", "Ezra": "Ezra", "Neh": "Nehemiah",
    "Esth": "Esther", "Job": "Job", "Ps": "Psalms", "Prov": "Proverbs", "Eccl": "Ecclesiastes",
    "Song": "Song of Solomon", "Isa": "Isaiah", "Jer": "Jeremiah", "Lam": "Lamentations",
    "Ezek": "Ezekiel", "Dan": "Daniel", "Hos": "Hosea", "Joel": "Joel", "Amos": "Amos",
    "Obad": "Obadiah", "Jonah": "Jonah", "Mic": "Micah", "Nah": "Nahum", "Hab": "Habakkuk",
    "Zeph": "Zephaniah", "Hag": "Haggai", "Zech": "Zechariah", "Mal": "Malachi",
    "Matt": "Matthew", "Mark": "Mark", "Luke": "Luke", "John": "John", "Acts": "Acts",
    "Rom": "Romans", "1Cor": "1 Corinthians", "2Cor": "2 Corinthians", "Gal": "Galatians",
    "Eph": "Ephesians", "Phil": "Philippians", "Col": "Colossians",
    "1Thess": "1 Thessalonians", "2Thess": "2 Thessalonians", "1Tim": "1 Timothy",
    "2Tim": "2 Timothy", "Titus": "Titus", "Phlm": "Philemon", "Heb": "Hebrews",
    "Jas": "James", "1Pet": "1 Peter", "2Pet": "2 Peter", "1John": "1 John", "2John": "2 John",
    "3John": "3 John", "Jude": "Jude", "Rev": "Revelation",
}
