"""Screenshots of the search screen, Similar verses and the study view's chip row.

Usage: .venv/bin/python tests/e2e/search_shots.py [base_url] [--before]
Writes docs/search/{before,after}-<w>x<h>-<theme>-<state>.png (device scale 1, to keep
them small). Every query is shot once at 390x844 light; other sizes and themes get the
states that differ there. One browser, one page at a time. Prints what each query
showed, so the run can be read without the images.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = next((a for a in sys.argv[1:] if a.startswith("http")), "http://127.0.0.1:8711")
BEFORE = "--before" in sys.argv
OUT = Path(__file__).resolve().parents[2] / "docs" / "search"
OUT.mkdir(parents=True, exist_ok=True)
PREFIX = "before" if BEFORE else "after"

QUERIES = {
    "01-reference": "rom 8 28",
    "02-phrase": "green pastures",
    "03-topic": "forgiveness",
    "04-question": "verses about forgiving someone who keeps hurting you",
    "05-anxiety": "what does the Bible say about anxiety",
    "06-strongs": "G26",
    "07-meaning-only": "when you feel far from God",
    "08-nonsense": "qzxv blorptangle",
}
ALL = ["00-empty", *QUERIES]
EXTRA = [] if BEFORE else ["09-return", "10-offline", "11-fallback", "12-similar"]
STATES = {
    (390, 844, "light"): ALL + EXTRA + ["20-study-rail"],
    (360, 740, "light"): ["03-topic", "04-question", "20-study-rail"],
    (360, 740, "dark"): ["20-study-rail"],
    (390, 844, "dark"): ["04-question", "06-strongs", "20-study-rail"],
    (390, 844, "parchment"): [] if BEFORE else ["04-question"],
    (1280, 800, "light"): ["02-phrase", "04-question", "06-strongs", "20-study-rail"],
    (1280, 800, "dark"): ["04-question", "20-study-rail"],
}


def settle(page, ms=1500):
    page.wait_for_timeout(ms)
    page.wait_for_function("""() => { const d = Alpine.$data(document.body);
        return !d.searchLoading && !(d.srch && (d.srch.kw.status === 'loading' || d.srch.meaning.status === 'loading')); }""",
                           timeout=15000)
    page.wait_for_timeout(250)


def open_search(page):
    if not page.is_visible("#srch-input, .search-modal input"):
        page.evaluate("Alpine.$data(document.body).openSearch()")
    page.wait_for_selector("#srch-input:visible, .search-modal input:visible")


def run_query(page, q):
    open_search(page)
    inp = page.locator("#srch-input:visible, .search-modal input.input-search:visible").first
    inp.fill("")
    inp.type(q, delay=5)
    if not BEFORE and page.evaluate("Alpine.$data(document.body).srchKind()") != "reference":
        page.keyboard.press("Enter")
    settle(page)


def describe(page):
    return page.evaluate("""() => {
        const vis = (el) => !!(el && el.offsetParent);
        const t = (n) => n.textContent.replace(/\\s+/g, ' ').trim();
        return {
            heads: [...document.querySelectorAll('.results-group-header, .srch-h')].filter(vis).map(t),
            refs: [...document.querySelectorAll('.search-result .result-ref, .srch-hit .srch-ref')].filter(vis).slice(0, 6).map(t),
            notes: [...document.querySelectorAll('.search-no-results, .srch-note, .srch-nothing, .srch-goto, .srch-word, .srch-row, .srch-empty-line')]
                .filter(vis).map(t).map(s => s.slice(0, 120)),
        };
    }""")


def shoot(page, tag, name):
    page.screenshot(path=str(OUT / f"{PREFIX}-{tag}-{name}.png"))


def study_rail(page, tag):
    page.goto(f"{BASE}/John/3/16?study=")
    page.wait_for_selector("#study-view[open] .study-chip", timeout=15000)
    page.wait_for_timeout(1200)
    n = page.evaluate("""() => { const r = document.querySelector('.study-chips').getBoundingClientRect();
        return [...document.querySelectorAll('.study-chip')].map(c => c.getBoundingClientRect())
            .filter(b => b.left >= r.left - 1 && b.right <= r.right + 1).length; }""")
    shoot(page, tag, "20-study-rail")
    return n


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for (w, h, theme), states in STATES.items():
            if not states:
                continue
            tag = f"{w}x{h}-{theme}"
            phone = w < 900
            ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=phone, is_mobile=phone,
                                      service_workers="block", color_scheme="dark" if theme == "dark" else "light")
            ctx.add_init_script(f"localStorage.setItem('theme', '{theme}');")
            page = ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{BASE}/Psalms/23")
            page.wait_for_selector("#verse-1")
            for name in states:
                if name == "00-empty":
                    open_search(page)
                    page.wait_for_timeout(300)
                    shoot(page, tag, name)
                elif name in QUERIES:
                    run_query(page, QUERIES[name])
                    shoot(page, tag, name)
                    if theme == "light" and w == 390:
                        print(tag, name, repr(QUERIES[name]), describe(page))
                elif name == "09-return":
                    # Open a verse about the idea, then come back with the chip's Results
                    run_query(page, QUERIES["04-question"])
                    page.locator(".srch-meaning .srch-hit").nth(3).tap()
                    page.wait_for_function("!Alpine.$data(document.body).loading && !document.getElementById('search-view').open")
                    page.wait_for_timeout(500)
                    shoot(page, tag, "09-jumped")
                    page.tap(".return-chip-results")
                    page.wait_for_selector("#srch-input:visible")
                    page.wait_for_timeout(500)
                    shoot(page, tag, name)
                elif name == "10-offline":
                    page.goto(f"{BASE}/Psalms/23")
                    page.wait_for_function("async () => (await window.offlineStorage.getChapterVerses('BSB', 'Psalms', 23)).length === 6")
                    ctx.set_offline(True)
                    run_query(page, "still waters")
                    run_query(page, "green pastures")
                    shoot(page, tag, name)
                    print(tag, name, describe(page))
                    ctx.set_offline(False)
                elif name == "11-fallback":
                    page.goto(f"{BASE}/Psalms/23")
                    page.wait_for_selector("#verse-1")
                    page.route("**/api/search/meaning*", lambda route: route.fulfill(json={
                        "query": "x", "scope": "all", "translation": "BSB", "mode": "keyword", "fallback": True,
                        "results": [{"type": "verse", "book": "Psalms", "chapter": 46, "verse": 10,
                                     "snippet": "“Be still, and know that I am God.”", "match": "keyword"},
                                    {"type": "verse", "book": "Matthew", "chapter": 11, "verse": 28,
                                     "snippet": "Come to Me, all you who are weary and burdened, and I will give you <mark>rest</mark>.", "match": "keyword"}]}))
                    run_query(page, "where can I find rest when I am tired")
                    shoot(page, tag, name)
                    page.unroute("**/api/search/meaning*")
                elif name == "12-similar":
                    page.goto(f"{BASE}/Isaiah/40/31?study=cross-references")
                    page.wait_for_selector(".similar-load:visible", timeout=15000)
                    page.tap(".similar-load")
                    page.wait_for_selector(".similar-list .xref-item")
                    page.evaluate("document.querySelector('.similar').scrollIntoView({ block: 'start' })")
                    page.wait_for_timeout(300)
                    shoot(page, tag, name)
                elif name == "20-study-rail":
                    print(tag, "whole commentary chips beside the tools:", study_rail(page, tag))
            if errors:
                print("PAGE ERRORS", tag, errors)
            ctx.close()
        browser.close()


if __name__ == "__main__":
    run()
