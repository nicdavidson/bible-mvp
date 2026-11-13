"""Shared rules for computed word studies (build: scripts/build_word_study.py,
API: backend/routers/wordstudy.py). docs/WORD_STUDY_2026-11.md explains each rule.

Nothing here writes prose about a word: it decodes the STEPBible parsing codes
into their standard grammatical names and defines which tokens are counted.
"""

# Which tokens count as "the text" for counts, collocations and samples.
# OT: every TAHOT token except LXX-reconstructed words (word_type 'X...').
# NT: tokens in the SBL Greek New Testament (BSB's base text). TR and Byzantine
# counts are reported beside it (editions column).
PRIMARY_TEXT_SQL = """((b.testament = 'OT' AND COALESCE(w.word_type, '') NOT LIKE 'X%')
                       OR (b.testament = 'NT' AND w.editions LIKE '%SBL%'))"""
PRIMARY_TEXT_LABEL = {"OT": "Hebrew/Aramaic OT (TAHOT, Leningrad Codex)",
                      "NT": "Greek NT (SBLGNT, as in TAGNT)"}
NT_EDITIONS = ("SBL", "TR", "Byz")


def edition_sql(column: str) -> str:
    """SQL test that `column` (TAGNT editions, e.g. 'NA28+SBL+Treg+TR«3+Byz') lists the
    edition bound as a parameter. Exact name: LIKE '%TR%' would also match 'Treg'
    (LIKE ignores case). 'TR«3' (in the TR, word order displaced) counts as TR."""
    return (f"('+' || replace(replace({column}, '«', '+'), '»', '+') || '+') "
            "LIKE '%+' || ? || '+%'")


def editions_of(editions: str | None) -> set:
    """'NA28+SBL+TR«3' -> {'NA28', 'SBL', 'TR'}."""
    return {e.split("«")[0].split("»")[0] for e in (editions or "").split("+") if e}

# Canonical sections used to spread sample verses (by books.book_order).
SECTIONS = [
    ("Law", 1, 5), ("History", 6, 17), ("Wisdom and Poetry", 18, 22), ("Prophets", 23, 39),
    ("Gospels", 40, 43), ("Acts", 44, 44), ("Paul's Letters", 45, 57),
    ("General Letters", 58, 65), ("Revelation", 66, 66),
]


def section_of(book_order: int) -> str:
    for name, lo, hi in SECTIONS:
        if lo <= book_order <= hi:
            return name
    return "?"


def unpad(strong: str) -> str:
    """'H0430' -> 'H430'."""
    return strong[0] + str(int(strong[1:])) if strong and strong[1:].isdigit() else strong


def pad(strong: str) -> str:
    """'H430' -> 'H0430' (word_alignments format)."""
    return strong[0] + strong[1:].zfill(4) if strong and strong[1:].isdigit() else strong


# --- parts of speech --------------------------------------------------------------------

HEBREW_PREFIXES = {"C", "c", "R", "Rd", "Td", "Ti", "Tr"}  # ו, prepositions, article, interrogative ה, relative ש


def main_segment(grammar: str) -> str:
    """Hebrew/Aramaic parsing of the word itself, without prefixes/suffixes.

    'HR/Ncfsa' -> 'Ncfsa'; 'HC/Vqw3ms' -> 'Vqw3ms'; 'ANcbsd/Ta' -> 'Ncbsd';
    'HR/Sp3ms' -> 'R' (a preposition carrying a suffix).
    """
    if not grammar:
        return ""
    segs = [s for s in grammar[1:].split("/") if s]
    i = 0
    while (i + 1 < len(segs) and segs[i] in HEBREW_PREFIXES
           and not segs[i + 1].startswith("S")):
        i += 1
    return segs[i] if i < len(segs) else ""


def pos_code(grammar: str, hebrew: bool) -> str:
    """Part of speech: Greek 'N', 'V', 'CONJ', 'ADV'...; Hebrew 'N', 'V', 'C', 'R'..."""
    if not grammar:
        return ""
    if hebrew:
        return main_segment(grammar)[:1]
    return grammar.replace(" ", "-").split("-")[0]


POS_LABEL = {
    # Greek (Robinson)
    "N": "noun", "V": "verb", "A": "adjective", "ADV": "adverb", "CONJ": "conjunction",
    "COND": "conditional particle", "PREP": "preposition", "PRT": "particle", "T": "article",
    "P": "personal pronoun", "R": "relative pronoun", "D": "demonstrative pronoun",
    "I": "interrogative pronoun", "X": "indefinite pronoun", "F": "reflexive pronoun",
    "S": "possessive pronoun", "C": "reciprocal pronoun", "K": "correlative pronoun",
    "Q": "correlative or interrogative pronoun", "INJ": "interjection",
}
HEBREW_POS_LABEL = {
    "N": "noun", "V": "verb", "A": "adjective", "D": "adverb", "C": "conjunction",
    "R": "preposition", "T": "particle", "P": "pronoun", "S": "suffix",
}

CONTENT_POS = {"N", "V", "A"}
# Lemmas the parsing calls nouns or verbs but which do grammatical work; excluded
# from collocations like function words. Kept short and listed in the doc.
FUNCTION_LEMMAS = {
    "H3605": "kol, 'all' (noun in the parsing)",
    "H369": "ʾayin, 'there is not'",
    "H3426": "yesh, 'there is'",
    "H996": "bayin, 'between'",
    "H1961": "hayah, 'be'",
    "G1510": "eimi, 'be'",
    "G3956": "pas, 'all'",
}


