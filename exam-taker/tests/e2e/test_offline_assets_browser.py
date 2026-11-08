"""Batch 10b.2 in a real browser: with every non-local host BLOCKED the app makes zero external requests, the
fonts are Literata / Atkinson Hyperlegible (really loaded, from /app/static) and a formula renders as KaTeX.
Skipped when Playwright or Chromium is missing."""
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import pytest

from tests.e2e.ports import free_port

pw_sync = pytest.importorskip("playwright.sync_api")

APP_DIR = Path(__file__).resolve().parents[2]
pytestmark = [pytest.mark.e2e]
LOCAL = {"localhost", "127.0.0.1"}


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    work = tmp_path_factory.mktemp("etp_offline")
    shutil.copytree(APP_DIR / "tests" / "fixtures" / "workspace", work, dirs_exist_ok=True)
    shutil.copytree(APP_DIR / ".streamlit", work / ".streamlit", dirs_exist_ok=True)
    qfile = work / "questions" / "sample" / "sample.json"
    qs = json.loads(qfile.read_text(encoding="utf-8"))
    qs[0]["question"] = "Compute $x^2$ when $x = 3$."                             # a formula in the question stem
    qfile.write_text(json.dumps(qs), encoding="utf-8")
    for old in (work / "logs" / "attempts").glob("*.json"):
        old.unlink()
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(APP_DIR / "main.py"), "--server.headless", "true",
         "--server.port", str(port), "--browser.gatherUsageStats", "false"],
        cwd=work, stdout=open(work / "server.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT)
    url = f"http://localhost:{port}"
    for _ in range(150):
        try:
            urllib.request.urlopen(url + "/_stcore/health", timeout=2)
            break
        except Exception:
            time.sleep(0.4)
    else:
        proc.terminate()
        pytest.skip("streamlit did not start in time")
    try:
        yield url
    finally:
        proc.terminate()


@pytest.fixture(scope="module")
def browser():
    with pw_sync.sync_playwright() as pw:
        try:
            b = pw.chromium.launch()
        except Exception as e:
            pytest.skip(f"Chromium not available: {e}")
        yield b
        b.close()


@pytest.fixture
def offline(browser):
    """A page whose context aborts every request to a non-local host and remembers it."""
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    external = []

    def gate(route):
        host = urlparse(route.request.url).hostname
        if host in LOCAL or route.request.url.startswith(("data:", "blob:", "about:")):
            route.continue_()
        else:
            external.append(route.request.url)
            route.abort()

    ctx.route("**/*", gate)
    page = ctx.new_page()
    page.external = external
    page.console_log = []                                           # saved with a failure (conftest.py)
    page.on("console", lambda m: page.console_log.append(f"{m.type}: {m.text}"))
    page.on("pageerror", lambda e: page.console_log.append(f"pageerror: {e}"))
    page.on("requestfailed", lambda r: page.console_log.append(f"requestfailed: {r.url}"))
    yield page
    ctx.close()


def open_exam(page, url):
    page.goto(url + "/")
    page.wait_for_selector(".st-key-qstem", timeout=60000)
    # fonts load lazily: ask for them and wait until the browser really has them (condition, not a sleep)
    page.wait_for_function(
        """async () => (await Promise.all([document.fonts.load("16px Literata"),
                                            document.fonts.load("16px 'Atkinson Hyperlegible'")]))
                         .every(list => list.length > 0)""", timeout=30000)


def loaded_families(page):
    return page.evaluate("""() => [...document.fonts].filter(f => f.status === 'loaded')
                                  .map(f => f.family.replace(/["']/g, ''))""")


def test_no_external_request_on_any_exam_page(server, offline):
    open_exam(offline, server)
    for path in ("/practice-bookmarks", "/regressive-practice", "/bookmarks", "/progress"):
        offline.goto(server + path)
        offline.wait_for_timeout(2500)
    assert offline.external == [], offline.external


def test_static_files_are_served_by_the_app(server, offline):
    for path, kind in (("/app/static/fonts/fonts.css", "css"), ("/app/static/katex/katex.min.css", "css"),
                       ("/app/static/katex/katex.min.js", "javascript"), ("/app/static/katex/auto-render.min.js", "javascript"),
                       ("/app/static/katex/fonts/KaTeX_Main-Regular.woff2", "font")):
        resp = offline.request.get(server + path)
        assert resp.status == 200, path
        assert len(resp.body()) > 1000, path


def test_fonts_are_literata_and_atkinson_with_the_network_blocked(server, offline):
    open_exam(offline, server)
    stem = offline.evaluate("() => getComputedStyle(document.querySelector('.st-key-qstem p')).fontFamily")
    assert stem.split(",")[0].strip(" \"'") == "Literata", stem
    ui = offline.evaluate("() => getComputedStyle(document.querySelector('.stButton button p, .stButton button')).fontFamily")
    assert "Atkinson Hyperlegible" in ui, ui
    assert offline.evaluate("() => document.fonts.check('16px Literata')")
    assert offline.evaluate("() => document.fonts.check(\"16px 'Atkinson Hyperlegible'\")")
    families = set(loaded_families(offline))
    assert {"Literata", "Atkinson Hyperlegible"} <= families, families            # really loaded, not a fallback
    assert offline.evaluate("async () => (await document.fonts.load(\"16px 'JetBrains Mono'\")).length > 0")
    assert offline.external == []


def test_a_formula_renders_as_katex_with_the_network_blocked(server, offline):
    open_exam(offline, server)
    assert offline.locator(".st-key-qstem .katex").count() >= 2                  # $x^2$ and $x = 3$
    assert offline.external == []


def test_the_katex_component_head_renders_from_static(server, offline, monkeypatch):
    """render_math_text()'s iframe document (auto-render from /app/static) renders $x^2$ with no CDN."""
    import streamlit.components.v1 as components
    from utils import ui_helpers
    captured = {}
    monkeypatch.setattr(components, "html", lambda html, **kw: captured.setdefault("html", html))
    ui_helpers.render_math_text("Value: $x^2$")
    open_exam(offline, server)
    offline.evaluate("""html => { const f = document.createElement('iframe'); f.id = 'mathframe'; f.srcdoc = html;
                                  document.body.appendChild(f); }""", captured["html"])
    frame = offline.frame_locator("#mathframe")
    frame.locator(".katex").first.wait_for(timeout=15000)
    assert offline.external == []
