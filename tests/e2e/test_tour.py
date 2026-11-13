"""Browser flows for the first-run walkthrough (modules/tour.js), at phone size: it starts
on a fresh device's first plain load, Skip keeps it away for good, Settings replays it,
stepping through to the end leaves the reader as it was, and a deep link doesn't start it.

Uses the shared server and browser (conftest.py), with tour=True: a device that hasn't
seen the walkthrough. Reduced motion, so the ring and caption never sit mid-transition.
"""
import pytest

from tests.e2e.conftest import new_page

pytest.importorskip("playwright.sync_api")

TITLES = [
    "Choose a passage", "Select verses", "Study", "Commentaries", "Cross-references and notes",
    "Hebrew and Greek", "Search", "Finding your way back",
]
NO_TOUR = "!document.querySelector('.tour, .tour-spot, .tour-card')"
STEP_READY = """(() => {
    const c = document.querySelector('dialog.tour[open] .tour-card');
    return !!c && !c.hasAttribute('aria-busy') && !!document.querySelector('.tour-count').textContent;
})()"""


def _app(pg, expr):
    return pg.evaluate(f"(() => {{ const a = Alpine.$data(document.body); return {expr}; }})()")


def _step(pg):
    pg.wait_for_function(STEP_READY)
    return pg.inner_text(".tour-count"), pg.inner_text(".tour-title")


def _assert_layout(pg):
    """The caption is fully on screen and never over the ringed control."""
    r = pg.evaluate("""() => {
        const box = el => { const r = el.getBoundingClientRect(); return [r.top, r.bottom, r.left, r.right]; };
        const centered = document.querySelector('.tour').classList.contains('is-centered');
        return { card: box(document.querySelector('.tour-card')), w: innerWidth, h: innerHeight,
                 spot: centered ? null : box(document.querySelector('.tour-spot')) };
    }""")
    top, bottom, left, right = r["card"]
    assert top >= 0 and left >= 0 and bottom <= r["h"] and right <= r["w"], r
    if r["spot"]:
        s_top, s_bottom, _, _ = r["spot"]
        assert bottom <= s_top or top >= s_bottom, r


def _ring_fits(pg, selector):
    """JS: the ring surrounds the element (within a few px), for wait_for_function."""
    return f"""(() => {{
        const t = document.querySelector({selector!r})?.getBoundingClientRect();
        const s = document.querySelector('.tour-spot')?.getBoundingClientRect();
        if (!t || !s) return false;
        return Math.abs(s.top - Math.max(t.top - 6, 2)) < 2 && Math.abs(s.left - Math.max(t.left - 6, 2)) < 2
            && Math.abs(s.right - Math.min(t.right + 6, innerWidth - 2)) < 2;
    }})()"""


def _state(pg):
    return _app(pg, """({
        selection: a.highlightedVerses.length, word: a.selectedWord, study: a.study.open,
        dialogs: document.querySelectorAll('dialog[open]').length,
        wordMarked: document.querySelectorAll('.word.selected').length,
        path: location.pathname + location.search,
    })""")


@pytest.fixture
def fresh(browser):
    ctx, pg, errors = new_page(browser, 390, 844, tour=True)
    pg.emulate_media(reduced_motion="reduce")
    tour_requests = []
    pg.on("request", lambda r: "/modules/tour.js" in r.url and tour_requests.append(r.url))
    pg.tour_requests = tour_requests
    yield pg
    ctx.close()
    assert not errors, errors


def test_first_plain_load_shows_it_and_skip_keeps_it_away(server, fresh):
    pg = fresh
    pg.goto(f"{server}/John/3")
    assert _step(pg) == ("1 of 8", "Choose a passage")
    # An accessible dialog: labelled, focus inside it, real buttons with room for a thumb
    assert pg.get_attribute("dialog.tour", "aria-labelledby") == "tour-title"
    assert pg.evaluate("document.activeElement.classList.contains('tour-next')")
    for sel in (".tour-skip", ".tour-next"):
        box = pg.locator(sel).bounding_box()
        assert box["height"] >= 44 and box["width"] >= 44, (sel, box)
    assert pg.evaluate("document.querySelector('.tour-skip').tagName") == "BUTTON"
    pg.wait_for_function(_ring_fits(pg, ".header .nav-title"))
    _assert_layout(pg)
    assert pg.evaluate("localStorage.getItem('tourDone')") is None

    pg.click(".tour-skip")
    pg.wait_for_function(NO_TOUR)
    assert pg.evaluate("localStorage.getItem('tourDone')") == "1"
    assert _state(pg)["dialogs"] == 0

    # Never again on this device: the module isn't even fetched
    pg.tour_requests.clear()
    pg.reload()
    pg.wait_for_selector("#verse-16")
    pg.wait_for_load_state("networkidle")
    assert pg.evaluate(NO_TOUR)
    assert pg.tour_requests == []


def test_home_waits_for_a_chapter(server, fresh):
    pg = fresh
    pg.goto(f"{server}/")
    pg.wait_for_selector(".home .picker-book")
    pg.wait_for_load_state("networkidle")
    assert pg.evaluate(NO_TOUR)
    pg.click('.home .picker-book[data-book="John"]')
    pg.click('.home .picker-chapter[aria-label="John 3"]')
    assert _step(pg) == ("1 of 8", "Choose a passage")


