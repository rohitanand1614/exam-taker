"""Batches 6.2 + 7 and carry-over polish: look of the insight pages.

Behaviour and chart data are locked by tests/test_insights_flow.py / test_ui_charts.py.
"""
import ast
import re
import tomllib
from pathlib import Path

import pytest

from tests.test_insights_flow import (  # noqa: F401  (fixtures/helpers reused, not copied)
    spread, no_network, groups, similar, contextual, select_suite, by_label, tab_counts)
from utils import ui_components, ui_helpers
from utils.ui_helpers import TOKENS

pytestmark = pytest.mark.ui

ROOT = Path(__file__).resolve().parent.parent
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿←-⇿️]")


# ------------------------------------------------------------------ helpers
def walk(node):
    yield node
    for child in getattr(node, "children", {}).values():
        yield from walk(child)


def block_key(block):
    ident = getattr(getattr(block, "proto", None), "id", "") or ""
    return ident.split("-", 2)[2] if ident.startswith("$$ID-") else None


def keyed_blocks(at):
    return {block_key(b): b for b in walk(at.main) if block_key(b)}


def md_values(at):
    return [m.value for m in at.get("markdown") if not m.value.lstrip().startswith("<style>")]


def all_md(at):
    return "\n".join(md_values(at))


def visible_strings(at):
    out = []
    for kind in ("button", "markdown", "title", "caption", "subheader", "header", "expander", "status",
                 "radio", "checkbox", "selectbox", "multiselect", "info", "success", "warning", "error",
                 "metric", "text_input", "text_area", "slider", "tab"):
        for el in at.get(kind):
            for attr in ("label", "value", "body", "placeholder"):
                v = getattr(el, attr, None)
                if isinstance(v, str):
                    out.append(v)
            opts = getattr(el, "options", None)
            if isinstance(opts, (list, tuple)):
                out.extend(o for o in opts if isinstance(o, str))
    out.extend(t.label for t in at.tabs)
    return out


def assert_no_emoji(at):
    bad = [s for s in visible_strings(at) if EMOJI.search(s)]
    assert not bad, bad


def head(at, title):
    md = all_md(at)
    assert 'class="etp-pagehead"' in md
    assert f"<h1>{title}</h1>" in md
    return md


# ============================================================ Progress_Dashboard
@pytest.fixture
def progress(spread, app):
    at = app("pages/Progress_Dashboard.py").run()
    assert not at.exception
    return at


def test_progress_head_and_subtitle(progress):
    md = head(progress, "Progress dashboard")
    assert "10 questions" in md


def test_progress_no_emoji_anywhere(progress):
    assert_no_emoji(progress)


def test_progress_stat_tiles_have_the_tab_counts(progress):
    tiles = {m.label: m.value for m in progress.metric}
    assert tiles == {"Mastered": "6", "Mixed": "1", "Struggling": "2", "Unattempted": "1"}
    assert tab_counts(progress) == {k: int(v) for k, v in tiles.items()}   # same numbers as 6.0


def test_progress_tab_labels_are_plain_text_with_counts(progress):
    assert [t.label for t in progress.tabs] == ["Mastered (6)", "Mixed (1)", "Struggling (2)", "Unattempted (1)"]


def test_progress_questions_are_list_rows(progress):
    tabs = list(progress.tabs)
    rows = [sum(m.value.count('class="etp-li"') for m in t.markdown) for t in tabs]
    assert rows == [6, 1, 2, 1]


def test_progress_each_question_has_a_review_card(progress):
    keys = set(keyed_blocks(progress))
    assert len([k for k in keys if k.startswith("explain_")]) == 10
    assert any(k.startswith("opt_correct_") for k in keys)


def test_progress_tab_colours_come_from_tokens(progress):
    styles = [m.value for m in progress.get("markdown") if m.value.lstrip().startswith("<style>")]
    page_css = [s for s in styles if "aria-selected" in s and ":root" not in s]
    assert page_css, "page keeps a small tab-colour style block"
    joined = "\n".join(page_css)
    for key in ("success", "warning", "danger"):
        assert TOKENS[key] in joined
    for old in ("#52c46e", "#c9a227", "#d96060"):
        assert old not in joined


