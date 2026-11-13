"""Second-stage link chooser: attachment of function words + agreement of directions.

The HMM (model.py) gives, for each English word, a posterior over source words.
Most remaining errors are function words ("the", "of", "to", "and", pronouns,
auxiliaries) that land one word off, and repeated lemmas. This stage re-decides
each English word among a few candidates:

    - the HMM's top three choices (and "no link"),
    - the source word of the nearest content word to the left and to the right
      (attachment: "of" usually goes with the noun after it, "the" with its noun),

scoring each with a conditional logit over features that include the forward
posterior, the reverse-direction posterior P(this English word | source word)
(model.reverse_posteriors), whether the two directions agree, the attachment
relations, and the diagonal, most of them specific to the word's class
(each frequent function word has its own weights). It is trained out-of-fold on
BSB gold so its inputs look like those it sees at run time.
"""
import math
from collections import defaultdict

from .model import NO_LINK

WORD_CLASS = {w: w for w in (
    "the a of to and in for with from on by at that which who this not be there as so "
    "then but if when all or no what these those into upon").split()}
WORD_CLASS.update({w: "pron" for w in ("i", "you", "he", "she", "it", "we", "they")})
WORD_CLASS.update({w: "aux" for w in ("will", "shall", "may", "have", "do", "can",
                                      "would", "should", "might", "must", "let")})


def word_class(e: str) -> str:
    return WORD_CLASS.get(e, "content")


def is_function(e: str) -> bool:
    return e in WORD_CLASS


def _log(x: float) -> float:
    return math.log(max(x, 1e-6))


def candidates(model, english, sources, post, rev, top=3):
    """Per English word: [(source index or None, {feature: value})]."""
    I, J = len(sources), len(english)
    if I == 0:
        return [[(None, {"bias_null": 1.0})] for _ in english]
    best = [max(range(I + 1), key=lambda i: row[i]) for row in post]
    content_link = [best[j] if best[j] < I and not is_function(english[j]) else None
                    for j in range(J)]
    rev_best = [max(range(J), key=lambda j: rev[i][j]) for i in range(I)]
    lemma_count = defaultdict(int)
    for s in sources:
        lemma_count[s.strong] += 1
    out = []
    for j, e in enumerate(english):
        cls = word_class(e)
        left = next((content_link[k] for k in range(j - 1, -1, -1)
                     if content_link[k] is not None), None)
        right = next((content_link[k] for k in range(j + 1, J)
                      if content_link[k] is not None), None)
        row = post[j]
        order = sorted(range(I + 1), key=lambda i: -row[i])[:top]
        cand = list(dict.fromkeys(order + [x for x in (left, right) if x is not None]))
        feats = []
        for c in cand:
            if c == I:
                feats.append((None, {f"null|{cls}": 1.0, "null": 1.0,
                                     "lf": _log(row[I]), f"lf|{cls}": _log(row[I])}))
                continue
            lf, lr = _log(row[c]), _log(rev[c][j])
            f = {"lf": lf, f"lf|{cls}": lf, "lr": lr, f"lr|{cls}": lr,
                 "diag": abs((c + 0.5) / I - (j + 0.5) / J)}
            if c == best[j]:
                f[f"rank1|{cls}"] = 1.0
            if c == left:
                f[f"left|{cls}"] = 1.0
            if c == right:
                f[f"right|{cls}"] = 1.0
            rb = rev_best[c]
            if rb == j:
                f[f"agree|{cls}"] = 1.0
            elif all(best[k] == c for k in range(min(rb, j), max(rb, j) + 1)):
                f[f"agreespan|{cls}"] = 1.0
            if lemma_count[sources[c].strong] > 1:
                f[f"rep|{cls}"] = 1.0
                f["rep_lr"] = lr
            feats.append((c, f))
        out.append(feats)
    return out


class Reranker:
    def __init__(self, l2: float = 1e-4, epochs: int = 8, lr: float = 0.2):
        self.w: dict[str, float] = {}
        self.l2, self.epochs, self.lr = l2, epochs, lr

    def _scores(self, cand):
        w = self.w
        return [sum(w.get(k, 0.0) * v for k, v in f.items()) for _, f in cand]

    def probs(self, cand):
        sc = self._scores(cand)
        m = max(sc)
        ex = [math.exp(s - m) for s in sc]
        z = sum(ex)
        return [x / z for x in ex]

    def fit(self, data, log=print):
        """data: [(candidates for one word, set of indices into it that are correct)]"""
        g2 = defaultdict(lambda: 1e-8)
        for ep in range(self.epochs):
            ll = 0.0
            for cand, good in data:
                p = self.probs(cand)
                pg = sum(p[k] for k in good)
                ll += math.log(max(pg, 1e-12))
                grad = defaultdict(float)
                for k, (_, f) in enumerate(cand):
                    # d log sum_{good} p / d w = E_good[f] - E_all[f]
                    coef = (p[k] / pg if k in good else 0.0) - p[k]
                    if coef:
                        for name, v in f.items():
                            grad[name] += coef * v
                for name, gv in grad.items():
                    gv -= self.l2 * self.w.get(name, 0.0)
                    g2[name] += gv * gv
                    self.w[name] = self.w.get(name, 0.0) + self.lr * gv / math.sqrt(g2[name])
            log(f"  rerank epoch {ep + 1}: log-lik/word {ll / max(len(data), 1):.4f}")


def training_data(model, examples):
    """Out-of-fold examples -> reranker training rows (words whose gold is among candidates)."""
    data, covered, total = [], 0, 0
    for ex in examples:
        if not ex.sources:
            continue
        post = model.posteriors(ex.english, ex.sources)
        rev = model.reverse_posteriors(ex.english, ex.sources)
        I = len(ex.sources)
        for cand, g in zip(candidates(model, ex.english, ex.sources, post, rev), ex.gold):
            if g is None:
                continue
            gold_idx = {i for i, s in enumerate(ex.sources) if s.pos in g} if g else {I}
            good = {k for k, (c, _) in enumerate(cand)
                    if (c if c is not None else I) in gold_idx}
            total += 1
            if good:
                covered += 1
                data.append((cand, good))
    return data, covered, total


def align(model, reranker, english, sources, constraints=None):
    """[(position or None, confidence)] per English word, reranked.

    Words fixed by a constraint (a KJV tag, an italic word) keep the constrained
    HMM decision; the reranker decides the rest.
    """
    post = model.posteriors(english, sources, constraints)
    I = len(sources)
    if I == 0:
        return [(None, 1.0) for _ in english]
    rev = model.reverse_posteriors(english, sources)
    out = []
    for j, cand in enumerate(candidates(model, english, sources, post, rev)):
        c = constraints[j] if constraints else None
        if c is not None:
            row = post[j]
            b = max(range(I + 1), key=lambda i: row[i])
            out.append((None, row[b]) if (b == I or c == NO_LINK) else (sources[b].pos, row[b]))
            continue
        p = reranker.probs(cand)
        k = max(range(len(cand)), key=lambda x: p[x])
        idx = cand[k][0]
        out.append((None if idx is None else sources[idx].pos, p[k]))
    return out
