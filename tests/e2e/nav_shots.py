"""Screenshots of the passage picker and the way-back chip (docs/nav/after-*.png).

Usage: .venv/bin/python tests/e2e/nav_shots.py http://127.0.0.1:8471
The before-*.png files were taken from v2/integration with the same steps.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8471"
OUT = Path(__file__).resolve().parents[2] / "docs" / "nav"
OUT.mkdir(parents=True, exist_ok=True)


def shot(page, name):
    page.screenshot(path=str(OUT / f"after-{name}.png"))
    print("saved", name)


def jump(page, touch=True):
    page.goto(f"{BASE}/John/3")
    page.wait_for_selector("#verse-16")
    page.locator("#verse-16").scroll_into_view_if_needed()
    (page.tap if touch else page.click)("#verse-16 .verse-num")
    page.wait_for_timeout(800)
    if touch:
        page.locator(".peek-chip", has_text="Cross-refs").tap()
        page.wait_for_timeout(500)
        page.locator(".crossref-list a").first.tap()
    else:
        page.locator(".study-ref-grid a").first.click()
    page.wait_for_function("!Alpine.$data(document.body).loading && Alpine.$data(document.body).navReturn")
    page.wait_for_timeout(700)


with sync_playwright() as p:
    b = p.chromium.launch()
    for (w, h) in [(360, 740), (390, 844)]:
        ctx = b.new_context(viewport={"width": w, "height": h}, has_touch=True, is_mobile=True,
                            device_scale_factor=2, service_workers="block")
        page = ctx.new_page()
        tag = f"{w}x{h}"
        page.goto(f"{BASE}/")
        page.wait_for_selector(".home .picker-book")
        page.wait_for_timeout(500)
        shot(page, f"{tag}-01-home")
        page.goto(f"{BASE}/John/3")
        page.wait_for_selector("#verse-16")
        page.wait_for_timeout(500)
        shot(page, f"{tag}-02-reading-header")
        page.tap(".nav-title")
        page.wait_for_timeout(500)
        shot(page, f"{tag}-03-picker-books")
        page.tap('#passage-picker .picker-book[data-book="Psalms"]')
        page.wait_for_timeout(400)
        shot(page, f"{tag}-04-picker-chapters")
        page.fill("#passage-picker .picker-input", "rom 8:28")
        page.wait_for_timeout(300)
        shot(page, f"{tag}-05-picker-typed")
        page.fill("#passage-picker .picker-input", "")
        page.tap("#passage-picker .picker-all-books")
        page.tap("#passage-picker .picker-tabs button >> text=Recent")
        page.wait_for_timeout(300)
        shot(page, f"{tag}-06-picker-recent")
        page.keyboard.press("Escape")
        jump(page)
        shot(page, f"{tag}-07-after-xref-jump-chip")
        ctx.close()
    for theme in ["light", "dark", "parchment"]:
        ctx = b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True,
                            device_scale_factor=2, service_workers="block")
        page = ctx.new_page()
        page.goto(f"{BASE}/")
        page.evaluate(f"localStorage.setItem('theme', '{theme}')")
        jump(page)
        shot(page, f"390x844-{theme}-chip")
        page.tap(".nav-title")
        page.wait_for_timeout(500)
        shot(page, f"390x844-{theme}-picker")
        ctx.close()
    ctx = b.new_context(viewport={"width": 1280, "height": 800}, service_workers="block")
    page = ctx.new_page()
    page.goto(f"{BASE}/John/3")
    page.wait_for_selector("#verse-16")
    page.click(".nav-title")
    page.wait_for_timeout(500)
    shot(page, "1280x800-03-picker")
    page.keyboard.press("Escape")
    jump(page, touch=False)
    shot(page, "1280x800-07-after-xref-jump-chip")
    ctx.close()
    b.close()
