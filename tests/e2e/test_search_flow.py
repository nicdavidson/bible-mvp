"""Browser flows for the search screen (modules/search.js), "Similar verses" in the study
view, the Hymns pane order and the study rail at phone widths.

Uses the shared server and browser (conftest.py). /api/search and /api/search/meaning
allow 30 requests a minute per address, so these tests type few queries and reuse them.
"""
import re

import pytest

from tests.e2e.conftest import new_page

pytest.importorskip("playwright.sync_api")


def _app(pg, expr):
    return pg.evaluate(f"(() => {{ const a = Alpine.$data(document.body); return {expr}; }})()")


def _path(pg):
    return pg.evaluate("location.pathname + location.search")


def _wait_ref(pg, ref):
    pg.wait_for_function(f"(() => {{ const a = Alpine.$data(document.body); "
                         f"return a.currentReference === {ref!r} && !a.loading && !a.navBusy; }})()")
    pg.wait_for_timeout(50)


def _search(pg, q, enter=True):
    """Type q into the open search screen; Enter loads verses about the idea too."""
    if not pg.is_visible("#srch-input"):
        pg.evaluate("Alpine.$data(document.body).openSearch()")
        pg.wait_for_selector("#srch-input:visible")
    pg.fill("#srch-input", q)
    if enter:
        pg.press("#srch-input", "Enter")
    pg.wait_for_function("""() => { const a = Alpine.$data(document.body);
        return a.srch.kw.q === a._srchKey() && a.srch.kw.status !== 'loading' && a.srch.meaning.status !== 'loading'; }""")
    pg.wait_for_timeout(100)


def _hits(pg, section=None):
    sel = f"#search-view .srch-{section} .srch-hit" if section else "#search-view .srch-hit"
    return pg.eval_on_selector_all(sel, "els => els.filter(e => e.offsetParent).map(e => e.dataset.hit)")


@pytest.fixture
def phone(browser, server):
    ctx, pg, errors = new_page(browser, 390, 844)
    pg.goto(f"{server}/Psalms/23")
    pg.wait_for_selector("#verse-1")
    yield pg
    ctx.close()
    assert not errors, errors


@pytest.fixture
def desktop(browser, server):
    ctx, pg, errors = new_page(browser, 1280, 800, touch=False)
    pg.goto(f"{server}/Psalms/23")
    pg.wait_for_selector("#verse-1")
    yield pg
    ctx.close()
    assert not errors, errors


# ---------- every kind of query lands in the right place ----------

def test_query_kinds(phone):
    pg = phone
    pg.click(".header-right .btn-icon[title^='Search']")
    pg.wait_for_selector("#srch-input:visible")
    assert pg.evaluate("document.activeElement.id") == "srch-input"
    assert "search=" in _path(pg)                          # the screen is a history entry
    # Nothing typed: examples of each kind
    assert pg.locator(".srch-example").count() >= 4

    # A sloppy reference: one obvious row, no keyword noise, Enter goes there
    pg.fill("#srch-input", "rom 8 28")
    pg.wait_for_selector(".srch-goto:visible")
    assert "Romans 8:28" in pg.inner_text(".srch-goto")
    assert not _hits(pg)
    pg.press("#srch-input", "Enter")
    _wait_ref(pg, "Romans 8:28")
    assert _path(pg) == "/Romans/8/28" and _app(pg, "a.highlightedVerses") == [28]

    # A remembered phrase: verses with the words lead; Psalm 23:2 once, in the reader's text
    _search(pg, "green pastures")
    assert _app(pg, "a.srchOrder()[0]") == "kw"
    kw = _hits(pg, "kw")
    assert kw[0] == "Psalms|23|2" and kw.count("Psalms|23|2") == 1
    assert "He makes me lie down" in pg.inner_text(".srch-kw .srch-hit >> nth=0")   # BSB
    assert "Psalms|23|2" not in _hits(pg, "meaning")

    # A question: verses about the idea lead, labelled as found by meaning
    _search(pg, "verses about forgiving someone who keeps hurting you")
    assert _app(pg, "a.srchOrder()[0]") == "meaning"
    first = pg.eval_on_selector("#search-view .srch-section", "e => e.className")
    assert "srch-meaning" in first
    assert pg.inner_text("#srch-m-h").startswith("≈") or "may be about this idea" in pg.inner_text("#srch-m-h")
    assert "may be about this idea" in pg.inner_text("#srch-m-h")
    assert "not exact words" in pg.inner_text(".srch-meaning .srch-how summary")
    assert len(_hits(pg, "meaning")) >= 5
    text = pg.inner_text("#search-view").lower()
    assert "the bible says" not in text and "answer:" not in text

    # Nonsense: one plain message, no guessed verses
    _search(pg, "qzxv blorptangle")
    assert pg.is_visible(".srch-nothing")
    assert not _hits(pg)
    assert "only be a guess" in pg.inner_text(".srch-nothing")


