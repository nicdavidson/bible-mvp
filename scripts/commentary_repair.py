"""
Repairs for commentary text taken from SermonIndex SWORD modules (sermonindex.net/modules/sword).

Their converter damaged the text in three systematic ways (docs/COMMENTARY_LIBRARY_2026-11.md):

1. Every ALL-CAPS word of 8 or more letters was deleted ("THE REVELATION OF JESUS CHRIST"
   became "THE OF JESUS CHRIST"; "companion in TRIBULATION." became "companion in .").
   No module holds a single all-caps word of 8+ letters, while 7-letter ones are common.
   `restore_caps` puts them back from an independent scan of the same book (archive.org
   OCR): it aligns the two texts on 5-word sequences that occur once in each, diffs the
   stretches between those anchors word by word, and inserts only words the scan has and
   the module lacks that are themselves ALL-CAPS and 8+ letters long. Anything else the
   scan differs by (OCR errors, running heads, page numbers) is ignored.
2. Its Scripture linker turned the word "is" in front of a number into "Isaiah"
   ("this 69 weeks of years Isaiah 476 years"). `fix_is_isaiah` undoes that where the
   number cannot be an Isaiah reference (see the rule there) and leaves everything else.
3. A stray space after curly apostrophes and opening quotes ("God’ s", "“ Elohim”") and
   before some punctuation. `tidy_spacing` closes those up.

All functions work on the text produced by commentary_text.markup_to_text (plain text with
reference placeholders), before it is rendered.
"""
from __future__ import annotations

import bisect
import collections
import difflib
import re

# ---------------------------------------------------------------------------
# 1. ALL-CAPS words deleted by the converter
# ---------------------------------------------------------------------------

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9’'\-]*")
_CAPS_WORD = re.compile(r"^[A-Z][A-Z’'\-]*[A-Z]$")
_GRAM = 5          # anchor length in words
_MAX_GAP = 400     # longest stretch between anchors that is diffed (words)


def _norm(tok: str) -> str:
    return re.sub(r"[^a-z0-9]", "", tok.lower())


def _letters(w: str) -> int:
    return sum(c.isalpha() for c in w)


def dropped_by_converter(w: str) -> bool:
    """The converter deleted exactly the ALL-CAPS words of 8+ letters."""
    return bool(_CAPS_WORD.match(w)) and _letters(w) >= 8


def clean_ocr(text: str) -> str:
    """archive.org djvu text: join hyphenated line ends, drop lines that repeat (running
    heads) and lines with no letters (page numbers, chart debris)."""
    text = text.replace("\r", "")
    text = re.sub(r"(\w)-\n\s*(\w)", r"\1\2", text)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n")]

    def head_key(ln):   # "80 THE THINGS WHICH SHALL BE HEREAFTER. 95" -> its words
        return re.sub(r"[\d\W]+", " ", ln).strip().lower()
    counts = collections.Counter(head_key(ln) for ln in lines if ln)
    return "\n".join(ln for ln in lines
                     if ln and counts[head_key(ln)] < 3 and not re.fullmatch(r"[\d\W]+", ln))


def _join_fragments(words: list[str], vocab: set[str]) -> list[str]:
    """OCR splits long words across lines ("CON SUMMATION"); join caps fragments shorter
    than 8 letters with the next one when the result is a word seen elsewhere."""
    out, i = [], 0
    while i < len(words):
        w, j = words[i], i + 1
        while (_letters(w) < 8 and j < len(words) and _CAPS_WORD.match(w)
               and _CAPS_WORD.match(words[j]) and _norm(w + words[j]) in vocab):
            w += words[j]
            j += 1
        out.append(w)
        i = j
    return out


def _anchor_chain(mn: list[str], rn: list[str]) -> list[tuple[int, int]]:
    """(module index, scan index) of 5-word sequences unique in both, longest monotonic run."""
    n = _GRAM
    gm = collections.Counter(tuple(mn[i:i + n]) for i in range(len(mn) - n + 1))
    gr = collections.Counter(tuple(rn[i:i + n]) for i in range(len(rn) - n + 1))
    rpos = {}
    for i in range(len(rn) - n + 1):
        g = tuple(rn[i:i + n])
        if gr[g] == 1 and gm.get(g) == 1:
            rpos[g] = i
    pairs = [(i, rpos[g]) for i in range(len(mn) - n + 1) if (g := tuple(mn[i:i + n])) in rpos]
    tails, tails_idx, prev = [], [], [-1] * len(pairs)
    for k, (_i, j) in enumerate(pairs):
        p = bisect.bisect_left(tails, j)
        if p == len(tails):
            tails.append(j)
            tails_idx.append(k)
        else:
            tails[p] = j
            tails_idx[p] = k
        prev[k] = tails_idx[p - 1] if p else -1
    chain, k = [], tails_idx[-1] if tails_idx else -1
    while k >= 0:
        chain.append(pairs[k])
        k = prev[k]
    return chain[::-1]


