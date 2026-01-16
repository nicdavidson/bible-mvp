"""
Database initialization and connection management for BibleMVP.
Uses SQLite with FTS5 for full-text search.
"""
import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_PATH = Path(__file__).parent.parent / "data" / "bible.db"


def get_db_connection() -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema."""
    logger.info(f"Database path: {DATABASE_PATH}")
    logger.info(f"Database exists: {DATABASE_PATH.exists()}")

    if DATABASE_PATH.exists():
        # Check if it has data
        conn = get_db_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM verses")
            count = cursor.fetchone()[0]
            logger.info(f"Verses in database: {count}")
        except Exception as e:
            logger.error(f"Error checking database: {e}")
        finally:
            conn.close()
    else:
        logger.warning("Database file not found! Creating empty schema...")
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection()
        try:
            conn.executescript(SCHEMA)
            conn.commit()
        finally:
            conn.close()


SCHEMA = """
-- Translations table
CREATE TABLE IF NOT EXISTS translations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    is_public_domain INTEGER NOT NULL DEFAULT 1,
    license_info TEXT
);

-- Books table (canonical order)
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    abbreviation TEXT NOT NULL,
    testament TEXT NOT NULL CHECK (testament IN ('OT', 'NT')),
    book_order INTEGER NOT NULL UNIQUE
);

-- Verses table
CREATE TABLE IF NOT EXISTS verses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    translation_id TEXT NOT NULL,
    book TEXT NOT NULL,
    book_order INTEGER NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    text TEXT NOT NULL,
    FOREIGN KEY (translation_id) REFERENCES translations(id),
    UNIQUE (translation_id, book, chapter, verse)
);

-- Create index for verse lookups
CREATE INDEX IF NOT EXISTS idx_verses_lookup
ON verses(book, chapter, verse, translation_id);

-- Full-text search for verses
CREATE VIRTUAL TABLE IF NOT EXISTS verses_fts USING fts5(
    text,
    book,
    chapter,
    verse,
    content='verses',
    content_rowid='id'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS verses_ai AFTER INSERT ON verses BEGIN
    INSERT INTO verses_fts(rowid, text, book, chapter, verse)
    VALUES (new.id, new.text, new.book, new.chapter, new.verse);
END;

CREATE TRIGGER IF NOT EXISTS verses_ad AFTER DELETE ON verses BEGIN
    INSERT INTO verses_fts(verses_fts, rowid, text, book, chapter, verse)
    VALUES ('delete', old.id, old.text, old.book, old.chapter, old.verse);
END;

CREATE TRIGGER IF NOT EXISTS verses_au AFTER UPDATE ON verses BEGIN
    INSERT INTO verses_fts(verses_fts, rowid, text, book, chapter, verse)
    VALUES ('delete', old.id, old.text, old.book, old.chapter, old.verse);
    INSERT INTO verses_fts(rowid, text, book, chapter, verse)
    VALUES (new.id, new.text, new.book, new.chapter, new.verse);
END;

-- Lexicon (Strong's definitions)
CREATE TABLE IF NOT EXISTS lexicon (
    strong_number TEXT PRIMARY KEY,
    language TEXT NOT NULL CHECK (language IN ('hebrew', 'greek')),
    original TEXT NOT NULL,
    transliteration TEXT,
    pronunciation TEXT,
    definition TEXT NOT NULL,
    extended_definition TEXT,
    derivation TEXT
);

-- Words (interlinear data)
CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    text TEXT NOT NULL,
    strong_number TEXT,
    parsing TEXT,
    translation TEXT,
    FOREIGN KEY (verse_id) REFERENCES verses(id),
    FOREIGN KEY (strong_number) REFERENCES lexicon(strong_number)
);

CREATE INDEX IF NOT EXISTS idx_words_verse ON words(verse_id);
CREATE INDEX IF NOT EXISTS idx_words_strong ON words(strong_number);

-- Commentary entries
CREATE TABLE IF NOT EXISTS commentary_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    reference_start INTEGER NOT NULL DEFAULT 1,
    reference_end INTEGER,
    content TEXT NOT NULL,
    searchable_text TEXT
);

CREATE INDEX IF NOT EXISTS idx_commentary_lookup
ON commentary_entries(book, chapter, reference_start, reference_end);

-- Full-text search for commentary
CREATE VIRTUAL TABLE IF NOT EXISTS commentary_fts USING fts5(
    searchable_text,
    source,
    book,
    chapter,
    content='commentary_entries',
    content_rowid='id'
);

-- Commentary FTS triggers
CREATE TRIGGER IF NOT EXISTS commentary_ai AFTER INSERT ON commentary_entries BEGIN
    INSERT INTO commentary_fts(rowid, searchable_text, source, book, chapter)
    VALUES (new.id, new.searchable_text, new.source, new.book, new.chapter);
END;

CREATE TRIGGER IF NOT EXISTS commentary_ad AFTER DELETE ON commentary_entries BEGIN
    INSERT INTO commentary_fts(commentary_fts, rowid, searchable_text, source, book, chapter)
    VALUES ('delete', old.id, old.searchable_text, old.source, old.book, old.chapter);
END;

-- Cross-references
CREATE TABLE IF NOT EXISTS cross_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_book TEXT NOT NULL,
    source_chapter INTEGER NOT NULL,
    source_verse INTEGER NOT NULL,
    target_book TEXT NOT NULL,
    target_chapter INTEGER NOT NULL,
    target_verse INTEGER NOT NULL,
    target_book_order INTEGER NOT NULL,
    relationship_type TEXT
);

