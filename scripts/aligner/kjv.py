"""KJV with Strong's numbers (eBible.org eng-kjv2006, public domain) as alignment data.

eBible's KJV USFM tags most content words with a Strong's number
(`\\w beginning|strong="H7225"\\w*`) and marks the italic words the
translators supplied (`\\add was\\add*`). We use it two ways:

1. as a human-tagged gold set to score the statistical aligner on KJV, and
2. as the primary source for the shipped KJV alignment.

A Strong's tag names a lemma, not a word position. We resolve it to a
STEPBible position in the verse's Textus Receptus / Masoretic tokens:
unique when the lemma occurs once among them, by order when the verse has
as many tagged English spans as source occurrences, otherwise left to the
aligner (which then chooses among that lemma's positions only).

Source: https://ebible.org/Scriptures/eng-kjv2006_usfm.zip
"""
import difflib
import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .sources import _pad
from .text import tappable_spans

KJV_USFM_URL = "https://ebible.org/Scriptures/eng-kjv2006_usfm.zip"
KJV_CACHE_KEY = "kjv-strongs/eng-kjv2006_usfm.zip"

USFM_BOOKS = {
    "GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus", "NUM": "Numbers",
    "DEU": "Deuteronomy", "JOS": "Joshua", "JDG": "Judges", "RUT": "Ruth",
    "1SA": "1 Samuel", "2SA": "2 Samuel", "1KI": "1 Kings", "2KI": "2 Kings",
    "1CH": "1 Chronicles", "2CH": "2 Chronicles", "EZR": "Ezra", "NEH": "Nehemiah",
    "EST": "Esther", "JOB": "Job", "PSA": "Psalms", "PRO": "Proverbs",
    "ECC": "Ecclesiastes", "SNG": "Song of Solomon", "ISA": "Isaiah",
    "JER": "Jeremiah", "LAM": "Lamentations", "EZK": "Ezekiel", "DAN": "Daniel",
    "HOS": "Hosea", "JOL": "Joel", "AMO": "Amos", "OBA": "Obadiah", "JON": "Jonah",
    "MIC": "Micah", "NAM": "Nahum", "HAB": "Habakkuk", "ZEP": "Zephaniah",
    "HAG": "Haggai", "ZEC": "Zechariah", "MAL": "Malachi", "MAT": "Matthew",
    "MRK": "Mark", "LUK": "Luke", "JHN": "John", "ACT": "Acts", "ROM": "Romans",
    "1CO": "1 Corinthians", "2CO": "2 Corinthians", "GAL": "Galatians",
    "EPH": "Ephesians", "PHP": "Philippians", "COL": "Colossians",
    "1TH": "1 Thessalonians", "2TH": "2 Thessalonians", "1TI": "1 Timothy",
    "2TI": "2 Timothy", "TIT": "Titus", "PHM": "Philemon", "HEB": "Hebrews",
    "JAS": "James", "1PE": "1 Peter", "2PE": "2 Peter", "1JN": "1 John",
    "2JN": "2 John", "3JN": "3 John", "JUD": "Jude", "REV": "Revelation",
}

