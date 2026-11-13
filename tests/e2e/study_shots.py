"""Screenshots of the study view at phone and desktop sizes, light and dark.

Usage: .venv/bin/python tests/e2e/study_shots.py [base_url] [--quick]
Writes docs/study-view/*.png. Expects the synthetic sources from
tests/fixtures/study_seed.py in the DB the server uses (for the many-source shots).
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
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    return ctx, page, errors


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for theme in THEMES:
            for w, h in SIZES:
                tag = f"{w}x{h}-{theme}"
                ctx, page, errors = new_page(browser, w, h, theme)
                page.goto(f"{BASE}/John/3")
                page.wait_for_selector("#verse-16")
                tap = page.tap if w < 900 else page.click
                page.locator("#verse-16").scroll_into_view_if_needed()
                tap("#verse-16 .verse-num")
                tap("#verse-18 .verse-num")
                page.wait_for_timeout(700)
                page.screenshot(path=str(OUT / f"{tag}-01-selection.png"))
                tap(".verse-action-bar .action-bar-study")
                page.wait_for_selector(".study-pane-body p", timeout=10000)
                page.wait_for_timeout(500)
                page.screenshot(path=str(OUT / f"{tag}-02-study-open.png"))
                # Henry: passage-level entry with a context note
                tap('.study-chip[data-slug="matthew-henry"]')
                page.wait_for_timeout(900)
                page.screenshot(path=str(OUT / f"{tag}-03-henry.png"))
                # Long chapter-level entry with marked paragraphs
                tap('.study-chip[data-slug="lindqvist-chapter-studies"]')
                page.wait_for_timeout(1200)
                page.screenshot(path=str(OUT / f"{tag}-04-chapter-entry-focus.png"))
                # Source info
                tap('.study-chip[data-slug="lindqvist-chapter-studies"]')
                page.wait_for_selector("#study-info[open]")
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / f"{tag}-05-source-info.png"))
                page.keyboard.press("Escape")
                # Empty source info with nearest
                page.locator('.study-chip[data-slug="pell-s-expositor"]').scroll_into_view_if_needed()
                tap('.study-chip[data-slug="pell-s-expositor"]')
                page.wait_for_selector("#study-info[open]")
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / f"{tag}-06-empty-source.png"))
                page.keyboard.press("Escape")
                # Reference peek inside commentary
                tap('.study-chip[data-slug="john-gill"]')
                page.wait_for_timeout(800)
                link = page.locator('.study-pane[data-slug="john-gill"] a.commentary-ref').first
                link.scroll_into_view_if_needed()
                link.click()
                page.wait_for_selector("#study-peek[open] .study-verses span", timeout=8000)
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / f"{tag}-07-ref-peek.png"))
                page.keyboard.press("Escape")
                # Manage sources
                tap(".study-manage-btn")
                page.wait_for_selector("#study-manage[open]")
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / f"{tag}-08-manage.png"))
                page.keyboard.press("Escape")
                if w < 900:
                    pane = page.locator('.study-pane[data-slug="john-gill"] .study-pane-scroll')
                    pane.evaluate("el => el.scrollBy(0, 400)")
                    page.wait_for_timeout(400)
                    page.screenshot(path=str(OUT / f"{tag}-09-strip-collapsed.png"))
                print(tag, "errors:", errors[:5])
                ctx.close()
        browser.close()


if __name__ == "__main__":
    run()
