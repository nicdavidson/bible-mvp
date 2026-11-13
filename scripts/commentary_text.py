"""
Shared text handling for commentary imports.

Every commentary row is stored the same way, matching the existing Henry/Gill rows:

    content          plain text, paragraphs separated by "\\n\\n", with Bible references
                     wrapped as <a href="#" class="commentary-ref" data-ref="Book C:V">..</a>.
                     No other markup. '<' and '>' from the source are escaped, so the only
                     tags that can reach the browser are the anchors generated here.
    searchable_text  the same text without anchors (and without '<' / '>'), for FTS5.

Sources arrive as ThML or OSIS fragments (CrossWire SWORD modules), Tyndale XML, or plain
text (HelloAO JSON). `markup_to_text` reduces any of them to plain text in which
references are kept as placeholders; `render` turns that into (content, searchable_text),
validating every link target against the KJV versification so no link points at a verse
that does not exist.
"""
from __future__ import annotations

import html
import re

from add_commentary_links import BOOK_ABBREVS as _LINKER_ABBREVS
from sword_reader import OSIS_BOOKS

# ---------------------------------------------------------------------------
# Book name resolution
# ---------------------------------------------------------------------------

_EXTRA_ABBREVS = {
    # OSIS ids and common short forms not in the linker table
    "Gn": "Genesis", "Lv": "Leviticus", "Nm": "Numbers", "Dt": "Deuteronomy",
    "Jsh": "Joshua", "Jg": "Judges", "Rt": "Ruth", "Ezr": "Ezra", "Neh": "Nehemiah",
    "Jb": "Job", "Psalm": "Psalms", "Pss": "Psalms", "Prv": "Proverbs", "Qoh": "Ecclesiastes",
    "Cant": "Song of Solomon", "Song of Solomon": "Song of Solomon", "SS": "Song of Solomon",
    "Jer": "Jeremiah", "Jr": "Jeremiah", "Ezk": "Ezekiel", "Dan": "Daniel", "Dn": "Daniel",
    "Hos": "Hosea", "Jl": "Joel", "Amo": "Amos", "Jnh": "Jonah", "Mic": "Micah",
    "Nah": "Nahum", "Hb": "Habakkuk", "Hg": "Haggai", "Hagg": "Haggai", "Zc": "Zechariah", "Ml": "Malachi",
    "Mr": "Mark", "Mrk": "Mark", "Luk": "Luke", "Jhn": "John", "Acts": "Acts",
    "Rm": "Romans", "Php": "Philippians", "Phi": "Philippians", "Phlm": "Philemon",
    "He": "Hebrews", "Jas": "James", "Jud": "Jude", "Jde": "Jude", "Rv": "Revelation",
    "Apoc": "Revelation",
    "1Thess": "1 Thessalonians", "2Thess": "2 Thessalonians", "1John": "1 John",
    "2John": "2 John", "3John": "3 John", "1Jo": "1 John", "2Jo": "2 John", "3Jo": "3 John",
}


def _norm_key(s: str) -> str:
    return re.sub(r"[\s.]", "", s).lower()


BOOK_LOOKUP: dict[str, str] = {}
for _k, _v in list(_LINKER_ABBREVS.items()) + list(_EXTRA_ABBREVS.items()) + OSIS_BOOKS:
    BOOK_LOOKUP.setdefault(_norm_key(_k), _v)
for _osis, _name in OSIS_BOOKS:
    BOOK_LOOKUP[_norm_key(_name)] = _name
# Roman-numeral prefixes used by some 19th-century texts ("I Cor", "II Kings")
for _k, _v in list(BOOK_LOOKUP.items()):
    if _k[:1] in "123":
        roman = {"1": "i", "2": "ii", "3": "iii"}[_k[0]]
        BOOK_LOOKUP.setdefault(roman + _k[1:], _v)
# "Peter" alone is ambiguous; the old linker mapped it to 1 Peter. Keep that for
# compatibility with existing rows but never resolve it from structured osisRefs.
_AMBIGUOUS = {"peter"}


def resolve_book(token: str) -> str | None:
    return BOOK_LOOKUP.get(_norm_key(token))


# ---------------------------------------------------------------------------
# Reference parsing + validation
# ---------------------------------------------------------------------------

_REF_RE = re.compile(
    r"^\s*(?P<book>(?:[1-3]|I{1,3})?\s*[A-Za-z][A-Za-z ]*?)[\s.]*"
    r"(?P<ch>\d+)(?:\s*[.:]\s*(?P<v>\d+))?"
    r"(?:\s*[-–—]\s*(?:(?:[1-3]?[A-Za-z]+)\.)?(?:(?P<ch2>\d+)[.:])?(?P<v2>\d+))?"
)