def test_progress_empty_state_no_emoji(workspace, app):
    at = app("pages/Progress_Dashboard.py").run()
    assert not at.exception
    assert_no_emoji(at)
    head(at, "Progress dashboard")


# ================================================================ Topic_Analysis
@pytest.fixture
def topic(spread, app):
    at = app("pages/Topic_Analysis.py").run()
    return select_suite(at)


def test_topic_head_and_subtitle(topic):
    md = head(topic, "Topic analysis")
    assert "6 topics" in md and "sample" in md


def test_topic_no_emoji_anywhere(topic):
    assert_no_emoji(topic)


def test_topic_no_emoji_before_choosing_a_suite(spread, app):
    at = app("pages/Topic_Analysis.py").run()
    assert_no_emoji(at)


def test_topic_section_headings_plain(topic):
    assert [s.value for s in topic.subheader if s.value != "LLM Configuration"] == [
        "Weak areas", "Topic mastery", "Detailed breakdown", "Targeted drill"]


def test_topic_stat_tiles_keep_the_6_0_values(topic):
    assert {m.label: m.value for m in topic.metric} == {
        "Total Questions": "10", "Overall Accuracy": "60.0%", "Topics Identified": "6"}


def test_topic_drill_button_primary_with_icon_and_key(topic):
    btn = by_label(topic.button, "Start Targeted Drill")[0]
    assert btn.proto.type == "primary"
    assert btn.proto.icon.startswith(":material/")
    assert btn.key == "topic_drill_start"


def test_topic_drill_options_have_no_emoji_and_keep_their_words(topic):
    assert by_label(topic.checkbox, "Double-Loop")
    assert by_label(topic.checkbox, "Include Wrong Questions")


def test_topic_tag_mapping_stays_in_an_expander_without_emoji(topic):
    found = by_label(list(topic.get("expander")) + list(topic.get("status")), "Tag to Topic")
    assert found and not EMOJI.search(found[0].label)


def test_topic_dataframes_keep_columns(topic):
    frames = [f.value for f in topic.get("arrow_data_frame")]
    assert ["Topic", "Total", "Correct", "Wrong", "Unattempted", "Accuracy"] in [list(f.columns) for f in frames]
    assert ["Tag", "Mapped Topic"] in [list(f.columns) for f in frames]


def test_topic_refresh_button_icon(topic):
    btn = by_label(topic.button, "Refresh analysis")[0]
    assert btn.proto.icon.startswith(":material/")


# ====================================================== Similar_Questions_Management
def test_similar_head(similar):
    head(similar, "Similar questions")


def test_similar_no_emoji_exact_mode(similar):
    assert_no_emoji(similar)


def test_similar_no_emoji_clean_bank(workspace, app, monkeypatch):
    from utils import similarity
    monkeypatch.setattr(similarity, "find_duplicates", lambda suite=None: [])
    at = app("pages/Similar_Questions_Management.py").run()
    assert_no_emoji(at)
    assert any("No exact duplicates" in s.value for s in at.success)


def test_similar_sidebar_controls_present_and_themed(similar):
    assert by_label(similar.sidebar.selectbox, "Select Exam Suite")
    assert by_label(similar.sidebar.radio, "Method")
    assert all(not EMOJI.search(i.value) for i in similar.sidebar.info)


def test_similar_each_group_is_a_bordered_container(similar):
    blocks = keyed_blocks(similar)
    assert {"simgroup_0", "simgroup_1"} <= set(blocks)


