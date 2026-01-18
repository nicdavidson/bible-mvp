#!/usr/bin/env python3
"""
Import Spurgeon's Morning and Evening devotionals from CCEL.

Source: https://ccel.org/ccel/spurgeon/morneve.toc.html
Public Domain - Charles Spurgeon died in 1892.

Usage:
    python scripts/import_spurgeon.py
"""
import sqlite3
import urllib.request
import time
import re
from pathlib import Path
from html.parser import HTMLParser

DATABASE_PATH = Path(__file__).parent.parent / "data" / "bible.db"
CCEL_BASE = "https://ccel.org/ccel/spurgeon"

# Days per month (non-leap year - Feb 29 is handled specially)
DAYS_PER_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]


class DevotionalParser(HTMLParser):
    """Parse CCEL devotional HTML to extract content."""

    def __init__(self):
        super().__init__()
        self.in_content = False
        self.in_verse = False
        self.in_title = False
        self.depth = 0
        self.verse_ref = ""
        self.title = ""
        self.content_parts = []
        self.current_text = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # Look for the main content div
        if tag == "div" and "class" in attrs_dict:
            classes = attrs_dict["class"].split()
            if "theology" in classes or "text" in classes:
                self.in_content = True
                self.depth = 1
            elif self.in_content:
                self.depth += 1

        # Scripture reference is usually in a verse class or similar
        if self.in_content and tag in ("span", "p"):
            if "class" in attrs_dict and "verse" in attrs_dict["class"]:
                self.in_verse = True

        # Title
        if tag in ("h1", "h2", "h3"):
            self.in_title = True

        # Add paragraph breaks
        if self.in_content and tag == "p":
            if self.current_text.strip():
                self.content_parts.append(self.current_text.strip())
                self.current_text = ""

    def handle_endtag(self, tag):
        if tag in ("h1", "h2", "h3"):
            self.in_title = False

        if tag in ("span", "p") and self.in_verse:
            self.in_verse = False

        if self.in_content and tag == "div":
            self.depth -= 1
            if self.depth <= 0:
                self.in_content = False
                if self.current_text.strip():
                    self.content_parts.append(self.current_text.strip())

        if self.in_content and tag == "p":
            if self.current_text.strip():
                self.content_parts.append(self.current_text.strip())
                self.current_text = ""

    def handle_data(self, data):
        if self.in_title and not self.title:
            self.title = data.strip()
        elif self.in_verse and not self.verse_ref:
            self.verse_ref = data.strip()
        elif self.in_content:
            self.current_text += data


def fetch_html(url: str, timeout: int = 30) -> str | None:
    """Fetch HTML from URL."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'BibleMVP/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"    Error fetching {url}: {e}")
        return None


def clean_text(text: str) -> str:
    """Clean up HTML entities and whitespace."""
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)  # Remove HTML entities
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    return text.strip()


def parse_devotional_simple(html: str) -> dict:
    """Simple regex-based parser for CCEL pages."""
    result = {
        "verse_ref": "",
        "content": ""
    }

    # Try to extract verse reference - usually in quotes at the start
    verse_match = re.search(r'"([^"]+)"\s*[-—]\s*([A-Za-z0-9:\s]+\d+:\d+)', html)
    if verse_match:
        result["verse_ref"] = verse_match.group(2).strip()
    else:
        # Try another pattern
        verse_match = re.search(r'<[^>]*class="[^"]*verse[^"]*"[^>]*>([^<]+)</[^>]+>', html)
        if verse_match:
            result["verse_ref"] = verse_match.group(1).strip()

    # Extract main text content - look for the devotional body
    # Remove script and style tags first
    clean_html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    clean_html = re.sub(r'<style[^>]*>.*?</style>', '', clean_html, flags=re.DOTALL)

    # Try to find content in theology or text divs
    content_match = re.search(r'<div[^>]*class="[^"]*(?:theology|text)[^"]*"[^>]*>(.*?)</div>',
                              clean_html, flags=re.DOTALL)
    if content_match:
        content = content_match.group(1)
    else:
        # Fall back to body content between certain markers
        body_match = re.search(r'<body[^>]*>(.*?)</body>', clean_html, flags=re.DOTALL)
        if body_match:
            content = body_match.group(1)
        else:
            content = clean_html

    # Remove HTML tags but keep paragraph structure
    content = re.sub(r'<br\s*/?>', '\n', content)
    content = re.sub(r'</p>', '\n\n', content)
    content = re.sub(r'<[^>]+>', '', content)
    content = clean_text(content)

    # Remove navigation and footer text
    content = re.sub(r'Previous.*?Next', '', content, flags=re.DOTALL)
    content = re.sub(r'Table of Contents.*', '', content, flags=re.DOTALL)

    result["content"] = content
    return result


def create_table(conn):
    """Create devotionals table if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devotionals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            month INTEGER NOT NULL,
            day INTEGER NOT NULL,
            time_of_day TEXT NOT NULL CHECK (time_of_day IN ('morning', 'evening')),
            title TEXT,
            verse_ref TEXT,
            content TEXT NOT NULL,
            searchable_text TEXT,
            UNIQUE(source, month, day, time_of_day)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_devotionals_date ON devotionals(month, day)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_devotionals_source ON devotionals(source)")
    conn.commit()


