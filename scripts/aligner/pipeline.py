"""Training sets, calibration and database writers for the alignment build."""
import bisect
import sqlite3
from dataclasses import replace

from .data import (bsb_examples, flag_suspect_gold, implausible_links, kjv_examples,
                   modern_vocab, plain_examples, split_of)
from .kjv import ADDED, AMBIGUOUS, ORDERED, UNIQUE
from .model import NO_LINK, Aligner, Params
from .rerank import Reranker, is_function
from .rerank import align as rerank_align
from .rerank import training_data as rerank_training_data
from .sources import load_source_tokens
from .text import clean_word

# english_word_alignments.method
METHOD_GOLD = 0    # human alignment (Clear-Bible, BSB)
METHOD_TAGGED = 1  # resolved from a human Strong's tag (KJV)
METHOD_MODEL = 2   # statistical aligner

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS english_word_alignments (
    translation_id TEXT NOT NULL,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    english_word_position INTEGER NOT NULL,  -- 1-based tappable-word index (see aligner/text.py)
    english_word TEXT NOT NULL,
    original_word_position INTEGER,         -- word_alignments.word_position, same verse
    confidence REAL DEFAULT 1.0,            -- calibrated: about P(link is right)
    method INTEGER NOT NULL DEFAULT 0,      -- 0 human alignment, 1 Strong's tag, 2 aligner
    PRIMARY KEY (translation_id, book, chapter, verse, english_word_position)
) WITHOUT ROWID
"""


class Context:
    """Everything the steps share: DB, source tokens, vocabulary, BSB gold."""

    def __init__(self, db_path, kjv_zip, log=print):
        self.conn = sqlite3.connect(db_path)
        self.log = log
        self.kjv_zip = kjv_zip
        log("Loading source tokens...")
        self.src = load_source_tokens()
        self.vocab = modern_vocab(self.conn)
        log("Building BSB gold from Clear-Bible...")
        self.bsb = bsb_examples(self.conn, self.src, self.vocab, log=log)
        self._suspect = None
        self._kjv = None

    @property
    def suspect(self) -> set:
        if self._suspect is None:
            self.log("Flagging shifted gold verses...")
            m = Aligner(Params())
            m.fit(self.bsb, self.vocab, log=lambda *a: None)
            self._suspect = flag_suspect_gold(self.bsb, m)
            self.log(f"  {len(self._suspect)} of {len(self.bsb)} BSB verses have shifted gold")
        return self._suspect

    @property
    def kjv(self):
        if self._kjv is None:
            self._kjv = kjv_examples(self.conn, self.src, self.vocab, self.kjv_zip)
        return self._kjv

    def bsb_clean(self, splits=("train", "dev", "test")):
        return [e for e in self.bsb if e.key not in self.suspect and split_of(e.key[0]) in splits]

    def kjv_training(self, splits=("train", "dev", "test")):
        """KJV tag gold for training: unique tags only, italic words unscored."""
        exs, _ = self.kjv
        return [replace(e, gold=[g if g else None for g in e.gold])
                for e in exs if split_of(e.key[0]) in splits]


def train(ctx: Context, splits, with_kjv: bool, params: Params | None = None) -> Aligner:
    bsb = ctx.bsb_clean(splits)
    examples = bsb + (ctx.kjv_training(splits) if with_kjv else [])
    m = Aligner(params or Params())
    m.fit(examples, ctx.vocab, log=ctx.log, jump_examples=bsb)
    return m


def self_train(ctx: Context, base: Aligner, splits, translation: str,
               tau: float = 0.7, params: Params | None = None) -> Aligner:
    """One round of self-training on a translation's own (unlabeled) text.

    Links the base model is confident about (posterior >= tau) become extra
    training pairs, which teaches the emission tables that translation's
    vocabulary (archaic forms, spelling of names). No gold of that translation
    is used. Jumps stay estimated from BSB gold only.
    """
    pseudo = []
    for ex in plain_examples(ctx.conn, translation, ctx.src, ctx.vocab):
        links = base.align(ex.english, ex.sources)
        pseudo.append(replace(ex, gold=[frozenset({p}) if p is not None and c >= tau else None
                                        for p, c in links]))
    bsb = ctx.bsb_clean(splits)
    m = Aligner(params or base.p)
    m.fit(bsb + pseudo, ctx.vocab, log=ctx.log, jump_examples=bsb)
    return m


# --- calibration ----------------------------------------------------------------------

class Calibrator:
    """Isotonic (pool-adjacent-violators) map from raw posterior to accuracy."""

    def __init__(self, points=None):
        self.points = points or [(0.0, 0.0), (1.0, 1.0)]

    @classmethod
    def fit(cls, pairs):
        """pairs: [(raw confidence, 1 if correct else 0)]"""
        pairs = sorted(pairs)
        blocks = []  # [sum_y, n, max_x]
        for x, y in pairs:
            blocks.append([y, 1, x])
            while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] >= blocks[-1][0] / blocks[-1][1]:
                y2, n2, x2 = blocks.pop()
                blocks[-1][0] += y2
                blocks[-1][1] += n2
                blocks[-1][2] = x2
        pts = [(b[2], b[0] / b[1]) for b in blocks]
        return cls([(0.0, pts[0][1])] + pts + [(1.0, pts[-1][1])])

    def __call__(self, x: float) -> float:
        xs = [p[0] for p in self.points]
        i = bisect.bisect_left(xs, x)
        if i <= 0:
            return self.points[0][1]
        if i >= len(xs):
            return self.points[-1][1]
        (x0, y0), (x1, y1) = self.points[i - 1], self.points[i]
        return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)


class ClassCalibrator:
    """Separate isotonic maps for function words and content words."""

    def __init__(self, function: Calibrator, content: Calibrator):
        self.function, self.content = function, content

    def __call__(self, conf: float, english_key: str) -> float:
        return (self.function if is_function(english_key) else self.content)(conf)


class Predictor:
    """HMM (+ optional reranker) + calibration: what writes rows and gets evaluated."""

    def __init__(self, model: Aligner, reranker: Reranker | None = None, calib=None):
        self.model, self.reranker, self.calib = model, reranker, calib

    def raw(self, english, sources, constraints=None):
        if self.reranker is None:
            return self.model.align(english, sources, constraints)
        return rerank_align(self.model, self.reranker, english, sources, constraints)

    def align(self, english, sources, constraints=None):
        out = self.raw(english, sources, constraints)
        if self.calib is None:
            return out
        return [(p, self.calib(c, e)) for e, (p, c) in zip(english, out)]


def fit_calibrator(pred: Predictor, examples) -> ClassCalibrator:
    """Isotonic maps fitted on examples the predictor was not trained on."""
    pairs = {True: [], False: []}
    for ex in examples:
        for e, g, (pos, conf) in zip(ex.english, ex.gold, pred.raw(ex.english, ex.sources)):
            if g and pos is not None:
                pairs[is_function(e)].append((conf, 1 if pos in g else 0))
    return ClassCalibrator(Calibrator.fit(pairs[True]), Calibrator.fit(pairs[False]))


def train_reranker(ctx: Context, splits) -> Reranker:
    """Out-of-fold: two HMMs on alternate halves of the books, each decodes the other half."""
    exs = ctx.bsb_clean(splits)
    books = sorted({e.key[0] for e in exs})
    halves = [set(books[0::2]), set(books[1::2])]
    data = []
    for k in (0, 1):
        m = Aligner(Params())
        m.fit([e for e in exs if e.key[0] in halves[k]], ctx.vocab, log=lambda *a: None)
        other = [e for e in exs if e.key[0] in halves[1 - k]][::2]
        d, covered, total = rerank_training_data(m, other)
        ctx.log(f"  rerank fold {k}: {total} words, gold among candidates {covered / total:.3f}")
        data.extend(d)
    rr = Reranker()
    rr.fit(data, log=ctx.log)
    return rr


# --- writing --------------------------------------------------------------------------

def ensure_table(conn):
    """Create the alignment table; migrate the old rowid layout without losing rows."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(english_word_alignments)")]
    if cols and ("id" in cols or "method" not in cols):
        conn.execute("ALTER TABLE english_word_alignments RENAME TO _ewa_old")
        conn.execute(TABLE_SQL)
        conn.execute("""
            INSERT OR REPLACE INTO english_word_alignments
            (translation_id, book, chapter, verse, english_word_position, english_word,
             original_word_position, confidence, method)
            SELECT translation_id, book, chapter, verse, english_word_position, english_word,
                   original_word_position, confidence, 0 FROM _ewa_old
        """)
        conn.execute("DROP TABLE _ewa_old")
    else:
        conn.execute(TABLE_SQL)
    conn.commit()


