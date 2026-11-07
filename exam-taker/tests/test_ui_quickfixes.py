"""Batch 4.1: small exam-page fixes (radio width, Next icon order, page icon)."""
import ast
import re
from pathlib import Path

import pytest

from utils import ui_helpers

pytestmark = pytest.mark.ui

ROOT = Path(__file__).resolve().parent.parent
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿️]")


def _calls(path, attr):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == attr]


def _kw(call, name):
    for k in call.keywords:
        if k.arg == name:
            return ast.literal_eval(k.value) if isinstance(k.value, ast.Constant) else k.value
    return None


def test_exam_radio_uses_width_stretch():
    """AppTest does not expose element width, so assert on the source."""
    radios = _calls(ROOT / "utils" / "exam_view.py", "radio")
    assert radios, "exam_view must contain the answer radio"
    assert all(_kw(r, "width") == "stretch" for r in radios)


def test_nav_next_button_icon_after_label():
    css = ui_helpers._GLOBAL_CSS
    bodies = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        if ".st-key-nav_next button" in m.group(1):
            bodies.append(m.group(2))
    assert any("row-reverse" in b for b in bodies)


def test_app_page_icon_is_material_not_emoji():
    calls = _calls(ROOT / "app.py", "set_page_config")
    assert len(calls) == 1
    assert _kw(calls[0], "page_icon") == ":material/menu_book:"
    assert not EMOJI.search(ast.unparse(calls[0]))
