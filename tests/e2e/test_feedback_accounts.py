"""Feedback from the side menu (signed out) and the account controls, against a fake
Supabase: the app is started with SUPABASE_URL set and every request to it is answered
by Playwright, so nothing leaves the machine."""
import json
import os
import subprocess
import sys
import time
import urllib.request

import pytest

from tests.e2e.conftest import ROOT, _free_port, new_page

FAKE = "https://fake-supabase.test"
USER = {"id": "11111111-1111-1111-1111-111111111111", "email": "reader@example.org",
        "aud": "authenticated", "role": "authenticated"}


@pytest.fixture(scope="module")
def sb_server():
    port = _free_port()
    env = {**os.environ, "SUPABASE_URL": FAKE, "SUPABASE_ANON_KEY": "anon", "APP_ENV": "test"}
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


def _fake_supabase(pg):
    """Answer every Supabase call; return the list the calls are recorded in."""
    calls = []

    def handle(route):
        req = route.request
        path = req.url.split(FAKE, 1)[1].split("?")[0]
        body = req.post_data_json if req.post_data else None
        calls.append((req.method, path, body))
        cors = {"access-control-allow-origin": "*", "access-control-allow-headers": "*",
                "access-control-allow-methods": "*"}
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers=cors)
        if path == "/auth/v1/token":
            out = {"access_token": "t", "refresh_token": "r", "token_type": "bearer",
                   "expires_in": 3600, "expires_at": int(time.time()) + 3600, "user": USER}
        elif path == "/auth/v1/user":
            out = USER
        elif path.startswith("/rest/v1/rpc/") or req.method == "POST":
            return route.fulfill(status=201 if "rpc" not in path else 204, headers=cors, body="")
        else:
            out = []
        route.fulfill(status=200, headers={**cors, "content-type": "application/json"},
                      body=json.dumps(out))

    pg.route(f"{FAKE}/**", handle)
    return calls


def _open(browser, base):
    ctx, pg, errors = new_page(browser, 390, 844)
    calls = _fake_supabase(pg)
    pg.goto(f"{base}/John/3")
    pg.wait_for_selector("#verse-16")
    return ctx, pg, errors, calls


def test_signed_out_feedback_from_the_menu(sb_server, browser):
    ctx, pg, errors, calls = _open(browser, sb_server)
    pg.click(".btn-hamburger")
    pg.click("[data-testid=menu-feedback]")
    assert pg.locator(".feedback-form input[type=file]").count() == 0   # uploads need an account
    pg.fill(".feedback-form textarea", "The chips overlap on my phone")
    pg.fill("#feedback-contact", "me@example.org")
    pg.click(".feedback-form button[type=submit]")
    pg.wait_for_selector(".feedback-success:visible")
    sent = [b for m, p, b in calls if p == "/rest/v1/bug_reports" and m == "POST"]
    assert len(sent) == 1
    assert sent[0]["user_id"] is None and sent[0]["user_email"] == "me@example.org"
    assert sent[0]["description"] == "The chips overlap on my phone"
    assert not errors
    ctx.close()


def test_change_password_and_close_account(sb_server, browser):
    ctx, pg, errors, calls = _open(browser, sb_server)
    pg.click(".btn-hamburger")
    pg.click(".side-menu-signin")
    pg.fill("input[type=email].auth-input", USER["email"])
    pg.fill("input[placeholder=Password]", "secret-1")
    pg.click(".auth-actions button:has-text('Sign In')")
    pg.wait_for_selector("#new-password")

    pg.fill("#new-password", "secret-2")
    pg.click("button:has-text('Change password')")
    pg.wait_for_selector(".auth-success:has-text('Password changed')")
    assert any(m == "PUT" and p == "/auth/v1/user" and b["password"] == "secret-2"
               for m, p, b in calls)

    pg.once("dialog", lambda d: d.accept())
    pg.click("[data-testid=delete-account]")
    pg.wait_for_selector(".auth-signed-out")
    assert any(p == "/rest/v1/rpc/delete_own_account" for _, p, _ in calls)
    assert not errors
    ctx.close()


def test_menu_item_hidden_when_accounts_are_off(server, browser):
    ctx, pg, errors = new_page(browser, 390, 844)
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-16")
    pg.click(".btn-hamburger")
    assert not pg.locator("[data-testid=menu-feedback]").is_visible()
    ctx.close()