def import_spurgeon():
    """Import all Spurgeon Morning and Evening devotionals."""
    print("\n" + "=" * 60)
    print("Importing Spurgeon's Morning and Evening Devotionals")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_PATH)
    create_table(conn)
    cursor = conn.cursor()

    # Check if already imported
    cursor.execute("SELECT COUNT(*) FROM devotionals WHERE source = 'Spurgeon'")
    existing = cursor.fetchone()[0]
    if existing > 0:
        print(f"\nFound {existing} existing entries. Clearing and re-importing...")
        cursor.execute("DELETE FROM devotionals WHERE source = 'Spurgeon'")
        conn.commit()

    total_imported = 0
    errors = 0

    for month_idx, days in enumerate(DAYS_PER_MONTH):
        month = month_idx + 1
        month_name = MONTH_NAMES[month_idx]
        print(f"\n  {month_name}...")
        month_count = 0

        for day in range(1, days + 1):
            for time_of_day, suffix in [("morning", "am"), ("evening", "pm")]:
                # Build URL: morneve.d0101am.html
                url = f"{CCEL_BASE}/morneve.d{month:02d}{day:02d}{suffix}.html"

                html = fetch_html(url)
                if not html:
                    errors += 1
                    continue

                parsed = parse_devotional_simple(html)

                if not parsed["content"] or len(parsed["content"]) < 50:
                    print(f"    Warning: Short/empty content for {month_name} {day} {time_of_day}")
                    errors += 1
                    continue

                title = f"{time_of_day.capitalize()}, {month_name} {day}"

                cursor.execute("""
                    INSERT OR REPLACE INTO devotionals
                    (source, month, day, time_of_day, title, verse_ref, content, searchable_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "Spurgeon",
                    month,
                    day,
                    time_of_day,
                    title,
                    parsed["verse_ref"],
                    parsed["content"],
                    parsed["content"].lower()
                ))
                month_count += 1
                total_imported += 1

                # Be nice to the server
                time.sleep(0.2)

        print(f"    Added {month_count} entries")
        conn.commit()

    # Handle Feb 29 for leap years
    print("\n  Checking February 29 (leap year)...")
    for time_of_day, suffix in [("morning", "am"), ("evening", "pm")]:
        url = f"{CCEL_BASE}/morneve.d0229{suffix}.html"
        html = fetch_html(url)
        if html:
            parsed = parse_devotional_simple(html)
            if parsed["content"] and len(parsed["content"]) >= 50:
                cursor.execute("""
                    INSERT OR REPLACE INTO devotionals
                    (source, month, day, time_of_day, title, verse_ref, content, searchable_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "Spurgeon",
                    2,
                    29,
                    time_of_day,
                    f"{time_of_day.capitalize()}, February 29",
                    parsed["verse_ref"],
                    parsed["content"],
                    parsed["content"].lower()
                ))
                total_imported += 1
                print(f"    Added Feb 29 {time_of_day}")

    conn.commit()
    conn.close()

    print(f"\n{'=' * 60}")
    print(f"Import complete!")
    print(f"Total entries: {total_imported}")
    print(f"Errors/skipped: {errors}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    import_spurgeon()
