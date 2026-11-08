"""Batch 10a: the bookmark control in the exam card shows coloured chips with filled dots (design: BookmarkChip).
Same colour directives as the Bookmarks page pills; the stored value is still the BOOKMARK_COLORS key."""
import json
from pathlib import Path
import re

import pytest

from tests.test_ui_practice import EMOJI
from utils import bookmark_manager, ui_components, ui_helpers

pytestmark = pytest.mark.ui

COLOURS = list(bookmark_manager.BOOKMARK_COLORS)                      # storage order
SHORT = ["Important", "Review later", "Interesting", "Hard", "Solved"]
DIRECTIVES = ["red", "orange", "blue", "violet", "green"]
EXPECTED = [f":{d}[●] {s}" for d, s in zip(DIRECTIVES, SHORT)]

# (page, selector key, save key, remove key, how to get the question id/suffix)
PAGES = {
    "exam": ("app.py", "bm_sel_sample_q1", "bm_btn_sample_q1", "bm_rm_sample_q1"),
    "incorrect": ("pages/Practice_Incorrect.py", "bm_sel_sample_q1", "bm_btn_sample_q1", "bm_rm_sample_q1"),
    "bookmarks": ("pages/Practice_Bookmarks.py", "bm_sel_sample_q1", "bm_btn_sample_q1", "bm_rm_sample_q1"),
    "drill": ("pages/Targeted_Drill.py", "drill_bm_sel_sample_q1_0", "drill_bm_btn_sample_q1_0",
              "drill_bm_rm_sample_q1_0"),
}


def questions(ws):
    return json.loads((ws / "questions/sample/sample.json").read_text(encoding="utf-8"))


def registry(ws):
    return json.loads((ws / "bookmarks" / "registry.json").read_text(encoding="utf-8"))


def open_page(app, ws, name, bookmarked=None):
    path = PAGES[name][0]
    if bookmarked or name == "bookmarks":
        bookmark_manager.save_bookmark(questions(ws)[0], bookmarked or COLOURS[0])
    at = app(path)
    if name == "drill":
        at.session_state["drill_questions"] = questions(ws)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def group(at, key):
    found = [g for g in at.get("button_group") if g.key == key]
    assert len(found) == 1, (key, [g.key for g in at.get("button_group")])
    return found[0]


def _walk(block, out):
    for child in getattr(block, "children", {}).values():
        out.append(child)
        _walk(child, out)


def popover_labels(at):
    blocks = []
    _walk(at.main, blocks)
    return [b.proto.popover.label for b in blocks if b.type == "popover"]


def caption_texts(at):
    return [c.value for c in at.caption]


@pytest.fixture(params=list(PAGES))
def name(request):
    return request.param


# ------------------------------------------------------------------ the control
def test_colour_picker_is_a_single_select_pills_group(name, workspace, app):
    at = open_page(app, workspace, name)
    g = group(at, PAGES[name][1])
    assert g.proto.click_mode == 0                                  # SINGLE
    assert not list(at.selectbox) or PAGES[name][1] not in [s.key for s in at.selectbox]


def test_five_options_in_bookmark_colours_order_with_dot_and_short_name(name, workspace, app):
    at = open_page(app, workspace, name)
    g = group(at, PAGES[name][1])
    assert [o.content for o in g.proto.options] == EXPECTED
    assert [o.content for o in g.proto.options] == [ui_components.bookmark_pill_label(c) for c in COLOURS]


def test_pill_labels_use_the_same_directives_as_the_bookmarks_page(workspace, app):
    src = (Path(__file__).parent.parent / "pages" / "Bookmarks.py").read_text(encoding="utf-8")
    page_map = dict(re.findall(r'"([A-Za-z ]+ \([A-Za-z]+\))": "([a-z]+)"', src))
    assert page_map == ui_components.BOOKMARK_DIRECTIVE


def test_labels_have_no_emoji(name, workspace, app):
    at = open_page(app, workspace, name, bookmarked=COLOURS[1])
    labels = [o.content for o in group(at, PAGES[name][1]).proto.options] + popover_labels(at) + caption_texts(at)
    assert not [s for s in labels if EMOJI.search(s)], labels


def test_default_is_the_first_option_when_not_bookmarked(name, workspace, app):
    at = open_page(app, workspace, name)
    assert group(at, PAGES[name][1]).value == [COLOURS[0]]


@pytest.mark.parametrize("colour", COLOURS)
def test_default_is_the_current_bookmark(name, colour, workspace, app):
    if name == "bookmarks":
        pytest.skip("Practice bookmarks seeds its own bookmark")
    at = open_page(app, workspace, name, bookmarked=colour)
    assert group(at, PAGES[name][1]).value == [colour]


# ------------------------------------------------------------------ saving / removing (stored value unchanged)
@pytest.mark.parametrize("colour", COLOURS)
def test_save_stores_the_chosen_colour_key(name, colour, workspace, app):
    at = open_page(app, workspace, name)
    _, sel, save, _ = PAGES[name][0], *PAGES[name][1:]
    group(at, sel).set_value([colour]).run()   # AppTest wants a list, even for single select
    at.button(key=save).click().run()
    assert not at.exception
    assert registry(workspace)["sample_q1"]["color"] == colour


def test_remove_is_unchanged(name, workspace, app):
    at = open_page(app, workspace, name, bookmarked=COLOURS[3])
    at.button(key=PAGES[name][3]).click().run()
    assert "sample_q1" not in registry(workspace)


# ------------------------------------------------------------------ popover label and status line
def test_popover_label_when_not_bookmarked(name, workspace, app):
    if name == "bookmarks":
        pytest.skip("Practice bookmarks only shows bookmarked questions")
    at = open_page(app, workspace, name)
    assert "Bookmark" in popover_labels(at)
    assert not [c for c in caption_texts(at) if "Bookmarked as" in c]


@pytest.mark.parametrize("i", range(5))
def test_popover_label_when_bookmarked_is_dot_and_short_name(name, i, workspace, app):
    if name == "bookmarks":
        pytest.skip("Practice bookmarks seeds its own bookmark")
    at = open_page(app, workspace, name, bookmarked=COLOURS[i])
    assert EXPECTED[i] in popover_labels(at), popover_labels(at)


def test_status_line_inside_the_popover(name, workspace, app):
    at = open_page(app, workspace, name, bookmarked=COLOURS[0])
    assert any(c == f"Bookmarked as {EXPECTED[0]}" for c in caption_texts(at)), caption_texts(at)


# ------------------------------------------------------------------ pill CSS
def css_rules(part):
    return [m.group(2) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", ui_helpers._GLOBAL_CSS)
            if part in m.group(1)]


def test_selected_pill_is_visibly_selected():
    body = " ".join(css_rules('stBaseButton-pillsActive'))
    assert "border-color" in body and "background-color" in body


@pytest.mark.parametrize("hook", ["st-key-bm_sel_", "st-key-drill_bm_sel_"])
@pytest.mark.parametrize("n,tok", [(1, "red"), (2, "orange"), (3, "blue"), (4, "purple"), (5, "green")])
def test_selected_bookmark_pill_edge_uses_its_own_bm_colour(hook, n, tok):
    """The pills sit in the order of BOOKMARK_COLORS, so the n-th active pill takes the n-th bm_* token."""
    rules = [(m.group(1), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", ui_helpers._GLOBAL_CSS)
             if hook in m.group(1) and "pillsActive" in m.group(1) and f"nth-child({n})" in m.group(1)]
    assert rules, (hook, n)
    assert any(f"border-color: var(--etp-bm-{tok})" in body for _, body in rules), rules
