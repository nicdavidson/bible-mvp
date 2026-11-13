"""Statistical word aligner: English word -> source token (or none), with a confidence.

Model (per verse, each English word chosen independently given the verse):

    P(a_j = i | e_j)  proportional to  p(e_j | s_i) * prior(i | j)        i = 1..I
    P(a_j = NULL | e_j) proportional to  p0 * p(e_j | NULL)

Emission p(e | s) is a mixture over the source token's features:
    lemma (Strong's), Hebrew function morphemes (prefix/suffix dStrongs),
    grammar (Hebrew verb person/conjugation, construct state, Greek case,
    tense/mood, person), the STEPBible gloss of that token (identity match on
    normalized English), and a uniform floor.
Feature tables p(e | f) and the mixture weights are estimated by EM on gold
links (which feature 'explains' each gold English word is latent).

Prior: a fast_align-style diagonal term exp(-lambda * |i/I - j/J|), plus a
second pass that rewards a link agreeing with its neighbours' links
(English phrases translating one source word, and runs of source order).

The confidence stored for a link is its posterior after the second pass.
"""
import math
from collections import defaultdict
from dataclasses import dataclass, field

from .sources import gloss_keys, token_features

NO_LINK = "no-link"  # constraint: this English word has no source word

FEATURE_TYPES = ("L", "M", "hv", "hp", "hn", "hs", "gt", "gv", "gp", "gc", "W", "U")


def _ftype(f: str) -> str:
    return f.split(":", 1)[0]


@dataclass
class Example:
    """One verse: normalized English keys, candidate source tokens, gold (optional)."""
    key: tuple
    english: list            # normalized English keys, one per tappable word
    sources: list            # SourceToken list (edition-filtered)
    gold: list | None = None  # per English word: frozenset(positions) / frozenset() = none / None = unscored
    words: list = field(default_factory=list)  # surface forms (for reports)


@dataclass
class Params:
    lam: float = 4.0          # diagonal prior sharpness
    p0: float = 0.03          # prior probability of no link
    delta: float = 0.02       # add-delta smoothing for feature tables
    neighbour: float = 1.5    # weight of the neighbour-agreement pass (0 = off; diag only)
    em_iters: int = 6
    decoder: str = "hmm"      # 'hmm' (jump model, forward-backward) or 'diag'
    diag_weight: float = 0.5  # hmm: exponent on the diagonal prior mixed into emissions
    max_jump: int = 12        # hmm: jumps beyond +-max_jump share one bucket
    jump_classes: int = 80    # hmm: the N most frequent English words get their own jump model
    jump_backoff: float = 20.0


