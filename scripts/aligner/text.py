"""English tokenization and normalization.

POSITIONS CONTRACT. `english_word_alignments.english_word_position` is the
1-based index of a word among the *tappable* words of the verse text, exactly as
the reader UI numbers them in `formatVerseText()` (frontend/static/js/app.js):

    text.split(/\\s+/) and each piece must fully match
    /^([.,;:!?'"()—]*)([a-zA-Z'-]+)([.,;:!?'"()—]*)$/

Pieces that do not match (for example ones containing a curly quote, a digit
or a bracket) are not tappable and do not advance the counter. If the UI's
tokenizer changes, this function must change with it and the alignment build
must be re-run.
"""
import re
import unicodedata

_PUNCT = r"""[.,;:!?'"()—]*"""
_TAP_RE = re.compile(rf"^({_PUNCT})([a-zA-Z'-]+)({_PUNCT})$")
_WS_RE = re.compile(r"\s+")


def tappable_words(text: str) -> list[str]:
    """Return the tappable words of a verse, in UI position order (position = index + 1)."""
    out = []
    for piece in _WS_RE.split(text):
        m = _TAP_RE.match(piece)
        if m:
            out.append(m.group(2))
    return out


def tappable_spans(text: str) -> list[tuple[str, int, int]]:
    """Like tappable_words but with (word, start, end) character offsets into `text`."""
    out = []
    for m in re.finditer(r"\S+", text):
        piece = m.group(0)
        t = _TAP_RE.match(piece)
        if t:
            start = m.start() + t.start(2)
            out.append((t.group(2), start, start + len(t.group(2))))
    return out


def clean_word(word: str) -> str:
    """Strip characters the UI would not show inside a tappable word (for display rows)."""
    return "".join(c for c in word if c.isalpha() or c in "'-")


# --- English normalization ---------------------------------------------------

# Early Modern English forms that BSB/WEB never use. Mapped to the modern form
# before stemming so that a model trained on modern English can score them.
ARCHAIC = {
    "thou": "you", "thee": "you", "ye": "you", "thy": "your", "thine": "your",
    "thyself": "yourself", "yourselves": "yourself",
    "hath": "has", "hast": "have", "hadst": "had", "doth": "does", "dost": "do",
    "didst": "did", "art": "are", "wast": "were", "wert": "were",
    "shalt": "shall", "wilt": "will", "canst": "can", "couldest": "could",
    "wouldest": "would", "shouldest": "should", "mayest": "may", "mightest": "might",
    "saith": "says", "spake": "spoke", "sware": "swore", "brake": "broke",
    "bare": "bore", "gat": "got", "clave": "clung", "wist": "knew", "wot": "know",
    "unto": "to", "whither": "where", "thither": "there", "hither": "here",
    "whence": "where", "thence": "there", "hence": "here", "yea": "yes",
    "nay": "no", "lo": "behold", "verily": "truly", "ere": "before",
    "aught": "anything", "naught": "nothing", "nought": "nothing",
    "shew": "show", "shewed": "showed", "sheweth": "shows", "shewing": "showing",
    "holpen": "helped", "durst": "dared", "begat": "fathered",
    "an": "a",
}

# Normalize the copula and auxiliaries to one key each; they are translated from
# the same source features (verb person/tense) whatever the surface form.
LEMMA = {
    "am": "be", "is": "be", "are": "be", "was": "be", "were": "be", "been": "be",
    "being": "be", "be": "be",
    "has": "have", "have": "have", "had": "have", "having": "have",
    "does": "do", "did": "do", "done": "do", "doing": "do",
    "said": "say", "says": "say", "saying": "say",
    "went": "go", "gone": "go", "goes": "go",
    "came": "come", "comes": "come", "coming": "come",
    "made": "make", "makes": "make", "making": "make",
    "gave": "give", "given": "give", "gives": "give",
    "took": "take", "taken": "take", "takes": "take",
    "saw": "see", "seen": "see", "sees": "see",
    "knew": "know", "known": "know", "knows": "know",
    "spoke": "speak", "spoken": "speak", "spake": "speak",
    "him": "he", "his": "he", "himself": "he",
    "her": "she", "hers": "she", "herself": "she",
    "them": "they", "their": "they", "theirs": "they", "themselves": "they",
    "me": "i", "my": "i", "mine": "i", "myself": "i",
    "us": "we", "our": "we", "ours": "we", "ourselves": "we",
    "your": "you", "yours": "you", "yourself": "you",
    "its": "it", "itself": "it",
    "men": "man", "women": "woman", "children": "child", "brethren": "brother",
    "brothers": "brother", "feet": "foot", "teeth": "tooth", "oxen": "ox",
}

_VOWELS = set("aeiou")


def _strip_archaic_ending(w: str, vocab) -> str:
    """loveth -> love, walkest -> walk, didst -> did, using a modern vocabulary.

    Only strips when the bare word is not itself a modern word (beast, midst,
    priest and harvest stay as they are) and the stripped candidate is.
    """
    if vocab is None or w in vocab:
        return w
    for suffix in ("eth", "est", "edst", "st"):
        if w.endswith(suffix) and len(w) > len(suffix) + 1:
            stem = w[: -len(suffix)]
            for cand in (stem, stem + "e", stem + "ed" if suffix == "edst" else None,
                         stem[:-1] if len(stem) > 2 and stem[-1] == stem[-2] else None):
                if cand and cand in vocab:
                    return cand
    return w


def stem(w: str) -> str:
    """A small, deterministic suffix stripper (an equivalence key, not a real lemma)."""
    if len(w) <= 3:
        return w
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("sses"):
        return w[:-2]
    if w.endswith(("ches", "shes", "xes", "zes")):
        return w[:-2]
    if w.endswith("s") and not w.endswith(("ss", "us", "is")):
        w = w[:-1]
    if w.endswith("ing") and len(w) > 5:
        base = w[:-3]
        if len(base) > 2 and base[-1] == base[-2] and base[-1] not in "lsz":
            base = base[:-1]
        return base
    if w.endswith("ed") and len(w) > 4:
        base = w[:-2]
        if base.endswith("i"):
            return base[:-1] + "y"
        if len(base) > 2 and base[-1] == base[-2] and base[-1] not in "lsz":
            base = base[:-1]
        return base
    if w.endswith("e") and len(w) > 4:
        return w[:-1]
    return w


def normalize(word: str, vocab=None) -> str:
    """Map an English surface word to the key the model uses.

    `vocab` (a set of lowercase modern words, from BSB/WEB) enables -eth/-est
    stripping for Early Modern English (KJV, YLT, ASV, Darby).
    """
    w = unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode().lower()
    w = w.strip("'-")
    if w.endswith("'s"):
        w = w[:-2]
    elif w.endswith("s'"):
        w = w[:-1]
    w = w.replace("'", "")
    if not w:
        return ""
    w = ARCHAIC.get(w, w)
    w = _strip_archaic_ending(w, vocab)
    w = ARCHAIC.get(w, w)
    if w in LEMMA:
        return LEMMA[w]
    return stem(w)


# --- Original-language helpers ----------------------------------------------

def strip_diacritics(s: str) -> str:
    """Lowercase, drop accents/points/cantillation and anything that is not a letter."""
    d = unicodedata.normalize("NFD", s)
    return "".join(c for c in d if unicodedata.category(c).startswith("L")).lower()
