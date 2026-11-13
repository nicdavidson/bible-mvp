"""Commentary full-text search without a second stored copy of the text.

`commentary_entries.content` holds each entry as HTML whose only tags are the
reference anchors the importer generates (scripts/commentary_text.py), with
'<', '>' and entity-like '&' escaped. The plain text FTS5 indexes is that text
with the anchors unwrapped and '&lt;' / '&gt;' read as spaces, which is what the
importer used to store separately as `searchable_text` (~208 MB).

Now FTS5 reads it through a view:

    commentary_search(id, searchable_text, source, book, chapter)
      searchable_text = COALESCE(search_override, commentary_plain(content))

`commentary_plain` is a SQL function every connection that indexes or snippets
commentary must register (`register(conn)`; backend/database.py does it for the
app). `search_override` holds the stored text only for entries where it differs
from the derived one (668 of 141,380 when this was introduced: whitespace that
the HTML lost, e.g. 'thata' for 'that a'), so the index and snippets see exactly
the text they saw before. docs/COMMENTARY_LIBRARY_2026-11.md, "Search storage".

Without `commentary_plain`, snippet() fails with "no such function"; MATCH
alone and reading `content` work without it.
"""
import re

ANCHOR_RE = re.compile(r'<a href="#" class="commentary-ref" data-ref="[^"]*">(.*?)</a>', re.S)
ENTITY_RE = re.compile(r"&(amp|lt|gt);")
_ENTITY = {"amp": "&", "lt": " ", "gt": " "}

SEARCH_TEXT_SQL = "COALESCE(search_override, commentary_plain(content))"


def plain_text(content: str | None) -> str:
    """content HTML -> the text FTS5 indexes (see module docstring)."""
    if content is None:
        return None
    return ENTITY_RE.sub(lambda m: _ENTITY[m.group(1)], ANCHOR_RE.sub(r"\1", content))


def register(conn) -> None:
    conn.create_function("commentary_plain", 1, plain_text, deterministic=True)


VIEW_SQL = f"""
CREATE VIEW IF NOT EXISTS commentary_search AS
    SELECT id, {SEARCH_TEXT_SQL} AS searchable_text, source, book, chapter
    FROM commentary_entries
"""

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS commentary_fts USING fts5(
    searchable_text,
    source,
    book,
    chapter,
    content='commentary_search',
    content_rowid='id'
)
"""

TRIGGERS_SQL = f"""
CREATE TRIGGER IF NOT EXISTS commentary_ai AFTER INSERT ON commentary_entries BEGIN
    INSERT INTO commentary_fts(rowid, searchable_text, source, book, chapter)
    VALUES (new.id, COALESCE(new.search_override, commentary_plain(new.content)),
            new.source, new.book, new.chapter);
END;
CREATE TRIGGER IF NOT EXISTS commentary_ad AFTER DELETE ON commentary_entries BEGIN
    INSERT INTO commentary_fts(commentary_fts, rowid, searchable_text, source, book, chapter)
    VALUES ('delete', old.id, COALESCE(old.search_override, commentary_plain(old.content)),
            old.source, old.book, old.chapter);
END;
CREATE TRIGGER IF NOT EXISTS commentary_au AFTER UPDATE OF content, search_override, source,
        book, chapter ON commentary_entries BEGIN
    INSERT INTO commentary_fts(commentary_fts, rowid, searchable_text, source, book, chapter)
    VALUES ('delete', old.id, COALESCE(old.search_override, commentary_plain(old.content)),
            old.source, old.book, old.chapter);
    INSERT INTO commentary_fts(rowid, searchable_text, source, book, chapter)
    VALUES (new.id, COALESCE(new.search_override, commentary_plain(new.content)),
            new.source, new.book, new.chapter);
END;
"""


def override_for(content: str, searchable: str):
    """What to store in search_override: the importer's text when derivation differs."""
    return None if plain_text(content) == searchable else searchable
