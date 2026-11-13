"""Text helpers shared by meaning search, its build step and its evaluation.

Pure Python, no numpy: the router imports this even when meaning search is unavailable.
"""
from __future__ import annotations

import re

# Words that carry no topic in a reader's question. Includes question scaffolding
# ("what does the Bible say about ...") that would otherwise dominate BM25.
STOPWORDS = frozenset("""
a about above after again against all am an and any are as at be because been before being
below between both but by can could did do does doing don down during each few for from further
had has have having he her here hers herself him himself his how i if in into is it its itself
just me more most my myself no nor not now of off on once only or other our ours ourselves out
over own same she should so some such than that the their theirs them themselves then there these
they this those through to too under until up very was we were what when where which while who
whom why will with would you your yours yourself yourselves
bible scripture scriptures verse verses passage passages say says said talk talks teach teaches
tell tells mean means find show want get someone something thing things way
""".split())

_SUFFIXES = ("fulness", "iness", "ness", "ment", "ings", "ing", "ies", "ied", "ity", "ful",
             "ous", "ed", "es", "ly", "s", "y")


def _stem(word: str) -> str:
    for suf in _SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= 4:
            return word[: -len(suf)]
    return word


def content_terms(q: str, limit: int = 12) -> list[str]:
    out = []
    for w in re.findall(r"[a-z]+", q.lower().replace("’", "'").replace("'s", "")):
        if w not in STOPWORDS and len(w) > 1 and w not in out:
            out.append(w)
    return out[:limit]


def fts_or_query(q: str) -> str:
    """Stop-worded OR query with crude suffix stripping + prefix match, ranked by BM25.

    A stronger keyword baseline than today's AND query: "forgiving someone who keeps
    hurting you" -> "forgiv"* OR "keep"* OR "hurt"*. Only quoted terms, so no FTS syntax
    from the user reaches MATCH.
    """
    terms = []
    for w in content_terms(q):
        s = _stem(w)
        terms.append(f'"{s}"*' if len(s) >= 4 else f'"{s}"')
    return " OR ".join(terms)


def fts_today_query(q: str) -> str:
    """The exact query /api/search builds today (implicit AND, last word prefix)."""
    from .routers.passages import _fts_query
    return _fts_query(q)


def unit_texts(rows, variant: str) -> list[str]:
    """Texts to embed, one per verse. rows: (book, chapter, verse, book_order, text) in order.

    'verse'  the verse alone
    'window' previous + this + next verse in the same chapter (context for short verses)
    """
    texts = [r[4] for r in rows]
    if variant == "verse":
        return texts
    if variant != "window":
        raise ValueError(variant)
    out = []
    for i, r in enumerate(rows):
        parts = [texts[i]]
        if i > 0 and rows[i - 1][0] == r[0] and rows[i - 1][1] == r[1]:
            parts.insert(0, texts[i - 1])
        if i + 1 < len(rows) and rows[i + 1][0] == r[0] and rows[i + 1][1] == r[1]:
            parts.append(texts[i + 1])
        out.append(" ".join(parts))
    return out
