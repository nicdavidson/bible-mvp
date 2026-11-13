"""Browser flows for reader navigation (modules/nav.js): one navigate(), the return
chip, the passage picker, Back/Forward, plan mode, deep links, the study view over
a jumped-to passage, offline, and the word-link confidence rule.

Uses the shared server and browser (conftest.py). Phone sizes 360x740 and 390x844,
desktop 1280x800.
"""
import re

import pytest

from tests.e2e.conftest import new_page

pytest.importorskip("playwright.sync_api")

PHONES = [(360, 740), (390, 844)]


def _app(pg, expr):
    return pg.evaluate(f"(() => {{ const a = Alpine.$data(document.body); return {expr}; }})()")


def _path(pg):
    return pg.evaluate("location.pathname + location.search")


def _wait_ref(pg, ref):
    """Wait until the reader shows ref and its navigation has finished (history, chip, scroll)."""
    pg.wait_for_function(f"(() => {{ const a = Alpine.$data(document.body); "
                         f"return a.currentReference === {ref!r} && !a.loading && !a.navBusy; }})()")
    pg.wait_for_timeout(50)


def _chip(pg):
    """Chip label if the chip is showing, else None."""
    if not pg.is_visible(".return-chip"):
        return None
    return pg.inner_text(".return-chip-back").strip()


@pytest.fixture
def phone(browser):
    ctx, pg, errors = new_page(browser, 390, 844)
    yield pg
    ctx.close()
    assert not errors, errors


@pytest.fixture
def desktop(browser):
    ctx, pg, errors = new_page(browser, 1280, 800, touch=False)
    yield pg
    ctx.close()
    assert not errors, errors


# ---------- references ----------

@pytest.mark.parametrize("typed,canonical", [
    ("rom 8:28", "Romans 8:28"),
    ("Rom. 8.28", "Romans 8:28"),
    ("ROMANS 8 28", "Romans 8:28"),
    ("jn3:16", "John 3:16"),
    ("john 3:16-18", "John 3:16-18"),
    ("John 3:18-16", "John 3:16-18"),
    ("John 3:16–18", "John 3:16-18"),
    ("1jn 4:8", "1 John 4:8"),
    ("1 john 4 8", "1 John 4:8"),
    ("i john 4:8", "1 John 4:8"),
    ("ps 23", "Psalms 23"),
    ("psalm 23", "Psalms 23"),
    ("song of songs 2", "Song of Solomon 2"),
    ("jude 5", "Jude 1:5"),
    ("obad 3", "Obadiah 1:3"),
    ("matth 5:9", "Matthew 5:9"),
    ("revel 21", "Revelation 21"),
    ("Genesis 1-3", "Genesis 1"),
    ("  gen   1  ", "Genesis 1"),
])
def test_reference_parsing(server, desktop, typed, canonical):
    desktop.goto(f"{server}/")
    desktop.wait_for_function("window.BibleRef")
    got = desktop.evaluate("t => { const r = BibleRef.parse(t); return r.chapter ? BibleRef.format(r) : r }", typed)
    assert got == canonical


@pytest.mark.parametrize("typed,message", [
    ("jo 3", "Which book?"),
    ("xyz 3", "no book called"),
    ("psalms 151", "Psalms has 150 chapters"),
    ("jude 2:1", "Jude has 1 chapter"),
])
def test_reference_errors(server, desktop, typed, message):
    desktop.goto(f"{server}/")
    desktop.wait_for_function("window.BibleRef")
    assert message in desktop.evaluate("t => BibleRef.parse(t).error", typed)