def test_strongs_number_and_original_word_lead_to_the_word_study(phone):
    pg = phone
    _search(phone, "ἀγάπη", enter=False)
    pg.wait_for_selector(".srch-word:visible")
    assert "G26" in pg.inner_text(".srch-word")
    _search(pg, "agape", enter=False)                       # a transliteration: offered beside the words
    pg.wait_for_selector(".srch-row:has-text('G26')")
    _search(pg, "G26", enter=False)
    pg.wait_for_selector(".srch-word:visible")
    assert pg.inner_text("#srch-kw-h").find("Verses with this word") >= 0
    pg.press("#srch-input", "Enter")
    pg.wait_for_selector("#word-study[open] #ws-title")
    assert _path(pg) == "/word/G26"
    # Back from the word study comes back to the search
    pg.go_back()
    pg.wait_for_selector("#srch-input:visible")
    assert pg.input_value("#srch-input") == "G26"


# ---------- each verse once ----------

def test_a_verse_appears_once(desktop):
    pg = desktop
    # Across translations (P1-7): living water matched BSB, KJV and WEB rows before
    _search(pg, "living water", enter=False)
    pg.click(".srch-kw .srch-more") if pg.is_visible(".srch-kw .srch-more") else None
    kw = _hits(pg, "kw")
    assert len(kw) == len(set(kw)) and "Jeremiah|2|13" in kw
    # Matched only in another translation: the reader's text, with the matching wording under it
    sos = pg.locator(".srch-hit[data-hit='Song of Solomon|4|15']")
    assert sos.locator(".srch-alt-tr").inner_text() in ("KJV", "WEB")
    # Across the two lists: a verse matching both ways is listed once
    _search(pg, "forgiveness")
    for name in ("kw", "meaning"):
        more = pg.locator(f".srch-{name} .srch-more")
        if more.is_visible():
            more.click()
    both = _hits(pg)
    assert len(both) == len(set(both)) and len(both) > 20
    kw, meaning = set(_hits(pg, "kw")), set(_hits(pg, "meaning"))
    assert kw and meaning and not (kw & meaning)
    assert "More verses that may be about this idea" in pg.inner_text("#srch-m-h")


# ---------- a result opens as a jump, and the way back keeps everything ----------

def test_jump_and_return_with_chip_and_back(phone):
    pg = phone
    _search(pg, "forgiveness")
    pg.click(".srch-meaning .srch-more")
    body = "#search-view .srch-body"
    target = pg.locator(".srch-meaning .srch-hit").nth(6)
    target.scroll_into_view_if_needed()
    pg.wait_for_timeout(100)
    scroll = pg.eval_on_selector(body, "e => e.scrollTop")
    assert scroll > 300                                    # well down the results
    hit = target.get_attribute("data-hit")
    book, ch, v = hit.split("|")
    ref = f"{book} {ch}:{v}"
    target.tap()
    _wait_ref(pg, ref)
    assert _app(pg, "a.highlightedVerses") == [int(v)]
    assert not pg.is_visible("#srch-input")
    assert pg.inner_text(".return-chip-back").strip() == "Back to Psalms 23"

    def back_at_results():
        pg.wait_for_selector("#srch-input:visible")
        pg.wait_for_timeout(300)
        assert pg.input_value("#srch-input") == "forgiveness"
        assert hit in _hits(pg, "meaning") and _hits(pg, "kw")
        assert abs(pg.eval_on_selector(body, "e => e.scrollTop") - scroll) < 4
        assert _app(pg, "a.currentReference") == "Psalms 23"

    # The chip's Results
    pg.tap(".return-chip-results")
    back_at_results()
    # Browser Back
    pg.locator(f".srch-hit[data-hit='{hit}']").tap()
    _wait_ref(pg, ref)
    pg.go_back()
    back_at_results()
    # Back again closes search onto where reading was
    pg.go_back()
    pg.wait_for_function("!document.getElementById('search-view').open")
    assert _path(pg) == "/Psalms/23"
    # The chip's "Back to Psalms 23" skips the search entry
    _search(pg, "forgiveness")
    pg.locator(".srch-kw .srch-hit").first.tap()
    pg.wait_for_function("Alpine.$data(document.body).currentReference !== 'Psalms 23' && !Alpine.$data(document.body).loading")
    pg.tap(".return-chip-back")
    _wait_ref(pg, "Psalms 23")
    assert not pg.is_visible("#srch-input")


