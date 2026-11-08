"""Batch 10b.2: fonts and KaTeX are served from the app's own static/ folder (no CDN at run time).
Static checks here; the real-browser check (zero external requests, fonts and formulas render with the network
blocked) is tests/e2e/test_offline_assets_browser.py."""
import re
import tomllib
from pathlib import Path

import pytest

from tools import fetch_assets
from utils import ui_helpers

APP = Path(__file__).resolve().parent.parent
STATIC = APP / "static"
EXTERNAL = re.compile(r"fonts\.googleapis\.com|fonts\.gstatic\.com|cdn\.jsdelivr\.net|cdnjs\.|unpkg\.com", re.I)
UI_SOURCES = ["app.py", "main.py", *[f"pages/{p.name}" for p in (APP / "pages").glob("*.py")],
              *[f"utils/{p.name}" for p in (APP / "utils").glob("*.py") if "backup" not in p.name]]

pytestmark = pytest.mark.ui


def test_static_serving_is_enabled():
    cfg = tomllib.loads((APP / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert cfg["server"]["enableStaticServing"] is True


def test_asset_files_are_all_present():
    assert fetch_assets.check() == 0


def test_fonts_css_covers_the_three_families_and_weights():
    css = (STATIC / "fonts" / "fonts.css").read_text(encoding="utf-8")
    seen = set(re.findall(r"font-family: '([^']+)';\s*font-style: normal;\s*font-weight: ([^;]+);", css))
    assert {("Literata", "400"), ("Literata", "500"), ("Literata", "600"),
            ("Atkinson Hyperlegible", "400"), ("Atkinson Hyperlegible", "700"), ("JetBrains Mono", "400")} <= seen
    assert "font-display: swap" in css and "unicode-range" in css


def test_every_font_file_referenced_exists():
    for css_file, prefix in (("fonts/fonts.css", "/app/static/fonts/"), ("katex/katex.min.css", "/app/static/katex/fonts/")):
        text = (STATIC / css_file).read_text(encoding="utf-8")
        files = re.findall(re.escape(prefix) + r"([\w.-]+\.woff2)", text)
        assert files, css_file
        base = STATIC / Path(css_file).parent / ("fonts" if "katex" in css_file else "")
        assert all((base / f).stat().st_size > 1000 for f in files), css_file


@pytest.mark.parametrize("name", ["OFL-Literata.txt", "OFL-Atkinson-Hyperlegible.txt", "OFL-JetBrains-Mono.txt"])
def test_font_licences_are_bundled(name):
    assert "SIL OPEN FONT LICENSE" in (STATIC / "fonts" / name).read_text(encoding="utf-8").upper()


def test_katex_licence_is_bundled():
    assert "MIT License" in (STATIC / "katex" / "LICENSE").read_text(encoding="utf-8")


def test_katex_css_has_only_local_woff2_sources():
    css = (STATIC / "katex" / "katex.min.css").read_text(encoding="utf-8")
    assert not EXTERNAL.search(css)
    assert ".woff)" not in css and ".ttf)" not in css


def test_global_css_has_the_font_faces_inline_with_local_woff2_urls():
    """Streamlit serves static .css/.js as text/plain + nosniff, which browsers refuse as stylesheet/script, so
    the @font-face rules are inlined (woff2 files are fine) instead of @import-ing static/fonts/fonts.css."""
    css = ui_helpers._GLOBAL_CSS
    assert "@import" not in css
    assert css.count("@font-face") >= 6
    assert "font-family: 'Literata'" in css and "font-family: 'Atkinson Hyperlegible'" in css
    assert "/app/static/fonts/literata-latin-" in css and ".woff2" in css


def test_quill_iframe_css_has_the_same_inline_font_faces(monkeypatch):
    import streamlit.components.v1 as components
    seen = {}
    monkeypatch.setattr(components, "html", lambda html, **kw: seen.setdefault("html", html))
    ui_helpers.inject_quill_dark_mode()
    assert "@font-face" in seen["html"] and "@import" not in seen["html"]
    assert not EXTERNAL.search(seen["html"])


def test_katex_head_never_links_static_css_or_js_directly():
    """A <link>/<script src> to /app/static/*.css|js is blocked (text/plain + nosniff): they are fetched and handed
    to the browser as blob URLs with the right MIME type."""
    head = ui_helpers._KATEX_HEAD
    assert 'href="/app/static' not in head and 'src="/app/static' not in head
    for needle in ("/app/static", "/katex/", "katex.min.css", "katex.min.js", "auto-render.min.js",
                   "createObjectURL", "text/css", "text/javascript"):
        assert needle in head, needle
    assert "@font-face" in head or "/app/static/fonts/" in head


@pytest.mark.parametrize("rel", UI_SOURCES)
def test_no_cdn_host_in_ui_sources(rel):
    assert not EXTERNAL.search((APP / rel).read_text(encoding="utf-8")), rel


def test_rendered_html_of_the_quill_style_has_no_cdn_host(seeded_app):
    assert not EXTERNAL.search(seeded_app)


@pytest.fixture
def seeded_app():
    """All CSS/HTML the ui_helpers hand to the browser, as one string."""
    import inspect
    return ui_helpers._GLOBAL_CSS + ui_helpers._KATEX_HEAD + inspect.getsource(ui_helpers.inject_quill_dark_mode)


def test_fetch_assets_tool_is_importable_and_has_check_mode():
    assert fetch_assets.URL_PREFIX == "/app/static"
    assert fetch_assets.KATEX_VERSION == "0.16.11"
    assert callable(fetch_assets.fetch_fonts) and callable(fetch_assets.fetch_katex)
