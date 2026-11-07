"""Batch 5.2: shared list-row components (utils/ui_components.py) + their CSS."""
import re

import pytest

from utils import bookmark_manager, ui_components as ui, ui_helpers

pytestmark = pytest.mark.ui

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿️]")


# ------------------------------------------------------------- list_row_html
def test_list_row_structure():
    html = ui.list_row_html("What is 2+2?", "geography · sample", "#d48a80")
    assert 'class="etp-li"' in html
    assert '<div class="etp-li__q">What is 2+2?</div>' in html
    assert '<div class="etp-li__meta">geography · sample</div>' in html
    assert 'class="etp-li__dot"' in html and "#d48a80" in html


def test_list_row_without_dot():
    assert "etp-li__dot" not in ui.list_row_html("Q", "meta")


def test_list_row_escapes_html_but_keeps_math():
    html = ui.list_row_html("<b>bold</b> $x^2$ and $$a_1$$", "<i>m</i>")
    assert "&lt;b&gt;bold&lt;/b&gt;" in html and "&lt;i&gt;m&lt;/i&gt;" in html
    assert "$x^2$" in html and "$$a_1$$" in html


def test_list_row_repairs_broken_latex():
    assert "$\\frac12$" in ui.list_row_html("see $\x0crac12$", "")


def test_list_row_meta_accepts_sequence():
    assert "a · b · c" in ui.list_row_html("Q", ["a", "b", "c"])


def test_list_row_none_safe():
    assert 'class="etp-li"' in ui.list_row_html(None, None)


def test_list_row_has_no_emoji():
    assert not EMOJI.search(ui.list_row_html("Q", "meta", "#fff"))


# ---------------------------------------------------------------- count_line
@pytest.mark.parametrize("args,expected", [
    ((41, 12, "saved"), "41 saved · showing 12"),
    ((3, 3, "archived"), "3 archived · showing 3"),
    ((0, 0, "saved"), "0 saved · showing 0"),
])
def test_count_line(args, expected):
    assert ui.count_line(*args) == expected


# ------------------------------------------------------------ BOOKMARK_STYLE
def test_bookmark_style_covers_every_bookmark_colour():
    assert set(ui.BOOKMARK_STYLE) == set(bookmark_manager.BOOKMARK_COLORS)


@pytest.mark.parametrize("name,token,label", [
    ("Important (Red)", "bm_red", "Important"),
    ("Review Later (Orange)", "bm_orange", "Review later"),
    ("Interesting (Blue)", "bm_blue", "Interesting"),
    ("Hard (Purple)", "bm_purple", "Hard"),
    ("Solved (Green)", "bm_green", "Solved"),
])
def test_bookmark_style_values(name, token, label):
    assert ui.BOOKMARK_STYLE[name] == (ui_helpers.TOKENS[token], label)


def test_bookmark_style_has_no_emoji():
    for colour, label in ui.BOOKMARK_STYLE.values():
        assert not EMOJI.search(colour + label)


def test_bookmark_style_unknown_name_helper():
    assert ui.bookmark_style("Nope") == (ui_helpers.TOKENS["ink_muted"], "Nope")
    assert ui.bookmark_style("Hard (Purple)")[1] == "Hard"


# ----------------------------------------------------------------------- CSS
@pytest.mark.parametrize("cls", [
    ".etp-list", ".etp-li", ".etp-li__q", ".etp-li__meta", ".etp-li__dot",
    ".etp-chip", ".etp-chip--red", ".etp-chip--orange", ".etp-chip--blue",
    ".etp-chip--purple", ".etp-chip--green",
])
def test_css_has_class(cls):
    assert cls in ui_helpers._GLOBAL_CSS


def test_row_text_is_clamped_to_two_lines():
    bodies = [m.group(2) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", ui_helpers._GLOBAL_CSS)
              if ".etp-li__q" in m.group(1)]
    assert any("-webkit-line-clamp: 2" in b for b in bodies)


def test_every_emitted_list_class_has_css():
    html = ui.list_row_html("Q", "meta", "#fff")
    for cls in set(re.findall(r'class="([^"]+)"', html)):
        for c in cls.split():
            assert "." + c in ui_helpers._GLOBAL_CSS, c


def test_bookmark_css_variables_defined():
    for name in ("red", "orange", "blue", "purple", "green"):
        assert f"--etp-bm-{name}:{ui_helpers.TOKENS['bm_' + name]}" in ui_helpers._GLOBAL_CSS.replace(" ", "")
