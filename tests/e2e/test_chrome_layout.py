"""The phone reading layout, measured, so chrome can't creep back above the text.

Before this layout (v2/nav) at 390x844 the first verse started 267px down and Scripture
had 57% of the first screen (51% at 360x740); with a verse selected the action bar sat on
top of the sheet's tab bar. These tests pin the new numbers and the one-bottom-bar rule,
check the controls that moved are still reachable, and check contrast of the new controls
in the three themes.
"""
import pytest

from tests.e2e.conftest import new_page
from tests.e2e.chrome_shots import MEASURE

pytest.importorskip("playwright.sync_api")

PHONES = [(360, 740), (390, 844)]


def _ready(pg):
    pg.wait_for_function("!Alpine.$data(document.body).loading && !Alpine.$data(document.body).navBusy")
    pg.wait_for_timeout(300)


def _visible_bottom_bars(pg):
    return pg.evaluate("""() => [...document.querySelectorAll('.reading-bar, .verse-action-bar, .panel-resources')]
        .filter(el => { const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
            return cs.display !== 'none' && cs.visibility !== 'hidden' && r.top < innerHeight && r.bottom > innerHeight - 4; })
        .map(el => el.className.split(' ')[0])""")


@pytest.mark.parametrize("size", PHONES)
def test_scripture_starts_near_the_top(server, browser, size):
    w, h = size
    ctx, pg, errors = new_page(browser, w, h)
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-16")
    _ready(pg)
    m = pg.evaluate(MEASURE)
    assert m["firstVerseTop"] <= 90, m          # was 267
    assert m["scripture"] >= 80, m              # was 51% (360x740) and 57% (390x844)
    # Nothing between the header and the text
    for gone in [".passage-title-btn", ".interlinear-toggle-header", ".nav-buttons"]:
        assert not pg.is_visible(gone), gone
    # Previous/next chapter: at the bottom, named, in thumb reach
    prev, nxt = pg.locator(".reading-bar-step").all()
    assert prev.inner_text().strip() == "John 2" and nxt.inner_text().strip() == "John 4"
    assert nxt.bounding_box()["y"] > h * 0.85
    assert _visible_bottom_bars(pg) == ["reading-bar"]
    ctx.close()
    assert not errors, errors


@pytest.mark.parametrize("size", PHONES)
def test_one_bottom_bar_with_a_verse_selected(server, browser, size):
    w, h = size
    ctx, pg, errors = new_page(browser, w, h)
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-3")
    _ready(pg)
    pg.tap("#verse-3 .verse-num")
    pg.wait_for_function("getComputedStyle(document.querySelector('.verse-action-bar')).opacity === '1'")
    assert _visible_bottom_bars(pg) == ["verse-action-bar"]
    assert pg.evaluate(MEASURE)["scripture"] >= 80
    # Every action is labelled and at least 44px tall; Copy, Memorize and Topics are behind More
    for btn in pg.locator(".verse-action-bar .action-bar-btn:visible").all():
        assert btn.bounding_box()["height"] >= 44
    labels = pg.locator(".verse-action-bar .action-bar-text:visible").all_inner_texts()
    assert labels == ["Study", "Refs", "Note", "Highlight", "Share", "More"]
    pg.tap(".action-bar-more")
    pg.wait_for_selector(".action-more button:visible")
    assert pg.locator(".action-more button:visible").all_inner_texts()[:2] == ["Copy", "Memorize"]
    pg.keyboard.press("Escape")
    pg.wait_for_selector(".action-more", state="hidden")
    # Share works on the selection (it used to need a separate share mode)
    pg.tap(".action-bar-share")
    pg.wait_for_selector(".share-modal, [x-show='showShareModal']", state="attached")
    assert pg.evaluate("Alpine.$data(document.body).showShareModal")
    assert pg.evaluate("Alpine.$data(document.body).getShareReference()") == "John 3:3"
    ctx.close()
    assert not errors, errors


def test_chip_never_covers_a_control(server, browser):
    ctx, pg, errors = new_page(browser, 390, 844)
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-16")
    pg.evaluate("Alpine.$data(document.body).navigate('Genesis 22:2', { kind: 'jump' })")
    pg.wait_for_function("Alpine.$data(document.body).navReturn && !Alpine.$data(document.body).navBusy")
    pg.wait_for_timeout(400)
    chip = pg.locator(".return-chip").bounding_box()
    for el in pg.locator("button:visible, a:visible, input:visible").all():
        if el.evaluate("e => !!e.closest('.return-chip')"):
            continue
        b = el.bounding_box()
        if not b or b["width"] == 0:
            continue
        overlap = not (b["x"] + b["width"] <= chip["x"] or chip["x"] + chip["width"] <= b["x"]
                       or b["y"] + b["height"] <= chip["y"] or chip["y"] + chip["height"] <= b["y"])
        assert not overlap, el.evaluate("e => e.outerHTML.slice(0, 120)")
    # ...also at the end of the chapter, where the Next chapter button is
    for _ in range(2):
        pg.evaluate("document.querySelector('.panel-text .panel-body').scrollTo(0, 1e6)")
        pg.wait_for_timeout(600)
    nxt = pg.locator(".chapter-end-next").bounding_box()
    chip = pg.locator(".return-chip").bounding_box()
    assert nxt["y"] + nxt["height"] <= chip["y"], (nxt, chip)
    ctx.close()
    assert not errors, errors