@pytest.mark.parametrize("size", PHONES)
def test_typed_reference_in_sloppy_form(server, browser, size):
    ctx, pg, errors = new_page(browser, *size)
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-16")
    pg.tap(".nav-title")
    pg.wait_for_selector("#passage-picker[open]")
    pg.fill("#passage-picker .picker-input", "rom 8:28")
    # The typed text is read back canonically before going
    pg.wait_for_selector("#passage-picker .picker-go", state="visible")
    assert pg.inner_text("#passage-picker .picker-go").strip() == "Go to Romans 8:28"
    pg.press("#passage-picker .picker-input", "Enter")
    _wait_ref(pg, "Romans 8:28")
    # Canonical everywhere: URL, title, state, history entry, Recent
    assert _path(pg) == "/Romans/8/28"
    assert pg.inner_text(".nav-title-ref") == "Romans 8"
    # On phones the running head is the only title above the text (the passage header is gone)
    assert not pg.is_visible(".passage-title-btn")
    assert _app(pg, "a.currentBook") == "Romans"
    assert pg.evaluate("history.state.ref") == "Romans 8:28"
    assert pg.evaluate("JSON.parse(localStorage.readingHistory)[0].reference") == "Romans 8:28"
    assert _app(pg, "a.highlightedVerses") == [28]
    # Next chapter works from a typed reference (P1-3); on phones it's in the reading bar,
    # which the selection's action bar replaces until the selection is cleared
    pg.tap(".action-bar-dismiss")
    pg.tap(".reading-bar-step.is-next")
    _wait_ref(pg, "Romans 9")
    # A mistake is explained in the picker, and the reader stays where it is
    pg.tap(".nav-title")
    pg.fill("#passage-picker .picker-input", "psalms 151")
    pg.press("#passage-picker .picker-input", "Enter")
    assert "Psalms has 150 chapters" in pg.inner_text("#passage-picker .picker-hint")
    assert _app(pg, "a.currentReference") == "Romans 9"
    pg.keyboard.press("Escape")   # the first Escape clears the search field (platform behaviour)
    pg.keyboard.press("Escape")
    pg.wait_for_function("!document.getElementById('passage-picker').open")
    # Search accepts a reference too (P1-7)
    pg.click(".header-right .btn-icon[title^='Search']")
    pg.fill(".input-search", "jn 3:16")
    pg.press(".input-search", "Enter")
    _wait_ref(pg, "John 3:16")
    assert _path(pg) == "/John/3/16"
    ctx.close()
    assert not errors, errors


def test_old_recent_entries_are_cleaned_up(server, browser):
    """Recent saved by older versions ("rom 8:28", duplicates per chapter) is migrated."""
    ctx, pg, errors = new_page(browser, 390, 844)
    pg.goto(f"{server}/")
    pg.evaluate("""localStorage.setItem('readingHistory', JSON.stringify([
        {reference: 'rom 8:28', translation: 'BSB', timestamp: 3},
        {reference: 'Romans 8', translation: 'BSB', timestamp: 2},
        {reference: 'jn 3', translation: 'KJV', timestamp: 1},
        {reference: 'garbage', translation: 'BSB', timestamp: 0}]))""")
    pg.reload()
    pg.wait_for_selector(".home-continue")
    hist = pg.evaluate("JSON.parse(localStorage.readingHistory)")
    assert [h["reference"] for h in hist] == ["Romans 8:28", "John 3"]
    assert hist[1]["translation"] == "KJV" and hist[0]["timestamp"] == 3
    assert pg.inner_text(".home-continue-ref") == "Romans 8:28"
    ctx.close()
    assert not errors, errors


# ---------- the picker ----------

