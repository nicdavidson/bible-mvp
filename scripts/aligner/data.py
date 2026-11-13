"""Build model examples (verses) for training and evaluation, and the book splits."""
import re
import sqlite3

from .clear import build_gold
from .kjv import ADDED, ORDERED, UNIQUE, load_kjv_usfm, project_to_text, resolve_tags
from .model import Example
from .sources import candidate_tokens
from .text import normalize, tappable_words

# Held-out books: never used for training or tuning. Chosen to cover both
# testaments and each genre.
TEST_BOOKS = {
    "Ruth", "2 Samuel",                              # OT narrative
    "Job", "Song of Solomon", "Lamentations",        # OT poetry / wisdom
    "Hosea", "Habakkuk", "Zechariah",                # OT prophecy
    "Mark",                                          # NT narrative
    "Galatians", "1 Peter", "1 John",                # NT epistles
    "Revelation",                                    # NT apocalyptic
}
# Tuning books (hyperparameters, thresholds). Also excluded from training
# when evaluating; included in the final production model.
DEV_BOOKS = {"Joshua", "Ecclesiastes", "Micah", "Philippians", "James", "2 Peter"}


FUNCTION_WORDS = set(
    "the of and a to in be you he i they it that for with we on as at by from this so "
    "then but not have do will shall all who which there what when she these those "
    "now if or no into because may let one up out".split())


def flag_suspect_gold(examples, model, min_bad: int = 2, min_rate: float = 0.3,
                      floor: float = 0.002) -> set:
    """Verses whose gold looks shifted (Clear-Bible links attached to the wrong words).

    In a few percent of verses the Clear-Bible BSB alignment points English
    words at the wrong source words, apparently after the BSB text was revised
    and target token ids moved (e.g. John 10:36 links 'Father' to the relative
    pronoun). A gold link on a content word is implausible when its source
    lemma practically never produces that word anywhere else (model table
    probability < floor) and the word is not in that token's gloss. A verse is
    suspect when at least `min_bad` of its content-word links, and at least
    `min_rate` of them, are implausible.
    """
    suspect = set()
    for ex in examples:
        by_pos = {t.pos: t for t in ex.sources}
        n = bad = 0
        for e, g in zip(ex.english, ex.gold or []):
            if not g or e in FUNCTION_WORDS:
                continue
            n += 1
            best = 0.0
            for p in g:
                tok = by_pos.get(p)
                if tok is None:
                    continue
                feats, gloss = model._features(tok)
                if e in gloss:
                    best = 1.0
                    break
                for f in feats:
                    if f.startswith("L:"):
                        best = max(best, model.table.get(f, {}).get(e, 0.0))
            if best < floor:
                bad += 1
        if bad >= min_bad and bad >= min_rate * n:
            suspect.add(ex.key)
    return suspect


def split_of(book: str) -> str:
    if book in TEST_BOOKS:
        return "test"
    if book in DEV_BOOKS:
        return "dev"
    return "train"


def modern_vocab(conn: sqlite3.Connection) -> set[str]:
    """Lowercase words of the modern-English translations (for -eth/-est stripping)."""
    vocab = set()
    for (text,) in conn.execute(
            "SELECT text FROM verses WHERE translation_id IN ('BSB', 'WEB')"):
        vocab.update(w.lower() for w in re.findall(r"[A-Za-z]+", text))
    return vocab


def verse_texts(conn, translation: str) -> dict:
    return {(b, c, v): t for b, c, v, t in conn.execute(
        "SELECT book, chapter, verse, text FROM verses WHERE translation_id = ?",
        (translation,))}


def plain_examples(conn, translation: str, src: dict, vocab) -> list[Example]:
    """Examples with no gold, for aligning a translation from its DB text."""
    out = []
    for key, text in verse_texts(conn, translation).items():
        words = tappable_words(text)
        out.append(Example(key, [normalize(w, vocab) for w in words],
                           candidate_tokens(src.get(key, []), translation), None, words))
    return out


def bsb_examples(conn, src: dict, vocab, log=print) -> list[Example]:
    """BSB verses with Clear-Bible gold re-keyed to STEPBible positions."""
    gold, stats = build_gold("BSB", src)
    log(f"  BSB gold: {stats}")
    db = verse_texts(conn, "BSB")
    out = []
    for key, (text, words, g) in gold.items():
        if db.get(key) != text:
            continue  # only verses whose DB text is the text the gold was built on
        out.append(Example(key, [normalize(w, vocab) for w in words],
                           candidate_tokens(src.get(key, []), "BSB"), list(g), words))
    return out


def ylt_examples(src: dict, vocab, log=print) -> list[Example]:
    """YLT verses with Clear-Bible gold (WLC / SBLGNT sources). Evaluation only:
    YLT is not in the app's verses table."""
    gold, stats = build_gold("YLT", src, nt_source="SBLGNT", ot_source="WLC")
    log(f"  YLT gold: {stats}")
    out = []
    for key, (text, words, g) in gold.items():
        out.append(Example(key, [normalize(w, vocab) for w in words],
                           candidate_tokens(src.get(key, []), "BSB"), list(g), words))
    return out


def kjv_examples(conn, src: dict, vocab, zip_path, include_ordered=False):
    """KJV verses with gold from the eBible Strong's tags.

    Gold per word: {position} for a uniquely resolved tag (and, if requested,
    a tag resolved by order), frozenset() for an italic supplied word, None
    otherwise (untagged, ambiguous or unresolvable: not scored).
    Also returns the per-word resolution {key: [(status, positions)]}.
    """
    usfm = load_kjv_usfm(zip_path)
    out, resolution = [], {}
    for key, text in verse_texts(conn, "KJV").items():
        words = tappable_words(text)
        cands = candidate_tokens(src.get(key, []), "KJV")
        res = resolve_tags(project_to_text(usfm.get(key, []), text), cands)
        resolution[key] = res
        gold = []
        for status, positions in res:
            if status == UNIQUE or (include_ordered and status == ORDERED):
                gold.append(frozenset(positions))
            elif status == ADDED:
                gold.append(frozenset())
            else:
                gold.append(None)
        out.append(Example(key, [normalize(w, vocab) for w in words], cands, gold, words))
    return out, resolution
