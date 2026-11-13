"""Browser flows for the study view's Hymns pane (modules/hymns.js): shown only where
hymns are linked, the passage's hymns before the chapter's, why each is linked (a
computed quotation with its evidence), a hymn's sheet, and studying one of its passages.

Uses the shared server and browser (conftest.py).
"""
import pytest

from tests.e2e.conftest import new_page

pytest.importorskip("playwright.sync_api")

HPANE = '.study-pane[data-slug="hymns"]'
HTOOL = '.study-tool[data-slug="hymns"]'


def _app(pg, expr):
    return pg.evaluate(f"(() => {{ const a = Alpine.$data(document.body); return {expr}; }})()")


def _open(pg, server, path):
    pg.goto(f"{server}{path}")
    pg.wait_for_selector("#study-view[open]")
    pg.wait_for_function("!Alpine.$data(document.body).study.loading")
    pg.wait_for_function("['ready', 'none'].includes(Alpine.$data(document.body).studyHymns.status)")


@pytest.fixture
def phone(browser):
    ctx, pg, errors = new_page(browser, 390, 844)
    yield pg
    ctx.close()
    assert not errors, errors


def test_psalm_23_and_100_have_hymns(server, phone):
    pg = phone
    _open(pg, server, "/Psalms/23/1-6?study=hymns")
    assert pg.is_visible(HTOOL)
    pg.wait_for_function("Alpine.$data(document.body).study.active === 'hymns'")
    assert pg.locator(HTOOL).get_attribute("aria-pressed") == "true"
    n = _app(pg, "a.studyHymns.passage.length")
    assert n >= 10
    assert pg.inner_text(f"{HTOOL} .study-tool-count") == str(n)
    text = pg.inner_text(HPANE)
    assert "not a complete list" in text
    first = pg.locator(f"{HPANE} .hymn-item").first
    assert first.locator(".hymn-title").inner_text() == "The Lord's My Shepherd"
    assert "Scottish Psalter" in first.inner_text()
    assert "Tune: Marosa" in first.inner_text()
    # A metrical psalm whose title is only a number leads with its first line
    assert pg.locator(f"{HPANE} .hymn-title", has_text="My shepherd is the living Lord").count() == 1
    # Words under copyright: no first line
    assert "Cloud Received Christ" in text
    card = pg.locator(f"{HPANE} .hymn-item", has_text="Cloud Received Christ")
    assert card.locator(".hymn-first:visible").count() == 0

    _open(pg, server, "/Psalms/100/1?study=hymns")
    assert pg.is_visible(HTOOL)
    assert pg.locator(f"{HPANE} .hymn-title", has_text="All People That On Earth Do Dwell").count() == 1
    assert "A metrical version of Psalm 100" in pg.inner_text(HPANE)


def test_no_hymns_no_pane(server, phone):
    pg = phone
    _open(pg, server, "/Leviticus/13/2?study=cross-references")
    assert _app(pg, "a.studyHymns.status") == "ready"
    assert not pg.is_visible(HTOOL)
    assert not pg.is_visible(HPANE)
    assert "hymns" not in _app(pg, "a.studyPaneOrder()")
    # A link straight to hymns where there are none lands on a pane that exists
    _open(pg, server, "/Leviticus/13/2?study=hymns")
    pg.wait_for_function("Alpine.$data(document.body).study.active !== 'hymns'")
    assert not pg.is_visible(HPANE)


def test_chapter_hymns_are_a_separate_group(server, phone):
    pg = phone
    _open(pg, server, "/Romans/8/28?study=hymns")
    groups = pg.locator(f"{HPANE} .hymn-group:visible")
    assert groups.count() == 2
    assert groups.nth(1).locator("h4").inner_text() == "On other verses of Romans 8"
    assert "Romans 8:" in groups.nth(1).inner_text()


def test_computed_quotation_shows_evidence_and_hymn_sheet_studies_a_passage(server, phone):
    pg = phone
    _open(pg, server, "/Revelation/4/8?study=hymns")
    card = pg.locator(f"{HPANE} .hymn-item", has_text="Holy, Holy, Holy").first
    why = card.locator(".hymn-why.is-computed")
    assert "Computed" in why.inner_text()
    assert why.locator(".hymn-evidence").inner_text() == "holy holy holy lord god almighty"
    assert "Revelation 4:8 in the KJV" in why.inner_text()

    card.tap()
    pg.wait_for_selector("#study-hymn[open] .hymn-passage")
    sheet = pg.locator("#study-hymn")
    assert "Heber" in sheet.inner_text()
    refs = sheet.locator(".hymn-passage-ref").all_inner_texts()
    assert refs == ["Study Isaiah 6:3", "Study Revelation 4:4–11", "Study Revelation 4:8"]
    sheet.locator(".hymn-passage", has_text="Isaiah 6:3").tap()
    pg.wait_for_function("""Alpine.$data(document.body).studyRefLabel() === 'Isaiah 6:3'
        && !Alpine.$data(document.body).study.loading""")
    assert not pg.is_visible("#study-hymn")
    assert "Back to" in pg.inner_text(".study-back")
    pg.go_back()
    pg.wait_for_function("Alpine.$data(document.body).studyRefLabel() === 'Revelation 4:8'")