@pytest.mark.parametrize("size", PHONES)
def test_picker_navigation(server, browser, size):
    ctx, pg, errors = new_page(browser, *size)
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-16")
    # John 3 -> Psalm 23: three taps, no typing
    pg.tap(".nav-title")
    pg.wait_for_selector("#passage-picker[open]")
    assert pg.get_attribute('#passage-picker .picker-book[data-book="John"]', "aria-current") == "true"
    pg.tap('#passage-picker .picker-book[data-book="Psalms"]')
    pg.tap('#passage-picker .picker-chapter[aria-label="Psalms 23"]')
    _wait_ref(pg, "Psalms 23")
    assert _path(pg) == "/Psalms/23"
    assert not pg.evaluate("document.getElementById('passage-picker').open")
    assert not _chip(pg)   # reading on: no way-back chip
    # The current book and chapter are marked in the picker
    pg.tap(".nav-title")
    pg.wait_for_selector("#passage-picker[open]")
    assert pg.get_attribute('#passage-picker .picker-book[data-book="Psalms"]', "aria-current") == "true"
    pg.tap('#passage-picker .picker-book[data-book="Psalms"]')
    assert pg.inner_text("#passage-picker .picker-chapter.is-current") == "23"
    pg.tap('#passage-picker .picker-chapter[aria-label="Psalms 24"]')
    _wait_ref(pg, "Psalms 24")
    # One-chapter books open directly
    pg.tap(".nav-title")
    pg.tap('#passage-picker .picker-book[data-book="Obadiah"]')
    _wait_ref(pg, "Obadiah 1")
    # Typing filters the books; a book name alone opens its chapters
    pg.tap(".nav-title")
    pg.fill("#passage-picker .picker-input", "jo")
    pg.wait_for_function("document.querySelectorAll('#passage-picker .picker-book').length > 0 && [...document.querySelectorAll('#passage-picker .picker-book')].every(b => b.offsetParent === null || /jo/i.test(b.textContent))")
    books = pg.locator("#passage-picker .picker-book:visible").all_inner_texts()
    assert set(books) == {"Joshua", "Job", "Joel", "Jonah", "John", "1 John", "2 John", "3 John"}
    pg.fill("#passage-picker .picker-input", "ezek")
    pg.press("#passage-picker .picker-input", "Enter")
    pg.wait_for_selector("#passage-picker .picker-chapters:visible")
    assert pg.inner_text("#passage-picker .picker-chapters-head h3") == "Ezekiel"
    # Recent is one tap away
    pg.tap("#passage-picker .picker-all-books")
    pg.tap("#passage-picker .picker-tabs button >> text=Recent")
    pg.wait_for_selector("#passage-picker .picker-list-ref:visible")
    recent = pg.locator("#passage-picker .picker-list-ref:visible").all_inner_texts()
    assert recent[:4] == ["Obadiah 1", "Psalms 24", "Psalms 23", "John 3"]
    pg.locator("#passage-picker .picker-list-ref:visible", has_text="John 3").tap()
    _wait_ref(pg, "John 3")
    # Translation is in the picker on phones (P1-5); switching keeps the place, no new entry
    n = pg.evaluate("history.length")
    pg.tap(".nav-title")
    pg.tap("#passage-picker .picker-translation button >> text=KJV")
    pg.wait_for_function("document.querySelector('#verse-16').textContent.includes('only begotten')")
    assert pg.evaluate("history.length") == n and _path(pg) == "/John/3"
    assert pg.inner_text(".nav-title-tr") == "KJV"
    # Tapping outside closes it (closedby="any" or the fallback)
    pg.mouse.click(5, 5)
    pg.wait_for_function("!document.getElementById('passage-picker').open")
    ctx.close()
    assert not errors, errors


def test_picker_keyboard(server, desktop):
    desktop.goto(f"{server}/John/3")
    desktop.wait_for_selector("#verse-16")
    desktop.click("body", position={"x": 5, "y": 300})
    desktop.keyboard.press("g")
    desktop.wait_for_selector("#passage-picker[open]")
    assert desktop.evaluate("document.activeElement.classList.contains('picker-input')")
    desktop.keyboard.type("1 cor 13")
    desktop.keyboard.press("Enter")
    _wait_ref(desktop, "1 Corinthians 13")
    # Esc closes without navigating; focus goes back to the button that opened it
    desktop.click(".nav-title")
    desktop.wait_for_selector("#passage-picker[open]")
    desktop.keyboard.press("Escape")
    desktop.wait_for_function("!document.getElementById('passage-picker').open")
    assert desktop.evaluate("document.activeElement.classList.contains('nav-title')")
    # Arrow keys don't turn the page while the picker is open
    desktop.click(".nav-title")
    desktop.focus('#passage-picker .picker-book[data-book="Genesis"]')
    desktop.keyboard.press("ArrowRight")
    desktop.wait_for_timeout(300)
    assert _app(desktop, "a.currentReference") == "1 Corinthians 13"


def test_home_is_the_picker(server, browser):
    ctx, pg, errors = new_page(browser, 360, 740)
    pg.goto(f"{server}/")
    pg.wait_for_selector(".home .picker-book")
    assert not pg.is_visible(".panel-resources")   # no empty study sheet on Home (P2-5)
    assert not pg.is_visible(".home-continue")     # nothing read yet
    pg.locator('.home .picker-book[data-book="Mark"]').tap()
    pg.locator('.home .picker-chapter[aria-label="Mark 4"]').tap()
    _wait_ref(pg, "Mark 4")
    # Home from the menu, then Continue reading
    pg.tap(".btn-hamburger")
    pg.locator(".side-menu-item", has_text="Home").tap()
    pg.wait_for_selector(".home-continue:visible")
    assert _path(pg) == "/"
    pg.tap(".home-continue")
    _wait_ref(pg, "Mark 4")
    pg.go_back()
    pg.wait_for_selector(".home-continue:visible")
    ctx.close()
    assert not errors, errors


