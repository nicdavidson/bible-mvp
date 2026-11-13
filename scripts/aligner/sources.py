"""Source-language (Hebrew/Greek) tokens per verse, keyed exactly like `word_alignments`.

Tokens are read from the STEPBible TAHOT/TAGNT files with the same reference
parsing and renumbering as scripts/import_stepbible_alignment.py, so
(book, chapter, verse, position) here is the row the API joins to. We read the
files rather than the table because the model needs the full dStrongs
(prefix and suffix morphemes), which the table does not keep.
"""
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from import_stepbible_alignment import (  # noqa: E402
    BOOK_MAP,
    REF_RE,
    clean_gloss,
    extract_primary_strong,
    renumber_split_verses,
)

from .text import normalize, strip_diacritics  # noqa: E402

ALIGNMENT_DIR = SCRIPTS_DIR.parent / "data" / "alignment"

ALT_REF_RE = re.compile(r"[A-Za-z0-9]+\.\d+\.\d+([(\[{])(\d+)\.(\d+)[)\]}]#")

# Greek edition a translation's NT follows (TAGNT editions column).
# None = no filter. Hebrew has no edition column; all translations use the MT.
TRANSLATION_EDITION = {
    "BSB": "SBL",   # SBLGNT
    "KJV": "TR",    # Scrivener 1894 Textus Receptus
    "WEB": "Byz",   # Robinson-Pierpont Byzantine
    "YLT": "TR",
    "ASV": "WH",    # ASV 1901 follows Westcott-Hort closely
}

# Hebrew dStrongs that are punctuation, not words.
_HEB_PUNCT = {"H9014", "H9015", "H9016", "H9017", "H9018", "H9019"}
_DSTRONG_RE = re.compile(r"([HG])(\d{4})([A-Za-z]?)")


@dataclass
class SourceToken:
    pos: int                     # word_alignments.word_position
    text: str                    # original-language surface form
    strong: str | None           # base Strong's, 'H7225' / 'G2316' (as in word_alignments)
    morphemes: list = field(default_factory=list)  # Hebrew function morphemes ('H9003', ...)
    grammar: str = ""
    gloss: str = ""
    editions: str | None = None
    word_type: str | None = None
    alt_ref: tuple | None = None  # (chapter, verse) of the bracketed alternative reference
    alt_kind: str | None = None   # '(', '[' or '{' for an alternative reference

    @property
    def lemma(self) -> str | None:
        return self.strong

    def in_edition(self, edition: str | None) -> bool:
        """Exact edition name. TAGNT lists editions that have the word in a different
        order with the displacement ('TR«3': in the TR, 3 words earlier; 'Byz»1': one
        later); the word is in that edition, so it counts."""
        if edition is None or self.editions is None:
            return True
        return edition in {e.split("«")[0].split("»")[0] for e in self.editions.split("+")}


def _base_strong(code: str) -> str:
    m = _DSTRONG_RE.match(code)
    return f"{m.group(1)}{m.group(2)}" if m else code


def _hebrew_morphemes(dstrongs: str) -> list[str]:
    """Function morphemes (prefixes, suffixes) of a Hebrew word, excluding the root."""
    out = []
    for piece in re.split(r"[/\\]", dstrongs or ""):
        piece = piece.strip()
        if not piece or piece.startswith("{"):
            continue
        code = _base_strong(piece)
        if code.startswith("H9") and code not in _HEB_PUNCT:
            out.append(code)
    return out


def _iter_rows(path: Path):
    is_greek = "TAGNT" in path.name
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line[:1].isalnum():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            m = REF_RE.match(parts[0])
            if not m:
                continue
            book = BOOK_MAP.get(m.group(1))
            if not book:
                continue
            chapter, verse, pos = int(m.group(2)), int(m.group(3)), int(m.group(4))
            word_type = m.group(5).strip() or None
            alt = ALT_REF_RE.match(parts[0])
            alt_kind = alt.group(1) if alt else None
            alt_ref = (int(alt.group(2)), int(alt.group(3))) if alt else None
            if is_greek:
                text = parts[1].split("(")[0].strip()
                gloss = clean_gloss(parts[2]) if len(parts) > 2 else None
                dstrongs = parts[3]
                grammar = dstrongs.split("=")[1] if "=" in dstrongs else ""
                editions = parts[5].strip() if len(parts) > 5 else None
                morphemes = []
            else:
                text = parts[1]
                gloss = clean_gloss(parts[3]) if len(parts) > 3 else None
                dstrongs = parts[4] if len(parts) > 4 else ""
                grammar = parts[5] if len(parts) > 5 else ""
                editions = None
                morphemes = _hebrew_morphemes(dstrongs)
            strong = extract_primary_strong(dstrongs, is_greek=is_greek)
            if not gloss and not strong:
                continue  # the importer skips these too
            yield (book, chapter, verse, pos, text, strong, morphemes, grammar or "",
                   gloss or "", editions, word_type, alt_ref, alt_kind)