def pos_label(code: str, hebrew: bool) -> str:
    return (HEBREW_POS_LABEL if hebrew else POS_LABEL).get(code, code)


def is_function_lemma(strong: str, pos: str) -> bool:
    return pos not in CONTENT_POS or strong in FUNCTION_LEMMAS


# --- forms ----------------------------------------------------------------------------

G_TENSE = {"P": "present", "I": "imperfect", "F": "future", "A": "aorist", "R": "perfect",
           "L": "pluperfect", "2F": "second future", "2A": "second aorist",
           "2R": "second perfect", "2L": "second pluperfect"}
G_VOICE = {"A": "active", "M": "middle", "P": "passive", "E": "middle or passive",
           "D": "middle deponent", "O": "passive deponent", "N": "middle or passive deponent",
           "Q": "impersonal active", "X": "no voice"}
G_MOOD = {"I": "indicative", "S": "subjunctive", "O": "optative", "M": "imperative",
          "N": "infinitive", "P": "participle", "R": "imperative participle"}
G_CASE = {"N": "nominative", "G": "genitive", "D": "dative", "A": "accusative", "V": "vocative"}
G_NUMBER = {"S": "singular", "P": "plural"}

H_STEM = {"q": "Qal", "N": "Niphal", "p": "Piel", "P": "Pual", "h": "Hiphil", "H": "Hophal",
          "t": "Hithpael", "o": "Polel", "O": "Polal", "r": "Hithpolel", "m": "Poel",
          "M": "Poal", "k": "Palel", "K": "Pulal", "Q": "Qal passive", "l": "Pilpel",
          "L": "Polpal", "f": "Hithpalpel", "D": "Nithpael", "j": "Pealal", "i": "Pilel",
          "u": "Hothpaal", "c": "Tiphil", "v": "Hishtaphel", "w": "Nithpalel",
          "y": "Nithpoel", "z": "Hithpoel"}
A_STEM = {"q": "Peal", "Q": "Peil", "u": "Hithpeel", "p": "Pael", "P": "Ithpaal",
          "M": "Hithpaal", "a": "Aphel", "h": "Haphel", "s": "Saphel", "e": "Shaphel",
          "H": "Hophal", "i": "Ithpeel", "t": "Hishtaphel", "v": "Ishtaphel",
          "w": "Hithaphel", "o": "Polel", "z": "Ithpoel", "r": "Hithpolel",
          "f": "Hithpalpel", "b": "Hephal", "c": "Tiphel", "m": "Poel", "l": "Palpel",
          "L": "Ithpalpel", "O": "Ithpolel", "G": "Ittaphal"}
H_CONJ = {"p": "perfect", "q": "sequential perfect", "i": "imperfect",
          "w": "sequential imperfect", "h": "cohortative", "j": "jussive", "v": "imperative",
          "r": "participle", "s": "passive participle", "a": "infinitive absolute",
          "c": "infinitive construct"}
H_NUMBER = {"s": "singular", "p": "plural", "d": "dual"}
H_STATE = {"a": "absolute", "c": "construct", "d": "determined"}


def form_of(grammar: str, hebrew: bool) -> tuple[str, str]:
    """(key, label) grouping occurrences by form.

    Verbs: Greek tense-voice-mood ('V-AAI', 'aorist active indicative'); Hebrew stem and
    conjugation ('Vqp', 'Qal perfect'). Nouns, adjectives, pronouns: case and number
    (Greek) or number and state (Hebrew). Other words: the part of speech.
    """
    if not grammar:
        return "", "unparsed"
    if not hebrew:  # Greek (Robinson codes)
        parts = grammar.replace(" ", "-").split("-")
        pos = parts[0]
        if pos == "V" and len(parts) > 1:
            tvm = parts[1]
            tense = tvm[:2] if tvm[:1] == "2" else tvm[:1]
            rest = tvm[len(tense):]
            if len(rest) >= 2:
                label = " ".join(x for x in (G_TENSE.get(tense, tense), G_VOICE.get(rest[0], rest[0]),
                                             G_MOOD.get(rest[1], rest[1])) if x)
                return f"V-{tvm}", label
            return f"V-{tvm}", "verb"
        if len(parts) > 1 and len(parts[1]) >= 2 and parts[1][0] in G_CASE \
                and parts[1][1] in G_NUMBER:
            return f"{pos}-{parts[1][:2]}", f"{G_CASE[parts[1][0]]} {G_NUMBER[parts[1][1]]}"
        return pos, POS_LABEL.get(pos, pos)
    aramaic = grammar[0] == "A"
    seg = main_segment(grammar)
    if not seg:
        return "", "unparsed"
    if seg[0] == "V" and len(seg) >= 3:
        stem = (A_STEM if aramaic else H_STEM).get(seg[1], seg[1])
        return f"V{seg[1:3]}", f"{stem} {H_CONJ.get(seg[2], seg[2])}"
    if seg[0] in "NAP" and len(seg) >= 5 and seg[-2] in H_NUMBER and seg[-1] in H_STATE:
        return f"{seg[0]}-{seg[-2:]}", f"{H_NUMBER[seg[-2]]} {H_STATE[seg[-1]]}"
    return seg[:1], HEBREW_POS_LABEL.get(seg[:1], seg[:1])