class Aligner:
    def __init__(self, params: Params | None = None):
        self.p = params or Params()
        self.table: dict[str, dict[str, float]] = {}   # feature -> {english: prob}
        self.null: dict[str, float] = {}
        self.weights: dict[str, float] = {t: 1.0 / len(FEATURE_TYPES) for t in FEATURE_TYPES}
        self.vocab_size = 1
        self._feat_cache: dict[int, tuple] = {}
        self.jumps: dict[str, dict[int, float]] = {}   # 'OT'/'NT' -> {jump: prob}
        self.starts: dict[str, list[float]] = {}       # 'OT'/'NT' -> P(first link in decile)

    # --- features --------------------------------------------------------------------
    def _features(self, tok) -> tuple:
        cached = self._feat_cache.get(id(tok))
        if cached is None or cached[0] is not tok:
            cached = (tok, token_features(tok), gloss_keys(tok, getattr(self, "vocab", None)))
            self._feat_cache[id(tok)] = cached
        return cached[1], cached[2]

    def _components(self, e: str, tok):
        """[(feature_or_type, weighted_prob)] for emission of e by tok."""
        feats, gloss = self._features(tok)
        by_type = defaultdict(list)
        for f in feats:
            by_type[_ftype(f)].append(f)
        out = []
        V = self.vocab_size
        for t, fs in by_type.items():
            w = self.weights.get(t, 0.0) / len(fs)
            for f in fs:
                tab = self.table.get(f)
                if tab is None:
                    prob = 1.0 / V
                else:
                    prob = tab.get(e, tab.get("\0", 1.0 / V))
                out.append((f, w * prob))
        if gloss:
            out.append(("W", self.weights["W"] * (1.0 / len(gloss) if e in gloss else 0.0)))
        out.append(("U", self.weights["U"] / V))
        return out

    def reverse_posteriors(self, english: list, sources: list) -> list[list[float]]:
        """Reverse direction: for each source word, P(English word j | source), j = 0..J-1
        plus a last entry for 'no English word'. Uses p(s|e) ~ p(e|s) / p(e) (Bayes on
        the same lexical table) with the diagonal prior, so frequent English words
        ('the', 'of') do not win every source word."""
        I, J = len(sources), len(english)
        if J == 0:
            return [[1.0] for _ in sources]
        lam = self.p.lam
        ep = getattr(self, "eprob", {})
        floor = ep.get("\0", 1e-6)
        out = []
        for i, s in enumerate(sources):
            row = []
            for j, e in enumerate(english):
                pr = math.exp(-lam * abs((i + 0.5) / I - (j + 0.5) / J))
                row.append(self.emission(e, s) / ep.get(e, floor) * pr)
            row.append(sum(row) * 0.05 + 1e-12)
            z = sum(row)
            out.append([x / z for x in row])
        return out

    def emission(self, e: str, tok) -> float:
        return sum(p for _, p in self._components(e, tok))

    # --- training --------------------------------------------------------------------
    def fit(self, examples: list[Example], vocab=None, log=print, jump_examples=None):
        """Estimate emission tables from gold links; jumps from `jump_examples`
        (default: the same examples). Gold that covers only some words (KJV tags)
        should not be used for jumps."""
        self.vocab = vocab
        pairs = []          # (english, token, weight)
        null_counts = defaultdict(float)
        evocab = set()
        for ex in examples:
            by_pos = {t.pos: t for t in ex.sources}
            for e, g in zip(ex.english, ex.gold or []):
                if g is None or not e:
                    continue
                evocab.add(e)
                if not g:
                    null_counts[e] += 1
                    continue
                toks = [by_pos[p] for p in g if p in by_pos]
                for t in toks:
                    pairs.append((e, t, 1.0 / len(toks)))
        self.vocab_size = len(evocab) + 1
        efreq = defaultdict(float)
        for e, _, c in pairs:
            efreq[e] += c
        tot = sum(efreq.values()) + self.vocab_size
        self.eprob = {e: (c + 1) / tot for e, c in efreq.items()}
        self.eprob["\0"] = 1 / tot
        total_null = sum(null_counts.values())
        self.null = {e: (c + 0.1) / (total_null + 0.1 * self.vocab_size)
                     for e, c in null_counts.items()}
        self.null["\0"] = 0.1 / (total_null + 0.1 * self.vocab_size)
        log(f"  training pairs: {len(pairs):,}  english types: {len(evocab):,}")

        # init: every feature gets full credit for every gold word it co-occurs with
        counts = defaultdict(lambda: defaultdict(float))
        for e, t, c in pairs:
            feats, _ = self._features(t)
            for f in feats:
                counts[f][e] += c
        self._normalize(counts)
        for it in range(self.p.em_iters):
            counts = defaultdict(lambda: defaultdict(float))
            type_mass = defaultdict(float)
            ll = 0.0
            for e, t, c in pairs:
                comps = self._components(e, t)
                z = sum(p for _, p in comps)
                ll += c * math.log(z)
                for f, p in comps:
                    r = c * p / z
                    t_ = _ftype(f) if ":" in f else f
                    type_mass[t_] += r
                    if ":" in f:
                        counts[f][e] += r
            self._normalize(counts)
            mass = sum(type_mass.values())
            self.weights = {t: max(type_mass.get(t, 0.0) / mass, 1e-4) for t in FEATURE_TYPES}
            log(f"  EM {it + 1}: log-lik/pair {ll / max(len(pairs), 1):.4f}  weights " +
                " ".join(f"{t}={w:.3f}" for t, w in self.weights.items() if w > 0.005))
        self._fit_jumps(jump_examples if jump_examples is not None else examples)
        if total_null:
            words = sum(1 for ex in examples for g in (ex.gold or []) if g is not None)
            log(f"  gold no-link rate {total_null / max(words, 1):.4f}")

    def _jump_class(self, e: str) -> str:
        return e if e in self.jump_words else "*"

    def _fit_jumps(self, examples):
        """Jump distribution between consecutive linked English words, by testament
        and by the earlier English word (for frequent words: 'the' and 'of' attach
        to what follows, pronouns and auxiliaries to a verb nearby...)."""
        K = self.p.max_jump
        freq = defaultdict(int)
        for ex in examples:
            for e, g in zip(ex.english, ex.gold or []):
                if g:
                    freq[e] += 1
        self.jump_words = set(sorted(freq, key=freq.get, reverse=True)[: self.p.jump_classes])
        counts = defaultdict(lambda: defaultdict(float))
        starts = {"OT": [1.0] * 10, "NT": [1.0] * 10}
        for ex in examples:
            if not ex.gold or not ex.sources:
                continue
            tes = "OT" if ex.sources[0].strong and ex.sources[0].strong.startswith("H") else "NT"
            index = {t.pos: i for i, t in enumerate(ex.sources)}
            prev = None
            prev_e = None
            for e, g in zip(ex.english, ex.gold):
                if not g:
                    continue
                idx = [index[p] for p in g if p in index]
                if not idx:
                    continue
                if prev is None:
                    cur = min(idx)
                    starts[tes][min(9, cur * 10 // len(ex.sources))] += 1
                else:
                    cur = min(idx, key=lambda i: abs(i - prev))
                    d = max(-K - 1, min(K + 1, cur - prev))
                    counts[(tes, "*")][d] += 1
                    if prev_e in self.jump_words:
                        counts[(tes, prev_e)][d] += 1
                prev = cur
                prev_e = e
        rng = range(-K - 1, K + 2)
        self.jumps = {}
        for tes in ("OT", "NT"):
            c = counts[(tes, "*")]
            tot = sum(c.values()) + len(rng) * 0.5
            glob = {d: (c.get(d, 0.0) + 0.5) / tot for d in rng}
            self.jumps[(tes, "*")] = glob
            a = self.p.jump_backoff
            for w in self.jump_words:
                cw = counts.get((tes, w))
                if not cw:
                    continue
                n = sum(cw.values())
                self.jumps[(tes, w)] = {d: (cw.get(d, 0.0) + a * glob[d]) / (n + a) for d in rng}
            z = sum(starts[tes])
            self.starts[tes] = [x / z for x in starts[tes]]

    def _normalize(self, counts):
        V, d = self.vocab_size, self.p.delta
        table = {}
        for f, row in counts.items():
            tot = sum(row.values())
            denom = tot + d * V
            tab = {e: (c + d) / denom for e, c in row.items() if c > 1e-3}
            tab["\0"] = d / denom
            table[f] = tab
        self.table = table

    # --- decoding --------------------------------------------------------------------
    def posteriors(self, english: list, sources: list, constraints=None) -> list[list[float]]:
        """Per English word: [P(source 0..I-1), P(NULL)].

        constraints (HMM only): per English word None (free), NO_LINK (must have
        no source) or a collection of allowed source positions.
        """
        I = len(sources)
        if I == 0:
            return [[1.0] for _ in english]
        if self.p.decoder == "hmm" and self.jumps:
            return self._posteriors_hmm(english, sources, constraints)
        return self._posteriors_diag(english, sources)

    def _posteriors_hmm(self, english: list, sources: list, constraints=None):
        """First-order HMM over source positions with a 'null, remember i' state
        per position (Och & Ney), forward-backward marginals."""
        I, J = len(sources), len(english)
        tes = "OT" if sources[0].strong and sources[0].strong.startswith("H") else "NT"
        K = self.p.max_jump
        p0 = self.p.p0
        lam, gam = self.p.lam, self.p.diag_weight
        emis = []
        for j, e in enumerate(english):
            row = [self.emission(e, s) for s in sources]
            if gam:
                row = [x * math.exp(-gam * lam * abs((i + 0.5) / I - (j + 0.5) / J))
                       for i, x in enumerate(row)]
            emis.append(row)
        nul = [self.null.get(e, self.null["\0"]) for e in english]
        if constraints:
            for j, c in enumerate(constraints):
                if c is None:
                    continue
                if c == NO_LINK:
                    emis[j] = [0.0] * I
                    nul[j] = nul[j] or 1e-9
                else:
                    allowed = {i for i, s in enumerate(sources) if s.pos in c}
                    if allowed:
                        emis[j] = [x if i in allowed else 0.0 for i, x in enumerate(emis[j])]
                        if not any(emis[j]):
                            emis[j] = [1e-9 if i in allowed else 0.0 for i in range(I)]
                        nul[j] = 0.0
        trans_by_class = {}

        def trans_for(e):
            cls = self._jump_class(e)
            if (tes, cls) not in self.jumps:
                cls = "*"
            m = trans_by_class.get(cls)
            if m is None:
                jumps = self.jumps[(tes, cls)]
                far = jumps[K + 1]
                m = []
                for a in range(I):
                    row = [jumps.get(b - a, far) for b in range(I)]
                    z = sum(row)
                    m.append([(1 - p0) * x / z for x in row])
                trans_by_class[cls] = m
            return m
        st = self.starts[tes]
        init = [st[min(9, i * 10 // I)] for i in range(I)]
        z = sum(init)
        init = [x / z for x in init]

        # forward
        fr, fn = [], []
        ar = [(1 - p0) * init[i] * emis[0][i] for i in range(I)]
        an = [p0 * init[i] * nul[0] for i in range(I)]
        c = sum(ar) + sum(an)
        ar = [x / c for x in ar]
        an = [x / c for x in an]
        fr.append(ar)
        fn.append(an)
        for j in range(1, J):
            prev = [ar[i] + an[i] for i in range(I)]
            em = emis[j]
            trans = trans_for(english[j - 1])
            ar = [0.0] * I
            for a in range(I):
                pa = prev[a]
                if pa == 0.0:
                    continue
                ta = trans[a]
                for b in range(I):
                    ar[b] += pa * ta[b]
            ar = [ar[b] * em[b] for b in range(I)]
            an = [p0 * nul[j] * prev[i] for i in range(I)]
            c = sum(ar) + sum(an) or 1e-300
            ar = [x / c for x in ar]
            an = [x / c for x in an]
            fr.append(ar)
            fn.append(an)
        # backward (beta for real and null-with-memory-i are equal)
        post = [None] * J
        br = [1.0] * I
        for j in range(J - 1, -1, -1):
            pr = [fr[j][i] * br[i] for i in range(I)]
            pn = sum(fn[j][i] * br[i] for i in range(I))
            z = sum(pr) + pn or 1e-300
            post[j] = [x / z for x in pr] + [pn / z]
            if j == 0:
                break
            em = emis[j]
            trans = trans_for(english[j - 1])
            nb = [em[b] * br[b] for b in range(I)]
            nn = p0 * nul[j]
            new = []
            for a in range(I):
                ta = trans[a]
                new.append(sum(ta[b] * nb[b] for b in range(I)) + nn * br[a])
            c = max(new) or 1e-300
            br = [x / c for x in new]
        return post

    def _posteriors_diag(self, english: list, sources: list) -> list[list[float]]:
        I, J = len(sources), len(english)
        lam, p0 = self.p.lam, self.p.p0
        emis = [[self.emission(e, s) for s in sources] for e in english]
        post = []
        for j, e in enumerate(english):
            pri = [math.exp(-lam * abs((i + 0.5) / I - (j + 0.5) / J)) for i in range(I)]
            zp = sum(pri)
            row = [(1 - p0) * emis[j][i] * pri[i] / zp for i in range(I)]
            row.append(p0 * self.null.get(e, self.null["\0"]))
            z = sum(row)
            post.append([x / z for x in row])
        if self.p.neighbour <= 0:
            return post
        # Second pass: a link is more likely if a neighbour links to the same or an
        # adjacent source token (phrases; monotone runs).
        beta = self.p.neighbour
        out = []
        for j in range(J):
            row = []
            for i in range(I):
                support = 0.0
                for jj in (j - 1, j + 1):
                    if 0 <= jj < J:
                        nb = post[jj]
                        s = nb[i]
                        if i > 0:
                            s += 0.5 * nb[i - 1]
                        if i + 1 < I:
                            s += 0.5 * nb[i + 1]
                        support = max(support, s)
                row.append(post[j][i] * (1.0 + beta * support))
            row.append(post[j][I])
            z = sum(row)
            out.append([x / z for x in row])
        return out

    def align(self, english: list, sources: list, constraints=None):
        """[(position or None, confidence)] per English word (see posteriors)."""
        post = self.posteriors(english, sources, constraints)
        out = []
        for j, row in enumerate(post):
            best = max(range(len(row)), key=lambda i: row[i])
            if best == len(sources):
                out.append((None, row[best]))
            else:
                out.append((sources[best].pos, row[best]))
        return out
