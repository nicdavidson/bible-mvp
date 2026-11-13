"""Browser flows for the study view's Cross-references and Notes panes
(modules/study_panes.js): reading cross-references inline, peeking and coming back,
writing and editing notes on a selection, overlapping notes, deep links, the reader's
source order, offline, and writing with the keyboard up.

Uses the shared server and browser (conftest.py).
"""
import json

import pytest

from tests.e2e.conftest import new_page

pytest.importorskip("playwright.sync_api")

XPANE = '.study-pane[data-slug="cross-references"]'
NPANE = '.study-pane[data-slug="notes"]'


def _app(pg, expr):
    return pg.evaluate(f"(() => {{ const a = Alpine.$data(document.body); return {expr}; }})()")


def _path(pg):
    return pg.evaluate("location.pathname + location.search")


def _study_ready(pg):
    pg.wait_for_selector("#study-view[open]")
    pg.wait_for_function("!Alpine.$data(document.body).study.loading")


@pytest.fixture
def phone(browser):
    ctx, pg, errors = new_page(browser, 390, 844)
    yield pg
    ctx.close()
    assert not errors, errors


def _select_range(pg, server):
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-16")
    pg.locator("#verse-16").scroll_into_view_if_needed()
    pg.tap("#verse-16 .verse-num")
    pg.tap("#verse-18 .verse-num")
    assert _app(pg, "a.highlightedVerses") == [16, 17, 18]
    pg.wait_for_function("""() => { const bar = document.querySelector('.verse-action-bar');
        return bar && bar.style.display !== 'none' && getComputedStyle(bar).opacity === '1'; }""")


def test_crossrefs_swipe_read_inline_peek_and_return(server, phone):
    pg = phone
    _select_range(pg, server)
    pg.tap(".verse-action-bar .action-bar-study")
    _study_ready(pg)
    assert pg.get_attribute(".study-chip[aria-pressed='true']", "data-slug") not in (None, "cross-references")
    # The pinned button says how many there are
    pg.wait_for_function("Alpine.$data(document.body).studyXref.status === 'ready'")
    total = _app(pg, "a.studyXref.items.length")
    assert total > 40
    assert pg.inner_text('.study-tool[data-slug="cross-references"] .study-tool-count') == str(total)

    # Swipe past the commentary to the cross-references (the track is a scroll-snap carousel)
    pg.wait_for_timeout(700)   # a swipe right after opening is taken as the view placing itself
    pg.evaluate(f"""() => {{ const t = document.querySelector('.study-track');
        t.scrollTo({{ left: document.querySelector('{XPANE}').offsetLeft }}); }}""")
    pg.wait_for_function("Alpine.$data(document.body).study.active === 'cross-references'", timeout=5000)
    assert _path(pg).endswith("?study=cross-references")
    # Commentary stays the remembered source
    assert "cross" not in (json.loads(pg.evaluate("localStorage.getItem('studySourcePrefs') || '{}'")).get("last") or "")

    # Grouped by verse, strongest first, text inline; the rest one tap away
    groups = pg.locator(f"{XPANE} .xref-group h4").all_inner_texts()
    assert groups == ["On verse 16", "On verse 17", "On verse 18"]
    first = pg.locator(f"{XPANE} .xref-item").first
    assert first.locator(".xref-ref").inner_text() == "Romans 5:8"
    assert "But God proves His love" in first.locator(".xref-text").inner_text()
    shown = pg.locator(f"{XPANE} .xref-item").count()
    assert shown == 9
    pg.tap(f"{XPANE} .xref-more")
    assert pg.locator(f"{XPANE} .xref-item").count() == total
    pg.tap(f"{XPANE} .xref-order button >> text=Bible order")
    assert pg.locator(f"{XPANE} .xref-group").first.locator(".xref-ref").first.inner_text().startswith("Genesis")
    assert "OpenBible.info" in pg.inner_text(f"{XPANE} .study-attribution")

    # Tap a reference: the peek shows it in its context, and can study it
    pg.tap(f"{XPANE} .xref-item >> nth=0")
    pg.wait_for_selector("#study-peek[open] .study-verse")
    target = pg.inner_text("#study-peek-title")
    assert pg.locator("#study-peek .study-verse.is-context").count() >= 2
    assert pg.locator("#study-peek .study-verse:not(.is-context)").count() == 1
    pg.locator("#study-peek .study-primary-btn").click()
    pg.wait_for_function(f"document.getElementById('study-title').textContent === {target.replace('-', '–')!r}")
    pg.go_back()
    pg.wait_for_function("document.getElementById('study-title').textContent === 'John 3:16–18'")
    assert _path(pg) == "/John/3/16-18?study=cross-references"
    pg.wait_for_function("Alpine.$data(document.body).study.active === 'cross-references'")

    # Read the chapter: a jump, and the chip comes back to these cross-references
    pg.tap(f"{XPANE} .xref-item >> nth=0")
    pg.wait_for_selector("#study-peek[open] .study-verse")
    pg.locator("#study-peek .study-text-btn", has_text="Read the chapter").click()
    pg.wait_for_function("!document.getElementById('study-view').open && !Alpine.$data(document.body).navBusy")
    assert "Back to cross-references on John 3:16–18" in pg.inner_text(".return-chip-back")
    pg.tap(".return-chip-back")
    _study_ready(pg)
    assert _path(pg) == "/John/3/16-18?study=cross-references"


