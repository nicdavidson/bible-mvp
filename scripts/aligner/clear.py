"""Clear-Bible manual alignments (BSB, YLT) re-keyed to STEPBible word positions.

Clear-Bible numbers source words in its own texts (WLCM/WLC for Hebrew, in
Hebrew versification; SBLGNT for Greek). The app's interlinear and the
`english_word_alignments.original_word_position` column use STEPBible
TAHOT/TAGNT positions in English versification. The two numberings agree in
most verses but not all (Hebrew versification shifts, TAGNT words that SBLGNT
lacks), so we map every Clear source word to a STEPBible token by aligning the
two word streams chapter by chapter on their consonantal / unaccented spelling.

Data: https://github.com/Clear-Bible/Alignments (data CC BY 4.0; BSB text CC0,
YLT public domain).
"""
import csv
import difflib
import json
from collections import defaultdict
from pathlib import Path

from .sources import SourceToken, candidate_tokens, surface_key
from .text import tappable_spans

CLEAR_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "clear-bible" / "data"

BOOK_IDS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
    "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon",
    "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah",
    "Malachi", "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians",
    "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon",
    "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude",
    "Revelation",
]


def parse_bcv(digits: str):
    """'01001001...' -> (book, chapter, verse). Accepts a leading 'o'/'n'."""
    if digits[:1] in ("o", "n"):
        digits = digits[1:]
    return BOOK_IDS[int(digits[0:2]) - 1], int(digits[2:5]), int(digits[5:8])


def clear_word_id(source_id: str) -> str:
    """Hebrew ids carry a morpheme digit (o + BBCCCVVVWWW + P); drop it."""
    return source_id[:12]


