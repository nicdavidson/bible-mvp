"""Browser flows for the word panel and the word study (modules/wordstudy.js):
tapping a word, opening the full study, the verses behind a rendering and behind a
collocate, leaving for a verse and coming back (chip and browser Back), deep links,
homographs, the uncertain-link rule, search by Strong's number, credits, offline.

Uses the shared server and browser (conftest.py).
"""
import re
import unicodedata

import pytest

from tests.e2e.conftest import new_page

pytest.importorskip("playwright.sync_api")


def _nfc(s):
    # Sources mix Greek oxia (U+1F71) and tonos (U+03AC) for the same accent
    return unicodedata.normalize("NFC", s)


def _app(pg, expr):
    return pg.evaluate(f"(() => {{ const a = Alpine.$data(document.body); return {expr}; }})()")


def _path(pg):
    return pg.evaluate("decodeURIComponent(location.pathname + location.search)")


def _study_ready(pg):
    pg.wait_for_selector("#word-study[open] #ws-title")
    pg.wait_for_function("!Alpine.$data(document.body).ws.loading")


@pytest.fixture
def phone(browser):
    ctx, pg, errors = new_page(browser, 390, 844)
    yield pg
    ctx.close()
    assert not errors, errors


def _tap_love(pg, server):
    """1 John 4:8, BSB: select the verse, then tap "love" (the second tap is the word)."""
    pg.goto(f"{server}/1-John/4")
    pg.wait_for_selector("#verse-8")
    pg.locator("#verse-8").scroll_into_view_if_needed()
    pg.tap("#verse-8 .verse-num")
    pg.wait_for_function("Alpine.$data(document.body).highlightedVerses.includes(8)")
    pg.locator("#verse-8 .word[data-word='love']").last.tap()
    pg.wait_for_selector(".panel-word .qw-study:visible")


def test_word_panel_stays_quick_and_leads_to_the_study(server, phone):
    pg = phone
    _tap_love(pg, server)
    panel = pg.locator(".panel-word")
    assert _nfc(panel.locator(".qw-original").inner_text()) == _nfc("ἀγάπη")
    pg.wait_for_function("document.querySelector('.panel-word .qw-count')?.offsetParent")
    # One named lexicon gloss and a count; no occurrence list or chart in the panel
    assert "love; goodwill; esteem" in panel.inner_text()
    assert "Abbott-Smith" in panel.locator(".qw-src").first.inner_text()
    assert panel.locator(".qw-count").inner_text() == "116 times in the New Testament"
    assert panel.locator(".occurrence-list, .freq-chart, .gloss-chips").count() == 0

    pg.tap(".qw-study")
    _study_ready(pg)
    assert _path(pg) == "/word/G26"
    pg.wait_for_selector(".panel-word", state="hidden")
    assert _nfc(pg.inner_text("#ws-title")) == _nfc("ἀγάπη")
    assert "116 times in 106 verses in the New Testament" in pg.inner_text(".ws-count")
    # Every lexicon is credited where it is shown
    credits = pg.locator("#ws-sec-lex .ws-credit").all_inner_texts()
    assert any("Abbott-Smith" in c and "Public domain" in c for c in credits)
    assert any("Dodson" in c and "CC0" in c for c in credits)
    assert any("Strong's" in c for c in credits)
    names = pg.locator("#ws-sec-lex .ws-lex-name").all_inner_texts()
    assert names == ["Abbott-Smith", "Dodson", "Strong's"]
    # Computed sections are labelled as computed, and lower than the counted ones
    order = pg.evaluate("""[...document.querySelectorAll('#word-study .ws-sec')]
        .filter(s => s.offsetParent).map(s => s.id || s.querySelector('h2').textContent)""")
    idx = [order.index(k) for k in ("ws-sec-lex", "ws-sec-tr", "ws-sec-where", "ws-sec-with")]
    assert idx == sorted(idx)
    assert "Computed" in pg.inner_text("#ws-sec-with h2")