class RefResolver:
    """Turns reference strings into canonical 'Book C:V[-W]' targets, validated."""

    def __init__(self, v11n: dict[str, list[int]]):
        self.v11n = v11n

    def valid(self, book: str, ch: int, v: int | None = None) -> bool:
        chapters = self.v11n.get(book)
        if not chapters or ch < 1 or ch > len(chapters):
            return False
        return v is None or 1 <= v <= chapters[ch - 1]

    def target(self, book: str, ch: int, v: int | None, ch2: int | None, v2: int | None) -> str | None:
        if not self.valid(book, ch, v):
            return None
        if v is None:
            return f"{book} {ch}"
        if v2 is not None and (ch2 is None or ch2 == ch) and v2 > v and self.valid(book, ch, v2):
            return f"{book} {ch}:{v}-{v2}"
        return f"{book} {ch}:{v}"

    def parse(self, ref: str, default_book: str | None = None) -> str | None:
        """Parse an osisRef / ThML passage / display string. First reference wins."""
        if not ref:
            return None
        ref = ref.strip().split(";")[0].split(",")[0].strip()
        ref = re.sub(r"^[A-Za-z]+:", "", ref)  # osisRef work prefix, e.g. "Bible:Gen.1.1"
        m = _REF_RE.match(ref)
        if not m:
            return None
        book_tok = m.group("book").strip()
        if _norm_key(book_tok) in _AMBIGUOUS:
            return None
        book = resolve_book(book_tok)
        if not book:
            return None
        ch = int(m.group("ch"))
        v = int(m.group("v")) if m.group("v") else None
        ch2 = int(m.group("ch2")) if m.group("ch2") else None
        v2 = int(m.group("v2")) if m.group("v2") else None
        return self.target(book, ch, v, ch2, v2)


# Free-text references ("Joh 3:16", "Psa 119:1-8", "1 Cor. 13:4") found in plain text.
_text_tokens = set(_LINKER_ABBREVS) | set(_EXTRA_ABBREVS) | {n for _o, n in OSIS_BOOKS}
_text_tokens |= {re.sub(r"^[1-3]\s?", "", k) for k in _text_tokens}   # "Cor" for "1 Cor"
_text_tokens = {k for k in _text_tokens if k and k[0].isupper()}
_abbrev_alt = "|".join(re.escape(k) for k in sorted(_text_tokens, key=len, reverse=True))
TEXT_REF_RE = re.compile(
    rf"(?<!\w)((?:(?:[1-3]|I{{1,3}})\s?)?(?:{_abbrev_alt}))\.?\s+(\d+):(\d+)(?:\s?[-–]\s?(\d+))?\b"
)
_ANCHOR_SPLIT = re.compile(r"(<a\b[^>]*>.*?</a>)", re.S)


def anchor(target: str, display_html: str) -> str:
    return f'<a href="#" class="commentary-ref" data-ref="{html.escape(target, quote=True)}">{display_html}</a>'


def link_text_refs(content_html: str, resolver: RefResolver) -> tuple[str, int]:
    """Link free-text references outside existing anchors. Returns (html, links_added)."""
    added = 0

    def repl(m: re.Match) -> str:
        nonlocal added
        book_tok, ch, v, v2 = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        if _norm_key(book_tok) in _AMBIGUOUS:
            return m.group(0)
        book = resolve_book(book_tok)
        if not book:
            return m.group(0)
        target = resolver.target(book, ch, v, None, int(v2) if v2 else None)
        if not target:
            return m.group(0)
        added += 1
        return anchor(target, m.group(0))

    parts = _ANCHOR_SPLIT.split(content_html)
    for i in range(0, len(parts), 2):  # even indices are outside anchors
        parts[i] = TEXT_REF_RE.sub(repl, parts[i])
    return "".join(parts), added


# ---------------------------------------------------------------------------
# Mojibake
# ---------------------------------------------------------------------------

_MOJIBAKE_RE = re.compile(r"[Â-ô][\u0080-¿ŒœŠšŸŽžƒˆ˜–—‘-„†-•…‰‹›€™]{1,3}")


def fix_mojibake(s: str) -> str:
    """Repair UTF-8 text that was decoded as cp1252/latin-1 ("Ã†non" -> "Ænon")."""
    if "Ã" not in s and "â" not in s and "Â" not in s:
        return s

    def to_byte(ch: str) -> bytes:
        try:
            return ch.encode("cp1252")
        except UnicodeEncodeError:
            return ch.encode("latin-1")  # C1 controls cp1252 leaves undefined (0x81, 0x9d...)

    def repl(m):
        frag = m.group(0)
        try:
            return b"".join(to_byte(c) for c in frag).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return frag

    return _MOJIBAKE_RE.sub(repl, s)