# ---------- jumps and the way back ----------

def _topic_jump(pg, tap):
    """From the selected verse: More > Topics (phone) or the Topics tab (wide), the first
    topic, then its first single-verse reference: a jump from the reader."""
    pg.wait_for_function("Alpine.$data(document.body).verseTopics.length > 0")
    if pg.is_visible(".action-bar-more"):
        tap(".action-bar-more")
        tap(".action-more button >> text=Topics")
    else:
        pg.click(".panel-resources .tab-btn >> text=Topics")
    pg.locator(".topic-verse-section .topic-chip").first.click()
    pg.wait_for_selector(".topic-ref-item")
    item = pg.locator(".topic-ref-item").filter(has_not_text="-").first
    target = item.locator(".topic-ref-label").inner_text()
    item.click()
    _wait_ref(pg, target)
    return target


def _jump_from_john_3_16(pg, server):
    """Select John 3:16 and follow a topical reference from it."""
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-16")
    pg.locator("#verse-16").scroll_into_view_if_needed()
    pg.tap("#verse-16 .verse-num")
    return _topic_jump(pg, pg.tap)


@pytest.mark.parametrize("size", PHONES)
def test_jump_and_return_with_the_chip(server, browser, size):
    ctx, pg, errors = new_page(browser, *size)
    target = _jump_from_john_3_16(pg, server)
    assert _chip(pg) == "Back to John 3:16"
    # The sheet folds after a jump so the verse and the chip both show (P1-10)
    assert not _app(pg, "a.resourcesPanelExpanded")
    # The chip floats above the action bar, clear of the text controls (it covered Share)
    chip = pg.locator(".return-chip").bounding_box()
    bar = pg.locator(".verse-action-bar").bounding_box()
    assert chip["y"] + chip["height"] <= bar["y"]
    box = pg.locator(f"#verse-{target.split(':')[1]}").bounding_box()
    assert 0 < box["y"] < size[1] * 0.75
    # One tap back, verse still selected and in view
    pg.tap(".return-chip-back")
    _wait_ref(pg, "John 3:16")
    assert _path(pg) == "/John/3/16" and not _chip(pg)
    assert _app(pg, "a.highlightedVerses") == [16]
    v16 = pg.locator("#verse-16").bounding_box()
    assert 0 < v16["y"] < size[1]
    # Forward goes to the jump again, with its chip
    pg.go_forward()
    _wait_ref(pg, target)
    assert _chip(pg) == "Back to John 3:16"
    # Dismiss: stays here, chip gone, and Back/Forward won't bring it back for this entry
    pg.tap(".return-chip-dismiss")
    pg.wait_for_selector(".return-chip", state="hidden")
    assert pg.evaluate("history.state.ret") is None
    pg.go_back()
    _wait_ref(pg, "John 3:16")
    pg.go_forward()
    _wait_ref(pg, target)
    assert not _chip(pg)
    ctx.close()
    assert not errors, errors


def test_jump_and_return_with_browser_back(server, phone):
    target = _jump_from_john_3_16(phone, server)
    n = phone.evaluate("history.length")
    phone.go_back()
    _wait_ref(phone, "John 3:16")
    assert not _chip(phone)
    assert phone.evaluate("history.length") == n   # Back never adds entries (P0-1)
    phone.go_forward()
    _wait_ref(phone, target)
    assert _chip(phone) == "Back to John 3:16"


def test_reading_on_clears_the_chip(server, phone):
    target = _jump_from_john_3_16(phone, server)
    assert _chip(phone)
    phone.tap(".action-bar-dismiss")
    phone.tap(".reading-bar-step.is-next")
    phone.wait_for_function(f"Alpine.$data(document.body).currentReference !== {target!r} && !Alpine.$data(document.body).loading && !Alpine.$data(document.body).navBusy")
    assert not _chip(phone)
    # ...and Back to the jumped-to passage shows it again: Back agrees with the chip
    # (the selection was cleared before reading on, and the entry follows the selection)
    phone.go_back()
    _wait_ref(phone, target.split(":")[0])
    assert _chip(phone) == "Back to John 3:16"