# Strong's (1890) gave some inflected forms their own number; STEPBible files
# them under one lemma (and has a few numbers of its own). Each set below is
# one lemma for matching purposes. Pronoun, demonstrative and eimi forms come
# from the lexicon's own derivations ("dative case of G4771"); the rest were
# found by pairing, in verses where exactly one KJV tag and one STEPBible
# lemma were left unmatched, and checked against the lexicon.
STRONGS_CLASSES = [
    # su, "you"
    {"G4771", "G4571", "G4671", "G4675", "G5209", "G5210", "G5213", "G5216"},
    # ego, "I" (STEPBible files most oblique forms under G3165)
    {"G1473", "G3165", "G1691", "G1698", "G1700", "G3427", "G3450",
     "G2248", "G2249", "G2254", "G2257"},
    # houtos, "this"
    {"G3778", "G5023", "G5025", "G5026", "G5124", "G5125", "G5126", "G5127",
     "G5128", "G5129", "G5130"},
    # eimi, "to be"
    {"G1510", "G1511", "G2076", "G2258", "G1526", "G2071", "G2070", "G2075",
     "G2252", "G2253", "G5600", "G5607", "G1488", "G1498", "G2073", "G2077", "G2468"},
    {"G1492", "G6063"},          # eido / oida
    {"H1980", "H3212"},          # halak / yalak, "to walk"
    {"G0756", "G0757"}, {"G4412", "G4413"}, {"G3440", "G3441"}, {"G0680", "G0681"},
    {"G1636", "G1638"}, {"G2112", "G2117"}, {"G5224", "G5225"}, {"G0567", "G0568"},
    {"G2908", "G2909"}, {"G5305", "G5306"}, {"G4053", "G4055"}, {"G4991", "G4992"},
    {"H5892", "H6145"}, {"H2451", "H2454"},
]
_CLASS_OF = {code: min(group) for group in STRONGS_CLASSES for code in group}


def lemma_class(code: str | None) -> str | None:
    """Canonical id of the lemma class a (padded) Strong's number belongs to."""
    if not code:
        return code
    return _CLASS_OF.get(code, code)


# A closing marker (\\w*) is followed by content; an opening marker (\\w ) eats one space.
_MARKER_RE = re.compile(r"\\(\+?[a-z]+\d*)(\*)|\\(\+?[a-z]+\d*)\s?|([^\\]+)")
_STRONG_RE = re.compile(r'strong="([^"]+)"')


@dataclass
class KjvWord:
    key: str            # letters only, lowercase (for matching to our KJV text)
    strongs: tuple      # ('H7225',) or ()
    added: bool         # italic word supplied by the translators (\add)


def _key(s: str) -> str:
    return "".join(c for c in s.lower() if c.isalpha())


def parse_verse_usfm(body: str) -> list[KjvWord]:
    """Parse one verse's USFM into words with their Strong's tags and \\add flag.

    Text is first laid out character by character with the tag and \\add state
    in force, then split on whitespace, so a tag boundary inside a word
    (`\\w God|strong="H0430"\\w*'s`) still yields one word.
    """
    body = re.sub(r"\\f .*?\\f\*", " ", body)
    body = re.sub(r"\\x .*?\\x\*", " ", body)
    chars: list[tuple[str, tuple, bool]] = []
    add_depth = 0
    in_w = False
    w_buf: list[str] = []

    def lay_out(text: str, strongs: tuple):
        for c in text:
            chars.append((c, strongs, add_depth > 0))

    for m in _MARKER_RE.finditer(body):
        marker = m.group(1) or m.group(3)
        closing, text = m.group(2), m.group(4)
        if text is not None:
            if in_w:
                w_buf.append(text)
            else:
                lay_out(text, ())
            continue
        name = marker.lstrip("+")
        if name == "w":
            if closing:
                surface, _, attrs = "".join(w_buf).partition("|")
                tags = tuple(_norm_strong(s) for s in
                             " ".join(_STRONG_RE.findall(attrs)).split() if s)
                lay_out(surface, tags)
                in_w, w_buf = False, []
            else:
                in_w, w_buf = True, []
        elif name == "add":
            add_depth = max(add_depth + (-1 if closing else 1), 0)
        elif not closing and marker in ("p", "q", "q1", "q2", "b", "m", "nb", "pi"):
            lay_out(" ", ())

    words: list[KjvWord] = []
    piece: list = []
    for item in chars + [(" ", (), False)]:
        if item[0].isspace():
            letters = [x for x in piece if x[0].isalpha()]
            if letters:
                k = "".join(x[0] for x in letters).lower()
                tags = next((x[1] for x in letters if x[1]), ())
                added = all(x[2] for x in letters)
                words.append(KjvWord(k, tags, added))
            piece = []
        else:
            piece.append(item)
    return words


def _norm_strong(s: str) -> str:
    s = s.strip()
    m = re.match(r"([HG])(\d+)", s)
    if not m:
        return s
    return f"{m.group(1)}{int(m.group(2)):04d}"


