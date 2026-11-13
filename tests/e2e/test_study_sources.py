"""Browser flows for choosing commentaries (modules/study.js): the chip rail at phone width,
the All sheet, and Settings > Commentaries (show/hide, order, reset, new sources, the
last-source rule, links to a turned-off source).

Uses the shared server and browser (conftest.py). 390x844 unless a test says otherwise.
"""
import json

import pytest

from tests.e2e.conftest import new_page

pytest.importorskip("playwright.sync_api")

PREFS = "studySourcePrefs"
DEFAULT = [
    "scofield-notes-1917", "john-gill", "jamieson-fausset-brown", "tyndale-study-notes",
    "gaebelein-annotated-bible", "ironside-expositions", "newell-verse-by-verse", "darby-synopsis",
    "brooks-summarized-bible", "mackintosh-notes-on-the-pentateuch", "larkin-on-revelation",
    "treasury-of-david",
]
# Nothing on John 3:16 (the library as of DB 2026.11.13.2)
EMPTY_ON_JOHN_3_16 = {"ironside-expositions", "newell-verse-by-verse",
                      "mackintosh-notes-on-the-pentateuch", "larkin-on-revelation", "treasury-of-david"}

# The active chip's box lies inside the chip row's visible box
ACTIVE_CHIP_IN_VIEW = """() => {
    const row = document.querySelector('#study-view .study-chips').getBoundingClientRect();
    const chip = document.querySelector('#study-view .study-chip[aria-pressed="true"]');
    if (!chip) return false;
    const r = chip.getBoundingClientRect();
    return r.width > 0 && r.left >= row.left && r.right <= row.right;
}"""


def _app(pg, expr):
    return pg.evaluate(f"(() => {{ const a = Alpine.$data(document.body); return {expr}; }})()")


def _open(pg, server, path):
    pg.goto(f"{server}{path}")
    pg.wait_for_selector("#study-view[open]")
    pg.wait_for_function("!Alpine.$data(document.body).study.loading")
    pg.wait_for_selector("#study-view .study-chip[aria-pressed='true']")


def _rail(pg):
    return [c.get_attribute("data-slug") for c in pg.locator("#study-view .study-chip").all()]


def _set_prefs(pg, server, prefs):
    pg.goto(f"{server}/")
    pg.evaluate(f"localStorage.setItem('{PREFS}', {json.dumps(json.dumps(prefs))})")


def _prefs(pg):
    return json.loads(pg.evaluate(f"localStorage.getItem('{PREFS}') || '{{}}'"))


def _open_all(pg):
    pg.tap("#study-view .study-all-btn")
    pg.wait_for_selector("#study-all[open] .study-all-item")


def _sheet(pg):
    return [li.get_attribute("data-slug") for li in pg.locator("#study-all li").all()]


def _settings_from_study(pg):
    _open_all(pg)
    pg.tap("#study-all .study-all-choose")
    pg.wait_for_selector(".settings-modal .cm-row")
    pg.wait_for_function("!document.getElementById('study-view').open")


def _close_settings_back_to_study(pg):
    pg.click(".settings-modal .btn-close")
    pg.wait_for_function("document.getElementById('study-view').open")
    pg.wait_for_function("document.activeElement?.classList.contains('study-all-btn')")


def _settings_order(pg):
    return [r.get_attribute("data-slug") for r in pg.locator(".settings-modal .cm-row").all()]


@pytest.fixture
def phone(browser):
    ctx, pg, errors = new_page(browser, 390, 844)
    yield pg
    ctx.close()
    assert not errors, errors


# ---------- the rail ----------

def test_late_source_chip_is_fully_in_view(server, phone):
    """Romans 8:1 with Newell (7th of 9 chips): fully in view once the view has settled,
    including after the Hymns button appears and narrows the row (the clipping bug)."""
    pg = phone
    _open(pg, server, "/Romans/8/1?study=newell-verse-by-verse")
    pg.wait_for_function("Alpine.$data(document.body).studyHymns.status !== 'loading' && Alpine.$data(document.body).studyHymns.status !== 'idle'")
    pg.wait_for_selector('#study-view .study-tool[data-slug="hymns"]', state="visible")
    assert _app(pg, "a.study.active") == "newell-verse-by-verse"
    pg.wait_for_function(ACTIVE_CHIP_IN_VIEW)
    # Swiping (the arrow keys step panes the same way): still in view, every time
    for slug in ["darby-synopsis", "brooks-summarized-bible"]:
        pg.focus(".study-track .study-pane.is-active .study-pane-scroll")
        pg.keyboard.press("ArrowRight")
        pg.wait_for_function(f"Alpine.$data(document.body).study.active === '{slug}'")
        pg.wait_for_function(ACTIVE_CHIP_IN_VIEW)
    # Back to the first chip by tapping: the row scrolls to it
    pg.evaluate("document.querySelector('#study-view .study-chips').scrollLeft = 0")
    pg.tap('#study-view .study-chip[data-slug="scofield-notes-1917"]')
    pg.wait_for_function("Alpine.$data(document.body).study.active === 'scofield-notes-1917'")
    pg.wait_for_function(ACTIVE_CHIP_IN_VIEW)