def test_back_forward_through_reads_and_jumps(server, desktop):
    """Reads and jumps mixed: every step Back and Forward lands where it should,
    the chip follows the entry, and chained jumps return to the first place."""
    pg = desktop
    pg.goto(f"{server}/John/3")
    _wait_ref(pg, "John 3")
    pg.click(".nav-buttons .btn-nav >> text=Ch →")                      # read
    _wait_ref(pg, "John 4")
    pg.click("#verse-14 .verse-num")
    j1 = _topic_jump(pg, pg.click)                                      # jump
    pg.click(".topic-back-btn")
    pg.click(f"#verse-{j1.split(':')[1]} .verse-num")                  # deselect
    pg.click(f"#verse-{j1.split(':')[1]} .verse-num")                  # select again
    pg.wait_for_function(f"Alpine.$data(document.body).highlightedVerses[0] === {int(j1.split(':')[1])}")
    pg.wait_for_timeout(300)
    j2 = _topic_jump(pg, pg.click)                                      # chained jump
    assert _chip(pg) == "Back to John 4:14"                             # the first place, not j1
    pg.click(".nav-buttons .btn-nav >> text=Ch →")                      # read on
    pg.wait_for_function(f"Alpine.$data(document.body).currentReference !== {j2!r} && !Alpine.$data(document.body).loading && !Alpine.$data(document.body).navBusy")
    after = _app(pg, "a.currentReference")
    assert not _chip(pg)

    expected = [("John 3", None), ("John 4:14", None), (j1, "Back to John 4:14"),
                (j2, "Back to John 4:14"), (after, None)]
    n = pg.evaluate("history.length")
    for ref, chip in reversed(expected[:-1]):
        pg.go_back()
        _wait_ref(pg, ref)
        assert _chip(pg) == chip, ref
    for ref, chip in expected[1:]:
        pg.go_forward()
        _wait_ref(pg, ref)
        assert _chip(pg) == chip, ref
    assert pg.evaluate("history.length") == n
    # The chip from the chained jump goes straight back to the first place (two entries)
    pg.go_back()
    _wait_ref(pg, j2)
    pg.click(".return-chip-back")
    _wait_ref(pg, "John 4:14")
    assert pg.evaluate("history.state.idx") == 1


def test_search_hit_keeps_results(server, desktop):
    desktop.goto(f"{server}/John/3")
    _wait_ref(desktop, "John 3")
    desktop.keyboard.press("/")
    desktop.fill(".input-search", "living water")
    desktop.wait_for_selector(".search-result")
    desktop.locator(".search-result").first.click()
    desktop.wait_for_function("!Alpine.$data(document.body).loading && Alpine.$data(document.body).currentReference !== 'John 3'")
    assert _chip(desktop) == "Back to John 3"
    desktop.click(".return-chip-results")
    desktop.wait_for_selector(".search-result")
    assert desktop.input_value(".input-search") == "living water"


# ---------- plan mode ----------

