"""Batch 4.2: Practice_Incorrect and Practice_Bookmarks share the redesigned exam card.

Same UI contract as tests/test_ui_exam.py, driven through each page's own
selection widgets. Practice_Bookmarks has NO archive button (current behaviour).
"""
import json
import re

import pytest

from utils import bookmark_manager

pytestmark = pytest.mark.ui

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿←-⇿️]")

PAGES = {
    "incorrect": {"path": "pages/Practice_Incorrect.py", "mode": "inc_mode", "select": "inc_select",
                  "folder_state": "practice_incorrect_folder", "archive": True,
                  "head": "Practice incorrect", "sub": "3 questions you got wrong"},
    "bookmarks": {"path": "pages/Practice_Bookmarks.py", "mode": "bm_mode", "select": "bm_select",
                  "folder_state": "practice_bm_folder", "archive": False,
                  "head": "Practice bookmarks", "sub": "3 bookmarked questions"},
}


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
                 "status", "radio", "checkbox", "selectbox", "info", "success", "warning",
                 "error", "text_area", "multiselect"):
        for el in at.get(kind):
            for attr in ("label", "value", "body"):
                v = getattr(el, attr, None)
                if isinstance(v, str):
                    out.append(v)
            opts = getattr(el, "options", None)
            if isinstance(opts, (list, tuple)):
                out.extend(o for o in opts if isinstance(o, str))
    return out


def assert_no_emoji(at):
    bad = [s for s in visible_strings(at) if EMOJI.search(s)]
    assert not bad, bad


def iframe_html(at):
    return "\n".join(str(getattr(e.proto, "srcdoc", "")) for e in at.get("iframe"))


@pytest.fixture(params=list(PAGES))
def page(request, workspace, app):
    cfg = PAGES[request.param]
    if request.param == "bookmarks":
        qs = json.loads((workspace / "questions/sample/sample.json").read_text(encoding="utf-8"))
        for q in qs:
            bookmark_manager.save_bookmark(q, "Important (Red)")
    at = app(cfg["path"]).run()
    assert not at.exception
    assert [q["id"] for q in at.session_state.questions] == ["sample_q1", "sample_q2", "sample_q3"]
    at.cfg = cfg
    return at


def submit_q1(at, letter):
    at.radio(key="radio_sample_q1").set_value(letter).run()
    at.button(key="btn_sample_q1").click().run()
    assert not at.exception


def go_to(at, index):
    at.session_state.current_q_index = index
    at.run()
    assert not at.exception


# ------------------------------------------------------------------ the page
def test_page_head_shows_queue_size(page):
    md = all_md(page)
    assert 'class="etp-pagehead"' in md
    assert f"<h1>{page.cfg['head']}</h1>" in md
    assert page.cfg["sub"] in md


def test_no_emoji_before_and_after_submit(page):
    assert_no_emoji(page)
    submit_q1(page, "A")
    assert_no_emoji(page)


def test_no_emoji_multiselect(page):
    go_to(page, 1)
    assert_no_emoji(page)


def test_sidebar_title_has_no_emoji(page):
    titles = [t.value for t in page.sidebar.title]
    assert titles and not any(EMOJI.search(t) for t in titles)


def test_selection_widgets_unchanged(page):
    assert page.radio(key=page.cfg["mode"]) is not None
    assert page.selectbox(key=page.cfg["select"]).options == ["sample"]
    assert page.session_state[page.cfg["folder_state"]] == "sample"


# ------------------------------------------------------------- before submit
def test_badges(page):
    md = all_md(page)
    assert "etp-badge--easy" in md
    assert 'etp-badge--info">New<' in md


def test_radio_values_letters_labels_show_text(page):
    r = page.radio(key="radio_sample_q1")
    assert "Paris" in r.options[1]
    assert all(not re.match(r"^\W*[A-D]\)", o) for o in r.options)
    r.set_value("B").run()
    assert page.radio(key="radio_sample_q1").value == "B"


def test_stem_is_markdown_not_iframe(page):
    assert any("capital of France" in v for v in md_values(page))
    assert "capital of France" not in iframe_html(page)


def test_submit_in_keyed_container_primary(page):
    blocks = keyed_blocks(page)
    assert "qcard" in blocks and "nav_submit" in blocks
    btn = page.button(key="btn_sample_q1")
    assert btn.label == "Submit answer" and btn.proto.type == "primary"
    assert btn in list(blocks["nav_submit"].button)


def test_multiselect_hint_and_labels(page):
    go_to(page, 1)
    assert any("Select all that apply" in c.value for c in page.get("caption"))
    assert page.checkbox(key="chk_sample_q2_0").label.startswith("**A**")


def test_archive_button_presence(page):
    keys = [b.key for b in page.button]
    assert ("arch_btn_sample_q1" in keys) is page.cfg["archive"]


def test_bookmark_popover_widgets_reachable(page):
    keys = [b.key for b in page.button]
    assert "bm_btn_sample_q1" in keys
    assert [g for g in page.get("button_group") if g.key == "bm_sel_sample_q1"]


# -------------------------------------------------------------- after submit
@pytest.mark.parametrize("letter,kind", [("B", "success"), ("A", "danger")])
def test_banner(page, letter, kind):
    submit_q1(page, letter)
    assert f"etp-banner--{kind}" in all_md(page)


def test_option_rows_wrong_pick(page):
    submit_q1(page, "A")
    keys = set(keyed_blocks(page))
    assert "opt_wrong_sample_q1_0" in keys and "opt_missed_sample_q1_1" in keys
    assert {"opt_neutral_sample_q1_2", "opt_neutral_sample_q1_3"} <= keys
    md = all_md(page)
    assert "Your pick" in md and "Missed" in md


def test_option_rows_correct_pick(page):
    submit_q1(page, "B")
    assert "opt_correct_sample_q1_1" in set(keyed_blocks(page))


def test_no_analysis_header_no_radio_after_submit(page):
    submit_q1(page, "B")
    assert "Analysis" not in all_md(page)
    assert "radio_sample_q1" not in [r.key for r in page.radio]


def test_explanation_container_markdown(page):
    submit_q1(page, "B")
    blocks = keyed_blocks(page)
    assert "explain_sample_q1" in blocks
    inner = " ".join(m.value for m in blocks["explain_sample_q1"].markdown)
    assert "Paris is the capital of France" in inner
    assert "Paris is the capital" not in iframe_html(page)


def test_retry_containers(page):
    submit_q1(page, "B")
    blocks = keyed_blocks(page)
    assert "retry_sample_q1" in [b.key for b in blocks["nav_retry"].button]
    assert "hard_retry_sample_q1" in [b.key for b in blocks["nav_hard"].button]


def test_notes_expander(page):
    submit_q1(page, "B")
    found = [e for e in list(page.get("expander")) + list(page.get("status"))
             if e.label == "My notes & diagram"]
    assert found
    assert "diagram_sample_q1" in [t.key for t in found[0].text_area]
    assert "save_notes_sample_q1" in [b.key for b in found[0].button]


def test_banner_mentions_next_review(page):
    submit_q1(page, "B")
    assert "Next review" in all_md(page)


# --------------------------------------------------------------- empty states
def test_empty_state_no_emoji_and_message(workspace, app):
    at = app("pages/Practice_Bookmarks.py").run()  # no bookmarks in the workspace
    assert not at.exception
    assert at.session_state.questions == []
    assert_no_emoji(at)
    assert any("match" in i.value.lower() or "no " in i.value.lower() for i in at.info)