def test_rendering_and_collocate_verses_out_and_back(server, phone):
    pg = phone
    _tap_love(pg, server)
    pg.tap(".qw-study")
    _study_ready(pg)

    # The verses behind a rendering: KJV "charity"
    pg.locator(".ws-tr", has_text="KJV").locator(".ws-meter-row", has_text="charity").tap()
    pg.wait_for_selector(".ws-list .ws-verse")
    assert _path(pg) == "/word/G26?list=rendering:KJV:charity"
    assert pg.inner_text("#ws-list-title") == "KJV: “charity”"
    assert "27 places" in pg.inner_text(".ws-list")
    first = pg.locator(".ws-list .ws-verse").first
    assert first.locator(".ws-verse-ref").inner_text() == "1 Corinthians 8:1"
    assert first.locator("mark.ws-hit").inner_text() == "charity"

    # Back to the study (browser Back), then the verses behind a collocate: pistis
    pg.go_back()
    pg.wait_for_function("!Alpine.$data(document.body).ws.list")
    assert _path(pg) == "/word/G26"
    pg.locator("#ws-sec-with .ws-word-row", has_text="pístis").tap()
    pg.wait_for_selector(".ws-list .ws-verse")
    assert _path(pg) == "/word/G26?list=with:G4102"
    assert "25 times in 24 verses" in pg.inner_text(".ws-list")
    assert pg.locator(".ws-list .ws-verse").count() == 24

    # A verse: read it in its chapter; the chip and Back both come back to this list
    pg.locator(".ws-list .ws-verse", has_text="1 Corinthians 13:13").tap()
    pg.wait_for_selector("#ws-peek[open] .study-verse")
    assert pg.inner_text("#ws-peek-title") == "1 Corinthians 13:13"
    pg.tap("#ws-peek .study-primary-btn")
    pg.wait_for_function("!Alpine.$data(document.body).ws.open && Alpine.$data(document.body).currentChapter === 13")
    assert _path(pg) == "/1-Corinthians/13/13"
    assert "word study of agápē" in pg.inner_text(".return-chip")
    pg.tap(".return-chip button >> nth=0")
    pg.wait_for_function("Alpine.$data(document.body).ws.open && Alpine.$data(document.body).ws.list")
    assert _path(pg) == "/word/G26?list=with:G4102"

    # Again, this time to study the verse, and back with the browser
    pg.locator(".ws-list .ws-verse", has_text="1 Corinthians 13:13").tap()
    pg.wait_for_selector("#ws-peek[open] .study-verse")
    pg.locator("#ws-peek .study-text-btn", has_text="Study").tap()
    pg.wait_for_selector("#study-view[open]")
    pg.wait_for_function("!Alpine.$data(document.body).study.loading")
    assert _app(pg, "a.studyRefLabel()") == "1 Corinthians 13:13"
    assert not _app(pg, "a.ws.open")
    pg.go_back()   # the study view closes onto the reader
    pg.wait_for_function("!Alpine.$data(document.body).study.open")
    pg.go_back()   # and the reader goes back to the word study's list
    pg.wait_for_function("Alpine.$data(document.body).ws.open && Alpine.$data(document.body).ws.list")
    assert _path(pg) == "/word/G26?list=with:G4102"
    # Close: back through the study's entries to where the word was tapped
    pg.tap("#word-study .ws-bar button:visible")   # back from the list
    pg.wait_for_function("!Alpine.$data(document.body).ws.list")
    pg.tap("#word-study .ws-bar button:visible")   # close
    pg.wait_for_function("!Alpine.$data(document.body).ws.open")
    pg.wait_for_function("location.pathname === '/1-John/4/8'")
    assert _app(pg, "a.currentBook") == "1 John"


