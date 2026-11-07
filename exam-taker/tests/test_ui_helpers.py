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


def test_global_css_nav_buttons_marker_selectors():
    css = ui_helpers._GLOBAL_CSS
    assert '#nav-buttons-marker' in css
    assert '[data-testid="column"]' in css
    assert '[data-testid="stElementContainer"]:has(#nav-buttons-marker) + [data-testid="stLayoutWrapper"]' in css


# ---------------------------------------------------------------- config.toml
def test_config_toml_parses_and_matches_tokens():
    cfg = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert cfg["theme"]["backgroundColor"] == TOKENS["bg"]
    assert cfg["theme"]["secondaryBackgroundColor"] == TOKENS["surface"]
    assert cfg["theme"]["sidebar"]["backgroundColor"] == TOKENS["surface_sunken"]