def _insert(t: str, pos: int, words: str) -> str:
    rest = t[pos:]
    glued = re.match(r"[^\w\s“\"‘(]*", rest).group(0)   # "Candlesticks.”" keeps its stop
    head, rest = t[:pos] + glued, rest[len(glued):]
    m = re.match(r"(\s*)([“\"‘']+)(?=[^\w\s]|$)", rest)
    if m:   # an emptied quotation: “” or “.” -> the word goes inside the quotes
        return head + m.group(1) + m.group(2) + words + rest[m.end():]
    return head + " " + words + rest


def _caps_context(texts, mtoks, pos) -> bool:
    """The module words on both sides of the gap are ALL-CAPS (or it ends the line)."""
    ei, end, _ = mtoks[pos - 1]
    t = texts[ei]
    before = re.findall(r"[A-Za-z]+", t[max(0, end - 20):end])
    after_text = t[end:end + 20]
    after = re.findall(r"[A-Za-z]+", after_text.split("\n")[0])
    caps = lambda w: w.isupper() and len(w) >= 2   # noqa: E731
    return bool(before) and caps(before[-1]) and (not after or caps(after[0]))


def restore_caps(texts: list[str], scan_text: str) -> tuple[list[str], collections.Counter]:
    """Put back ALL-CAPS 8+ letter words, taking them from `scan_text` (OCR of the same
    work). `texts` are the module's entries in reading order. Returns (texts, stats)."""
    ref = clean_ocr(scan_text)
    rtoks = [(m.group(0), k) for m in _TOKEN.finditer(ref) if (k := _norm(m.group(0)))]
    mtoks = [(ei, m.end(), k) for ei, t in enumerate(texts)
             for m in _TOKEN.finditer(t) if (k := _norm(m.group(0)))]
    mn, rn = [t[2] for t in mtoks], [t[1] for t in rtoks]
    vocab = set(mn) | set(rn)
    chain = _anchor_chain(mn, rn)
    st = collections.Counter()
    inserts = collections.defaultdict(list)
    for (i1, j1), (i2, j2) in zip(chain, chain[1:]):
        a0, b0 = i1 + _GRAM, j1 + _GRAM
        if i2 < a0 or j2 < b0:
            continue
        if i2 - a0 > _MAX_GAP or j2 - b0 > _MAX_GAP:
            st["stretches_too_long_to_diff"] += 1
            continue
        sm = difflib.SequenceMatcher(None, mn[a0:i2], rn[b0:j2], autojunk=False)
        for op, x1, _x2, y1, y2 in sm.get_opcodes():
            if op != "insert":
                continue
            words = [re.sub(r"^[^A-Za-z]+|[^A-Za-z]+$", "", rtoks[b0 + y][0]) for y in range(y1, y2)]
            words = _join_fragments([w for w in words if w], vocab)
            pos = a0 + x1
            if _caps_context(texts, mtoks, pos):
                # an ALL-CAPS heading in the module that the scan prints in small capitals
                # ("THE ." where the book has "The Salutation."): same word, module's case
                words = [w.upper() if re.fullmatch(r"[A-Z][a-z’']+", w) and _letters(w) >= 8 else w
                         for w in words]
            if not words or not all(dropped_by_converter(w) for w in words):
                if any(dropped_by_converter(w) for w in words):
                    st["caps_next_to_other_scan_text_skipped"] += 1
                continue
            ei, end, _ = mtoks[pos - 1]
            if mtoks[pos][0] != ei:
                st["at_entry_boundary_skipped"] += 1
                continue
            inserts[ei].append((end, " ".join(words)))
            st["caps_words_restored"] += len(words)
    out = list(texts)
    for ei, ins in inserts.items():
        t = out[ei]
        for pos, words in sorted(ins, reverse=True):
            t = _insert(t, pos, words)
        out[ei] = t
    st["entries_with_restored_words"] = len(inserts)
    st["anchors"] = len(chain)
    return out, st