def test_sources_with_nothing_here_are_only_in_the_all_sheet(server, phone):
    pg = phone
    _open(pg, server, "/John/3/16?study=")
    rail = _rail(pg)
    assert not EMPTY_ON_JOHN_3_16 & set(rail)
    assert rail == [s for s in DEFAULT if s not in EMPTY_ON_JOHN_3_16]
    # Swiping moves among the same sources: no pane for a source with nothing here
    panes = [p.get_attribute("data-slug") for p in pg.locator(".study-track > .study-pane:not(.study-pane-tool)").all()]
    assert panes == rail
    # All: every source, in order, the empty ones marked as nothing here
    assert pg.inner_text("#study-view .study-all-btn").split() == ["All", "12"]
    _open_all(pg)
    assert _sheet(pg) == DEFAULT
    for slug in EMPTY_ON_JOHN_3_16:
        row = pg.locator(f'#study-all li[data-slug="{slug}"]')
        assert "Nothing here" in row.inner_text()
        assert not row.locator("button.study-all-item").count()   # nothing to switch to
    assert "Verse note, verse 16" in pg.inner_text('#study-all li[data-slug="john-gill"]')
    assert pg.get_attribute('#study-all li[data-slug="scofield-notes-1917"] .study-all-item', "aria-current") == "true"


def test_all_sheet_offers_the_nearest_note(server, phone):
    """Scofield has nothing on Revelation 20:1; the sheet offers its nearest note."""
    pg = phone
    _open(pg, server, "/Revelation/20/1?study=")
    _open_all(pg)
    offer = pg.locator('#study-all li[data-slug="scofield-notes-1917"] .study-all-nearest')
    assert offer.is_visible() and "Nearest note: study verse" in offer.inner_text()
    offer.tap()
    pg.wait_for_function("!document.getElementById('study-all').open")
    pg.wait_for_function("Alpine.$data(document.body).study.active === 'scofield-notes-1917' && !Alpine.$data(document.body).study.loading")
    assert pg.inner_text("#study-title") != "Revelation 20:1"


def test_all_sheet_switches_source_closes_and_returns_focus(server, phone):
    pg = phone
    _open(pg, server, "/John/3/16?study=john-gill")
    _open_all(pg)
    # Focus moved into the sheet, onto the source in view
    assert pg.evaluate("document.activeElement.closest('#study-all li')?.dataset.slug") == "john-gill"
    # Escape closes it and focus comes back to All; the study view stays open
    pg.keyboard.press("Escape")
    pg.wait_for_function("!document.getElementById('study-all').open")
    pg.wait_for_function("document.activeElement?.classList.contains('study-all-btn')")
    assert pg.evaluate("document.getElementById('study-view').open")
    # A source with something here: switches, closes, focus back on All
    _open_all(pg)
    pg.tap('#study-all li[data-slug="darby-synopsis"] .study-all-item')
    pg.wait_for_function("!document.getElementById('study-all').open")
    pg.wait_for_function("Alpine.$data(document.body).study.active === 'darby-synopsis'")
    pg.wait_for_function("document.activeElement?.classList.contains('study-all-btn')")
    pg.wait_for_selector('.study-pane[data-slug="darby-synopsis"] .study-pane-body p')
    pg.wait_for_function(ACTIVE_CHIP_IN_VIEW)
    assert pg.evaluate("location.search") == "?study=darby-synopsis"


# ---------- Settings > Commentaries ----------