def write_rows(conn, translation: str, rows):
    """Replace all rows of one translation. rows: (key, pos, word, orig_pos, conf, method)."""
    ensure_table(conn)
    conn.execute("DELETE FROM english_word_alignments WHERE translation_id = ?", (translation,))
    conn.executemany("""
        INSERT INTO english_word_alignments
        (translation_id, book, chapter, verse, english_word_position, english_word,
         original_word_position, confidence, method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ((translation, k[0], k[1], k[2], pos, clean_word(word), orig, round(conf, 3), method)
          for k, pos, word, orig, conf, method in rows))
    conn.commit()


def bsb_rows(ctx: Context, pred: Predictor):
    """Human gold where it is sound; the aligner for verses with shifted gold."""
    model = pred.model
    for ex in ctx.bsb:
        if ex.key in ctx.suspect:
            for j, (pos, conf) in enumerate(pred.align(ex.english, ex.sources), 1):
                if pos is not None:
                    yield ex.key, j, ex.words[j - 1], pos, conf, METHOD_MODEL
            continue
        by_pos = {t.pos: t for t in ex.sources}
        bad, _ = implausible_links(ex, model)
        if bad:
            # Isolated gold errors (Genesis 1:3 links the second 'light' to
            # 'and there was'): take the aligner's link for those words only.
            predicted = pred.align(ex.english, ex.sources)
        for j, (e, g) in enumerate(zip(ex.english, ex.gold), 1):
            if g and (j - 1) in bad:
                pos, conf = predicted[j - 1]
                # Only when the aligner is itself fairly sure; otherwise the gold
                # is more often a legitimate idiom ('Naomi' for 'the two of them').
                if pos is not None and conf >= 0.5:
                    yield ex.key, j, ex.words[j - 1], pos, conf, METHOD_MODEL
                    continue
            if g:
                # One row per English word. When gold links it to several source
                # words ('the evil one' -> article + adjective), keep the one the
                # model finds most likely to produce this word, ties to the first.
                pos = max(sorted(g), key=lambda p: model.emission(e, by_pos[p])
                          if p in by_pos else -1.0)
                yield ex.key, j, ex.words[j - 1], pos, 1.0, METHOD_GOLD


TAG_CONFIDENCE = {UNIQUE: 1.0, ORDERED: 0.9}


def kjv_constraints(resolution):
    out = []
    for status, positions in resolution:
        if status in (UNIQUE, ORDERED, AMBIGUOUS):
            out.append(frozenset(positions))
        elif status == ADDED:
            out.append(NO_LINK)
        else:
            out.append(None)
    return out


def kjv_rows(ctx: Context, pred: Predictor, stats=None):
    exs, resolution = ctx.kjv
    for ex in exs:
        res = resolution[ex.key]
        links = pred.align(ex.english, ex.sources, kjv_constraints(res))
        for j, ((pos, conf), (status, _)) in enumerate(zip(links, res), 1):
            if stats is not None:
                stats[(status, pos is not None)] = stats.get((status, pos is not None), 0) + 1
            if pos is None:
                continue
            if status in TAG_CONFIDENCE:
                yield ex.key, j, ex.words[j - 1], pos, TAG_CONFIDENCE[status], METHOD_TAGGED
            elif status == AMBIGUOUS:
                yield ex.key, j, ex.words[j - 1], pos, conf, METHOD_TAGGED
            else:
                yield ex.key, j, ex.words[j - 1], pos, conf, METHOD_MODEL


def model_rows(ctx: Context, translation: str, pred: Predictor):
    for ex in plain_examples(ctx.conn, translation, ctx.src, ctx.vocab):
        for j, (pos, conf) in enumerate(pred.align(ex.english, ex.sources), 1):
            if pos is not None:
                yield ex.key, j, ex.words[j - 1], pos, conf, METHOD_MODEL