def load_clear_source(name: str) -> list[tuple[str, str, str]]:
    """[(word_id, surface, strongs)] for a Clear source text, morphemes merged."""
    words: dict[str, list] = {}
    with open(CLEAR_DIR / "sources" / f"{name}.tsv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            wid = clear_word_id(row["id"])
            if wid not in words:
                words[wid] = [row["text"], row.get("strongs", "")]
            else:
                words[wid][0] += row["text"]
    return [(wid, t, s) for wid, (t, s) in words.items()]


def _strong_num(s: str) -> str:
    digits = "".join(c for c in (s or "") if c.isdigit())
    return digits.lstrip("0")


def map_clear_to_step(clear_words, step_verses: dict, testament: str,
                      edition_translation: str | None = None) -> dict:
    """Map Clear word ids to STEPBible (book, chapter, verse, pos).

    testament: 'OT' (STEP tokens grouped by their Hebrew chapter) or 'NT'
    (TAGNT tokens of the given translation's edition, grouped by chapter).
    """
    step_groups = defaultdict(list)  # (book, chapter in the Clear numbering) -> [(key, tok)]
    for (book, ch, v), toks in step_verses.items():
        if v == 0 and testament == "NT":
            continue
        is_ot = BOOK_IDS.index(book) < 39
        if (testament == "OT") != is_ot:
            continue
        if testament == "NT" and edition_translation:
            toks = candidate_tokens(toks, edition_translation)
        for t in toks:
            if testament == "OT" and t.alt_kind == "(" and t.alt_ref:
                group_ch = t.alt_ref[0]
            else:
                group_ch = ch
            step_groups[(book, group_ch)].append((book, ch, v, t))

    clear_groups = defaultdict(list)
    for wid, text, strongs in clear_words:
        book, ch, _ = parse_bcv(wid)
        clear_groups[(book, ch)].append((wid, text, strongs))

    mapping = {}
    for key, cwords in clear_groups.items():
        stoks = step_groups.get(key, [])
        a = [surface_key(t) for _, t, _ in cwords]
        b = [surface_key(t.text) for *_, t in stoks]
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
                for k in range(i2 - i1):
                    book, ch, v, t = stoks[j1 + k]
                    mapping[cwords[i1 + k][0]] = (book, ch, v, t.pos)
            elif op == "replace":
                # Unequal block: pair by Strong's number in order.
                j = j1
                for i in range(i1, i2):
                    want = _strong_num(cwords[i][2])
                    for jj in range(j, j2):
                        if want and _strong_num(stoks[jj][3].strong) == want:
                            book, ch, v, t = stoks[jj]
                            mapping[cwords[i][0]] = (book, ch, v, t.pos)
                            j = jj + 1
                            break
    return mapping


def load_alignment_records(path: Path) -> dict[str, list[str]]:
    """target token id -> source word ids (Clear numbering), from a Burrito JSON file."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    links = defaultdict(list)
    for rec in data.get("records", []):
        src = [clear_word_id(s) for s in rec.get("source", [])]
        for tgt in rec.get("target", []):
            links[tgt].extend(src)
    return links


def load_target_tokens(path: Path) -> dict:
    """{(book, ch, v): [(token_id, text, skip_space_after), ...]} in token order."""
    verses = defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if not row.get("text"):
                continue
            skip = row.get("skip_space_after", "") == "y"
            if "isPunc" in row:  # YLT layout: no spacing info; punctuation hugs the left
                skip = False
            verses[parse_bcv(row["id"])].append((row["id"], row["text"], skip,
                                                  row.get("isPunc") == "True"))
    for toks in verses.values():
        toks.sort(key=lambda t: t[0])
    return verses


def build_text_with_spans(tokens) -> tuple[str, list[tuple[int, int]]]:
    """Rebuild verse text the way scripts/import_bsb.py does, keeping token spans."""
    parts, spans, offset = [], [], 0
    for i, (_, text, skip, is_punc) in enumerate(tokens):
        if is_punc and parts and parts[-1] == " ":
            parts.pop()
            offset -= 1
        spans.append((offset, offset + len(text)))
        parts.append(text)
        offset += len(text)
        if not skip:
            parts.append(" ")
            offset += 1
    text = "".join(parts)
    stripped = text.strip()
    lead = len(text) - len(text.lstrip())
    return stripped, [(s - lead, e - lead) for s, e in spans]


def gold_for_verse(verse_key, tokens, links, mapping):
    """(text, words, gold) where gold[i] is the set of STEP positions for tappable word i.

    Links that land in a different English verse than the target token cannot be
    stored (the table keys both sides on one verse) and are dropped; the second
    return field counts them.
    """
    text, spans = build_text_with_spans(tokens)
    words, gold, cross = [], [], 0
    for word, ws, we in tappable_spans(text):
        positions = set()
        for (tid, *_), (ts, te) in zip(tokens, spans):
            if ts < we and te > ws:
                for sid in links.get(tid, ()):
                    m = mapping.get(sid)
                    if m is None:
                        continue
                    if m[:3] != verse_key:
                        cross += 1
                        continue
                    positions.add(m[3])
        words.append(word)
        gold.append(frozenset(positions))
    return text, words, gold, cross


def build_gold(target: str, step_verses: dict, *, nt_source="SBLGNT", ot_source="WLCM"):
    """Gold alignments for a Clear-aligned translation ('BSB' or 'YLT').

    Returns ({verse_key: (text, words, gold_sets)}, stats).
    """
    tdir = CLEAR_DIR / "eng" / "targets" / target
    adir = CLEAR_DIR / "eng" / "alignments" / target
    stats = defaultdict(int)
    out = {}
    for testament, src_name, tsv in (("OT", ot_source, f"ot_{target}.tsv"),
                                      ("NT", nt_source, f"nt_{target}.tsv")):
        clear_words = load_clear_source(src_name)
        edition_tr = "BSB" if src_name == "SBLGNT" else None
        mapping = map_clear_to_step(clear_words, step_verses, testament, edition_tr)
        stats[f"{testament}_source_words"] += len(clear_words)
        stats[f"{testament}_source_mapped"] += len(mapping)
        links = load_alignment_records(adir / f"{src_name}-{target}-manual.json")
        targets = load_target_tokens(tdir / tsv)
        for vkey, toks in targets.items():
            text, words, gold, cross = gold_for_verse(vkey, toks, links, mapping)
            out[vkey] = (text, words, gold)
            stats["cross_verse_links_dropped"] += cross
            stats["words"] += len(words)
            stats["words_linked"] += sum(1 for g in gold if g)
        del links, targets, mapping, clear_words
    return out, dict(stats)


def source_token_index(tokens: list[SourceToken]) -> dict[int, SourceToken]:
    return {t.pos: t for t in tokens}