def test_hide_a_source_from_the_study_view_then_link_to_it(server, phone):
    pg = phone
    _open(pg, server, "/John/3/16?study=john-gill")
    _settings_from_study(pg)
    assert pg.get_attribute(".settings-nav-btn.active", "class") and "Commentaries" in pg.inner_text(".settings-nav-btn.active")
    assert _settings_order(pg) == DEFAULT
    gill = pg.locator('.cm-row[data-slug="john-gill"]')
    assert "John Gill (1697–1771) · 1746" in gill.inner_text() and "Baptist" in gill.inner_text()
    gill.locator(".cm-switch").click()
    assert pg.locator('.cm-row[data-slug="john-gill"] input').is_checked() is False
    assert _prefs(pg)["hidden"] == ["john-gill"]
    # Back in the study view, without a reload: Gill was in view, so the first source left is
    _close_settings_back_to_study(pg)
    pg.wait_for_function("Alpine.$data(document.body).study.active === 'scofield-notes-1917'")
    assert "john-gill" not in _rail(pg)
    assert "john-gill" not in [p.get_attribute("data-slug") for p in pg.locator(".study-track > .study-pane").all()]
    assert pg.inner_text("#study-view .study-all-btn").split() == ["All", "11"]
    _open_all(pg)
    assert "john-gill" not in _sheet(pg)
    pg.keyboard.press("Escape")
    # A link to it still opens it, for that visit
    pg.goto(f"{server}/John/3/16?study=john-gill")
    pg.wait_for_selector('.study-pane[data-slug="john-gill"] .study-pane-body p')
    assert _app(pg, "a.study.active") == "john-gill" and "john-gill" in _rail(pg)
    assert pg.evaluate("location.search") == "?study=john-gill"
    # ...and not on the next one
    pg.keyboard.press("Escape")
    pg.wait_for_function("!document.getElementById('study-view').open")
    pg.evaluate("Alpine.$data(document.body).openStudy('John 3:16')")
    pg.wait_for_function("!Alpine.$data(document.body).study.loading")
    pg.wait_for_selector("#study-view .study-chip[aria-pressed='true']")
    assert "john-gill" not in _rail(pg)


def test_reorder_then_reset(server, phone):
    pg = phone
    _open(pg, server, "/John/3/16?study=")
    _settings_from_study(pg)
    # Tyndale up two: before Gill and JFB. Focus stays on the arrow.
    pg.click('[data-move="tyndale-study-notes:-1"]')
    pg.wait_for_function("document.activeElement?.dataset.move === 'tyndale-study-notes:-1'")
    pg.click('[data-move="tyndale-study-notes:-1"]')
    # Darby to the very top: the up arrow disables there, focus moves to its down arrow
    for _ in range(7):
        pg.click('[data-move="darby-synopsis:-1"]')
    assert pg.is_disabled('[data-move="darby-synopsis:-1"]')
    pg.wait_for_function("document.activeElement?.dataset.move === 'darby-synopsis:1'")
    expected = ["darby-synopsis", "scofield-notes-1917", "tyndale-study-notes", "john-gill", "jamieson-fausset-brown"]
    assert _settings_order(pg)[:5] == expected
    assert _prefs(pg)["order"][:5] == expected
    _close_settings_back_to_study(pg)
    assert _rail(pg)[:5] == expected   # the rail follows, no reload
    _open_all(pg)
    assert _sheet(pg)[:5] == expected
    pg.keyboard.press("Escape")
    # Reset puts the default order back and turns everything on
    _settings_from_study(pg)
    pg.locator('.cm-row[data-slug="brooks-summarized-bible"] .cm-switch').click()
    assert not pg.locator('.cm-row[data-slug="brooks-summarized-bible"] input').is_checked()
    pg.click(".settings-modal .cm-reset")
    assert _settings_order(pg) == DEFAULT
    assert pg.locator('.cm-row[data-slug="brooks-summarized-bible"] input').is_checked()
    assert _prefs(pg)["order"] == [] and _prefs(pg)["hidden"] == []
    _close_settings_back_to_study(pg)
    assert _rail(pg) == [s for s in DEFAULT if s not in EMPTY_ON_JOHN_3_16]


