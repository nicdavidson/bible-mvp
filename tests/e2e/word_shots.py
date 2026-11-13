"""Screenshots of the word panel, the word study and the study view's Hymns pane.

Usage: .venv/bin/python tests/e2e/word_shots.py [base_url] [--quick]
Writes docs/word-study/*.png and docs/study-view/hymns-*.png
(360x740, 390x844, 1280x800; light and dark). One browser, one page at a time.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = next((a for a in sys.argv[1:] if a.startswith("http")), "http://127.0.0.1:8613")
QUICK = "--quick" in sys.argv
ROOT = Path(__file__).resolve().parents[2]
WS = ROOT / "docs" / "word-study"
SV = ROOT / "docs" / "study-view"
WS.mkdir(parents=True, exist_ok=True)

SIZES = [(390, 844)] if QUICK else [(360, 740), (390, 844), (1280, 800)]
THEMES = ["light"] if QUICK else ["light", "dark"]
# agape, logos, pistis, hesed (homographs), shalom, ruach, the article, a word used once
WORDS = ["G26", "G3056", "G4102", "H2617", "H7965", "H7307", "G3588", "G4"]
SECTIONS = ["ws-sec-tr", "ws-sec-where", "ws-sec-with"]


def ctx_for(browser, w, h, theme):
    mobile = w < 900
    ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=mobile, is_mobile=mobile,
                              device_scale_factor=2 if mobile else 1, service_workers="block",
                              color_scheme=theme)
    ctx.add_init_script(f"localStorage.setItem('theme', '{theme}');")
    return ctx


def study_ready(page):
    page.wait_for_selector("#word-study[open] #ws-title", timeout=15000)
    page.wait_for_function("!Alpine.$data(document.body).ws.loading")
    page.wait_for_timeout(300)


def scroll_to(page, el_id):
    ok = page.evaluate(f"""() => {{ const el = document.getElementById('{el_id}');
        if (!el || !el.offsetParent) return false;
        const sc = el.closest('.ws-scroll'); sc.scrollTop = el.offsetTop - 8; return true; }}""")
    page.wait_for_timeout(200)
    return ok


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for theme in THEMES:
            for w, h in SIZES:
                tag = f"{w}x{h}-{theme}"
                phone = w < 900
                ctx = ctx_for(browser, w, h, theme)
                page = ctx.new_page()
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                tap = page.tap if phone else page.click

                # The word panel, from a tap in the reader
                page.goto(f"{BASE}/1-John/4")
                page.wait_for_selector("#verse-8")
                page.locator("#verse-8").scroll_into_view_if_needed()
                if phone:
                    tap("#verse-8 .verse-num")
                    page.wait_for_timeout(400)
                word = page.locator("#verse-8 .word[data-word='love']").last
                word.tap() if phone else word.click()
                page.wait_for_selector(".panel-word .qw-count:visible", timeout=15000)
                page.wait_for_timeout(400)
                page.screenshot(path=str(WS / f"{tag}-01-word-panel.png"))
                tap(".qw-study")
                study_ready(page)

                # Every word: the top; on phones (and for agape everywhere) the sections too
                for strong in WORDS:
                    page.goto(f"{BASE}/word/{strong}")
                    study_ready(page)
                    page.screenshot(path=str(WS / f"{tag}-{strong}-1-top.png"))
                    if phone or strong in ("G26", "H2617"):
                        for i, sec in enumerate(SECTIONS, 2):
                            if scroll_to(page, sec):
                                page.screenshot(path=str(WS / f"{tag}-{strong}-{i}-{sec[7:]}.png"))

                # Verses behind a rendering and behind a collocate; a verse peek
                page.goto(f"{BASE}/word/G26?list=rendering:KJV:charity")
                page.wait_for_selector(".ws-list .ws-verse", timeout=15000)
                page.screenshot(path=str(WS / f"{tag}-02-list-rendering.png"))
                page.goto(f"{BASE}/word/G26?list=with:G4102")
                page.wait_for_selector(".ws-list .ws-verse", timeout=15000)
                page.screenshot(path=str(WS / f"{tag}-03-list-collocate.png"))
                page.locator(".ws-list .ws-verse").nth(1).click()
                page.wait_for_selector("#ws-peek[open] .study-verse", timeout=15000)
                page.wait_for_timeout(300)
                page.screenshot(path=str(WS / f"{tag}-04-verse-peek.png"))

                # The withheld link, revealed: the study says it is a closest match
                page.goto(f"{BASE}/John/3")
                page.wait_for_selector("#verse-3")
                page.evaluate("Alpine.$data(document.body).translation = 'WEB'")
                page.wait_for_function("document.querySelector('#verse-3').textContent.includes('certainly')")
                page.locator("#verse-3").scroll_into_view_if_needed()
                if phone:
                    tap("#verse-3 .verse-num")
                    page.wait_for_timeout(400)
                    tap('#verse-3 .word[data-position="5"]')
                else:
                    page.click('#verse-3 .word[data-position="5"]')
                page.wait_for_selector(".word-unsure:visible")
                page.screenshot(path=str(WS / f"{tag}-05-weak-link.png"))
                tap(".word-reveal")
                page.wait_for_selector(".qw-study:visible")
                page.wait_for_timeout(400)
                page.screenshot(path=str(WS / f"{tag}-06-weak-link-revealed.png"))
                tap(".qw-study")
                study_ready(page)
                page.screenshot(path=str(WS / f"{tag}-07-closest-match-study.png"))

                # Offline, never opened: clear, not broken
                page.goto(f"{BASE}/John/3")
                page.wait_for_selector("#verse-3")
                ctx.set_offline(True)
                page.evaluate("Alpine.$data(document.body).openWordStudy('G5')")
                page.wait_for_selector(".ws-offline:visible")
                page.screenshot(path=str(WS / f"{tag}-08-offline.png"))
                ctx.set_offline(False)

                # Hymns in the study view
                for ref, name in (("/Psalms/23/1-6", "psalm23"), ("/Psalms/100/1", "psalm100"),
                                  ("/Revelation/4/8", "rev4-computed"), ("/Romans/8/28", "rom8-chapter")):
                    page.goto(f"{BASE}{ref}?study=hymns")
                    page.wait_for_selector('.study-pane[data-slug="hymns"] .hymn-item', timeout=15000)
                    page.wait_for_timeout(700)
                    page.screenshot(path=str(SV / f"hymns-{tag}-{name}.png"))
                page.goto(f"{BASE}/Revelation/4/8?study=hymns")
                page.wait_for_selector('.study-pane[data-slug="hymns"] .hymn-item', timeout=15000)
                page.wait_for_timeout(500)
                page.locator('.study-pane[data-slug="hymns"] .hymn-item').first.click()
                page.wait_for_selector("#study-hymn[open] .hymn-passage", timeout=15000)
                page.wait_for_timeout(400)
                page.screenshot(path=str(SV / f"hymns-{tag}-sheet.png"))
                page.goto(f"{BASE}/Leviticus/13/2?study=cross-references")
                page.wait_for_function("['ready','none'].includes(Alpine.$data(document.body).studyHymns.status)")
                page.wait_for_timeout(500)
                page.screenshot(path=str(SV / f"hymns-{tag}-none-lev13.png"))

                if errors:
                    print(tag, "page errors:", errors)
                ctx.close()
                print("done", tag)
        browser.close()


if __name__ == "__main__":
    run()