def load_source_tokens(alignment_dir: Path = ALIGNMENT_DIR, books=None) -> dict:
    """Return {(book, chapter, verse): [SourceToken, ...]} in position order."""
    verses: dict = {}
    for path in sorted(alignment_dir.glob("TA[HG][O,N]T_*.txt")):
        rows = list(_iter_rows(path))
        if books is not None:
            rows = [r for r in rows if r[0] in books]
        for r in renumber_split_verses(rows):
            (book, chapter, verse, pos, text, strong, morphemes, grammar, gloss,
             editions, word_type, alt_ref, alt_kind) = r
            verses.setdefault((book, chapter, verse), []).append(SourceToken(
                pos=pos, text=text, strong=_pad(strong), morphemes=morphemes,
                grammar=grammar, gloss=gloss, editions=editions, word_type=word_type,
                alt_ref=alt_ref, alt_kind=alt_kind,
            ))
    for toks in verses.values():
        toks.sort(key=lambda t: t.pos)
    return verses


def _pad(strong: str | None) -> str | None:
    """'H430' -> 'H0430' (word_alignments stores 4-digit numbers)."""
    if not strong:
        return strong
    return strong[0] + strong[1:].zfill(4)


def candidate_tokens(tokens: list, translation: str) -> list:
    """Source tokens a translation can be aligned to: its Greek edition only, and no
    LXX-reconstructed Hebrew ('X' rows are not in the Masoretic Text)."""
    edition = TRANSLATION_EDITION.get(translation)
    return [t for t in tokens
            if t.in_edition(edition) and not (t.word_type or "").startswith("X")]


# --- model features -----------------------------------------------------------

def _hebrew_grammar_features(grammar: str) -> list[str]:
    feats = []
    segs = grammar.split("/") if grammar else []
    for i, seg in enumerate(segs):
        if i == 0 and seg[:1] in ("H", "A"):
            seg = seg[1:]
        if not seg:
            continue
        if seg[0] == "V" and len(seg) >= 3:
            conj = seg[2]
            feats.append(f"hv:{conj}")
            pgn = seg[3:6]
            if len(pgn) == 3 and pgn[0] in "123":
                feats.append(f"hp:{pgn}")
        elif seg[0] in "NA" and len(seg) >= 5 and seg[-1] == "c":
            feats.append("hn:construct")
        elif seg[0] == "S" and len(seg) >= 2 and seg[1] in "pd":
            feats.append(f"hs:{seg[:5]}")
    return feats


def _greek_grammar_features(grammar: str) -> list[str]:
    if not grammar:
        return []
    parts = grammar.split("-")
    pos = parts[0]
    feats = []
    if pos == "V" and len(parts) >= 2:
        tvm = parts[1]
        if len(tvm) >= 3:
            tense, voice, mood = tvm[0], tvm[1], tvm[2]
            feats.append(f"gt:{tense}{mood}")
            feats.append(f"gv:{voice}")
            if len(parts) >= 3 and parts[2][:1] in "123":
                feats.append(f"gp:{parts[2][:2]}")
    elif len(parts) >= 2 and parts[1][:1] in "NGDAV":
        feats.append(f"gc:{parts[1][0]}")
    return feats


def token_features(tok: SourceToken) -> list[str]:
    """Feature ids that may 'emit' an English word. The lemma comes first."""
    feats = []
    if tok.strong:
        feats.append("L:" + tok.strong)
    feats.extend("M:" + m for m in tok.morphemes)
    if tok.strong and tok.strong.startswith("H"):
        feats.extend(_hebrew_grammar_features(tok.grammar))
    else:
        feats.extend(_greek_grammar_features(tok.grammar))
    return feats


def gloss_keys(tok: SourceToken, vocab=None) -> set[str]:
    """Normalized words of the STEPBible gloss for this token."""
    out = set()
    for w in re.findall(r"[A-Za-z']+", tok.gloss or ""):
        n = normalize(w, vocab)
        if n:
            out.add(n)
    return out


def surface_key(text: str) -> str:
    """Letters only, no points/accents: used to match tokens across editions."""
    return strip_diacritics(text)