def test_saved_order_from_an_older_library_shows_new_sources_in_place(server, phone):
    """A device that saved its order before six sources were added (and when Matthew Henry
    was in the library): the new ones appear, each after its default neighbour."""
    pg = phone
    _set_prefs(pg, server, {"order": ["john-gill", "matthew-henry", "scofield-notes-1917", "jamieson-fausset-brown",
                                      "tyndale-study-notes", "ironside-expositions", "darby-synopsis"],
                            "hidden": ["matthew-henry"], "last": "matthew-henry"})
    _open(pg, server, "/Revelation/20/1?study=")
    expected = ["john-gill", "scofield-notes-1917", "jamieson-fausset-brown", "tyndale-study-notes",
                "gaebelein-annotated-bible", "ironside-expositions", "newell-verse-by-verse", "darby-synopsis",
                "brooks-summarized-bible", "mackintosh-notes-on-the-pentateuch", "larkin-on-revelation",
                "treasury-of-david"]
    assert _rail(pg) == [s for s in expected if s in {
        "john-gill", "jamieson-fausset-brown", "tyndale-study-notes", "gaebelein-annotated-bible",
        "newell-verse-by-verse", "darby-synopsis", "brooks-summarized-bible", "larkin-on-revelation"}]
    assert _app(pg, "a.study.active") == "john-gill"
    _open_all(pg)
    assert _sheet(pg) == expected
    pg.keyboard.press("Escape")
    _settings_from_study(pg)
    assert _settings_order(pg) == expected


def test_cannot_turn_every_source_off(server, phone):
    pg = phone
    _open(pg, server, "/John/3/16?study=")
    _settings_from_study(pg)
    for slug in DEFAULT[:-1]:
        pg.locator(f'.cm-row[data-slug="{slug}"] .cm-switch').click()
    last = pg.locator(f'.cm-row[data-slug="{DEFAULT[-1]}"] input')
    assert last.is_checked() and last.is_disabled()
    pg.locator(f'.cm-row[data-slug="{DEFAULT[-1]}"] .cm-switch').click(force=True)
    assert last.is_checked()
    assert len(_prefs(pg)["hidden"]) == 11
    # Spurgeon (Psalms only) is all that's on: nothing on John 3:16, and the view says so
    _close_settings_back_to_study(pg)
    assert _rail(pg) == []
    assert pg.is_visible("#study-view .study-chips-none")
    assert pg.inner_text("#study-view .study-all-btn").split() == ["All", "1"]
    # Every source turned off some other way (an old device): all of them show
    pg.evaluate(f"localStorage.setItem('{PREFS}', JSON.stringify({{ order: [], hidden: {json.dumps(DEFAULT)} }}))")
    pg.goto(f"{server}/John/3/16?study=")
    pg.wait_for_function("!Alpine.$data(document.body).study.loading")
    pg.wait_for_selector("#study-view .study-chip[aria-pressed='true']")
    assert _rail(pg) == [s for s in DEFAULT if s not in EMPTY_ON_JOHN_3_16]


def test_storage_unavailable_uses_defaults(server, browser):
    ctx, pg, errors = new_page(browser, 390, 844)
    ctx.add_init_script("""(() => {
        const real = Storage.prototype.getItem;
        Storage.prototype.getItem = function (k) { if (k === 'studySourcePrefs') throw new Error('blocked'); return real.call(this, k); };
        const realSet = Storage.prototype.setItem;
        Storage.prototype.setItem = function (k, v) { if (k === 'studySourcePrefs') throw new Error('blocked'); return realSet.call(this, k, v); };
    })()""")
    _open(pg, server, "/John/3/16?study=")
    assert _rail(pg) == [s for s in DEFAULT if s not in EMPTY_ON_JOHN_3_16]
    _settings_from_study(pg)
    pg.click('[data-move="john-gill:-1"]')   # can't be saved: nothing breaks
    _close_settings_back_to_study(pg)
    assert _rail(pg)[0] == "scofield-notes-1917"
    ctx.close()
    assert not errors, errors


def test_settings_tab_without_the_study_view(server, phone):
    """Settings > Commentaries from the menu: the list is there, changes apply on next open."""
    pg = phone
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-16")
    pg.wait_for_function("Alpine.$data(document.body).studySourceMeta.length === 12")
    pg.evaluate("Alpine.$data(document.body).openSettings('commentaries')")
    pg.wait_for_selector(".settings-modal .cm-row")
    assert _settings_order(pg) == DEFAULT
    pg.locator('.cm-row[data-slug="scofield-notes-1917"] .cm-switch').click()
    pg.click(".settings-modal .btn-close")
    pg.wait_for_function("!Alpine.$data(document.body).showSettings")
    assert not pg.evaluate("document.getElementById('study-view').open")
    pg.evaluate("Alpine.$data(document.body).openStudy('John 3:16')")
    pg.wait_for_function("!Alpine.$data(document.body).study.loading")
    pg.wait_for_selector("#study-view .study-chip[aria-pressed='true']")
    assert _rail(pg)[0] == "john-gill" and "scofield-notes-1917" not in _rail(pg)
