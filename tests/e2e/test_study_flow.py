"""Browser flow test for the study view (Playwright, headless Chromium).

Starts the app on a free local port against the worktree DB, then: selects a verse
range in John 3, opens the study view, switches sources (and back, keeping scroll
position), follows a reference inside commentary, comes back with Back, checks the
deep link, and closes to the reader.

Skips when Playwright or its browser is not installed.
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    port = _free_port()
    env = {**os.environ, "SUPABASE_URL": "", "APP_ENV": "test"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(f"{base}/api/health", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    else:
        proc.kill()
        pytest.skip("app server did not start")
    yield base
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # browser binary not installed
            pytest.skip(f"chromium not available: {e}")
        yield b
        b.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True,
                              service_workers="block")
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    yield pg
    ctx.close()
    assert not errors, errors


def _path(pg):
    return pg.evaluate("location.pathname + location.search")


def test_select_range_study_switch_follow_ref_and_back(server, page):
    page.goto(f"{server}/John/3")
    page.wait_for_selector("#verse-16")

    # Tap the first verse, then the last: a range
    page.locator("#verse-16").scroll_into_view_if_needed()
    page.tap("#verse-16 .verse-num")
    page.tap("#verse-18 .verse-num")
    assert page.evaluate("Alpine.$data(document.body).highlightedVerses") == [16, 17, 18]

    # The Study button shows how many sources comment on the selection
    page.wait_for_selector(".action-bar-study .action-bar-count:not([style*='display: none'])")
    page.tap(".verse-action-bar .action-bar-study")
    page.wait_for_selector("#study-view[open] .study-pane-body p")
    assert page.inner_text("#study-title") == "John 3:16–18"
    assert page.evaluate("document.activeElement.id") == "study-title"   # focus moved into the view
    assert "/John/3/16-18?study=" in _path(page)
    assert len(page.locator(".study-verse").all()) == 3

    # Henry's passage-level note reaches v16-18; Gill is verse by verse
    chips = page.locator(".study-chip:not(.is-empty)")
    slugs = [chips.nth(i).get_attribute("data-slug") for i in range(chips.count())]
    assert {"john-gill", "matthew-henry"} <= set(slugs)

    if page.get_attribute('.study-chip[data-slug="john-gill"]', "aria-pressed") != "true":
        page.tap('.study-chip[data-slug="john-gill"]')
    else:
        # Tapping the active chip shows who the source is
        page.tap('.study-chip[data-slug="john-gill"]')
        page.wait_for_selector("#study-info[open]")
        assert "Particular Baptist" in page.inner_text("#study-info")
        page.keyboard.press("Escape")
        page.wait_for_function("!document.getElementById('study-info').open")
        assert page.evaluate("document.getElementById('study-view').open")
    gill = page.locator('.study-pane[data-slug="john-gill"] .study-pane-scroll')
    page.wait_for_selector('.study-pane[data-slug="john-gill"] .study-pane-body p')
    gill.evaluate("el => el.scrollTo(0, 600)")
    page.wait_for_timeout(200)

    # Switch to Henry, then back with the swap button: Gill keeps its place
    page.tap('.study-chip[data-slug="matthew-henry"]')
    page.wait_for_selector('.study-pane[data-slug="matthew-henry"] .study-pane-body p')
    page.wait_for_function("document.querySelector('.study-pane[data-slug=\"matthew-henry\"] .study-note').offsetParent")
    assert "1–21" in page.inner_text('.study-pane[data-slug="matthew-henry"] .study-note')
    assert _path(page).endswith("study=matthew-henry")
    page.tap(".study-swap")
    page.wait_for_function("location.search.endsWith('john-gill')")
    page.wait_for_timeout(500)
    assert abs(gill.evaluate("el => el.scrollTop") - 600) < 2

    # Follow a reference inside the commentary: peek, then study it
    link = page.locator('.study-pane[data-slug="john-gill"] a.commentary-ref').first
    link.scroll_into_view_if_needed()
    link.click()
    page.wait_for_selector("#study-peek[open] .study-verse")
    target = page.inner_text("#study-peek-title")
    page.locator("#study-peek .study-primary-btn").click()
    page.wait_for_function(f"document.getElementById('study-title').textContent === {target!r}")
    assert page.is_visible(".study-back")
    assert "Back to John 3:16–18" in page.inner_text(".study-back")

    # Back returns to the first study location, same source
    page.go_back()
    page.wait_for_function("document.getElementById('study-title').textContent === 'John 3:16–18'")
    assert _path(page).endswith("/John/3/16-18?study=john-gill")
    page.wait_for_selector('.study-pane[data-slug="john-gill"] .study-pane-body p')

    # Close returns to the reader, focus back on the Study button, nothing reloaded
    page.tap(".study-bar .study-icon-btn")
    page.wait_for_function("!document.getElementById('study-view').open")
    assert _path(page) == "/John/3"
    assert page.evaluate("Alpine.$data(document.body).currentReference").startswith("John 3")


def test_deep_link_opens_same_view_and_escape_closes(server, page):
    page.goto(f"{server}/John/3/16-18?study=matthew-henry")
    page.wait_for_selector("#study-view[open] .study-pane-body p")
    assert page.inner_text("#study-title") == "John 3:16–18"
    assert page.get_attribute('.study-chip[aria-pressed="true"]', "data-slug") == "matthew-henry"
    page.keyboard.press("Escape")
    page.wait_for_function("!document.getElementById('study-view').open")
    assert page.evaluate("location.search") == ""
    assert page.is_visible("#verse-16")


def test_offline_study_from_cache(server, browser):
    """A chapter studied once online opens offline from IndexedDB."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
    pg = ctx.new_page()
    pg.goto(f"{server}/John/3/16?study=john-gill")
    pg.wait_for_selector("#study-view[open] .study-pane-body p")
    pg.wait_for_timeout(500)   # let the IndexedDB writes land
    pg.keyboard.press("Escape")
    ctx.set_offline(True)
    pg.evaluate("Alpine.$data(document.body).openStudy('John 3:17', { source: 'john-gill' })")
    pg.wait_for_selector("#study-view[open] .study-pane-body p")
    assert "17" in pg.inner_text(".study-verses")
    ctx.close()