def test_plan_mode_in_and_out(server, phone):
    pg = phone
    pg.goto(f"{server}/plan/chronological-year/3")
    pg.wait_for_selector(".plan-reading-bar:visible")
    pg.wait_for_function("!Alpine.$data(document.body).loading && Alpine.$data(document.body).verses.length > 0")
    assert pg.evaluate("history.length") == 2 and pg.evaluate("history.state.idx") == 0
    # The reading bar steps through days in plan reading (P0-5)
    prev, nxt = pg.locator(".reading-bar-step").all()
    assert prev.inner_text().strip() == "Day 2" and nxt.inner_text().strip() == "Day 4"
    nxt.tap()
    pg.wait_for_function("location.pathname === '/plan/chronological-year/4' && !Alpine.$data(document.body).loading && !Alpine.$data(document.body).navBusy")
    assert _app(pg, "a.planDay") == 4
    assert not _app(pg, "a.isDayCompleted(3)")   # moving on doesn't mark a day read
    pg.go_back()
    pg.wait_for_function("location.pathname === '/plan/chronological-year/3' && Alpine.$data(document.body).planDay === 3 && !Alpine.$data(document.body).loading && !Alpine.$data(document.body).navBusy")
    # A cross-reference from plan reading: the chip leads back to the day
    first_verse = pg.locator(".verse-box").first
    first_verse.locator(".verse-num").tap()
    pg.wait_for_function("Alpine.$data(document.body).currentBook")
    target = _topic_jump(pg, pg.tap)
    assert not _app(pg, "a.combinedPlanReading")
    assert _chip(pg) == "Back to Day 3 reading"
    pg.tap(".return-chip-back")
    pg.wait_for_function("location.pathname === '/plan/chronological-year/3' && Alpine.$data(document.body).combinedPlanReading && !Alpine.$data(document.body).loading && !Alpine.$data(document.body).navBusy")
    # Exit keeps reading the day's first chapter, as a normal chapter
    day_first = _app(pg, "a.planReadingChapters[0].book + ' ' + a.planReadingChapters[0].chapter")
    pg.tap(".btn-exit-plan")
    _wait_ref(pg, day_first)
    assert not pg.is_visible(".plan-reading-bar")
    assert _path(pg).startswith("/" + day_first.split(" ")[0])
    # Back returns to the plan day (P1-8), and Back again to where the plan was entered
    pg.go_back()
    pg.wait_for_function("location.pathname === '/plan/chronological-year/3' && Alpine.$data(document.body).combinedPlanReading")


def test_plan_list_opens_reading_at_its_section(server, phone):
    pg = phone
    pg.goto(f"{server}/John/3")
    _wait_ref(pg, "John 3")
    pg.evaluate("""localStorage.setItem('readingPlanProgress', JSON.stringify(
        {'chronological-year': {startDate: '2026-11-01', completedDays: []}}))""")
    pg.reload()
    _wait_ref(pg, "John 3")
    pg.evaluate("Alpine.$data(document.body).openReadingPlan()")
    pg.wait_for_selector(".reading-ref:visible")
    psalm = pg.locator(".reading-item", has_text="Psalms").locator(".reading-ref")
    psalm.tap()
    pg.wait_for_function("location.pathname.startsWith('/plan/chronological-year/') && !Alpine.$data(document.body).loading && !Alpine.$data(document.body).navBusy")
    assert _app(pg, "a.combinedPlanReading")
    head = pg.locator(".combined-section-header.section-psalms")
    pg.wait_for_timeout(300)
    assert 0 <= head.bounding_box()["y"] < 400   # scrolled to the Psalms section


# ---------- deep links ----------

@pytest.mark.parametrize("url,ref,path", [
    ("/John/3", "John 3", "/John/3"),
    ("/John/3/16", "John 3:16", "/John/3/16"),
    ("/John/3/16-18", "John 3:16-18", "/John/3/16-18"),
    ("/rom/8/28", "Romans 8:28", "/Romans/8/28"),
    ("/1-John/4/8", "1 John 4:8", "/1-John/4/8"),
    ("/Jude/5", "Jude 1:5", "/Jude/1/5"),
    ("/?ref=jn%203:16", "John 3:16", "/John/3/16"),
])
def test_deep_links(server, browser, url, ref, path):
    ctx, pg, errors = new_page(browser, 390, 844)
    pg.goto(f"{server}{url}")
    _wait_ref(pg, ref)
    assert _path(pg) == path
    assert pg.evaluate("history.length") == 2      # about:blank + this page: no duplicate entry (P0-1)
    assert pg.evaluate("history.state.nav") == 1
    if ":" in ref:
        v = int(re.search(r":(\d+)", ref).group(1))
        assert pg.locator(f"#verse-{v}").bounding_box()["y"] < 844
    ctx.close()
    assert not errors, errors


def test_deep_link_plan_home_study_and_bad(server, browser):
    ctx, pg, errors = new_page(browser, 390, 844)
    pg.goto(f"{server}/plan/chronological-year/10")
    pg.wait_for_function("Alpine.$data(document.body).combinedPlanReading && !Alpine.$data(document.body).loading && !Alpine.$data(document.body).navBusy")
    assert _app(pg, "a.planDay") == 10 and pg.inner_text(".nav-title-ref") == "Day 10"
    pg.goto(f"{server}/")
    pg.wait_for_selector(".home .picker-book")
    assert pg.evaluate("history.state.home") is True
    pg.goto(f"{server}/John/3/16?study=john-gill")
    pg.wait_for_selector("#study-view[open] .study-pane-body p")
    pg.keyboard.press("Escape")
    pg.wait_for_function("!document.getElementById('study-view').open")
    assert _path(pg) == "/John/3/16"
    assert pg.evaluate("history.state.ref") == "John 3:16"
    pg.goto(f"{server}/Nowhere/3")
    pg.wait_for_selector(".error:visible")
    assert "no book called" in pg.inner_text(".error")
    pg.goto(f"{server}/plan/no-such-plan/1")
    pg.wait_for_selector(".home .picker-book")
    ctx.close()
    assert not errors, errors


