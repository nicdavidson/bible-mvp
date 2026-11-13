"""About > Sources and rights at phone size (390x844): it opens from the About dialog and from
the direct link /?about=sources, lists the commentary sources the API returns (with each
licence line), and shows the rights-holder contact: a prefilled GitHub issue link, and an
email link first when one is configured (RIGHTS_CONTACT in modules/menus.js; tested through
the rendering function, no real address is committed)."""
import json
import urllib.parse
import urllib.request

import pytest

from tests.e2e.conftest import new_page

pytest.importorskip("playwright.sync_api")

SECTION = "#about-sources"


def _api_sources(server):
    with urllib.request.urlopen(f"{server}/api/commentary/sources") as r:
        return json.load(r)["sources"]


def _check_section(pg, server):
    pg.wait_for_selector(f"{SECTION} .about-source")
    api = _api_sources(server)
    items = pg.locator(f"{SECTION} .about-source")
    assert items.count() == len(api)
    names = [n.strip() for n in pg.locator(f"{SECTION} .about-source-name").all_inner_texts()]
    assert names == [s["source"] for s in api]
    licences = pg.locator(f"{SECTION} .about-source-license").all_inner_texts()
    assert [t.strip() for t in licences] == [s["license"] for s in api]
    assert "Public domain (no renewal found)" in licences
    # Real headings and links
    assert pg.locator(f"{SECTION} h4#about-sources-h").inner_text() == "Sources and rights"
    assert pg.locator(f"{SECTION} h5", has_text="Rights holders").count() == 1
    full = pg.locator(f"{SECTION} a", has_text="LICENSES.md")
    assert full.get_attribute("href") == "https://github.com/nicdavidson/bible-mvp/blob/master/LICENSES.md"
    links = pg.locator(f"{SECTION} .about-contact a")
    assert links.count() == 1                     # no email configured
    href = links.first.get_attribute("href")
    url = urllib.parse.urlparse(href)
    assert f"{url.scheme}://{url.netloc}{url.path}" == "https://github.com/nicdavidson/bible-mvp/issues/new"
    q = urllib.parse.parse_qs(url.query)
    assert q["title"] == ["Rights enquiry: <work>"]
    for field in ("**Work**", "**Claimant**", "**Basis of the claim**", "**Contact**"):
        assert field in q["body"][0]
    # Fits the phone: no sideways scroll inside the dialog
    assert pg.evaluate("""() => { const m = document.querySelector('.about-modal');
        return m.scrollWidth <= m.clientWidth + 1; }""")


def test_opens_from_about(browser, server):
    ctx, pg, errors = new_page(browser)
    pg.goto(f"{server}/John/3")
    pg.wait_for_selector("#verse-16")
    pg.evaluate("Alpine.$data(document.body).openAbout()")
    pg.wait_for_selector(".about-modal", state="visible")
    pg.locator(".about-link", has_text="Sources and rights").click()
    _check_section(pg, server)
    assert pg.evaluate("document.activeElement.id") == "about-sources-h"
    ctx.close()
    assert not errors, errors


def test_direct_link(browser, server):
    ctx, pg, errors = new_page(browser)
    pg.goto(f"{server}/?about=sources")
    pg.wait_for_selector(".about-modal", state="visible")
    _check_section(pg, server)
    top = pg.evaluate("document.getElementById('about-sources-h').getBoundingClientRect().top")
    assert 0 <= top < 844, top                    # scrolled into view
    ctx.close()
    assert not errors, errors


def test_email_first_when_configured(browser, server):
    ctx, pg, errors = new_page(browser)
    pg.goto(f"{server}/?about=sources")
    pg.wait_for_selector(".about-modal", state="visible")
    links = pg.evaluate("""() => window.BibleRights.rightsContactLinks(
        { ...window.BibleRights.RIGHTS_CONTACT, email: 'rights@example.org' })""")
    assert [link["kind"] for link in links] == ["email", "issue"]
    assert links[0]["href"].startswith("mailto:rights@example.org?subject=")
    assert pg.evaluate("window.BibleRights.RIGHTS_CONTACT.email") is None   # nothing committed
    ctx.close()
    assert not errors, errors
