"""Batch 5.3: restyled list / review pages.

Behaviour is locked by tests/test_review_flow.py; here we lock the LOOK:
page head with count line, no emoji, filters in the main area, list rows,
icon actions with unchanged keys, review card with option rows + explanation.
"""
import re

import pytest

from tests.test_review_flow import (  # noqa: F401  (fixtures reused, not copied)
    seeded, other_folder, seven_bookmarks, no_network, RED, PURPLE)
from utils import ui_helpers

pytestmark = pytest.mark.ui

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
    for kind in ("button", "markdown", "title", "caption", "subheader", "header", "expander",
                 "status", "radio", "checkbox", "selectbox", "multiselect", "info", "success",
                 "warning", "error", "metric", "text_input", "text_area", "download_button"):
        for el in at.get(kind):
            for attr in ("label", "value", "body", "placeholder"):
                v = getattr(el, attr, None) if kind != "download_button" else getattr(el.proto, attr, None)
                if isinstance(v, str):
                    out.append(v)
            opts = getattr(el, "options", None)
            if isinstance(opts, (list, tuple)):
                out.extend(o for o in opts if isinstance(o, str))
    return out


def assert_no_emoji(at):
    bad = [s for s in visible_strings(at) if EMOJI.search(s)]
    assert not bad, bad


def head(at, title):
    md = all_md(at)
    assert 'class="etp-pagehead"' in md
    assert f"<h1>{title}</h1>" in md
    return md


def row_count(at):
    return all_md(at).count('class="etp-li"')


def main_widgets(at, kind):
    return list(at.main.get(kind))


def sidebar_has_no_filters(at):
    assert not list(at.sidebar.multiselect) and not list(at.sidebar.selectbox)
    assert not list(at.sidebar.metric) and not list(at.sidebar.radio)


def by_label(elements, text):
    return [e for e in elements if text.lower() in (getattr(e, "label", "") or "").lower()]


# =================================================================== Bookmarks
@pytest.fixture
def bookmarks(seeded, app):
    at = app("pages/Bookmarks.py").run()
    assert not at.exception
    return at


def test_bookmarks_head_and_count_line(bookmarks):
    md = head(bookmarks, "Bookmarks")
    assert "3 saved · showing 2" in md


def test_bookmarks_no_emoji(bookmarks):
    assert_no_emoji(bookmarks)


def test_bookmarks_filters_in_main_area_not_sidebar(bookmarks):
    sidebar_has_no_filters(bookmarks)
    assert len(main_widgets(bookmarks, "button_group")) == 1            # colour pills
    assert by_label(main_widgets(bookmarks, "multiselect"), "source")   # source multiselect


def test_bookmarks_colour_pills_default_to_all_colours(bookmarks):
    pills = main_widgets(bookmarks, "button_group")[0]
    assert set(pills.value) == {RED, PURPLE}


def test_bookmarks_rows_with_colour_dots(bookmarks):
    assert row_count(bookmarks) == 2
    md = all_md(bookmarks)
    assert ui_helpers.TOKENS["bm_red"] in md and ui_helpers.TOKENS["bm_purple"] in md
    assert "etp-li__q" in md and "etp-li__meta" in md


def test_bookmarks_actions_keep_keys_and_use_icons(bookmarks):
    rem, arch = bookmarks.button(key="rem_sample_q1"), bookmarks.button(key="arch_sample_q1")
    assert rem.proto.icon == ":material/delete:" and rem.proto.type == "tertiary"
    assert arch.proto.icon == ":material/archive:" and arch.proto.type == "tertiary"


def test_bookmarks_review_card_has_option_rows_and_explanation(bookmarks):
    keys = set(keyed_blocks(bookmarks))
    assert any(k.startswith("opt_correct_") and "sample_q1" in k for k in keys)
    assert any(k.startswith("opt_neutral_") and "sample_q1" in k for k in keys)
    assert any(k.startswith("explain_") and "sample_q1" in k for k in keys)