# ---------- the study view over a jumped-to passage ----------

def test_study_from_jumped_passage_and_close(server, phone):
    pg = phone
    target = _jump_from_john_3_16(pg, server)
    assert _chip(pg) == "Back to John 3:16"
    verse = int(target.split(":")[1])
    pg.tap(f"#verse-{verse} .verse-num")   # deselect (the jump selected it)
    pg.wait_for_function("Alpine.$data(document.body).highlightedVerses.length === 0")
    pg.wait_for_timeout(400)                 # the action bar's leave transition
    pg.tap(f"#verse-{verse} .verse-num")
    pg.wait_for_function(f"Alpine.$data(document.body).highlightedVerses[0] === {verse}")
    # Tap once the bar has finished sliding in (its enter transition moves the button)
    pg.wait_for_function("""() => { const bar = document.querySelector('.verse-action-bar');
        return bar && bar.style.display !== 'none' && !/action-bar-(enter|leave)/.test(bar.className)
            && getComputedStyle(bar).opacity === '1'; }""")
    pg.tap(".verse-action-bar .action-bar-study")
    pg.wait_for_selector("#study-view[open]")
    pg.wait_for_function("!Alpine.$data(document.body).study.loading")
    assert "?study=" in _path(pg)
    # Close: back on the jumped-to passage, its chip still there, nothing reloaded
    pg.tap(".study-bar .study-icon-btn")
    pg.wait_for_function("!document.getElementById('study-view').open")
    assert _app(pg, "a.currentReference").startswith(target.split(":")[0])
    assert _chip(pg) == "Back to John 3:16"
    pg.tap(".return-chip-back")
    _wait_ref(pg, "John 3:16")
    # Commentary -> "Read the chapter" is a jump; the chip returns to the commentary
    pg.goto(f"{server}/John/3/16?study=john-gill")
    pg.wait_for_selector("#study-view[open] .study-pane-body a.commentary-ref")
    pg.locator('.study-pane[data-slug="john-gill"] a.commentary-ref').first.click()
    pg.wait_for_selector("#study-peek[open] .study-verse")
    pg.locator("#study-peek .study-text-btn", has_text="Read the chapter").click()
    pg.wait_for_function("!document.getElementById('study-view').open && !Alpine.$data(document.body).loading && !Alpine.$data(document.body).navBusy")
    assert _chip(pg) == "Back to commentary on John 3:16"
    pg.tap(".return-chip-back")
    pg.wait_for_selector("#study-view[open]")
    assert _path(pg) == "/John/3/16?study=john-gill"


# ---------- offline ----------

def test_offline_navigation_to_a_saved_chapter(server, browser):
    ctx, pg, errors = new_page(browser, 390, 844)
    pg.goto(f"{server}/Ruth/1")
    _wait_ref(pg, "Ruth 1")
    pg.wait_for_timeout(800)   # auto-cache lands in IndexedDB
    pg.tap(".reading-bar-step.is-next")
    _wait_ref(pg, "Ruth 2")
    ctx.set_offline(True)
    pg.tap(".nav-title")
    pg.fill("#passage-picker .picker-input", "ruth 1:16")
    pg.press("#passage-picker .picker-input", "Enter")
    _wait_ref(pg, "Ruth 1:16")
    assert "wherever you go" in pg.inner_text("#verse-16")
    assert _path(pg) == "/Ruth/1/16"
    # A chapter never read: the reader stays put and says why
    pg.tap(".nav-title")
    pg.fill("#passage-picker .picker-input", "ruth 4")
    pg.press("#passage-picker .picker-input", "Enter")
    pg.wait_for_selector(".toast.error")
    assert "isn't saved for offline use" in pg.inner_text(".toast.error")
    assert _app(pg, "a.currentReference") == "Ruth 1:16"
    ctx.close()
    assert not errors, errors