def test_settings_replays_it_and_escape_ends_it(server, browser):
    ctx, pg, errors = new_page(browser, 390, 844)          # a device that has seen it
    pg.emulate_media(reduced_motion="reduce")
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-16")
    pg.wait_for_load_state("networkidle")
    assert pg.evaluate(NO_TOUR)

    pg.click(".btn-hamburger")
    pg.click(".side-menu-item:has-text('Settings')")
    pg.click("button:has-text('Show the walkthrough')")
    assert _step(pg) == ("1 of 8", "Choose a passage")
    assert not _app(pg, "a.showSettings")
    pg.click(".tour-next")
    assert _step(pg) == ("2 of 8", "Select verses")
    pg.keyboard.press("Escape")
    pg.wait_for_function(NO_TOUR)
    s = _state(pg)
    assert (s["selection"], s["dialogs"], s["path"]) == (0, 0, "/John/3"), s

    # Focus goes back where it was
    pg.focus(".header .nav-title")
    pg.evaluate("() => { Alpine.$data(document.body).tourStart(); }")   # its promise ends with the tour
    _step(pg)
    assert pg.evaluate("document.activeElement.classList.contains('tour-next')")
    pg.keyboard.press("Escape")
    pg.wait_for_function(NO_TOUR)
    assert pg.evaluate("document.activeElement.classList.contains('nav-title')")
    ctx.close()
    assert not errors, errors


def test_every_step_then_done_leaves_the_reader_as_it_was(server, fresh):
    pg = fresh
    pg.goto(f"{server}/John/3")
    _step(pg)
    start = _state(pg)
    assert (start["selection"], start["dialogs"] - 1, start["path"]) == (0, 0, "/John/3")

    seen = []
    while True:
        count, title = _step(pg)
        seen.append(title)
        assert count == f"{len(seen)} of 8"
        _assert_layout(pg)
        if title == "Select verses":
            # The ring follows the control through a rotation and back
            pg.wait_for_function(_ring_fits(pg, ".verse-box.verse-highlighted"))
            pg.set_viewport_size({"width": 844, "height": 390})
            pg.wait_for_function(_ring_fits(pg, ".verse-box.verse-highlighted"))
            _assert_layout(pg)
            pg.set_viewport_size({"width": 390, "height": 844})
            pg.wait_for_function(_ring_fits(pg, ".verse-box.verse-highlighted"))
        if title == "Commentaries":
            assert _app(pg, "a.study.open")
            pg.wait_for_function(_ring_fits(pg, "#study-view .study-sources"))
            # Back to the Study button closes the study view the tour opened
            pg.click(".tour-back")
            assert _step(pg)[1] == "Study"
            assert not _app(pg, "a.study.open")
            pg.click(".tour-next")
            assert _step(pg)[1] == "Commentaries"
            assert _app(pg, "a.study.open")
        if title == "Hebrew and Greek":
            assert not _app(pg, "a.study.open") and _app(pg, "!!a.selectedWord")
        if pg.inner_text(".tour-next") == "Done":
            break
        pg.click(".tour-next")
    assert seen == TITLES

    pg.click(".tour-next")
    pg.wait_for_function(NO_TOUR)
    end = _state(pg)
    assert end == {**start, "dialogs": 0}, end
    assert pg.evaluate("localStorage.getItem('tourDone')") == "1"


def test_deep_link_does_not_start_it(server, fresh):
    pg = fresh
    pg.goto(f"{server}/John/3/16?study=john-gill")
    pg.wait_for_selector("#study-view[open] .study-pane-body p")
    pg.wait_for_load_state("networkidle")
    assert pg.evaluate(NO_TOUR)
    assert pg.tour_requests == []
    assert pg.evaluate("localStorage.getItem('tourDone')") is None
    # Closing the study view onto the chapter doesn't start it either
    pg.click("#study-view .study-bar .study-icon-btn")
    pg.wait_for_function("!document.getElementById('study-view').open")
    pg.wait_for_load_state("networkidle")
    assert pg.evaluate(NO_TOUR)

    # The next plain load does
    pg.goto(f"{server}/John/3")
    assert _step(pg) == ("1 of 8", "Choose a passage")


def test_escape_inside_the_study_view_puts_everything_back(server, fresh):
    pg = fresh
    pg.goto(f"{server}/John/3")
    _step(pg)
    start = _state(pg)
    for _ in range(3):
        pg.click(".tour-next")
    assert _step(pg)[1] == "Commentaries"
    assert _app(pg, "a.study.open")
    pg.keyboard.press("Escape")
    pg.wait_for_function(NO_TOUR)
    pg.wait_for_function("!Alpine.$data(document.body).study.open")
    assert _state(pg) == {**start, "dialogs": 0}
    assert pg.evaluate("localStorage.getItem('tourDone')") == "1"


def test_a_control_that_never_appears_drops_its_steps(server, fresh):
    pg = fresh
    pg.goto(f"{server}/John/3")
    _step(pg)
    # The study view never opens: its two steps go, the rest carry on
    pg.evaluate("() => { Alpine.$data(document.body).openStudy = async () => {}; }")
    pg.click(".tour-next")
    assert _step(pg) == ("2 of 8", "Select verses")
    pg.click(".tour-next")
    assert _step(pg) == ("3 of 8", "Study")
    pg.click(".tour-next")
    count, title = _step(pg)        # waits out the two bounded staging timeouts
    assert (count, title) == ("4 of 6", "Hebrew and Greek")
    assert not _app(pg, "a.study.open")
    pg.click(".tour-skip")
    pg.wait_for_function(NO_TOUR)
    s = _state(pg)
    assert (s["selection"], s["word"], s["study"], s["dialogs"], s["path"]) == (0, None, False, 0, "/John/3"), s
