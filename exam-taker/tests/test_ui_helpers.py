"""Batch 1: the global theme in utils/ui_helpers.py and .streamlit/config.toml."""
import inspect
import json
import re
import tomllib
from pathlib import Path

import pytest

from utils import ui_helpers
from utils.ui_helpers import TOKENS

pytestmark = pytest.mark.ui

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- public API
def test_public_api_signatures_unchanged():
    sig = inspect.signature
    assert list(sig(ui_helpers.prepare_math_text).parameters) == ["text"]
    p = sig(ui_helpers.render_math_text).parameters
    assert list(p) == ["text", "font_size", "font_weight", "extra_style", "height"]
    assert p["font_size"].default == "1rem"
    assert p["font_weight"].default == "normal"
    assert p["extra_style"].default == ""
    assert p["height"].default == 70
    assert list(sig(ui_helpers.inject_global_css).parameters) == []
    assert list(sig(ui_helpers.inject_quill_dark_mode).parameters) == []


# ------------------------------------------------------------ prepare_math_text
def test_prepare_math_text_converts_delimiters():
    assert ui_helpers.prepare_math_text(r"a \[x^2\] b") == "a $$x^2$$ b"
    assert ui_helpers.prepare_math_text(r"a \(x\) b") == "a $x$ b"
    assert ui_helpers.prepare_math_text("no math") == "no math"


def test_prepare_math_text_empty_safe():
    assert ui_helpers.prepare_math_text("") == ""
    assert ui_helpers.prepare_math_text(None) is None


# ---------------------------------------------------------------------- tokens
DESIGN_SYSTEM_COLOUR_KEYS = [
    "bg", "surface", "surface-raised", "surface-sunken", "border", "border-strong",
    "ink", "ink-reading", "ink-muted", "ink-faint",
    "accent", "accent-fill", "on-accent-fill", "selected-bg",
    "success", "success-bg", "success-border",
    "danger", "danger-bg", "danger-border",
    "warning", "warning-bg", "warning-border",
    "info", "info-bg",
]


@pytest.mark.parametrize("key", DESIGN_SYSTEM_COLOUR_KEYS)
def test_tokens_has_every_design_system_colour(key):
    assert key.replace("-", "_") in TOKENS


def test_tokens_match_tokens_json_slate_theme():
    data = json.loads((ROOT / "design-system" / "tokens.json").read_text(encoding="utf-8"))
    for tok in data["color"]["tokens"]:
        name = tok["name"].replace("-", "_")
        if name in TOKENS:
            assert TOKENS[name].lower() == tok["value"]["slate"].lower(), name


# -------------------------------------------------------------------- contrast
def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _lum(hex_):
    h = hex_.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(fg, bg):
    a, b = _lum(fg), _lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


TEXT_KEYS = ["ink", "ink_reading", "ink_muted", "accent", "success", "danger", "warning", "info"]
GROUND_KEYS = ["bg", "surface", "surface_sunken"]


@pytest.mark.parametrize("fg", TEXT_KEYS)
@pytest.mark.parametrize("bg", GROUND_KEYS)
def test_text_contrast_aa(fg, bg):
    ratio = contrast(TOKENS[fg], TOKENS[bg])
    assert ratio >= 4.5, f"{fg} on {bg}: {ratio:.2f}"


def test_on_accent_fill_contrast():
    assert contrast(TOKENS["on_accent_fill"], TOKENS["accent_fill"]) >= 4.5


def test_border_strong_contrast_on_surface():
    assert contrast(TOKENS["border_strong"], TOKENS["surface"]) >= 3.0


# ------------------------------------------------------------------------- CSS
@pytest.mark.parametrize("cls", [
    ".question-card", ".success-box", ".error-box", ".explanation-box", ".question-text",
])
def test_global_css_has_classes_pages_use(cls):
    assert cls in ui_helpers._GLOBAL_CSS


def test_global_css_no_fragile_nth_of_type_nav_rules():
    css = ui_helpers._GLOBAL_CSS
    assert "nav-buttons-marker" not in css
    assert "nth-of-type" not in css


