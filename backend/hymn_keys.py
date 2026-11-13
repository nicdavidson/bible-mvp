"""Join keys for hymn titles and first lines (shared by the build, the API and any
client that wants to match its own hymnal to the index, e.g. a church's hymn tracker).

title_key(s): lowercase; drop text in parentheses; drop a leading 'the', 'a' or 'an';
keep letters and digits only. "The Lord's My Shepherd" -> 'lordsmyshepherd';
"Some Glad Morning (I'll Fly Away)" -> 'somegladmorning'; "Holy, Holy, Holy!" -> 'holyholyholy'.
A client should also try the text inside parentheses as its own key.
"""
import re

ARTICLES = ("the ", "a ", "an ")


def title_key(value: str | None) -> str:
    s = re.sub(r"\([^)]*\)", " ", (value or "").lower().replace("’", "'")).strip()
    for article in ARTICLES:
        if s.startswith(article):
            s = s[len(article):]
            break
    return "".join(ch for ch in s if ch.isalnum())


def keys_for(value: str | None) -> set[str]:
    """title_key of the whole value and of each parenthetical alternative."""
    out = {title_key(value)}
    out |= {title_key(x) for x in re.findall(r"\(([^)]*)\)", value or "")}
    out.discard("")
    return out


PREFIX_MIN = 12  # letters a title must have to match the start of a first line


def keys_match(want: set[str], have) -> bool:
    """Equal keys, or a title that is the start of a first line ("Joy to the World" ->
    'joytotheworldthelordiscome'). Hymnals often title a hymn by its first words."""
    have = set(have)
    if want & have:
        return True
    return any(len(w) >= PREFIX_MIN and h.startswith(w) for w in want for h in have)
