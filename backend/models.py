"""
Pydantic models for BibleMVP API.
"""
from pydantic import BaseModel
from typing import Optional, List


class Verse(BaseModel):
    """A single Bible verse."""
    id: int
    book: str
    chapter: int
    verse: int
    text: str
    translation_id: str
    word_ids: Optional[List[int]] = None


class Word(BaseModel):
    """An interlinear word with Strong's data."""
    id: int
    text: str
    strong_number: Optional[str]
    original: Optional[str]
    transliteration: Optional[str]
    parsing: Optional[str]
    definition: Optional[str]
    position: int


class CrossReference(BaseModel):
    """A cross-reference between passages."""
    target_book: str
    target_chapter: int
    target_verse: int
    relationship_type: Optional[str]


class Passage(BaseModel):
    """A passage with verses and related data."""
    reference: str
    translation: str
    verses: List[Verse]
    cross_references: List[CrossReference]


class CommentaryEntry(BaseModel):
    """A commentary entry for a passage."""
    source: str
    content: str
    reference_start: int
    reference_end: Optional[int]


class SearchResult(BaseModel):
    """A search result item."""
    type: str  # 'verse', 'commentary', 'note'
    book: Optional[str]
    chapter: Optional[int]
    verse: Optional[int]
    source: Optional[str]
    snippet: str


class WordDetail(BaseModel):
    """Detailed lexicon entry for a word."""
    strong_number: str
    language: str
    original: str
    transliteration: Optional[str]
    pronunciation: Optional[str]
    definition: str
    extended_definition: Optional[str]
    derivation: Optional[str]
    occurrences: List[dict]
    count: int


class UserNote(BaseModel):
    """A user's note on a passage."""
    id: Optional[int]
    book: str
    chapter: int
    verse_start: int
    verse_end: Optional[int]
    content: str
    color: Optional[str]
    tags: Optional[List[str]]
    created_at: Optional[str]
    updated_at: Optional[str]


class Devotional(BaseModel):
    """A daily devotional entry."""
    date: str
    source: str
    title: Optional[str]
    content: str
    scripture_refs: Optional[List[str]]
