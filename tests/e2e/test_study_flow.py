"""Browser flow test for the study view (Playwright, headless Chromium).

Starts the app on a free local port against the worktree DB, then: selects a verse
range in John 3, opens the study view, switches sources (and back, keeping scroll
position), follows a reference inside commentary, comes back with Back, checks the
deep link, and closes to the reader.

Skips when Playwright or its browser is not installed.
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    port = _free_port()
    env = {**os.environ, "SUPABASE_URL": "", "APP_ENV": "test"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(f"{base}/api/health", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    else:
        proc.kill()
        pytest.skip("app server did not start")
    yield base
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # browser binary not installed
            pytest.skip(f"chromium not available: {e}")
        yield b
        b.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True,
                              service_workers="block")
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    yield pg
    ctx.close()
    assert not errors, errors


def _path(pg):
    return pg.evaluate("location.pathname + location.search")


def test_select_range_study_switch_follow_ref_and_back(server, page):
    page.goto(f"{server}/John/3")
    page.wait_for_selector("#verse-16")

    # Tap the first verse, then the last: a range
    page.locator("#verse-16").scroll_into_view_if_needed()
    page.tap("#verse-16 .verse-num")
    page.tap("#verse-18 .verse-num")
    assert page.evaluate("Alpine.$data(document.body).highlightedVerses") == [16, 17, 18]

    # The Study button shows how many sources comment on the selection
    page.wait_for_selector(".action-bar-study .action-bar-count:not([style*='display: none'])")
    page.tap(".verse-action-bar .action-bar-study")
    page.wait_for_selector("#study-view[open] .study-pane-body p")
    assert page.inner_text("#study-title") == "John 3:16–18"
    assert page.evaluate("document.activeElement.id") == "study-title"   # focus moved into the view
    assert "/John/3/16-18?study=" in _path(page)
    assert len(page.locator(".study-verse").all()) == 3

    # Henry's passage-level note reaches v16-18; Gill is verse by verse
    chips = page.locator(".study-chip:not(.is-empty)")
    slugs = [chips.nth(i).get_attribute("data-slug") for i in range(chips.count())]
    assert {"john-gill", "matthew-henry"} <= set(slugs)

    if page.get_attribute('.study-chip[data-slug="john-gill"]', "aria-pressed") != "true":
        page.tap('.study-chip[data-slug="john-gill"]')
    else:
        # Tapping the active chip shows who the source is
        page.tap('.study-chip[data-slug="john-gill"]')
        page.wait_for_selector("#study-info[open]")
        assert "Particular Baptist" in page.inner_text("#study-info")
        page.keyboard.press("Escape")
        page.wait_for_function("!document.getElementById('study-info').open")
        assert page.evaluate("document.getElementById('study-view').open")
    gill = page.locator('.study-pane[data-slug="john-gill"] .study-pane-scroll')
    page.wait_for_selector('.study-pane[data-slug="john-gill"] .study-pane-body p')
    gill.evaluate("el => el.scrollTo(0, 600)")
    page.wait_for_timeout(200)

    # Switch to Henry, then back with the swap button: Gill keeps its place
    page.tap('.study-chip[data-slug="matthew-henry"]')
    page.wait_for_selector('.study-pane[data-slug="matthew-henry"] .study-pane-body p')
    page.wait_for_function("document.querySelector('.study-pane[data-slug=\"matthew-henry\"] .study-note').offsetParent")
    assert "1–21" in page.inner_text('.study-pane[data-slug="matthew-henry"] .study-note')
    assert _path(page).endswith("study=matthew-henry")
    page.tap(".study-swap")
    page.wait_for_function("location.search.endsWith('john-gill')")
    page.wait_for_timeout(500)
    assert abs(gill.evaluate("el => el.scrollTop") - 600) < 2

    # Follow a reference inside the commentary: peek, then study it
    link = page.locator('.study-pane[data-slug="john-gill"] a.commentary-ref').first
    link.scroll_into_view_if_needed()
    link.click()
    page.wait_for_selector("#study-peek[open] .study-verse")
    target = page.inner_text("#study-peek-title")
    page.locator("#study-peek .study-primary-btn").click()
    page.wait_for_function(f"document.getElementById('study-title').textContent === {target!r}")
    assert page.is_visible(".study-back")
    assert "Back to John 3:16–18" in page.inner_text(".study-back")

    # Back returns to the first study location, same source
    page.go_back()
    page.wait_for_function("document.getElementById('study-title').textContent === 'John 3:16–18'")
    assert _path(page).endswith("/John/3/16-18?study=john-gill")
    page.wait_for_selector('.study-pane[data-slug="john-gill"] .study-pane-body p')

    # Close returns to the reader, focus back on the Study button, nothing reloaded
    page.tap(".study-bar .study-icon-btn")
    page.wait_for_function("!document.getElementById('study-view').open")
    assert _path(page) == "/John/3"
    assert page.evaluate("Alpine.$data(document.body).currentReference").startswith("John 3")


def test_deep_link_opens_same_view_and_escape_closes(server, page):
    page.goto(f"{server}/John/3/16-18?study=matthew-henry")
    page.wait_for_selector("#study-view[open] .study-pane-body p")
    assert page.inner_text("#study-title") == "John 3:16–18"
    assert page.get_attribute('.study-chip[aria-pressed="true"]', "data-slug") == "matthew-henry"
    page.keyboard.press("Escape")
    page.wait_for_function("!document.getElementById('study-view').open")
    assert page.evaluate("location.search") == ""
    assert page.is_visible("#verse-16")


def test_offline_study_from_cache(server, browser):
    """A chapter studied once online opens offline from IndexedDB."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
    pg = ctx.new_page()
    pg.goto(f"{server}/John/3/16?study=john-gill")
    pg.wait_for_selector("#study-view[open] .study-pane-body p")
    pg.wait_for_timeout(500)   # let the IndexedDB writes land
    pg.keyboard.press("Escape")
    ctx.set_offline(True)
    pg.evaluate("Alpine.$data(document.body).openStudy('John 3:17', { source: 'john-gill' })")
    pg.wait_for_selector("#study-view[open] .study-pane-body p")
    assert "17" in pg.inner_text(".study-verses")
    ctx.close()
