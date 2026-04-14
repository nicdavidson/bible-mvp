"""
Bible MVP API Tests
Tests all critical API endpoints against the production database.
"""
import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    """Create test client."""
    return TestClient(app)


# ========== HEALTH ==========

class TestHealth:
    def test_health_endpoint(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "database_exists" in data
        assert "stats" in data
        assert data["stats"]["verses"] > 0

    def test_health_has_all_stat_keys(self, client):
        stats = client.get("/api/health").json()["stats"]
        for key in ["verses", "cross_references", "commentary_entries",
                     "lexicon_entries", "word_alignments", "devotionals"]:
            assert key in stats


# ========== PASSAGE ==========

class TestPassage:
    def test_load_genesis_1(self, client):
        r = client.get("/api/passage/Genesis 1?translation=BSB")
        assert r.status_code == 200
        data = r.json()
        assert len(data["verses"]) == 31
        assert data["reference"] == "Genesis 1"
        assert data["translation"] == "BSB"

    def test_load_with_verse(self, client):
        r = client.get("/api/passage/John 3:16?translation=BSB")
        assert r.status_code == 200
        data = r.json()
        assert len(data["verses"]) >= 1

    def test_load_verse_range(self, client):
        r = client.get("/api/passage/Psalm 23:1-3?translation=BSB")
        assert r.status_code == 200
        data = r.json()
        assert len(data["verses"]) >= 1

    def test_invalid_reference(self, client):
        r = client.get("/api/passage/NotABook 99?translation=BSB")
        assert r.status_code in (200, 404)

    def test_psalm_119(self, client):
        """Longest chapter — should still return quickly."""
        r = client.get("/api/passage/Psalm 119?translation=BSB")
        assert r.status_code == 200
        data = r.json()
        assert len(data["verses"]) == 176

    def test_last_chapter(self, client):
        r = client.get("/api/passage/Revelation 22?translation=BSB")
        assert r.status_code == 200
        data = r.json()
        assert len(data["verses"]) > 0


# ========== SINGLE VERSE ==========

class TestVerse:
    def test_single_verse(self, client):
        r = client.get("/api/verse/John 3:16?translation=BSB")
        assert r.status_code == 200
        data = r.json()
        assert "text" in data
        assert len(data["text"]) > 0


# ========== COMMENTARY ==========

class TestCommentary:
    def test_commentary_genesis_1(self, client):
        r = client.get("/api/passage/Genesis 1/commentary")
        assert r.status_code == 200
        data = r.json()
        assert "entries" in data
        assert len(data["entries"]) > 0

    def test_commentary_has_source(self, client):
        r = client.get("/api/passage/Genesis 1/commentary")
        entries = r.json()["entries"]
        if entries:
            assert "source" in entries[0]
            assert "content" in entries[0]


# ========== CROSS REFERENCES ==========

class TestCrossRefs:
    def test_crossrefs_genesis_1_1(self, client):
        r = client.get("/api/passage/Genesis 1:1/crossrefs")
        assert r.status_code == 200
        data = r.json()
        assert "cross_references" in data

    def test_crossrefs_john_3_16(self, client):
        r = client.get("/api/passage/John 3:16/crossrefs")
        assert r.status_code == 200
        data = r.json()
        refs = data["cross_references"]
        assert len(refs) > 0


# ========== SEARCH ==========

class TestSearch:
    def test_search_basic(self, client):
        r = client.get("/api/search?q=love&translation=BSB")
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert len(data["results"]) > 0

    def test_search_empty(self, client):
        r = client.get("/api/search?q=xyznotfound123&translation=BSB")
        assert r.status_code == 200
        data = r.json()
        assert len(data["results"]) == 0

    def test_search_with_scope(self, client):
        r = client.get("/api/search?q=beginning&translation=BSB&scope=Genesis")
        assert r.status_code == 200


# ========== INTERLINEAR ==========

class TestInterlinear:
    def test_interlinear_genesis_1(self, client):
        r = client.get("/api/passage/Genesis 1/interlinear?translation=BSB")
        assert r.status_code == 200
        data = r.json()
        assert data["has_interlinear"] is True
        assert "verses" in data

    def test_interlinear_nt(self, client):
        r = client.get("/api/passage/John 1/interlinear?translation=BSB")
        assert r.status_code == 200


# ========== WORD ALIGNMENT ==========

class TestWordAlignment:
    def test_word_alignment(self, client):
        r = client.get("/api/word-alignment?book=Genesis&chapter=1&verse=1&word_position=1&translation=BSB")
        assert r.status_code == 200

    def test_strong_number_lookup(self, client):
        r = client.get("/api/word/H430")  # Elohim
        assert r.status_code == 200


# ========== DEVOTIONALS ==========

class TestDevotionals:
    def test_devotional_sources(self, client):
        r = client.get("/api/devotional/sources")
        assert r.status_code == 200

    def test_devotional_today(self, client):
        r = client.get("/api/devotional")
        assert r.status_code == 200


# ========== READING PLANS ==========

class TestReadingPlans:
    def test_list_plans(self, client):
        r = client.get("/api/reading-plans")
        assert r.status_code == 200
        data = r.json()
        assert "plans" in data
        assert isinstance(data["plans"], list)


# ========== TOPICS (NAVE'S) ==========

class TestTopics:
    def test_topics_search(self, client):
        r = client.get("/api/topics/search?q=love&limit=5")
        assert r.status_code == 200

    def test_topics_browse(self, client):
        r = client.get("/api/topics/browse?per_page=10")
        assert r.status_code == 200

    def test_topics_for_verse(self, client):
        r = client.get("/api/topics/for-verse?book=Genesis&chapter=1&verse=1")
        assert r.status_code == 200


# ========== OFFLINE ENDPOINTS ==========

class TestOffline:
    def test_offline_chapter(self, client):
        r = client.get("/api/offline/chapter?book=Genesis&chapter=1&translation=BSB")
        assert r.status_code == 200
        data = r.json()
        assert "verses" in data

    def test_offline_stats(self, client):
        r = client.get("/api/offline/stats")
        assert r.status_code == 200


# ========== STATIC FILES ==========

class TestStaticFiles:
    def test_index_html(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "verse-action-bar" in r.text

    def test_css_loads(self, client):
        r = client.get("/static/css/style.css")
        assert r.status_code == 200
        assert "FLOATING VERSE ACTION BAR" in r.text
        assert "LANDSCAPE PHONE LAYOUT" in r.text

    def test_js_loads(self, client):
        r = client.get("/static/js/app.js")
        assert r.status_code == 200
        assert "clearVerseSelection" in r.text
        assert "readingTouchStart" in r.text
        assert "startLongPress" in r.text
        assert "highlightSelectedVerses" in r.text

    def test_sw_version_placeholder(self, client):
        r = client.get("/static/sw.js")
        assert r.status_code == 200
        assert "__SW_VERSION__" in r.text

    def test_manifest(self, client):
        r = client.get("/static/manifest.json")
        assert r.status_code == 200


# ========== CLEAN URL ROUTES ==========

class TestCleanUrls:
    def test_book_chapter_url(self, client):
        r = client.get("/Genesis/1")
        assert r.status_code == 200

    def test_book_chapter_verse_url(self, client):
        r = client.get("/John/3/16")
        assert r.status_code == 200

    def test_map_route(self, client):
        r = client.get("/map")
        assert r.status_code == 200