def test_similar_questions_side_by_side_one_column_each(similar):
    """The first row of columns inside a group holds one column per question (option rows
    further down have their own small column rows, which are not counted)."""
    blocks = keyed_blocks(similar)

    def question_columns(group):
        for node in walk(group):
            kids = list(getattr(node, "children", {}).values())
            if len(kids) >= 2 and all(type(k).__name__ == "Column" for k in kids):
                return len(kids)
        return 0

    assert question_columns(blocks["simgroup_0"]) == 2
    assert question_columns(blocks["simgroup_1"]) == 3


def test_similar_checkbox_keys_unchanged_and_inside_their_group(similar):
    blocks = keyed_blocks(similar)
    in_g1 = {c.key for c in blocks["simgroup_1"].checkbox}
    assert in_g1 == {"select_1_0_sample_q2", "select_1_1_dup_q2", "select_1_2_dup_q2b"}


def test_similar_selected_count_line_per_group(similar):
    blocks = keyed_blocks(similar)
    text = lambda b: " ".join(c.value for c in b.caption)
    assert "0 selected" in text(blocks["simgroup_0"]) and "0 selected" in text(blocks["simgroup_1"])
    similar.checkbox(key="select_1_0_sample_q2").check()
    similar.checkbox(key="select_1_2_dup_q2b").check().run()
    blocks = keyed_blocks(similar)
    assert "0 selected" in text(blocks["simgroup_0"])
    assert "2 selected" in text(blocks["simgroup_1"])


def test_similar_archive_selected_is_not_a_filled_button(similar):
    btn = by_label(similar.button, "Archive Selected")[0]
    assert btn.proto.type != "primary"
    assert btn.proto.icon == ":material/archive:"
    assert btn.key == "archive_selected"


def test_archive_selected_css_is_a_danger_outline():
    bodies = [m.group(2) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", ui_helpers._GLOBAL_CSS)
              if ".st-key-archive_selected button" in m.group(1)]
    assert bodies and any("--etp-danger" in b and "transparent" in b for b in bodies)


def test_similar_instance_archive_buttons_keep_keys_and_get_icons(similar):
    btn = similar.button(key="archive_0_1_dup_q1")
    assert btn.proto.icon == ":material/archive:" and btn.proto.type == "tertiary"


def test_similar_option_rows_use_the_shared_style(similar):
    keys = set(keyed_blocks(similar))
    assert any(k.startswith("opt_correct_") for k in keys)
    assert any(k.startswith("opt_neutral_") for k in keys)


def test_similar_contextual_start_scan_is_primary_with_icon(contextual):
    btn = by_label(contextual.button, "Start Scan")[0]
    assert btn.proto.type == "primary" and btn.proto.icon.startswith(":material/")
    assert_no_emoji(contextual)


def test_similar_contextual_after_scan_no_emoji_and_stop_button_iconised(contextual):
    by_label(contextual.button, "Start Scan")[0].click().run()
    assert not contextual.exception
    assert_no_emoji(contextual)
    assert {"simgroup_0", "simgroup_1"} <= set(keyed_blocks(contextual))


# =================================================================== carry-over polish
def test_list_row_shows_math_as_plain_inner_text():
    html = ui_components.list_row_html("What is $x^2$ of $$a_1$$ ok?", "meta")
    assert "What is x^2 of a_1 ok?" in html
    assert "$" not in html


def test_list_row_math_strip_keeps_repaired_content():
    html = ui_components.list_row_html("see $\x0crac12$", "")
    assert "\\frac12" in html and "$" not in html


def test_list_row_text_without_math_is_untouched():
    assert "plain & simple" not in ui_components.list_row_html("plain & simple", "")  # still escaped
    assert "plain &amp; simple" in ui_components.list_row_html("plain & simple", "")


def test_pill_dot_colours_are_the_bookmark_tokens():
    """st.pills colours its dot with the theme's colour-directive palette."""
    cfg = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))["theme"]
    assert cfg["redColor"] == TOKENS["bm_red"]
    assert cfg["orangeColor"] == TOKENS["bm_orange"]
    assert cfg["blueColor"] == TOKENS["bm_blue"]
    assert cfg["violetColor"] == TOKENS["bm_purple"]
    assert cfg["greenColor"] == TOKENS["bm_green"]