# ---------- round two: the real commentary library ----------

def _needs_library(page, server):
    has = page.evaluate("""async () => (await (await fetch('/api/commentary/sources')).json())
        .sources.some(s => s.slug === 'treasury-of-david')""")
    if not has:
        pytest.skip("DB without the 13-source commentary library")


def _open(page, server, path, slug):
    page.goto(f"{server}{path}")
    page.wait_for_selector(f'.study-pane[data-slug="{slug}"] .study-pane-body p', timeout=15000)


def test_verse_entries_lead_and_overview_is_a_section(server, page):
    """Item 1: a source with an overview and matching verse entries leads with the verses."""
    page.goto(f"{server}/")
    _needs_library(page, server)
    _open(page, server, "/Psalms/23/1-3?study=treasury-of-david", "treasury-of-david")
    pane = '.study-pane[data-slug="treasury-of-david"]'
    headings = page.locator(f"{pane} .study-pane-body > article .study-entry-range").all_inner_texts()
    assert headings[:3] == ["Verse 1", "Verse 2", "Verse 3"]
    summary = page.inner_text(f"{pane} details.study-more summary")
    assert "note on the whole psalm" in summary
    assert not page.is_visible(f"{pane} .study-note")           # no "doesn't single out" banner
    assert page.inner_text('.study-chip[data-slug="treasury-of-david"] .study-chip-scope') == "v1–3"
    # Tyndale has the same shape on John 3:16 (verse note + passage note 16-21)
    _open(page, server, "/John/3/16?study=tyndale-study-notes", "tyndale-study-notes")
    tp = '.study-pane[data-slug="tyndale-study-notes"]'
    assert page.inner_text(f"{tp} .study-pane-body > article .study-entry-range") == "Verse 16"
    assert "verses 16–21" in page.inner_text(f"{tp} details.study-more summary")
    assert not page.is_visible(f"{tp} .study-note")


# selection -> (source, expected start of the first marked paragraph, or None for "can't tell")
FIND_CASES = [
    ("John 3:16-18", "john-calvin", "For God so loved the world"),
    ("Romans 8:28", "john-calvin", "And we know"),
    ("Psalms 23:3", "john-calvin", "He restoreth my soul"),
    ("Matthew 5:9", "john-calvin", "Happy are the peacemakers"),
    ("Genesis 1:3", "keil-delitzsch", "The word of God then went forth"),
    ("Romans 8:28", "matthew-henry", "II. The concurrence of all providences"),
    ("Psalms 23:4", "matthew-henry", "II. From his performing the office"),
    ("John 3:16", "matthew-henry", None),          # chapter outline cites v1-21: not a match
    ("Matthew 5:2", "catena-aurea", None),         # one "Ver. 1." above a quotation of 1-3
]


