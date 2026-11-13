"""Browser flow test for the study view (Playwright, headless Chromium).

Uses the shared server and browser (conftest.py), then: selects a verse
range in John 3, opens the study view, switches sources (and back, keeping scroll
position), follows a reference inside commentary, comes back with Back, checks the
deep link, and closes to the reader.

Skips when Playwright or its browser is not installed.
"""
import pytest

from tests.e2e.conftest import skip_tour

pytest.importorskip("playwright.sync_api")


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

    # Every source in the library has something on John 3:16-18
    chips = page.locator(".study-chip")
    slugs = [chips.nth(i).get_attribute("data-slug") for i in range(chips.count())]
    assert {"scofield-notes-1917", "john-gill", "tyndale-study-notes"} <= set(slugs)

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

    # Switch to Tyndale (verse notes, then its note on 16-21), then back with the swap
    # button: Gill keeps its place
    page.tap('.study-chip[data-slug="tyndale-study-notes"]')
    page.wait_for_selector('.study-pane[data-slug="tyndale-study-notes"] .study-pane-body p')
    assert "verses 16–21" in page.inner_text('.study-pane[data-slug="tyndale-study-notes"] details.study-more summary')
    assert _path(page).endswith("study=tyndale-study-notes")
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

    # Close returns to the reader, selection kept, nothing reloaded
    page.tap(".study-bar .study-icon-btn")
    page.wait_for_function("!document.getElementById('study-view').open")
    assert _path(page) == "/John/3/16-18"
    assert page.evaluate("Alpine.$data(document.body).highlightedVerses") == [16, 17, 18]
    assert page.evaluate("Alpine.$data(document.body).currentReference").startswith("John 3")


def test_deep_link_opens_same_view_and_escape_closes(server, page):
    page.goto(f"{server}/John/3/16-18?study=jamieson-fausset-brown")
    page.wait_for_selector("#study-view[open] .study-pane-body p")
    assert page.inner_text("#study-title") == "John 3:16–18"
    assert page.get_attribute('.study-chip[aria-pressed="true"]', "data-slug") == "jamieson-fausset-brown"
    page.keyboard.press("Escape")
    page.wait_for_function("!document.getElementById('study-view').open")
    assert page.evaluate("location.search") == ""
    assert page.is_visible("#verse-16")


@pytest.mark.parametrize("path,first", [
    # Scofield (first in the order) has a note on John 3:16: the view opens on it
    ("/John/3/16-18", "scofield-notes-1917"),
    # Scofield has nothing on Romans 8:28: the first source that does, not an empty pane
    ("/Romans/8/28", "john-gill"),
])
def test_deep_link_to_a_removed_source_opens_the_first_available(server, page, path, first):
    """Matthew Henry was removed on 2026-11-13; links shared before then still work."""
    page.goto(f"{server}{path}?study=matthew-henry")
    page.wait_for_selector(f'.study-pane[data-slug="{first}"] .study-pane-body p', timeout=15000)
    assert page.get_attribute('.study-chip[aria-pressed="true"]', "data-slug") == first
    assert not page.locator('.study-chip[data-slug="matthew-henry"]').count()
    assert _path(page) == f"{path}?study={first}"   # the link is rewritten to what is shown
    assert page.evaluate("Alpine.$data(document.body).study.error") is None
    if first == "john-gill":
        # Scofield has nothing here: not a chip, but listed under All as nothing here
        assert not page.locator('.study-chip[data-slug="scofield-notes-1917"]').count()
        page.tap(".study-all-btn")
        row = page.locator('#study-all li[data-slug="scofield-notes-1917"]')
        row.wait_for()
        assert "Nothing here" in row.inner_text()


def test_offline_study_from_cache(server, browser):
    """A chapter studied once online opens offline from IndexedDB."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
    skip_tour(ctx)
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
        pytest.skip("DB without the commentary library")


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


# selection -> (source, expected start of the first marked paragraph, or None for "can't tell").
# The sources whose passage notes carried verse markers (Calvin "16.", K&D "Gen 1:3", Catena
# "Ver. 1.", Henry's outline) were removed on 2026-11-13. The kept sources' wide notes (a
# Tyndale note on 16-21, Spurgeon's whole-psalm overview) don't single out a verse, and
# nothing may be marked in them.
FIND_CASES = [
    ("John 3:16", "tyndale-study-notes", None),
    ("Psalms 23:3", "treasury-of-david", None),
]


@pytest.mark.parametrize("ref,slug,expected", FIND_CASES)
def test_find_my_verses_in_passage_entries(server, page, ref, slug, expected):
    """Item 2: verse markers and narrow mentions; nothing is marked when nothing fits."""
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
    ("/John/3/16-18?study=tyndale-study-notes", "tyndale-study-notes"),
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
    """Item 7: commentary saved by the previous app version (old keys, start-only passage
    rows). Saved commentary from a source no longer in the library is not shown."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
    skip_tour(ctx)
    pg = ctx.new_page()
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-16")
    pg.wait_for_function("(JSON.parse(localStorage.getItem('studySourceMeta') || '[]')).length > 0")
    pg.wait_for_timeout(500)   # auto-cache of the chapter's verses
    # A passage source as an older library described it (fictional; start-only rows)
    pg.evaluate("""() => {
        const meta = JSON.parse(localStorage.getItem('studySourceMeta'));
        meta.push({ source: "Hale's Exposition", slug: 'hale-s-exposition', short_name: 'Hale',
                    author: 'Hale', kind: 'passage', sort_order: 60 });
        localStorage.setItem('studySourceMeta', JSON.stringify(meta));
    }""")
    pg.evaluate("""() => new Promise((resolve, reject) => {
        const req = indexedDB.open('BibleMVP');
        req.onsuccess = () => {
            const tx = req.result.transaction('commentary', 'readwrite');
            const st = tx.objectStore('commentary');
            st.put({ id: "Hale's Exposition:John:3:1", book: 'John', chapter: 3, source: "Hale's Exposition",
                     reference_start: 1, reference_end: 1, content: 'Old Hale on Nicodemus.' });
            st.put({ id: "Hale's Exposition:John:3:22", book: 'John', chapter: 3, source: "Hale's Exposition",
                     reference_start: 22, reference_end: 22, content: 'Old Hale on the Baptist.' });
            // Saved before Matthew Henry was removed from the library (2026-11-13)
            st.put({ id: 'Matthew Henry:John:3:1', book: 'John', chapter: 3, source: 'Matthew Henry',
                     reference_start: 1, reference_end: 1, content: 'Old Henry on Nicodemus.' });
            tx.oncomplete = resolve; tx.onerror = reject;
        };
        req.onerror = reject;
    })""")
    ctx.set_offline(True)
    pg.evaluate("Alpine.$data(document.body).openStudy('John 3:16', { source: 'hale-s-exposition' })")
    pg.wait_for_selector('.study-pane[data-slug="hale-s-exposition"] .study-pane-body p', timeout=10000)
    body = pg.inner_text('.study-pane[data-slug="hale-s-exposition"] .study-pane-body')
    assert "Old Hale on Nicodemus." in body and "Verses 1–21" in body
    assert not pg.locator('.study-chip[data-slug="matthew-henry"]').count()
    ctx.close()