def test_pill_dot_is_a_filled_circle_sized_up_in_css():
    """The Material 'fiber_manual_record' glyph is drawn as an OUTLINE ring in the default font fill,
    so the dot is a solid U+25CF character inside the colour directive instead."""
    bodies = [m.group(2) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", ui_helpers._GLOBAL_CSS)
              if '[data-testid="stButtonGroup"]' in m.group(1) and "stMarkdownColoredText" in m.group(1)]
    assert bodies and any("font-size" in b for b in bodies)
    src = (ROOT / "pages" / "Bookmarks.py").read_text(encoding="utf-8")
    assert "●" in src                       # the solid-circle character
    assert "fiber_manual_record" not in src


def _unused_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                imported[(a.asname or a.name).split(".")[0]] = a.name
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                imported[a.asname or a.name] = a.name
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    return sorted(set(imported) - used)


def test_app_py_has_no_unused_imports():
    assert _unused_imports(ROOT / "app.py") == []


# ============================================================ polish found in the screenshots
def test_tab_labels_have_room_between_them():
    bodies = [m.group(2) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", ui_helpers._GLOBAL_CSS)
              if '.stTabs [data-baseweb="tab-list"]' in m.group(1) and "tab-highlight" not in m.group(1)]
    gaps = [re.search(r"gap:\s*([\d.]+)rem", b) for b in bodies]
    assert any(g and float(g.group(1)) >= 1.25 for g in gaps)


def _weights(node):
    return [round(k.proto.weight, 2) for k in node.children.values()]


def _two_column_rows(block):
    """Blocks whose children are exactly two Column nodes, in document order."""
    out = []
    for n in walk(block):
        kids = list(getattr(n, "children", {}).values())
        if len(kids) == 2 and all(type(k).__name__ == "Column" for k in kids):
            out.append(n)
    return out


def test_option_status_column_is_wide_enough_in_narrow_similar_columns(similar):
    """In the side-by-side layout 'Correct' must not wrap: its column gets a larger share."""
    rows = [r for name, b in keyed_blocks(similar).items() if name.startswith("opt_correct_")
            for r in _two_column_rows(b)]
    assert rows
    assert all(_weights(r)[1] >= 0.25 for r in rows)


def test_option_status_column_default_share_unchanged_on_full_width_pages(workspace, app):
    # Practice_Incorrect shares the exam card (exam_view). app.py is deliberately not used in this file:
    # AppTest's in-process page cache is order-sensitive (a pages/ script run first, then app.py, makes
    # st.page_link raise KeyError 'url_pathname'), and this file otherwise only runs pages.
    at = app("pages/Practice_Incorrect.py").run()
    at.radio(key="radio_sample_q1").set_value("A").run()
    at.button(key="btn_sample_q1").click().run()
    rows = [r for name, b in keyed_blocks(at).items() if name.startswith("opt_") for r in _two_column_rows(b)]
    assert rows and all(_weights(r)[1] < 0.2 for r in rows)


def test_bookmark_popover_column_is_wider_than_archive(workspace, app):
    """'Bookmarked' is longer than 'Archive': give it the larger share so the label does not wrap."""
    at = app("pages/Practice_Incorrect.py").run()
    card = keyed_blocks(at)["qcard"]
    rows = _two_column_rows(card)
    head_tools = rows[1]            # rows[0] = (badges | tools), rows[1] = (bookmark | archive)
    w = _weights(head_tools)
    assert w[0] > w[1]


@pytest.mark.parametrize("state", ["idle", "started"])
def test_regressive_has_a_page_head(workspace, app, state):
    at = app("pages/Regressive_Practice.py").run()
    if state == "started":
        at.button(key="reg_start").click().run()
    assert 'class="etp-pagehead"' in all_md(at) and "<h1>Regressive practice</h1>" in all_md(at)
    assert_no_emoji(at)