def load_kjv_usfm(zip_path: Path) -> dict:
    """{(book, chapter, verse): [KjvWord, ...]} from the eBible USFM zip."""
    verses: dict = {}
    with zipfile.ZipFile(zip_path) as zf:
        for name in sorted(zf.namelist()):
            if not name.endswith(".usfm"):
                continue
            text = zf.read(name).decode("utf-8-sig")
            m = re.search(r"\\id (\w+)", text)
            book = USFM_BOOKS.get(m.group(1)) if m else None
            if not book:
                continue
            chapter, current = 0, None
            # Split on chapter and verse markers, keeping them.
            for tok in re.split(r"(\\c \d+|\\v \d+)", text):
                cm = re.match(r"\\c (\d+)", tok)
                vm = re.match(r"\\v (\d+)", tok)
                if cm:
                    chapter = int(cm.group(1))
                    current = None
                elif vm:
                    current = (book, chapter, int(vm.group(1)))
                    verses[current] = []
                elif current:
                    verses[current].extend(parse_verse_usfm(tok))
    return verses


def project_to_text(kjv_words: list[KjvWord], text: str):
    """Map eBible words onto the tappable words of our KJV verse text.

    Returns a list (one entry per tappable word) of KjvWord or None when the
    word has no counterpart in eBible's text (spelling or edition differences).
    """
    pieces = []  # (key, tappable_index or None)
    tap = {s: i for i, (_, s, _) in enumerate(tappable_spans(text))}
    for m in re.finditer(r"\S+", text):
        k = _key(m.group(0))
        if not k:
            continue
        idx = None
        for start, i in tap.items():
            if m.start() <= start < m.end():
                idx = i
                break
        pieces.append((k, idx))
    a = [p[0] for p in pieces]
    b = [w.key for w in kjv_words]
    out = [None] * len(tap)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                idx = pieces[i1 + k][1]
                if idx is not None:
                    out[idx] = kjv_words[j1 + k]
    return out


# Resolution status of a tagged word.
UNIQUE, ORDERED, AMBIGUOUS, MISSING, ADDED, UNTAGGED = (
    "unique", "ordered", "ambiguous", "missing", "added", "untagged")


def resolve_tags(projected: list, candidates: list) -> list[tuple]:
    """Resolve each tappable word's Strong's tag to STEPBible positions.

    projected: output of project_to_text; candidates: SourceToken list for the
    verse (already edition-filtered). Returns, per tappable word,
    (status, positions) where positions is a tuple of candidate positions with
    the tagged lemma (one position for unique/ordered).
    """
    by_lemma = defaultdict(list)
    for t in candidates:
        if t.strong:
            by_lemma[lemma_class(_pad(t.strong))].append(t.pos)

    # Group consecutive words carrying the same tag into one span (one occurrence).
    spans = defaultdict(list)  # lemma -> [[word indices], ...]
    prev = None
    for i, w in enumerate(projected):
        tag = lemma_class(w.strongs[0]) if (w and w.strongs) else None
        if tag and tag == prev:
            spans[tag][-1].append(i)
        elif tag:
            spans[tag].append([i])
        prev = tag

    out = []
    for i, w in enumerate(projected):
        if w is None:
            out.append((MISSING, ()))
        elif w.added:
            out.append((ADDED, ()))
        elif not w.strongs:
            out.append((UNTAGGED, ()))
        else:
            out.append(None)
    for lemma, lemma_spans in spans.items():
        positions = by_lemma.get(lemma, [])
        for k, span in enumerate(lemma_spans):
            for i in span:
                if projected[i].added:
                    continue
                if not positions:
                    out[i] = (MISSING, ())
                elif len(positions) == 1:
                    out[i] = (UNIQUE, (positions[0],))
                elif len(lemma_spans) == len(positions):
                    out[i] = (ORDERED, (positions[k],))
                else:
                    out[i] = (AMBIGUOUS, tuple(positions))
    return [o if o is not None else (UNTAGGED, ()) for o in out]