def test_note_on_a_range_close_reopen_edit_and_overlap(server, phone):
    pg = phone
    _select_range(pg, server)
    pg.tap(".verse-action-bar .action-bar-note")
    _study_ready(pg)
    assert _app(pg, "a.study.active") == "notes"
    # A first-time reader is told what this is for
    assert "only you can see them" in pg.inner_text(f"{NPANE} .study-tool-sub")
    pg.fill("#snote-new-ta", "Love gives first.")
    pg.tap(f"{NPANE} .note-save")
    pg.wait_for_selector(f"{NPANE} .snote .snote-text")
    stored = json.loads(pg.evaluate("localStorage.getItem('bible-notes')"))
    assert stored[0]["book"] == "John" and stored[0]["chapter"] == 3
    assert (stored[0]["startVerse"], stored[0]["endVerse"]) == (16, 18)
    assert pg.inner_text('.study-tool[data-slug="notes"] .study-tool-count') == "1"

    # Close, reopen: it's there
    pg.tap(".study-bar .study-icon-btn")
    pg.wait_for_function("!document.getElementById('study-view').open")
    pg.wait_for_timeout(300)
    pg.tap(".verse-action-bar .action-bar-note")
    _study_ready(pg)
    assert pg.inner_text(f"{NPANE} .snote-text") == "Love gives first."

    # Edit in place
    pg.tap(f"{NPANE} .snote-edit")
    pg.fill(f"{NPANE} .snote textarea", "Love gives first, and gives the Son.")
    pg.tap(f"{NPANE} .snote .note-save")
    pg.wait_for_function(f"document.querySelector('{NPANE} .snote-text')?.textContent === 'Love gives first, and gives the Son.'")
    assert len(json.loads(pg.evaluate("localStorage.getItem('bible-notes')"))) == 1

    # Unsaved writing survives closing the view
    pg.tap(f"{NPANE} .snote-add")
    pg.fill("#snote-new-ta", "A second thought.")
    pg.tap(".study-bar .study-icon-btn")
    pg.wait_for_function("!document.getElementById('study-view').open")
    pg.wait_for_function("JSON.parse(localStorage.getItem('bible-notes')).length === 2")

    # Studying v16 alone: the range note shows, labelled with its own verses
    pg.goto(f"{server}/John/3/16?study=notes")
    _study_ready(pg)
    pg.wait_for_selector(f"{NPANE} .snote.is-nearby")
    assert pg.inner_text(f"{NPANE} .snotes-nearby h4") == "Your notes on overlapping verses"
    assert pg.locator(f"{NPANE} .snote.is-nearby .snote-ref").first.inner_text() == "John 3:16–18"
    assert pg.is_visible("#snote-new-ta")   # nothing on v16 itself yet: the composer
    # Its label goes to those verses, where it can be edited
    pg.tap(f"{NPANE} .snote.is-nearby .snote-ref >> nth=0")
    pg.wait_for_function("document.getElementById('study-title').textContent === 'John 3:16–18'")
    assert pg.locator(f"{NPANE} .snote:not(.is-nearby)").count() == 2


@pytest.mark.parametrize("slug,ready", [
    ("cross-references", f"{XPANE} .xref-item"),
    ("notes", "#snote-new-ta"),
])
def test_deep_links_to_the_panes(server, phone, slug, ready):
    phone.goto(f"{server}/Romans/8/28?study={slug}")
    _study_ready(phone)
    phone.wait_for_selector(ready)
    assert _app(phone, "a.study.active") == slug
    assert phone.get_attribute(f'.study-tool[data-slug="{slug}"]', "aria-pressed") == "true"
    # The pane is the one in view
    box = phone.locator(f'.study-pane[data-slug="{slug}"]').bounding_box()
    assert abs(box["x"]) < 2
    phone.keyboard.press("Escape")
    phone.wait_for_function("!document.getElementById('study-view').open")
    assert _path(phone) == "/Romans/8/28"