def test_deep_link_homographs_and_back(server, browser):
    ctx, pg, errors = new_page(browser, 360, 740)
    pg.goto(f"{server}/word/H2617")
    _study_ready(pg)
    assert pg.inner_text("#ws-title") == "חֵסֵד"
    assert pg.get_attribute("#ws-title", "dir") == "rtl"
    hg = pg.locator(".ws-hg")
    assert hg.count() == 2
    assert "kindness" in hg.nth(0).inner_text() and hg.nth(0).get_attribute("aria-pressed") == "true"
    assert "245 times" in pg.inner_text(".ws-count")
    hg.nth(1).click()
    pg.wait_for_function("Alpine.$data(document.body).ws.data?.occurrences.homograph === 'H2617B'")
    assert _path(pg) == "/word/H2617?homograph=H2617B"
    assert "Twice" in pg.inner_text(".ws-count") or "2 times" in pg.inner_text(".ws-count")
    # BDB is credited (CC BY): the OpenScriptures line
    assert "Open Scriptures Hebrew Bible Project" in pg.inner_text("#ws-sec-lex")
    # A related word opens its own study; Back returns
    pg.locator("#ws-sec-related .ws-word-row", has_text="ḥāsad").click()
    pg.wait_for_function("Alpine.$data(document.body).ws.strong === 'H2616' && Alpine.$data(document.body).ws.data")
    assert _path(pg) == "/word/H2616"
    pg.go_back()
    pg.wait_for_function("Alpine.$data(document.body).ws.strong === 'H2617' && Alpine.$data(document.body).ws.data")
    # Homographs only show when a number has them
    pg.goto(f"{server}/word/G26")
    _study_ready(pg)
    assert pg.locator(".ws-hg").count() == 0
    # Closing a deep link leaves Home underneath
    pg.click("#word-study .ws-bar button:visible")
    pg.wait_for_function("!Alpine.$data(document.body).ws.open")
    assert _path(pg) == "/"
    # A function word: no collocates computed, so no section; a malformed number says so
    pg.goto(f"{server}/word/G3588")
    _study_ready(pg)
    assert not pg.is_visible("#ws-sec-with")
    assert "Small words like this one" in pg.inner_text("#ws-sec-tr")
    pg.goto(f"{server}/word/X99")
    pg.wait_for_selector("#word-study[open] .ws-state-title:visible")
    assert "isn't a Strong's number" in pg.inner_text("#word-study .ws-state-title")
    ctx.close()
    assert not errors, errors


def test_withheld_link_offers_no_confident_study(server, browser):
    ctx, pg, errors = new_page(browser, 1280, 800, touch=False)
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-3")
    pg.evaluate("Alpine.$data(document.body).translation = 'WEB'")
    pg.wait_for_function("document.querySelector('#verse-3').textContent.includes('certainly')")
    pg.click('#verse-3 .word[data-position="5"]')
    pg.wait_for_selector(".word-unsure:visible")
    assert not pg.is_visible(".qw-study")
    pg.click(".word-reveal")
    pg.wait_for_selector(".qw-study:visible")
    assert pg.inner_text(".qw-study").startswith("Study the closest match")
    assert "Not certain" in pg.inner_text(".word-unsure-note")
    pg.click(".qw-study")
    _study_ready(pg)
    note = pg.inner_text(".ws-from")
    assert "closest match for “certainly” in John 3:3" in note and "weak" in note
    ctx.close()
    assert not errors, errors


def test_search_strongs_number_opens_the_study(server, browser):
    ctx, pg, errors = new_page(browser, 1280, 800, touch=False)
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-3")
    pg.evaluate("Alpine.$data(document.body).showSearch = true")
    pg.fill(".input-search", "G4102")
    pg.keyboard.press("Enter")
    pg.wait_for_selector(".strongs-study:visible")
    pg.click(".strongs-study")
    _study_ready(pg)
    assert _path(pg) == "/word/G4102"
    assert _nfc(pg.inner_text("#ws-title")) == _nfc("πίστις")
    ctx.close()
    assert not errors, errors


def test_offline_word_study_is_clear_not_broken(server, browser):
    ctx, pg, errors = new_page(browser, 390, 844)
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-3")
    ctx.set_offline(True)
    pg.evaluate("Alpine.$data(document.body).openWordStudy('G5')")
    pg.wait_for_selector(".ws-offline:visible")
    assert "isn't saved on this device" in pg.inner_text(".ws-offline")
    assert not pg.is_visible(".ws-state-title")
    ctx.set_offline(False)
    pg.click(".ws-offline .study-primary-btn")
    _study_ready(pg)
    assert re.search(r"Abba|father", pg.inner_text("#word-study"), re.I)
    ctx.close()
    assert not [e for e in errors if "Failed to fetch" not in e], errors
