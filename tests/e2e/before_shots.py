"""Capture 'before' screenshots of the old commentary flow (run once, kept for reference).

Usage: .venv/bin/python tests/e2e/before_shots.py http://127.0.0.1:8231
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8231"
OUT = Path(__file__).resolve().parents[2] / "docs" / "study-view"
OUT.mkdir(parents=True, exist_ok=True)


def shot(page, name):
    page.screenshot(path=str(OUT / f"before-{name}.png"))
    print("saved", name)


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, has_touch=True,
                        is_mobile=True, device_scale_factor=2, service_workers="block")
    page = ctx.new_page()
    page.goto(f"{BASE}/John/3")
    page.wait_for_selector("#verse-16")
    page.locator("#verse-16").scroll_into_view_if_needed()
    page.tap("#verse-16 .verse-num")
    page.wait_for_timeout(600)
    shot(page, "01-phone-verse-selected")
    # extend selection to 16-18
    page.tap("#verse-17 .verse-num")
    page.tap("#verse-18 .verse-num")
    page.wait_for_timeout(300)
    shot(page, "02-phone-range-selected")
    page.tap(".verse-action-bar button[title=Study]")
    page.wait_for_timeout(800)
    shot(page, "03-phone-study-tab")
    # Commentary tab
    page.locator(".panel-tabs .tab-btn", has_text="Commentary").tap()
    page.wait_for_timeout(800)
    shot(page, "04-phone-commentary-tab")
    srcs = page.locator(".commentary-source-tab")
    print("source tabs:", srcs.all_inner_texts())
    if srcs.count() > 1:
        srcs.nth(1).tap()
        page.wait_for_timeout(600)
        shot(page, "05-phone-commentary-source-switched")
    page.evaluate("document.querySelector('.panel-resources .panel-body').scrollTop = 4000")
    page.wait_for_timeout(300)
    shot(page, "06-phone-commentary-scrolled")
    print("highlighted:", page.evaluate("Alpine.$data(document.body).highlightedVerses"))
    ctx.close()
    ctx = b.new_context(viewport={"width": 1280, "height": 800}, service_workers="block")
    page = ctx.new_page()
    page.goto(f"{BASE}/John/3/16")
    page.wait_for_selector("#verse-16")
    page.wait_for_timeout(800)
    page.locator(".panel-tabs .tab-btn", has_text="Commentary").click()
    page.wait_for_timeout(800)
    shot(page, "07-desktop-commentary-tab")
    b.close()
