"""Batch 2: pure HTML helpers in utils/ui_components.py (new file)."""
import re

import pytest

from utils import ui_components as ui
from utils import ui_helpers

pytestmark = pytest.mark.ui

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


# ---------------------------------------------------------------- option_label
@pytest.mark.parametrize("raw,expected", [
    ("A) Some text", "Some text"),
    ("B. Some text", "Some text"),
    ("(C) Some text", "Some text"),
    ("d) Some text", "Some text"),
    ("   A) Some text", "Some text"),
    ("A)   Some text", "Some text"),
    ("Some text", "Some text"),
    ("  Some text  ", "Some text"),
    ("", ""),
])
def test_option_label(raw, expected):
    assert ui.option_label(raw) == expected


def test_option_label_keeps_latex():
    assert ui.option_label("$a) b$") == "$a) b$"
    assert ui.option_label("A) $x^2$") == "$x^2$"


def test_option_label_none_safe():
    assert ui.option_label(None) == ""


# ---------------------------------------------------------------- option_state
@pytest.mark.parametrize("idx,correct,selected,expected", [
    (1, [1], [1], "correct"),
    (0, [1], [1], "neutral"),
    (2, [0, 2], [0], "missed"),
    (3, [1], [3], "wrong"),
    (0, [0, 2], [0, 2], "correct"),
    (1, [0], [], "neutral"),
    (0, [0], [], "missed"),
])
def test_option_state(idx, correct, selected, expected):
    assert ui.option_state(idx, correct, selected) == expected


# ----------------------------------------------------------------------- badge
@pytest.mark.parametrize("kind", ["easy", "medium", "hard", "info", "reattempt"])
def test_badge_kinds(kind):
    assert ui.badge(kind, "X") == f'<span class="etp-badge etp-badge--{kind}">X</span>'


def test_badge_escapes_text():
    assert "&lt;b&gt;" in ui.badge("info", "<b>")
    assert "<b>" not in ui.badge("info", "<b>")


def test_badge_unknown_kind_is_neutral():
    assert "etp-badge--neutral" in ui.badge("bogus", "x")


def test_difficulty_badge():
    assert ui.difficulty_badge("medium") == ui.badge("medium", "Medium")
    assert ui.difficulty_badge("HARD") == ui.badge("hard", "Hard")
    assert ui.difficulty_badge("Easy") == ui.badge("easy", "Easy")


def test_difficulty_badge_unknown_is_neutral():
    out = ui.difficulty_badge("weird")
    assert "etp-badge--neutral" in out and "Weird" in out
    assert "etp-badge--neutral" in ui.difficulty_badge(None)


# -------------------------------------------------------------------- meta_row
def test_meta_row_full():
    html = ui.meta_row(["a", "b"], "easy", True, "2030-01-01")
    assert "etp-badge--easy" in html
    assert "etp-badge--reattempt" in html and "Reattempt" in html
    assert "2030-01-01" in html
    assert "a · b" in html
    assert 'class="etp-tag"' in html


def test_meta_row_minimal():
    html = ui.meta_row([], "medium", False, None)
    assert "etp-badge--reattempt" not in html
    assert "etp-tag" not in html
    assert "New" in html  # no due date yet


def test_meta_row_escapes_tags():
    assert "&lt;script&gt;" in ui.meta_row(["<script>"], "easy", False, None)


# -------------------------------------------------------------------- feedback
def test_feedback_correct():
    kind, title, body = ui.feedback(1.0, ["B"])
    assert (kind, title) == ("success", "Correct")


def test_feedback_partial():
    kind, title, body = ui.feedback(0.67, ["A", "C"])
    assert kind == "partial"
    assert title == "Partly correct · score 0.67"
    assert body == "The right answers are A and C."


def test_feedback_wrong():
    assert ui.feedback(0.0, ["B"]) == ("danger", "Not correct", "The right answer is B.")


def test_feedback_three_answers():
    assert ui.feedback(0.0, ["A", "B", "C"])[2] == "The right answers are A, B and C."


# ---------------------------------------------------------------- option_row
@pytest.mark.parametrize("state,word", [
    ("correct", "Correct"), ("missed", "Missed"), ("wrong", "Your pick"),
])
def test_option_row_status_words(state, word):
    html = ui.option_row_html("B", "Paris", state)
    assert f'class="etp-option is-{state}"' in html
    assert f'<span class="etp-option__status">{word}</span>' in html
    assert '<span class="etp-option__key">B</span>' in html
    assert '<span class="etp-option__text">Paris</span>' in html


def test_option_row_neutral_has_no_status():
    html = ui.option_row_html("A", "x", "neutral")
    assert "is-neutral" in html and "etp-option__status" not in html


def test_option_row_unknown_state_is_neutral():
    assert "is-neutral" in ui.option_row_html("A", "x", "nonsense")