# ---------- scopes ----------

def test_scopes(phone):
    pg = phone
    _search(pg, "shepherd", enter=False)
    scopes = pg.locator(".srch-scope")
    assert [s.strip() for s in scopes.all_inner_texts()] == ["All", "OT", "NT", "Psalms", "Commentary"]
    assert min(b["height"] for b in [s.bounding_box() for s in scopes.all()]) >= 40
    nt = set(_app(pg, "NT_BOOKS"))
    pg.tap(".srch-scope[aria-label='New Testament']")
    pg.wait_for_function("Alpine.$data(document.body).srch.kw.q?.endsWith('|nt|BSB') && Alpine.$data(document.body).srch.kw.status === 'ready'")
    assert _hits(pg, "kw") and all(h.split("|")[0] in nt for h in _hits(pg, "kw"))
    pg.tap(".srch-scope[aria-label='Only Psalms']")
    pg.wait_for_function("Alpine.$data(document.body).srch.kw.q?.endsWith('|book:Psalms|BSB') && Alpine.$data(document.body).srch.kw.status === 'ready'")
    assert all(h.startswith("Psalms|") for h in _hits(pg, "kw"))
    pg.tap(".srch-scope[aria-label='Commentary only']")
    pg.wait_for_function("Alpine.$data(document.body).srch.kw.q?.endsWith('|commentary|BSB') && Alpine.$data(document.body).srch.kw.status === 'ready'")
    assert not _hits(pg, "kw") and not _hits(pg, "meaning") and _hits(pg, "comm")
    assert not pg.is_visible(".srch-find-idea")


# ---------- when meaning search can't help ----------

def test_fallback_is_not_labelled_as_meaning(phone):
    pg = phone
    pg.route("**/api/search/meaning*", lambda route: route.fulfill(json={
        "query": "x", "scope": "all", "translation": "BSB", "mode": "keyword", "fallback": True,
        "fallback_reason": "meaning search unavailable",
        "results": [{"type": "verse", "book": "Psalms", "chapter": 46, "verse": 10, "snippet": "Be still, and know that I am God",
                     "score": 0.016, "match": "keyword", "meaning_rank": None, "keyword_rank": 1}]}))
    _search(pg, "where can I find rest when I am tired")
    assert pg.inner_text("#srch-m-h").strip().startswith("Verses with some of your words")
    assert "≈" not in pg.inner_text("#srch-m-h")
    assert not pg.is_visible(".srch-meaning .srch-how")
    assert "isn't available right now" in pg.inner_text(".srch-meaning")
    assert "Psalms|46|10" in _hits(pg, "meaning")
    # Broken outright: keyword results stay, the meaning list says so and offers a retry
    pg.unroute("**/api/search/meaning*")
    pg.route("**/api/search/meaning*", lambda route: route.fulfill(status=500, body="no"))
    _search(pg, "where can I find rest when I am weary")
    assert "Couldn't search by meaning" in pg.inner_text(".srch-meaning")


def test_offline_keyword_search_over_saved_chapters(browser, server):
    ctx, pg, errors = new_page(browser, 390, 844)
    pg.goto(f"{server}/Psalms/23")
    pg.wait_for_selector("#verse-1")
    # The chapter is saved on this device as it is read (auto-save is on by default)
    pg.wait_for_function("""async () => (await window.offlineStorage.getChapterVerses('BSB', 'Psalms', 23)).length === 6""", timeout=15000)
    ctx.set_offline(True)
    _search(pg, "green pastures", enter=False)
    assert _hits(pg, "kw") == ["Psalms|23|2"]
    note = pg.inner_text(".srch-note:visible")
    assert "offline" in note.lower() and "saved on this device" in note
    _search(pg, "how do I stop being afraid")
    assert "needs a connection" in pg.inner_text("#search-view")
    ctx.set_offline(False)
    ctx.close()
    assert not [e for e in errors if "Failed to fetch" not in e], errors