def test_bookmarks_paging_buttons_styled(seven_bookmarks, app):
    at = app("pages/Bookmarks.py").run()
    prev, nxt = by_label(at.button, "Prev")[0], by_label(at.button, "Next")[0]
    assert prev.proto.icon == ":material/chevron_left:" and prev.disabled
    assert nxt.proto.icon == ":material/chevron_right:" and not nxt.disabled
    assert "Page 1 of 2" in all_md(at) or any("Page 1 of 2" in c.value for c in at.get("caption"))
    assert_no_emoji(at)


def test_bookmarks_empty_state_no_emoji(workspace, app):
    at = app("pages/Bookmarks.py").run()
    assert_no_emoji(at)
    head(at, "Bookmarks")


# =========================================================== Archived_Questions
@pytest.fixture
def archived(seeded, app):
    at = app("pages/Archived_Questions.py").run()
    assert not at.exception
    return at


def test_archived_head_count_no_emoji(archived):
    assert "1 archived · showing 1" in head(archived, "Archived questions")
    assert_no_emoji(archived)


def test_archived_filters_in_main(archived):
    sidebar_has_no_filters(archived)
    assert by_label(main_widgets(archived, "multiselect"), "source")


def test_archived_row_and_restore_button(archived):
    assert row_count(archived) == 1
    btn = archived.button(key="unarch_sample_q3")
    assert btn.proto.icon == ":material/unarchive:"
    assert btn.proto.type == "secondary"
    assert "Restore" in btn.label


def test_archived_review_card(archived):
    keys = set(keyed_blocks(archived))
    assert any(k.startswith("opt_correct_") and "sample_q3" in k for k in keys)
    assert any(k.startswith("explain_") and "sample_q3" in k for k in keys)


def test_archived_empty_state_no_emoji(workspace, app):
    at = app("pages/Archived_Questions.py").run()
    assert_no_emoji(at)
    head(at, "Archived questions")


# ================================================================ Wrong_Answers
@pytest.fixture
def wrong(seeded, app):
    at = app("pages/Wrong_Answers.py").run()
    assert not at.exception
    return at


def test_wrong_head_no_emoji(wrong):
    head(wrong, "Review mistakes")
    assert_no_emoji(wrong)


def test_wrong_filters_in_main(wrong):
    sidebar_has_no_filters(wrong)
    assert by_label(main_widgets(wrong, "selectbox"), "Choose a Subject")
    assert by_label(main_widgets(wrong, "radio"), "Filter Criteria")


def test_wrong_row_shows_times_and_last_date(wrong):
    assert row_count(wrong) == 1
    assert re.search(r"wrong 1 time · last on \d{1,2} [A-Z][a-z]{2}", all_md(wrong))


def test_wrong_review_card_shows_pick_and_right_answer(wrong):
    keys = set(keyed_blocks(wrong))
    assert any(k.startswith("opt_wrong_") and "sample_q3" in k for k in keys)    # your pick (A)
    assert any(k.startswith("opt_missed_") and "sample_q3" in k for k in keys)   # right answer (B)
    assert any(k.startswith("explain_") and "sample_q3" in k for k in keys)
    md = all_md(wrong)
    assert "Your pick" in md and "Missed" in md


def test_wrong_ever_incorrect_pluralises(seeded, app):
    at = app("pages/Wrong_Answers.py").run()
    by_label(at.radio, "Filter Criteria")[0].set_value("Ever Incorrect").run()
    assert row_count(at) == 2
    assert_no_emoji(at)


def test_wrong_empty_state_no_emoji(workspace, app):
    from utils import file_manager
    file_manager.reset_question_log("sample_q3")
    at = app("pages/Wrong_Answers.py").run()
    assert_no_emoji(at)
    assert any("No mistakes" in s.value for s in at.success)


# =============================================================== Search_Questions
@pytest.fixture
def search(workspace, app):
    at = app("pages/Search_Questions.py").run()
    assert not at.exception
    return at


def test_search_head_and_no_emoji(search):
    head(search, "Search questions")
    assert_no_emoji(search)


def test_search_box_first_then_filters_row(search):
    order = [getattr(w, "key", None) for w in walk(search.main)
             if getattr(w, "key", None) in ("keyword_search", "folder_search", "file_search")]
    assert order == ["keyword_search", "folder_search", "file_search"]