CREATE INDEX IF NOT EXISTS idx_crossref_source
ON cross_references(source_book, source_chapter, source_verse);

-- Devotionals
CREATE TABLE IF NOT EXISTS devotionals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,  -- MM-DD format
    source TEXT NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    scripture_refs TEXT  -- JSON array of references
);

CREATE INDEX IF NOT EXISTS idx_devotional_date ON devotionals(date);

-- User notes (stored locally but schema here for reference)
-- In practice, this will be in IndexedDB on the frontend
CREATE TABLE IF NOT EXISTS user_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse_start INTEGER NOT NULL,
    verse_end INTEGER,
    content TEXT NOT NULL,
    color TEXT,
    tags TEXT,  -- JSON array
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Insert default translations
INSERT OR IGNORE INTO translations (id, name, language, is_public_domain, license_info)
VALUES
    ('WEB', 'World English Bible', 'en', 1, 'Public Domain'),
    ('KJV', 'King James Version', 'en', 1, 'Public Domain'),
    ('ASV', 'American Standard Version (1901)', 'en', 1, 'Public Domain');

-- Insert books in canonical order
INSERT OR IGNORE INTO books (id, name, abbreviation, testament, book_order) VALUES
    (1, 'Genesis', 'Gen', 'OT', 1),
    (2, 'Exodus', 'Exod', 'OT', 2),
    (3, 'Leviticus', 'Lev', 'OT', 3),
    (4, 'Numbers', 'Num', 'OT', 4),
    (5, 'Deuteronomy', 'Deut', 'OT', 5),
    (6, 'Joshua', 'Josh', 'OT', 6),
    (7, 'Judges', 'Judg', 'OT', 7),
    (8, 'Ruth', 'Ruth', 'OT', 8),
    (9, '1 Samuel', '1Sam', 'OT', 9),
    (10, '2 Samuel', '2Sam', 'OT', 10),
    (11, '1 Kings', '1Kgs', 'OT', 11),
    (12, '2 Kings', '2Kgs', 'OT', 12),
    (13, '1 Chronicles', '1Chr', 'OT', 13),
    (14, '2 Chronicles', '2Chr', 'OT', 14),
    (15, 'Ezra', 'Ezra', 'OT', 15),
    (16, 'Nehemiah', 'Neh', 'OT', 16),
    (17, 'Esther', 'Esth', 'OT', 17),
    (18, 'Job', 'Job', 'OT', 18),
    (19, 'Psalms', 'Ps', 'OT', 19),
    (20, 'Proverbs', 'Prov', 'OT', 20),
    (21, 'Ecclesiastes', 'Eccl', 'OT', 21),
    (22, 'Song of Solomon', 'Song', 'OT', 22),
    (23, 'Isaiah', 'Isa', 'OT', 23),
    (24, 'Jeremiah', 'Jer', 'OT', 24),
    (25, 'Lamentations', 'Lam', 'OT', 25),
    (26, 'Ezekiel', 'Ezek', 'OT', 26),
    (27, 'Daniel', 'Dan', 'OT', 27),
    (28, 'Hosea', 'Hos', 'OT', 28),
    (29, 'Joel', 'Joel', 'OT', 29),
    (30, 'Amos', 'Amos', 'OT', 30),
    (31, 'Obadiah', 'Obad', 'OT', 31),
    (32, 'Jonah', 'Jonah', 'OT', 32),
    (33, 'Micah', 'Mic', 'OT', 33),
    (34, 'Nahum', 'Nah', 'OT', 34),
    (35, 'Habakkuk', 'Hab', 'OT', 35),
    (36, 'Zephaniah', 'Zeph', 'OT', 36),
    (37, 'Haggai', 'Hag', 'OT', 37),
    (38, 'Zechariah', 'Zech', 'OT', 38),
    (39, 'Malachi', 'Mal', 'OT', 39),
    (40, 'Matthew', 'Matt', 'NT', 40),
    (41, 'Mark', 'Mark', 'NT', 41),
    (42, 'Luke', 'Luke', 'NT', 42),
    (43, 'John', 'John', 'NT', 43),
    (44, 'Acts', 'Acts', 'NT', 44),
    (45, 'Romans', 'Rom', 'NT', 45),
    (46, '1 Corinthians', '1Cor', 'NT', 46),
    (47, '2 Corinthians', '2Cor', 'NT', 47),
    (48, 'Galatians', 'Gal', 'NT', 48),
    (49, 'Ephesians', 'Eph', 'NT', 49),
    (50, 'Philippians', 'Phil', 'NT', 50),
    (51, 'Colossians', 'Col', 'NT', 51),
    (52, '1 Thessalonians', '1Thess', 'NT', 52),
    (53, '2 Thessalonians', '2Thess', 'NT', 53),
    (54, '1 Timothy', '1Tim', 'NT', 54),
    (55, '2 Timothy', '2Tim', 'NT', 55),
    (56, 'Titus', 'Titus', 'NT', 56),
    (57, 'Philemon', 'Phlm', 'NT', 57),
    (58, 'Hebrews', 'Heb', 'NT', 58),
    (59, 'James', 'Jas', 'NT', 59),
    (60, '1 Peter', '1Pet', 'NT', 60),
    (61, '2 Peter', '2Pet', 'NT', 61),
    (62, '1 John', '1John', 'NT', 62),
    (63, '2 John', '2John', 'NT', 63),
    (64, '3 John', '3John', 'NT', 64),
    (65, 'Jude', 'Jude', 'NT', 65),
    (66, 'Revelation', 'Rev', 'NT', 66);
"""