# ---------- keyboard ----------

def test_keyboard_through_results(desktop):
    pg = desktop
    pg.keyboard.press("/")
    pg.wait_for_selector("#srch-input:visible")
    pg.keyboard.type("green pastures")
    _search(pg, "green pastures", enter=False)
    pg.keyboard.press("ArrowDown")
    assert pg.evaluate("document.activeElement.dataset.hit") == "Psalms|23|2"
    pg.keyboard.press("ArrowDown")
    second = pg.evaluate("document.activeElement.dataset.hit")
    assert second and second != "Psalms|23|2"
    pg.keyboard.press("ArrowUp")
    pg.keyboard.press("ArrowUp")
    assert pg.evaluate("document.activeElement.id") == "srch-input"
    pg.keyboard.press("ArrowDown")
    pg.keyboard.press("ArrowDown")
    pg.keyboard.press("Enter")
    pg.wait_for_function("!document.getElementById('search-view').open")
    book, ch, v = second.split("|")
    _wait_ref(pg, f"{book} {ch}:{v}")
    # Results come back with the opened result focused; Escape closes search
    pg.click(".return-chip-results")
    pg.wait_for_selector("#srch-input:visible")
    pg.wait_for_timeout(300)
    assert pg.evaluate("document.activeElement.dataset.hit") == second
    pg.keyboard.press("Escape")
    pg.wait_for_function("!document.getElementById('search-view').open")
    # The status line tells a screen reader what arrived
    assert pg.get_attribute("#srch-status", "role") == "status"


# ---------- study view ----------

def test_similar_verses_in_the_cross_references_pane(browser, server):
    ctx, pg, errors = new_page(browser, 390, 844)
    pg.goto(f"{server}/Isaiah/40/31?study=cross-references")
    pg.wait_for_selector(".xref-item")
    xrefs = set(pg.locator(".xref-body .xref-ref").all_inner_texts())
    sim = pg.locator(".similar")
    assert "Computed, not chosen by an editor" in sim.inner_text()
    assert not pg.locator(".similar-list .xref-item:visible").count()   # only when asked
    pg.locator(".similar-load").scroll_into_view_if_needed()
    pg.tap(".similar-load")
    pg.wait_for_selector(".similar-list .xref-item")
    refs = pg.locator(".similar-list .xref-ref").all_inner_texts()
    assert len(refs) >= 5 and not (set(refs) & xrefs)
    assert all(not r.startswith("Isaiah 40:") or abs(int(r.split(":")[1]) - 31) > 3 for r in refs)
    pg.locator(".similar-list .xref-item").first.tap()
    pg.wait_for_selector("#study-peek[open]")
    ctx.close()
    assert not errors, errors


def test_psalm_100_hymns_lead_with_the_familiar_one(browser, server):
    ctx, pg, errors = new_page(browser, 390, 844)
    pg.goto(f"{server}/Psalms/100?study=hymns")
    pg.wait_for_selector(".hymn-item")
    assert pg.locator(".hymn-title").first.inner_text() == "All People That On Earth Do Dwell"
    ctx.close()
    assert not errors, errors


@pytest.mark.parametrize("w,h,before", [(360, 740, 1), (390, 844, 1)])
def test_study_rail_shows_more_commentary_on_phones(browser, server, w, h, before):
    """Before this change one whole commentary chip fitted beside the tools at 360 and 390."""
    ctx, pg, errors = new_page(browser, w, h)
    pg.goto(f"{server}/John/3/16?study=")
    pg.wait_for_selector("#study-view[open] .study-chip")
    pg.wait_for_timeout(800)
    m = pg.evaluate("""() => { const r = document.querySelector('.study-chips').getBoundingClientRect();
        const chips = [...document.querySelectorAll('.study-chip')].map(c => c.getBoundingClientRect());
        return { whole: chips.filter(b => b.left >= r.left - 1 && b.right <= r.right + 1).length,
                 tools: [...document.querySelectorAll('.study-tool')].filter(t => t.offsetParent)
                        .map(t => [t.getAttribute('aria-label'), Math.round(t.getBoundingClientRect().width), Math.round(t.getBoundingClientRect().height)]) }; }""")
    assert m["whole"] >= 2 > before
    for name, tw, th in m["tools"]:
        assert re.match(r"(Cross-references|Hymns|Your notes)", name)   # named for screen readers
        assert tw >= 36 and th >= 44
    ctx.close()
    assert not errors, errors