@pytest.mark.parametrize("selector", [
    ".st-key-nav_retry button",
    ".st-key-nav_hard button",
    ".st-key-nav_next button",
    ".st-key-nav_submit button",
])
def test_global_css_keyed_nav_selectors(selector):
    assert selector in ui_helpers._GLOBAL_CSS


# ------------------------------------------------------- 3a: bookmark tokens
@pytest.mark.parametrize("key,value", [
    ("bm_red", "#d48a80"), ("bm_orange", "#d6a464"), ("bm_blue", "#8ea9cc"),
    ("bm_purple", "#b4a0cc"), ("bm_green", "#8cc29f"),
])
def test_bookmark_tokens(key, value):
    assert TOKENS[key] == value


# ------------------------------------------------------------- 3a: alerts CSS
@pytest.mark.parametrize("kind", ["Info", "Success", "Warning", "Error"])
def test_alert_css_targets_each_kind(kind):
    assert f'[data-testid="stAlertContent{kind}"]' in ui_helpers._GLOBAL_CSS


def _rule(css, selector):
    start = css.index(selector)
    return css[start:css.index("}", start)]


@pytest.mark.parametrize("kind,bg,border", [
    ("Success", "--etp-success-bg", "--etp-success-border"),
    ("Warning", "--etp-warn-bg", "--etp-warn-border"),
    ("Error", "--etp-danger-bg", "--etp-danger-border"),
])
def test_alert_css_uses_status_tokens(kind, bg, border):
    rule = _rule(ui_helpers._GLOBAL_CSS, f'[data-testid="stAlertContent{kind}"]')
    assert bg in rule and border in rule


def test_info_alert_uses_info_bg():
    rule = _rule(ui_helpers._GLOBAL_CSS, '[data-testid="stAlertContentInfo"]')
    assert "--etp-info-bg" in rule


# -------------------------------------------------- 3a: exam-page CSS hooks
@pytest.mark.parametrize("sel", [
    ".st-key-qcard", '[class*="st-key-opt_correct"]', '[class*="st-key-opt_missed"]',
    '[class*="st-key-opt_wrong"]', '[class*="st-key-opt_neutral"]',
    '[class*="st-key-explain_"]', ".etp-qnum",
])
def test_exam_css_hooks_present(sel):
    assert sel in ui_helpers._GLOBAL_CSS


def _bodies(css, selector):
    """Bodies of every rule whose selector list mentions `selector`."""
    out = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        if selector in m.group(1):
            out.append(m.group(2))
    return out


def test_missed_rows_dashed_and_neutral_dimmed():
    css = ui_helpers._GLOBAL_CSS
    assert any("dashed" in b for b in _bodies(css, '[class*="st-key-opt_missed"]'))
    assert any("opacity" in b for b in _bodies(css, '[class*="st-key-opt_neutral"]'))


# ---------------------------------------------------------- 3a: quill selector
def test_quill_selector_matches_real_iframe(monkeypatch):
    """Real iframe title is 'streamlit_quill.streamlit_quill' (found with Playwright)."""
    captured = {}
    monkeypatch.setattr(ui_helpers.components, "html",
                        lambda html, **kw: captured.setdefault("html", html))
    ui_helpers.inject_quill_dark_mode()
    js = captured["html"]
    assert "streamlit_quill.st_quill" not in js
    assert "quill" in js and "iframe[" in js
    assert "'load'" in js  # re-style after the iframe navigates


def test_topic_analysis_injects_global_css():
    src = (ROOT / "pages" / "Topic_Analysis.py").read_text(encoding="utf-8")
    assert src.count("inject_global_css()") == 1
    assert src.index("set_page_config") < src.index("inject_global_css()")


# ---------------------------------------------------------------- config.toml
def test_config_toml_parses_and_matches_tokens():
    cfg = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert cfg["theme"]["backgroundColor"] == TOKENS["bg"]
    assert cfg["theme"]["secondaryBackgroundColor"] == TOKENS["surface"]
    assert cfg["theme"]["sidebar"]["backgroundColor"] == TOKENS["surface_sunken"]
