"""Shared fixtures for the browser flow tests (Playwright, headless Chromium).

One app server and one browser for the whole run: this box is small and shared.
The server runs on a free port above 8400 against the worktree DB, with Supabase
off. Tests skip when Playwright or its browser is not installed.
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _free_port(start=8401, end=8999):
    for port in range(start, end):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("no free port above 8400")


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # browser binary not installed
            pytest.skip(f"chromium not available: {e}")
        yield b
        b.close()


# The first-run walkthrough (modules/tour.js) starts on a fresh device's first plain load
# and covers the page. Flows that aren't about it start as a device that has seen it.
SEEN_TOUR = "try { localStorage.setItem('tourDone', '1') } catch (e) {}"


def skip_tour(ctx):
    ctx.add_init_script(SEEN_TOUR)


def new_page(browser, width=390, height=844, touch=True, tour=False):
    """A fresh context (empty storage, except that the walkthrough counts as seen unless
    tour=True) at the given size. Returns (context, page, errors)."""
    ctx = browser.new_context(viewport={"width": width, "height": height}, has_touch=touch,
                              is_mobile=touch, service_workers="block")
    if not tour:
        skip_tour(ctx)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    return ctx, pg, errors


@pytest.fixture
def page(browser):
    ctx, pg, errors = new_page(browser)
    yield pg
    ctx.close()
    assert not errors, errors