# ---------------------------------------------------------------------------
# Markup -> text with reference placeholders
# ---------------------------------------------------------------------------

REF_OPEN, REF_MID, REF_CLOSE = "\x01", "\x02", "\x03"   # \x01target\x02display\x03

_BLOCK_TAGS = {"div", "p", "title", "blockquote", "table", "list", "chapter", "lg", "h1",
               "h2", "h3", "h4", "section", "head"}
_LINE_TAGS = {"br", "lb", "l", "item", "row", "tr", "li"}
_CELL_TAGS = {"cell", "td", "th"}
_DROP_WITH_CONTENT = re.compile(
    r"<(note|rdg|figure|img|script|style)\b[^>]*?(?:/>|>.*?</\1\s*>)", re.S | re.I
)
_REF_TAG = re.compile(
    r"<(reference|scripRef)\b([^>]*)>(.*?)</\1\s*>", re.S | re.I
)
_TAG = re.compile(r"<\s*(/?)\s*([A-Za-z][\w:]*)([^>]*)>", re.S)
_ATTR = re.compile(r'([\w:]+)\s*=\s*"([^"]*)"')


def markup_to_text(raw: str, extra_drop: re.Pattern | None = None) -> str:
    """ThML/OSIS/XHTML fragment -> plain text with paragraph breaks and ref placeholders."""
    s = fix_mojibake(raw)
    s = _DROP_WITH_CONTENT.sub(" ", s)
    if extra_drop is not None:
        s = extra_drop.sub(" ", s)

    def ref_repl(m):
        attrs = dict(_ATTR.findall(m.group(2)))
        inner = re.sub(r"<[^>]+>", "", m.group(3))
        target = attrs.get("osisRef") or attrs.get("passage") or ""
        if not target and attrs.get("parsed"):
            # ThML parsed="|Gen|1|1|0|0"
            p = [x for x in attrs["parsed"].split("|") if x]
            if len(p) >= 3:
                target = f"{p[0]} {p[1]}:{p[2]}"
        # display text keeps entities for now; unescaped below with the rest
        return f"{REF_OPEN}{target}{REF_MID}{inner}{REF_CLOSE}"

    s = _REF_TAG.sub(ref_repl, s)

    def tag_repl(m):
        name = m.group(2).lower().split(":")[-1]
        if name in _BLOCK_TAGS:
            return "\n\n"
        if name in _LINE_TAGS:
            return "\n"
        if name in _CELL_TAGS:
            return " "
        return ""

    s = _TAG.sub(tag_repl, s)
    s = re.sub(r"<[^>]*$", "", s)          # dangling partial tag at fragment end
    s = html.unescape(s)
    s = s.replace(" ", " ").replace("\r", "")
    s = re.sub(r"[ \t\f\v]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def plain_to_text(s: str) -> str:
    """Normalise already-plain text (HelloAO JSON)."""
    s = fix_mojibake(s).replace("\r", "").replace(" ", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


_ENTITYLIKE = re.compile(r"&(?=#?\w+;)")


def _escape(s: str) -> str:
    # Escape '<' and '>' always; '&' only where a browser would read an entity, so that
    # bare "&c." stays readable in x-text previews as well as x-html.
    return _ENTITYLIKE.sub("&amp;", s).replace("<", "&lt;").replace(">", "&gt;")


_PLACEHOLDER = re.compile(f"{REF_OPEN}(.*?){REF_MID}(.*?){REF_CLOSE}", re.S)


def render(text: str, resolver: RefResolver) -> tuple[str, str, int]:
    """Text with placeholders -> (content_html, searchable_text, link_count)."""
    links = 0
    out = []
    pos = 0
    for m in _PLACEHOLDER.finditer(text):
        out.append(_escape(text[pos:m.start()]))
        target_raw, display = m.group(1), m.group(2).strip()
        target = resolver.parse(target_raw) or resolver.parse(display)
        if target and display:
            out.append(anchor(target, _escape(display)))
            links += 1
        else:
            out.append(_escape(display))
        pos = m.end()
    out.append(_escape(text[pos:]))
    content = "".join(out)
    content, added = link_text_refs(content, resolver)
    links += added
    searchable = _PLACEHOLDER.sub(lambda m: m.group(2), text)
    searchable = searchable.replace("<", " ").replace(">", " ")
    return content, searchable, links