@pytest.mark.parametrize("ref,slug,expected", FIND_CASES)
def test_find_my_verses_in_passage_entries(server, page, ref, slug, expected):
    """Item 2: verse markers (Calvin "16.", K&D "Gen 1:3", Catena "Ver. 1.") and narrow mentions."""
    page.goto(f"{server}/")
    _needs_library(page, server)
    page.wait_for_function("window.BibleStudyText")
    first = page.evaluate("""async ([ref, slug]) => {
        const m = ref.match(/^(.+) (\\d+):(\\d+)(?:-(\\d+))?$/);
        const ctx = { book: m[1], chapter: +m[2], vs: +m[3], ve: m[4] ? +m[4] : +m[3] };
        const d = await (await fetch(`/api/passage/${encodeURIComponent(ref)}/commentary?source=${slug}`)).json();
        for (const e of d.entries) {
            const a = BibleStudyText.analyzeEntry(e, ctx);
            const f = a.paras.find(p => p.focus);
            if (f) return f.text;
        }
        return null;
    }""", [ref, slug])
    if expected is None:
        assert first is None
    else:
        assert first and first.startswith(expected), first


def test_calvin_banner_names_the_marked_part(server, page):
    page.goto(f"{server}/")
    _needs_library(page, server)
    _open(page, server, "/John/3/16-18?study=john-calvin", "john-calvin")
    pane = '.study-pane[data-slug="john-calvin"]'
    page.wait_for_function(f"document.querySelector('{pane} .study-note').offsetParent")
    note = page.inner_text(f"{pane} .study-note")
    assert "13–18" in note and "part on verses 16–18 is marked" in note
    assert page.inner_text(f"{pane} p.is-focus .study-vmark") == "16"
    # Found for you: the pane opened at the marked part, and the verses stay shown
    assert page.locator(f"{pane} .study-pane-scroll").evaluate("el => el.scrollTop") > 1000


def test_license_credit_shown_with_the_text(server, page):
    """Item 6: a CC BY-SA source shows its credit in the pane; public-domain ones do not."""
    page.goto(f"{server}/")
    _needs_library(page, server)
    _open(page, server, "/John/3/16?study=tyndale-study-notes", "tyndale-study-notes")
    credit = page.locator('.study-pane[data-slug="tyndale-study-notes"] .study-credit')
    assert credit.is_visible() and "CC BY-SA" in credit.inner_text()
    page.tap('.study-chip[data-slug="john-gill"]')
    page.wait_for_selector('.study-pane[data-slug="john-gill"] .study-pane-body p')
    assert not page.is_visible('.study-pane[data-slug="john-gill"] .study-credit')
    # The source line doesn't repeat the title: "John Gill" then dates, not "John Gill (1697-1771)"
    meta = page.inner_text('.study-pane[data-slug="john-gill"] .study-who-meta')
    assert "John Gill" not in meta and "1697–1771" in meta


@pytest.mark.parametrize("path,slug", [
    ("/John/3/16-18?study=john-gill", "john-gill"),
    ("/John/3/16-18?study=john-calvin", "john-calvin"),
    ("/Psalms/23/1-3?study=treasury-of-david", "treasury-of-david"),
])
def test_verses_shown_on_open(server, page, path, slug):
    """Item 9: every fresh open shows the verses, even when the pane jumps to the marked part."""
    page.goto(f"{server}/")
    _needs_library(page, server)
    _open(page, server, path, slug)
    page.wait_for_timeout(3500)
    assert page.is_visible(".study-text-body") and not page.is_visible(".study-text-peek")


def test_old_format_offline_chapter_still_opens(server, browser):
    """Item 7: commentary saved by the previous app version (old keys, start-only Henry rows)."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
    pg = ctx.new_page()
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-16")
    pg.wait_for_function("(JSON.parse(localStorage.getItem('studySourceMeta') || '[]')).length > 0")
    pg.wait_for_timeout(500)   # auto-cache of the chapter's verses
    pg.evaluate("""() => new Promise((resolve, reject) => {
        const req = indexedDB.open('BibleMVP');
        req.onsuccess = () => {
            const tx = req.result.transaction('commentary', 'readwrite');
            const st = tx.objectStore('commentary');
            st.put({ id: 'Matthew Henry:John:3:1', book: 'John', chapter: 3, source: 'Matthew Henry',
                     reference_start: 1, reference_end: 1, content: 'Old Henry on Nicodemus.' });
            st.put({ id: 'Matthew Henry:John:3:22', book: 'John', chapter: 3, source: 'Matthew Henry',
                     reference_start: 22, reference_end: 22, content: 'Old Henry on the Baptist.' });
            tx.oncomplete = resolve; tx.onerror = reject;
        };
        req.onerror = reject;
    })""")
    ctx.set_offline(True)
    pg.evaluate("Alpine.$data(document.body).openStudy('John 3:16', { source: 'matthew-henry' })")
    pg.wait_for_selector('.study-pane[data-slug="matthew-henry"] .study-pane-body p', timeout=10000)
    body = pg.inner_text('.study-pane[data-slug="matthew-henry"] .study-pane-body')
    assert "Old Henry on Nicodemus." in body and "Verses 1–21" in body
    ctx.close()