def test_moved_controls_still_reachable(server, browser):
    ctx, pg, errors = new_page(browser, 390, 844)
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-16")
    _ready(pg)
    # Original language: in the menu
    pg.tap(".btn-hamburger")
    pg.locator(".side-menu-item", has_text="Show Hebrew & Greek").tap()
    pg.wait_for_selector(".interlinear-row:visible")
    # This chapter's notes and Topics: from the reading bar
    pg.tap(".reading-bar-tool >> text=Topics")
    pg.wait_for_selector(".panel-resources.expanded .topic-search-input:visible")
    assert not pg.is_visible(".reading-bar")
    pg.tap(".btn-close-panel")
    pg.wait_for_selector(".reading-bar:visible")
    # The end of the chapter names the next one
    # (scrolling down hides the header and the text grows into its place: scroll again after)
    for _ in range(2):
        pg.evaluate("document.querySelector('.panel-text .panel-body').scrollTo(0, 1e6)")
        pg.wait_for_timeout(600)
    btn = pg.locator(".chapter-end-next")
    assert "John 4" in btn.inner_text()
    assert btn.bounding_box()["y"] + btn.bounding_box()["height"] <= pg.locator(".reading-bar").bounding_box()["y"]
    btn.tap()
    pg.wait_for_function("Alpine.$data(document.body).currentReference === 'John 4' && !Alpine.$data(document.body).navBusy")
    ctx.close()
    assert not errors, errors


def test_desktop_not_worse(server, browser):
    ctx, pg, errors = new_page(browser, 1280, 800, touch=False)
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-16")
    _ready(pg)
    m = pg.evaluate(MEASURE)
    assert m["firstVerseTop"] <= 220 and m["scripture"] >= 71, m   # v2/nav: 220px, 71%
    # Desktop keeps its passage header controls and the sidebar
    for kept in [".passage-title-btn", ".interlinear-toggle-header", ".nav-buttons", ".panel-resources .tab-btn"]:
        assert pg.is_visible(kept), kept
    assert not pg.is_visible(".reading-bar")
    pg.click("#verse-3 .verse-num")
    pg.wait_for_selector(".verse-action-bar .action-bar-text >> text=Copy")
    assert not pg.is_visible(".action-bar-more")
    ctx.close()
    assert not errors, errors


CONTRAST = """() => {
    const parse = c => { const m = c.match(/[\\d.]+/g).map(Number); return { r: m[0], g: m[1], b: m[2], a: m[3] ?? 1 }; };
    const lum = ({ r, g, b }) => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
    const bgOf = el => { const stack = []; for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor);
            if (c.a > 0) { stack.push(c); if (c.a >= 1) break; } }
        let out = { r: 255, g: 255, b: 255 };
        for (const c of stack.reverse()) out = { r: c.r * c.a + out.r * (1 - c.a), g: c.g * c.a + out.g * (1 - c.a), b: c.b * c.a + out.b * (1 - c.a) };
        return out; };
    const res = [];
    for (const sel of SELECTORS) for (const el of document.querySelectorAll(sel)) {
        if (!el.offsetParent && getComputedStyle(el).position !== 'fixed') continue;
        if (!el.textContent.trim()) continue;
        const fg = parse(getComputedStyle(el).color), bg = bgOf(el);
        const [a, b] = [lum(fg), lum(bg)].sort((x, y) => y - x);
        res.push([sel, Math.round(100 * (a + 0.05) / (b + 0.05)) / 100]);
        break;
    }
    return res;
}"""


@pytest.mark.parametrize("theme", ["light", "dark", "parchment"])
def test_new_controls_contrast(server, browser, theme):
    ctx, pg, errors = new_page(browser, 390, 844)
    pg.add_init_script(f"localStorage.setItem('theme', '{theme}')")
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-16")
    _ready(pg)
    reader = ['.reading-bar-step span', '.reading-bar-tool', '.chapter-end-hint', '.chapter-end-ref']
    got = pg.evaluate(CONTRAST.replace("SELECTORS", repr(reader)))
    pg.tap("#verse-3 .verse-num")
    pg.wait_for_timeout(500)
    got += pg.evaluate(CONTRAST.replace("SELECTORS", repr(['.action-bar-text'])))
    pg.goto(f"{server}/John/3/16?study=cross-references")
    pg.wait_for_selector(".xref-item")
    pg.wait_for_timeout(400)
    study = ['.study-tool-label', '.study-tool-count', '.study-tool-sub', '.xref-ref', '.xref-text',
             '.study-entry-range', '.study-attribution', '.study-chip-scope']
    got += pg.evaluate(CONTRAST.replace("SELECTORS", repr(study)))
    assert len(got) >= 10, got
    low = [(s, r) for s, r in got if r < 4.5]
    assert not low, (theme, low)
    ctx.close()
    assert not errors, errors
