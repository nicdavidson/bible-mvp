"""Screenshots and measurements of the phone reading chrome and the study view panes.

Usage: .venv/bin/python tests/e2e/chrome_shots.py http://127.0.0.1:8561 before|after
Writes docs/nav/chrome-<mode>-*.png and docs/study-view/panes-<mode>-*.png, and prints
the first verse's offset and the share of the first screen given to Scripture.
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8561"
MODE = sys.argv[2] if len(sys.argv) > 2 else "after"
ROOT = Path(__file__).resolve().parents[2]
NAV = ROOT / "docs" / "nav"
STUDY = ROOT / "docs" / "study-view"

# Same function as tests/e2e/test_chrome_layout.py
MEASURE = """() => {
    const vh = innerHeight;
    const first = document.querySelector('.verses .verse-box');
    const top = first.getBoundingClientRect().top;
    let bottom = Math.min(vh, document.querySelector('.panel-text .panel-body').getBoundingClientRect().bottom);
    for (const el of document.querySelectorAll('.panel-resources, .verse-action-bar, .reading-bar')) {
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden') continue;
        if (cs.position !== 'fixed' && cs.position !== 'sticky') continue;
        const r = el.getBoundingClientRect();
        if (r.height > 0 && r.top < bottom && r.top > top) bottom = r.top;
    }
    return { firstVerseTop: Math.round(top), scripture: Math.round(100 * (bottom - top) / vh) };
}"""


def ctx_for(b, w, h, theme):
    touch = w < 900
    ctx = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch,
                        device_scale_factor=2 if touch else 1, service_workers="block")
    ctx.add_init_script(f"localStorage.setItem('theme', '{theme}')")
    return ctx, ctx.new_page()


def settle(page, ms=600):
    page.wait_for_function("!Alpine.$data(document.body).loading && !Alpine.$data(document.body).navBusy")
    page.wait_for_timeout(ms)


def chrome(b, w, h, theme, results):
    ctx, page = ctx_for(b, w, h, theme)
    tag = f"{MODE}-{w}x{h}-{theme}"
    tap = page.tap if w < 900 else page.click
    page.goto(f"{BASE}/John/3")
    page.wait_for_selector("#verse-16")
    settle(page)
    results[f"{w}x{h} {theme} reading"] = page.evaluate(MEASURE)
    page.screenshot(path=str(NAV / f"chrome-{tag}-01-reading.png"))
    page.locator("#verse-3").scroll_into_view_if_needed()
    tap("#verse-3 .verse-num")
    page.wait_for_timeout(900)
    results[f"{w}x{h} {theme} selected"] = page.evaluate(MEASURE)
    page.screenshot(path=str(NAV / f"chrome-{tag}-02-verse-selected.png"))
    # a cross-reference jump: the way-back chip
    page.evaluate("Alpine.$data(document.body).navigate('Genesis 22:2', { kind: 'jump' })")
    page.wait_for_function("Alpine.$data(document.body).navReturn && !Alpine.$data(document.body).navBusy")
    page.wait_for_timeout(700)
    page.screenshot(path=str(NAV / f"chrome-{tag}-03-after-jump-chip.png"))
    if w < 900:
        page.evaluate("document.querySelector('.panel-text .panel-body').scrollTo(0, 99999)")
        page.wait_for_timeout(700)
        page.screenshot(path=str(NAV / f"chrome-{tag}-04-chapter-end.png"))
    ctx.close()


def panes_before(b, w, h, theme):
    ctx, page = ctx_for(b, w, h, theme)
    tag = f"before-{w}x{h}-{theme}"
    tap = page.tap if w < 900 else page.click
    page.goto(f"{BASE}/John/3")
    page.wait_for_selector("#verse-16")
    page.locator("#verse-16").scroll_into_view_if_needed()
    tap("#verse-16 .verse-num")
    page.wait_for_timeout(900)
    page.evaluate("const a = Alpine.$data(document.body); a.activeTab = 'crossrefs'; a.resourcesPanelExpanded = true; a.sheetExpand()")
    page.wait_for_timeout(600)
    page.screenshot(path=str(STUDY / f"panes-{tag}-01-crossrefs-sheet.png"))
    page.evaluate("Alpine.$data(document.body).openNoteForSelected()")
    page.wait_for_timeout(600)
    page.screenshot(path=str(STUDY / f"panes-{tag}-02-notes-sheet.png"))
    ctx.close()


def panes_after(b, w, h, theme):
    ctx, page = ctx_for(b, w, h, theme)
    tag = f"after-{w}x{h}-{theme}"
    page.goto(f"{BASE}/John/3/16-18?study=cross-references")
    page.wait_for_selector('.study-pane[data-slug="cross-references"] .xref-item')
    page.wait_for_timeout(700)
    page.screenshot(path=str(STUDY / f"panes-{tag}-01-crossrefs.png"))
    page.locator(".xref-more").click()
    page.wait_for_timeout(300)
    page.locator('.study-pane[data-slug="cross-references"] .study-pane-scroll').evaluate("el => el.scrollTo(0, 99999)")
    page.wait_for_timeout(300)
    page.screenshot(path=str(STUDY / f"panes-{tag}-02-crossrefs-all.png"))
    page.locator(".xref-ref").first.click()
    page.wait_for_selector("#study-peek[open] .study-verse")
    page.wait_for_timeout(400)
    page.screenshot(path=str(STUDY / f"panes-{tag}-03-crossref-peek.png"))
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    page.locator('.study-tool[data-slug="notes"]').click()
    page.wait_for_selector('.study-pane[data-slug="notes"] textarea')
    page.wait_for_timeout(600)
    page.screenshot(path=str(STUDY / f"panes-{tag}-04-notes-empty.png"))
    page.fill('.study-pane[data-slug="notes"] textarea', "God's love is the reason for the giving, not the result of it. Compare 1 John 4:9-10.")
    page.locator(".note-save").click()
    page.wait_for_timeout(400)
    page.goto(f"{BASE}/John/3/16?study=notes")
    page.wait_for_selector('.study-pane[data-slug="notes"] .snote')
    page.wait_for_timeout(600)
    page.screenshot(path=str(STUDY / f"panes-{tag}-05-notes-overlapping.png"))
    page.goto(f"{BASE}/John/3/16-18?study=john-gill")
    page.wait_for_selector('.study-pane[data-slug="john-gill"] .study-pane-body p')
    page.wait_for_timeout(600)
    page.screenshot(path=str(STUDY / f"panes-{tag}-06-rail-commentary.png"))
    if w < 900:
        # Writing with the keyboard up: the visual viewport shrinks to ~half
        page.goto(f"{BASE}/John/3/16-18?study=notes")
        page.wait_for_selector('.study-pane[data-slug="notes"] .snote')
        page.locator(".snote-edit").first.click()
        page.wait_for_selector('.study-pane[data-slug="notes"] textarea')
        page.set_viewport_size({"width": w, "height": int(h * 0.55)})
        page.wait_for_timeout(600)
        page.screenshot(path=str(STUDY / f"panes-{tag}-07-writing-keyboard.png"))
    ctx.close()


with sync_playwright() as p:
    b = p.chromium.launch()
    results = {}
    for (w, h) in [(360, 740), (390, 844), (1280, 800)]:
        for theme in ["light", "dark"]:
            chrome(b, w, h, theme, results)
            (panes_after if MODE == "after" else panes_before)(b, w, h, theme)
    b.close()
    print(json.dumps(results, indent=1))