def test_search_buttons_icons(search):
    s = by_label(search.button, "Search")[0]
    r = by_label(search.button, "Reset")[0]
    assert s.proto.icon == ":material/search:" and s.proto.type == "primary"
    assert r.proto.icon.startswith(":material/")


def test_search_results_are_list_rows_with_view_answer(search):
    search.text_input(key="keyword_search").set_value("France").run()
    by_label(search.button, "Search")[0].click().run()
    assert not search.exception
    assert row_count(search) == 1
    assert_no_emoji(search)
    labels = [e.label for e in list(search.get("expander")) + list(search.get("status"))]
    assert "View answer" in labels
    keys = set(keyed_blocks(search))
    assert any(k.startswith("opt_correct_") for k in keys)
    assert any(k.startswith("explain_") for k in keys)


def test_search_no_results_no_emoji(search):
    search.text_input(key="keyword_search").set_value("zzzz-nothing").run()
    by_label(search.button, "Search")[0].click().run()
    assert_no_emoji(search)


# ================================================================== Notes_Review
@pytest.fixture
def notes(seeded, app):
    at = app("pages/Notes_Review.py").run()
    assert not at.exception
    return at


def test_notes_head_count_no_emoji(notes):
    md = head(notes, "Notes review")
    assert "2 with notes" in md
    assert_no_emoji(notes)


def test_notes_exam_select_in_main(notes):
    sidebar_has_no_filters(notes)
    assert by_label(main_widgets(notes, "selectbox"), "Select Exam")


def test_notes_reorganize_button_style(notes):
    btn = by_label(notes.button, "Reorganize")[0]
    assert btn.proto.icon == ":material/auto_awesome:" and btn.proto.type == "secondary"
    assert btn.label == "Reorganize contextually"


def test_notes_export_buttons_near_head_with_icons(notes):
    buttons = list(notes.get("download_button"))
    assert [b.proto.label for b in buttons] == ["Download Markdown", "Download PDF"]
    assert all(b.proto.icon.startswith(":material/") for b in buttons)
    # export is no longer inside an expander
    assert "Export Notes" not in [e.label for e in notes.get("expander")]


def test_notes_reading_panels(notes):
    keys = set(keyed_blocks(notes))
    assert any(k.startswith("notepanel_") and "sample_q1" in k for k in keys)
    assert any(k.startswith("notepanel_") and "sample_q2" in k for k in keys)
    assert "note one" in all_md(notes) and "note two" in all_md(notes)


def test_notes_after_reorganize_no_emoji(notes):
    by_label(notes.button, "Reorganize")[0].click().run()
    assert not notes.exception
    assert_no_emoji(notes)
    assert any("organized by topic flow" in s.value for s in notes.success)


def test_notes_empty_state_no_emoji(workspace, app):
    at = app("pages/Notes_Review.py").run()
    assert_no_emoji(at)
    head(at, "Notes review")


# ======================================================== cleanup (Batch 4 pages)
def test_regressive_has_question_overline(workspace, app):
    import json
    at = app("pages/Regressive_Practice.py").run()
    at.button(key="reg_start").click().run()
    q1 = json.loads((workspace / "questions/sample/sample.json").read_text(encoding="utf-8"))[0]
    at.session_state.regressive_current_q = q1
    at.run()
    assert 'class="etp-qnum">Question 1<' in all_md(at)
    at.radio(key="opt_sample_q1_0").set_value("B").run()
    at.button(key="reg_submit_sample_q1_0").click().run()
    assert 'class="etp-qnum">Question 1<' in all_md(at)      # same question until Next
    assert not at.exception
    at.button(key="reg_next").click().run()
    assert 'class="etp-qnum">Question 2<' in all_md(at)


@pytest.mark.parametrize("page,names", [
    ("pages/Practice_Incorrect.py", ["st_quill", "st_mermaid"]),
    ("pages/Practice_Bookmarks.py", ["st_quill", "st_mermaid"]),
    ("pages/Targeted_Drill.py", ["archive_manager"]),
])
def test_unused_imports_removed(page, names):
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / page).read_text(encoding="utf-8")
    for n in names:
        assert len(re.findall(rf"\b{n}\b", src)) == 0, n