def test_saved_source_order_and_hidden_sources_still_respected(server, phone):
    phone.goto(f"{server}/")
    phone.evaluate("""localStorage.setItem('studySourcePrefs', JSON.stringify(
        { order: ['john-gill', 'matthew-henry'], hidden: ['matthew-henry'], last: null }))""")
    phone.goto(f"{server}/John/3/16")
    phone.wait_for_selector("#verse-16")
    phone.evaluate("Alpine.$data(document.body).openStudy('John 3:16')")
    _study_ready(phone)
    slugs = [c.get_attribute("data-slug") for c in phone.locator(".study-chip:not(.is-empty)").all()]
    assert slugs[0] == "john-gill" and "matthew-henry" not in slugs
    panes = [p.get_attribute("data-slug") for p in phone.locator(".study-track > .study-pane").all()]
    assert panes[0] == "john-gill" and panes[-2:] == ["cross-references", "notes"]
    # The tools aren't sources: not in Your sources, never remembered as the last source
    phone.tap('.study-tool[data-slug="cross-references"]')
    phone.wait_for_function("Alpine.$data(document.body).study.active === 'cross-references'")
    prefs = json.loads(phone.evaluate("localStorage.getItem('studySourcePrefs')"))
    assert prefs["order"] == ["john-gill", "matthew-henry"] and prefs["hidden"] == ["matthew-henry"]
    assert prefs.get("last") in (None, "john-gill")
    phone.tap(".study-manage-btn")
    phone.wait_for_selector("#study-manage[open]")
    names = phone.locator("#study-manage .study-manage-name").all_inner_texts()
    assert not any("Cross-ref" in n or "notes" == n.lower() for n in names)
    phone.keyboard.press("Escape")
    phone.wait_for_function("!document.getElementById('study-manage').open")


def test_offline_both_panes_for_a_cached_chapter(server, browser):
    ctx, pg, errors = new_page(browser, 390, 844)
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-16")
    pg.wait_for_function("!Alpine.$data(document.body).loading")
    pg.wait_for_timeout(1200)   # the chapter (verses + cross-references) lands in IndexedDB
    pg.evaluate("""localStorage.setItem('bible-notes', JSON.stringify([{ id: 1, book: 'John', chapter: 3,
        startVerse: 16, endVerse: 16, content: 'Saved before going offline.', created_at: new Date().toISOString(), synced: false }]))""")
    pg.reload()
    pg.wait_for_selector("#verse-16")
    ctx.set_offline(True)
    pg.evaluate("Alpine.$data(document.body).openStudy('John 3:16', { source: 'cross-references' })")
    _study_ready(pg)
    pg.wait_for_selector(f"{XPANE} .xref-item")
    assert _app(pg, "a.studyXref.offline")
    pg.tap(f"{XPANE} .xref-more")
    # A link into the saved chapter has its text; the rest show their reference and say why
    item = pg.locator(f"{XPANE} .xref-item", has_text="John 3:15")
    assert "everyone who believes in Him may have eternal life" in item.inner_text()
    assert "aren't saved on this device" in pg.inner_text(f"{XPANE} .study-note")
    pg.tap('.study-tool[data-slug="notes"]')
    pg.wait_for_selector(f"{NPANE} .snote-text")
    assert pg.inner_text(f"{NPANE} .snote-text") == "Saved before going offline."
    ctx.close()
    assert not errors, errors


def test_writing_with_the_keyboard_up_keeps_verses_and_field_in_view(server, browser):
    for (w, h) in [(360, 740), (390, 844)]:
        ctx, pg, errors = new_page(browser, w, h)
        pg.goto(f"{server}/John/3/16-18?study=notes")
        _study_ready(pg)
        pg.wait_for_selector("#snote-new-ta")
        pg.focus("#snote-new-ta")
        # The keyboard takes about 45% of the screen: the visible area shrinks
        kb_h = int(h * 0.55)
        pg.set_viewport_size({"width": w, "height": kb_h})
        pg.wait_for_timeout(500)
        ta = pg.locator("#snote-new-ta").bounding_box()
        verses = pg.locator(".study-text-body").bounding_box()
        save = pg.locator(f"{NPANE} .snote-new .note-save").bounding_box()
        assert pg.evaluate("document.activeElement.id") == "snote-new-ta"
        assert 0 <= verses["y"] and verses["height"] > 60, verses          # the verses stay
        assert ta["y"] >= verses["y"] + verses["height"] - 1 and ta["y"] + ta["height"] <= kb_h, ta
        assert save["y"] + save["height"] <= kb_h, save
        assert not pg.is_visible(".study-rail")
        pg.locator("#snote-new-ta").blur()
        pg.set_viewport_size({"width": w, "height": h})
        pg.wait_for_timeout(400)
        assert pg.is_visible(".study-rail")
        ctx.close()
        assert not errors, errors