def test_option_row_escapes_html_but_keeps_math():
    html = ui.option_row_html("A", "<b>bold</b> $x^2$ and $$\\frac{a}{b}$$", "neutral")
    assert "&lt;b&gt;bold&lt;/b&gt;" in html
    assert "$x^2$" in html
    assert "$$\\frac{a}{b}$$" in html


# ------------------------------------------------------------ banner / explain
def test_feedback_banner_html():
    html = ui.feedback_banner_html("partial", "Title", "Body")
    assert 'class="etp-banner etp-banner--partial"' in html
    assert "etp-banner__title" in html and "Title" in html and "Body" in html


def test_feedback_banner_skips_empty_body():
    assert "etp-banner__body" not in ui.feedback_banner_html("success", "Correct", "")


def test_explanation_html():
    html = ui.explanation_html("Line one.\n\nSecond $x^2$ <i>.")
    assert 'class="etp-explain"' in html
    assert "Explanation" in html
    assert "<p>Line one.</p>" in html
    assert "$x^2$" in html and "&lt;i&gt;" in html


# ------------------------------------------------------- page head, stat tiles
def test_page_head_html():
    html = ui.page_head_html("Bookmarks", "12 saved")
    assert 'class="etp-pagehead"' in html
    assert "<h1>Bookmarks</h1>" in html and "<p>12 saved</p>" in html
    assert "<p>" not in ui.page_head_html("Bookmarks", "")


def test_page_head_escapes():
    assert "&lt;" in ui.page_head_html("<x>", "<y>")


def test_stat_tile_html():
    html = ui.stat_tile_html("Accuracy", "82%", "+4% this week", "up")
    assert 'class="etp-stat"' in html
    assert "etp-stat__label" in html and "Accuracy" in html
    assert "etp-stat__value" in html and "82%" in html
    assert 'class="etp-stat__delta up"' in html and "+4% this week" in html


def test_stat_tile_without_delta():
    assert "etp-stat__delta" not in ui.stat_tile_html("Total", 40)
    assert ">40<" in ui.stat_tile_html("Total", 40)


def test_stat_tile_trend_down_and_unknown():
    assert 'etp-stat__delta down"' in ui.stat_tile_html("a", 1, "-1", "down")
    assert 'class="etp-stat__delta"' in ui.stat_tile_html("a", 1, "x", "sideways")


def test_stat_tiles_html_wraps_grid():
    html = ui.stat_tiles_html([("A", 1), ("B", 2, "+1", "up")])
    assert html.startswith('<div class="etp-stats">') and html.count('class="etp-stat"') == 2


# ------------------------------------------------------------------- no emoji
def test_no_emoji_in_any_output():
    outputs = [
        ui.badge("info", "x"), ui.difficulty_badge("hard"),
        ui.meta_row(["t1", "t2"], "hard", True, "2030-01-01"),
        ui.meta_row([], "easy", False, None),
        *ui.feedback(1.0, ["A"]), *ui.feedback(0.5, ["A", "B"]), *ui.feedback(0, ["C"]),
        ui.option_row_html("A", "x", "correct"), ui.option_row_html("A", "x", "missed"),
        ui.option_row_html("A", "x", "wrong"), ui.option_row_html("A", "x", "neutral"),
        ui.feedback_banner_html("success", "Correct", "Well done."),
        ui.explanation_html("text"), ui.page_head_html("T", "S"),
        ui.stat_tile_html("L", 1, "d", "up"), ui.stat_tiles_html([("A", 1)]),
    ]
    for out in outputs:
        assert not EMOJI.search(out), out


# ------------------------------------------------------------------------ CSS
@pytest.mark.parametrize("cls", [
    ".etp-badge", ".etp-badge--easy", ".etp-badge--medium", ".etp-badge--hard",
    ".etp-badge--info", ".etp-badge--reattempt", ".etp-tag",
    ".etp-option", ".etp-option__key", ".etp-option__text", ".etp-option__status",
    ".etp-option.is-correct", ".etp-option.is-missed", ".etp-option.is-wrong",
    ".etp-option.is-neutral", ".etp-option.is-selected",
    ".etp-banner", ".etp-banner--success", ".etp-banner--partial", ".etp-banner--danger",
    ".etp-banner__title", ".etp-banner__body",
    ".etp-explain", ".etp-pagehead", ".etp-stat", ".etp-stats",
    ".etp-stat__label", ".etp-stat__value", ".etp-stat__delta",
])
def test_component_css_in_global_css(cls):
    assert cls in ui_helpers._GLOBAL_CSS


def test_every_class_emitted_has_css():
    html = " ".join([
        ui.meta_row(["t"], "easy", True, "x"),
        ui.option_row_html("A", "x", "correct"),
        ui.feedback_banner_html("danger", "t", "b"),
        ui.explanation_html("e"), ui.page_head_html("t", "s"),
        ui.stat_tiles_html([("a", 1, "d", "up")]),
    ])
    for cls in set(re.findall(r'class="([^"]+)"', html)):
        for c in cls.split():
            if c in ("up", "down"):
                continue
            assert "." + c in ui_helpers._GLOBAL_CSS, c