# ---------- init runs once ----------

def test_init_runs_once(server, browser):
    ctx, pg, errors = new_page(browser, 390, 844)
    pg.add_init_script("""
        window.__pop = 0; window.__key = 0;
        const add = window.addEventListener.bind(window);
        window.addEventListener = (t, ...r) => { if (t === 'popstate') window.__pop++; return add(t, ...r); };
        const dadd = document.addEventListener.bind(document);
        document.addEventListener = (t, ...r) => { if (t === 'keydown') window.__key++; return dadd(t, ...r); };
    """)
    requests = []
    pg.on("request", lambda r: "/api/passage/John" in r.url and "/crossrefs" not in r.url
          and "/interlinear" not in r.url and requests.append(r.url))
    pg.goto(f"{server}/John/3")
    _wait_ref(pg, "John 3")
    pg.wait_for_timeout(500)
    assert pg.evaluate("window.__pop") == 1
    assert pg.evaluate("window.__key") == 1
    assert len(requests) == 1, requests
    ctx.close()
    assert not errors, errors


# ---------- word links: show a weak link as uncertain ----------

def _tap_word(pg, verse, position):
    pg.click(f'#verse-{verse} .word[data-position="{position}"]')
    pg.wait_for_selector(".panel-word:visible")
    pg.wait_for_function("Alpine.$data(document.body).selectedWord && Alpine.$data(document.body).selectedWord.text")


def test_word_link_confidence(server, desktop):
    pg = desktop
    pg.goto(f"{server}/John/3")
    _wait_ref(pg, "John 3")
    pg.evaluate("Alpine.$data(document.body).translation = 'WEB'")
    pg.wait_for_function("document.querySelector('#verse-3').textContent.includes('certainly')")
    # Weak content word (confidence 0.44 < 0.5): not stated as fact
    _tap_word(pg, 3, 5)
    assert _app(pg, "a.selectedWord.text") == "certainly"
    assert pg.is_visible(".word-unsure")
    assert "We aren't sure which Greek word" in pg.inner_text(".word-unsure")
    assert not pg.is_visible(".panel-word .word-original")
    pg.click(".word-reveal")
    assert pg.inner_text(".panel-word .word-original") == "ἀμὴν"
    assert "Not certain" in pg.inner_text(".word-unsure-note")
    # Function word at 0.66: shown for content words, but under the 0.7 bar for "the"
    _tap_word(pg, 2, 1)
    assert _app(pg, "a.selectedWord.text") == "The"
    assert "Small words like this" in pg.inner_text(".word-unsure")
    # Strong link (0.98): shown straight away
    _tap_word(pg, 1, 5)
    assert _app(pg, "a.selectedWord.text") == "man"
    assert not pg.is_visible(".word-unsure")
    assert not pg.is_visible(".word-unsure-note")
    assert pg.inner_text(".panel-word .word-original") == "ἄνθρωπος"
    # BSB human alignment always shows, whatever the word
    pg.evaluate("Alpine.$data(document.body).translation = 'BSB'")
    pg.wait_for_function("document.querySelector('#verse-1').textContent.includes('Nicodemus') && !document.querySelector('#verse-3').textContent.includes('certainly')")
    _tap_word(pg, 1, 4)
    assert _app(pg, "a.selectedWord.text") == "a"
    assert not pg.is_visible(".word-unsure")


def test_word_link_rule_offline_rows(server, desktop):
    """The same rule applies to links saved for offline use (confidence/method saved too)."""
    desktop.goto(f"{server}/")
    desktop.wait_for_function("window.BibleWordLink")
    s = lambda w, c, m: desktop.evaluate("([w, c, m]) => BibleWordLink.strength(w, c, m)", [w, c, m])
    assert s("certainly", 0.44, 2) == "unsure"
    assert s("love", 0.5, 2) == "sure"
    assert s("of", 0.69, 2) == "unsure"
    assert s("Of", 0.7, 1) == "sure"
    assert s("it's", 0.6, 2) == "unsure"      # straight apostrophe matches the curly list entry
    assert s("the", 0.1, 0) == "sure"         # human alignment
    assert s("the", None, None) == "sure"     # saved by an older version (BSB human links)