# Visible traces of a deleted word that could not be restored ("THE OF", "in . This", "“”").
GAP_SIGNATURE = re.compile(
    r"\b(?:THE|OF|AND|the|of|a|an|in|to|and)\s+[.,;:!?”)]|“\s*[.,]?\s*”|\bTHE\s+(?:OF|AND)\b")


# ---------------------------------------------------------------------------
# 2. "is" turned into "Isaiah"
# ---------------------------------------------------------------------------

_IS_NUMBER = re.compile(
    r"\bIsaiah(\s+)(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?(?:\s+\d/\d)?)(?!\s*[:\d])"
    r"(?=(\s+[A-Za-z%.]+)?)")
_QUANTITY_WORDS = {"years", "year", "times", "cubits", "cubit", "reeds", "furlongs", "miles",
                   "feet", "per", "percent", "x", "to", "days", "months", "weeks", "pounds",
                   "inches", "talents", "shekels", "hours", "men", "generations", "%"}
_IS_BEFORE_BOOK = re.compile(r"\bIsaiah(\s+)(?=[1-3]\s+[A-Z][a-z]+\.?\s+\d+:\d)")


def fix_is_isaiah(text: str, stats: collections.Counter | None = None,
                  examples: list | None = None) -> str:
    """Undo the linker's "is" -> "Isaiah" where the following number can't be a reference.

    "Isaiah N" (N not followed by ":verse") becomes "is N" when
      - N has a thousands separator, a decimal point or a fraction, or N > 66
        (Isaiah has 66 chapters): "Isaiah 476 years", "Isaiah 25,000 reeds", "Isaiah 19.5";
      - the word after N is a quantity ("6 cubits", "8 times", "3 x 6", "766 to 679");
      - the word before is a number or a date ("30 A. D. Isaiah 34").
    Never after a label colon ("Writer of the Book: Isaiah 766 to 679 B. C." is ambiguous).
    "Isaiah" directly before another book's reference ("Isaiah 1 Corinthians 6:9") is "is".
    Anything else ("(Isaiah 4)", "read Isaiah 53") is a real reference and left alone.
    """
    def repl(m):
        num, after = m.group(2), (m.group(3) or "").strip().lower().rstrip(".")
        before = text[max(0, m.start() - 12):m.start()]
        n_int = int(re.match(r"\d+", num.replace(",", "")).group(0))
        reason = None
        if re.search(r":\s*$", before):
            # a label, e.g. Brooks "Writer of the Book: Isaiah 766 to 679 B. C." (ambiguous)
            return m.group(0)
        if "," in num or "." in num or "/" in num or n_int > 66:
            reason = "number"
        elif after in _QUANTITY_WORDS:
            reason = "quantity"
        elif re.search(r"(?:\d|\bA\.\s?D\.|\bB\.\s?C\.)\s*$", before):
            reason = "date"
        if not reason:
            return m.group(0)
        if stats is not None:
            stats["is_isaiah_fixed"] += 1
        if examples is not None:
            examples.append((text[max(0, m.start() - 40):m.end() + 15], reason))
        return "is" + m.group(1) + num
    text = _IS_NUMBER.sub(repl, text)

    def repl_book(m):
        if stats is not None:
            stats["is_isaiah_fixed"] += 1
        if examples is not None:
            examples.append((text[max(0, m.start() - 40):m.end() + 25], "book"))
        return "is" + m.group(1)
    return _IS_BEFORE_BOOK.sub(repl_book, text)


# Leftover in the stored text = "Isaiah N" that the rule above would still change.
def is_isaiah_leftovers(text: str) -> int:
    n = collections.Counter()
    fix_is_isaiah(text, n)
    return n["is_isaiah_fixed"]


# ---------------------------------------------------------------------------
# 3. Spacing
# ---------------------------------------------------------------------------

def tidy_spacing(text: str) -> str:
    # "God’ s" -> "God’s", "ISAIAH 'S" -> "ISAIAH'S"
    text = re.sub(r"(?<=[A-Za-z]) ?([’']) +(s|S|t|d|ll|re|ve|m)\b", r"\1\2", text)
    # "“ Elohim”" -> "“Elohim”"
    text = re.sub(r"([“‘]) +(?=\w)", r"\1", text)
    # "Israel , as" -> "Israel, as"; keep spaced ellipses (". . .")
    text = re.sub(r"(?<=[\w”’)]) +([,;:!?])(?=\s|$|[”’])", r"\1", text)
    text = re.sub(r"(?<=[\w”’)]) +\.(?=\s|$|[”’)])(?! \.)", ".", text)
    return text
