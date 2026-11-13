"""Alignment scoring: precision / recall / F1 / AER, calibration, error classes.

Gold per English word is a frozenset of source positions (several when the
gold links one English word to several source words), frozenset() when the
word has no source, or None when the word is not scored (e.g. KJV words with
no Strong's tag). A prediction is one source position or None.

Token-level scores (the main numbers):
    precision = correct links / predicted links          (over scored words)
    recall    = correct links / words that have a gold link
    a link is correct when the predicted position is in the gold set.
AER uses the standard definition with S = P = all gold (word, position)
pairs; because our table stores one link per English word, pair-level recall
is capped below 1 when gold has multi-source words (reported as `aer_cap`).
"""
from collections import Counter, defaultdict

_GENRES = {
    "narrative": ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
                  "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
                  "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther",
                  "Matthew", "Mark", "Luke", "John", "Acts"],
    "poetry": ["Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Lamentations"],
    "prophecy": ["Isaiah", "Jeremiah", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
                 "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai",
                 "Zechariah", "Malachi", "Revelation"],
    "epistle": ["Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
                "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
                "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
                "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude"],
}
BOOK_GENRE = {b: g for g, books in _GENRES.items() for b in books}
NT_BOOKS = set(_GENRES["epistle"]) | {"Matthew", "Mark", "Luke", "John", "Acts", "Revelation"}


def testament(book: str) -> str:
    return "NT" if book in NT_BOOKS else "OT"


class Score:
    def __init__(self):
        self.pred = 0          # predicted links on scored words
        self.correct = 0
        self.gold_words = 0    # scored words with >= 1 gold link
        self.gold_pairs = 0
        self.null_words = 0    # scored words whose gold is 'no source'
        self.null_kept = 0     # ... that we also left unlinked

    def add(self, gold, pred):
        if gold is None:
            return
        if gold:
            self.gold_words += 1
            self.gold_pairs += len(gold)
        else:
            self.null_words += 1
            if pred is None:
                self.null_kept += 1
        if pred is not None:
            self.pred += 1
            if pred in gold:
                self.correct += 1

    def merge(self, other):
        for k in vars(self):
            setattr(self, k, getattr(self, k) + getattr(other, k))

    def as_dict(self):
        p = self.correct / self.pred if self.pred else 0.0
        r = self.correct / self.gold_words if self.gold_words else 0.0
        f = 2 * p * r / (p + r) if p + r else 0.0
        aer = 1 - 2 * self.correct / (self.pred + self.gold_pairs) if self.pred + self.gold_pairs else 0.0
        return {
            "precision": p, "recall": r, "f1": f, "aer": aer,
            "aer_cap": 1 - 2 * self.gold_words / (self.gold_words + self.gold_pairs)
            if self.gold_pairs else 0.0,
            "null_precision": self.null_kept / self.null_words if self.null_words else None,
            "words": self.gold_words + self.null_words, "pred": self.pred,
        }


def score_examples(examples, predictions, threshold=0.0):
    """Return {'all': Score, ('OT'|'NT'): Score, genre: Score}.

    predictions[k] is a list of (pos, conf) per English word; links with
    conf < threshold count as 'no link'.
    """
    out = defaultdict(Score)
    for ex in examples:
        pred = predictions[ex.key]
        book = ex.key[0]
        for g, (pos, conf) in zip(ex.gold, pred):
            p = pos if (pos is not None and conf >= threshold) else None
            for k in ("all", testament(book), BOOK_GENRE.get(book, "?"),
                      f"{testament(book)}-{BOOK_GENRE.get(book, '?')}"):
                out[k].add(g, p)
    return out


def calibration(examples, predictions, bins=(0.0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.01)):
    """Stated confidence vs actual precision, over links on words with a gold set."""
    rows = []
    stats = [[0, 0, 0.0] for _ in range(len(bins) - 1)]
    for ex in examples:
        for g, (pos, conf) in zip(ex.gold, predictions[ex.key]):
            if g is None or pos is None:
                continue
            for b in range(len(bins) - 1):
                if bins[b] <= conf < bins[b + 1]:
                    s = stats[b]
                    s[0] += 1
                    s[1] += int(pos in g)
                    s[2] += conf
                    break
    for b, (n, c, cs) in enumerate(stats):
        rows.append({"bin": f"{bins[b]:.2f}-{min(bins[b + 1], 1.0):.2f}", "links": n,
                     "mean_conf": cs / n if n else None, "accuracy": c / n if n else None})
    return rows


def threshold_curve(examples, predictions, thresholds=(0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)):
    rows = []
    for t in thresholds:
        d = score_examples(examples, predictions, t)["all"].as_dict()
        rows.append({"threshold": t, **{k: d[k] for k in ("precision", "recall", "f1", "pred")}})
    return rows


def error_classes(examples, predictions, source_index, limit=6):
    """Bucket wrong links and misses into classes, with examples."""
    counts = Counter()
    samples = defaultdict(list)
    for ex in examples:
        toks = source_index(ex.key)
        for j, (g, (pos, conf)) in enumerate(zip(ex.gold, predictions[ex.key])):
            if g is None:
                continue
            word = ex.words[j] if ex.words else ex.english[j]
            if pos is not None and g and pos in g:
                continue
            if pos is None and not g:
                continue
            if pos is None:
                cls = "missed (no link, gold has one)"
            elif not g:
                cls = "spurious (link, gold has none)"
            else:
                pt, gt = toks.get(pos), toks.get(min(g))
                if pt and gt and pt.strong and pt.strong == gt.strong:
                    cls = "same lemma, wrong occurrence"
                elif min(abs(pos - x) for x in g) == 1:
                    cls = "adjacent source word"
                else:
                    cls = "wrong source word"
            counts[cls] += 1
            if len(samples[cls]) < limit:
                gtxt = ",".join(f"{toks[x].text}#{x}" for x in sorted(g) if x in toks) or "-"
                ptxt = f"{toks[pos].text}#{pos}" if pos is not None and pos in toks else "-"
                samples[cls].append(f"{ex.key[0]} {ex.key[1]}:{ex.key[2]} '{word}' "
                                    f"pred {ptxt} ({conf:.2f}) gold {gtxt}")
    return counts, samples
