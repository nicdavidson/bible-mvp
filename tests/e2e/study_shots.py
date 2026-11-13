"""Screenshots of the study view with the real commentary library.

Usage: .venv/bin/python tests/e2e/study_shots.py [base_url] [--quick]
Writes docs/study-view/real-*.png (phones 360/390/430 and desktop 1280, light and dark).
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = next((a for a in sys.argv[1:] if a.startswith("http")), "http://127.0.0.1:8231")
QUICK = "--quick" in sys.argv
OUT = Path(__file__).resolve().parents[2] / "docs" / "study-view"
OUT.mkdir(parents=True, exist_ok=True)

SIZES = [(390, 844)] if QUICK else [(360, 740), (390, 844), (430, 932), (1280, 800)]
THEMES = ["light"] if QUICK else ["light", "dark"]


def new_page(browser, w, h, theme):
    mobile = w < 900
    ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=mobile, is_mobile=mobile,
                              device_scale_factor=2 if mobile else 1, service_workers="block",
                              color_scheme=theme)
    ctx.add_init_script(f"localStorage.setItem('theme', '{theme}');")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    return ctx, page, errors


def shot(page, tag, name):
    page.screenshot(path=str(OUT / f"real-{tag}-{name}.png"))


def ready(page, slug):
    page.wait_for_selector(f'.study-pane[data-slug="{slug}"] .study-pane-body p', timeout=15000)
    page.wait_for_timeout(600)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for theme in THEMES:
            for w, h in SIZES:
                tag = f"{w}x{h}-{theme}"
                phone = w < 900
                ctx, page, errors = new_page(browser, w, h, theme)
                tap = page.tap if phone else page.click

                # Reader: select 16-18, open the study view (first-time default order)
                page.goto(f"{BASE}/John/3")
                page.wait_for_selector("#verse-16")
                page.locator("#verse-16").scroll_into_view_if_needed()
                tap("#verse-16 .verse-num")
                tap("#verse-18 .verse-num")
                page.wait_for_timeout(600)
                tap(".verse-action-bar .action-bar-study")
                ready(page, page.evaluate("Alpine.$data(document.body).study.active"))
                shot(page, tag, "01-john3-open")

                # Tyndale: verse notes first, its note on 16-21 as a section below
                tap('.study-chip[data-slug="tyndale-study-notes"]')
                ready(page, "tyndale-study-notes")
                shot(page, tag, "02-tyndale-notes")

                # Who a source is (Gill: no repeated name)
                tap('.study-chip[data-slug="john-gill"]')
                ready(page, "john-gill")
                shot(page, tag, "03-gill")
                tap('.study-chip[data-slug="john-gill"]')
                page.wait_for_selector("#study-info[open]")
                page.wait_for_timeout(300)
                shot(page, tag, "04-source-info")
                page.keyboard.press("Escape")

                # Scofield: occasional notes, first in the owner's order
                tap('.study-chip[data-slug="scofield-notes-1917"]')
                ready(page, "scofield-notes-1917")
                shot(page, tag, "05-scofield")

                # All: every source and what it has here (5)
                tap(".study-all-btn")
                page.wait_for_selector("#study-all[open]")
                page.wait_for_timeout(300)
                shot(page, tag, "06-all-sources")
                page.keyboard.press("Escape")

                # Treasury of David on Psalm 23:1-3: verse expositions first, overview below
                page.goto(f"{BASE}/Psalms/23/1-3?study=treasury-of-david")
                ready(page, "treasury-of-david")
                page.wait_for_timeout(2900)   # the coordinator's 3.5 s check: verses still shown
                shot(page, tag, "07-treasury-psalm23")
                more = page.locator('.study-pane[data-slug="treasury-of-david"] .study-more summary').first
                more.scroll_into_view_if_needed()
                more.click()
                page.wait_for_timeout(300)
                shot(page, tag, "08-treasury-overview-open")

                # Tyndale: CC BY-SA credit with the text
                tap('.study-chip[data-slug="tyndale-study-notes"]')
                ready(page, "tyndale-study-notes")
                shot(page, tag, "09-tyndale-credit")

                if phone and theme == "light":
                    page.goto(f"{BASE}/John/3")
                    page.wait_for_selector("#verse-16")
                    page.evaluate("Alpine.$data(document.body).openSettings('offline')")
                    page.wait_for_selector(".download-option .download-size", timeout=20000)
                    page.locator(".download-section-header", has_text="Commentaries").scroll_into_view_if_needed()
                    page.wait_for_timeout(300)
                    shot(page, tag, "10-offline-sources")
                print(tag, "errors:", errors[:5])
                ctx.close()
        browser.close()


if __name__ == "__main__":
    run()
