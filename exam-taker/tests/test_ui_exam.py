"""Batch 3: UI contract of the redesigned exam page (app.py).

Widget keys and behaviour are locked by tests/test_exam_flow.py (Batch 0).
Here we lock the *look*: no emoji, markdown instead of iframes, badges,
keyed containers, banner, option rows, notes expander.
"""
import re
import shutil

import pytest

from tests.conftest import FIXTURE_WS  # noqa: F401  (ensures conftest import path)
from utils import ui_helpers

pytestmark = pytest.mark.ui

EXTRAS = FIXTURE_WS.parent / "extras"
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿←-⇿️]")


# ------------------------------------------------------------------ helpers
def walk(node):
    yield node
    for child in getattr(node, "children", {}).values():
        yield from walk(child)


def block_key(block):
    """AppTest 1.51 does not expose container keys; they are the tail of proto.id
    ("$$ID-<hash>-<key>")."""
    ident = getattr(getattr(block, "proto", None), "id", "") or ""
    return ident.split("-", 2)[2] if ident.startswith("$$ID-") else None


def keyed_blocks(at):
    return {block_key(b): b for b in walk(at.main) if block_key(b)}


def expanders(at):
    """st.expander with an icon is parsed by AppTest as a 'Status' node."""
    return list(at.get("expander")) + list(at.get("status"))


def md_values(at):
    """Page markdown, without the injected <style> blocks (they define every class)."""
    return [m.value for m in at.get("markdown") if not m.value.lstrip().startswith("<style>")]


def all_md(at):
    return "\n".join(md_values(at))


def visible_strings(at):
    out = []
    for kind in ("button", "markdown", "title", "caption", "subheader", "header",
                 "expander", "radio", "checkbox", "selectbox", "info", "success",
                 "warning", "error", "text_area", "multiselect"):
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


@pytest.fixture
def main(workspace, app):
    at = app("app.py").run()
    assert not at.exception
    return at


@pytest.fixture
def code_main(workspace, app):
    shutil.copytree(EXTRAS, workspace, dirs_exist_ok=True)
    at = app("app.py").run()
    assert not at.exception
    at.session_state.current_q_index = 3
    at.run()
    assert not at.exception
    assert at.session_state.questions[3]["id"] == "sample_code_q1"
    return at


def submit_q1(at, letter):
    at.radio(key="radio_sample_q1").set_value(letter).run()
    at.button(key="btn_sample_q1").click().run()
    assert not at.exception


@pytest.fixture
def q2_done(main):
    """Q2 (multi-select, index 1) answered fully right, via session index (no stale tree)."""
    main.session_state.current_q_index = 1
    main.run()
    main.checkbox(key="chk_sample_q2_0").check()
    main.checkbox(key="chk_sample_q2_2").check()
    main.run()
    main.button(key="btn_sample_q2").click().run()
    assert not main.exception
    return main


# ----------------------------------------------------------------- no emoji
def test_no_emoji_before_submit(main):
    assert_no_emoji(main)
    assert_no_emoji_in_sidebar_title(main)


def assert_no_emoji_in_sidebar_title(at):
    assert [t.value for t in at.sidebar.title] == ["Exam Taker Pro"]


def test_no_emoji_after_submit(main):
    submit_q1(main, "A")
    assert_no_emoji(main)


def test_no_emoji_multiselect_and_empty_states(q2_done):
    assert_no_emoji(q2_done)


def test_no_emoji_on_code_question(code_main):
    assert_no_emoji(code_main)


# ------------------------------------------------------------ radio / letters
def test_radio_values_are_letters_but_labels_show_text(main):
    r = main.radio(key="radio_sample_q1")
    assert len(r.options) == 4
    assert "Paris" in r.options[1]
    assert not any(o.lstrip("* ").startswith(("A)", "B)", "C)", "D)")) for o in r.options)
    assert all(not re.match(r"^\W*[A-D]\)", o) for o in r.options)
    r.set_value("B").run()
    assert main.radio(key="radio_sample_q1").value == "B"


def test_multiselect_unsubmitted_hint(main):
    main.session_state.current_q_index = 1
    main.run()
    texts = [c.value for c in main.get("caption")]
    assert any("Select all that apply" in t for t in texts)
    assert "Assertion" not in all_md(main)
    assert main.checkbox(key="chk_sample_q2_0").label.startswith("**A**")
    assert "2" in main.checkbox(key="chk_sample_q2_0").label


# --------------------------------------------------- markdown, not iframes
def test_stem_options_explanation_are_markdown_not_iframes(main):
    assert any("capital of France" in v for v in md_values(main))
    assert "capital of France" not in iframe_html(main)
    submit_q1(main, "B")
    assert any("Paris is the capital of France" in v for v in md_values(main))
    html = iframe_html(main)
    for text in ("capital of France", "Paris is the capital", "Berlin", "Madrid"):
        assert text not in html


# -------------------------------------------------------------------- badges
def test_difficulty_and_new_due_badges(main):
    md = all_md(main)
    assert "etp-badge--easy" in md
    assert 'etp-badge--info">New<' in md
    assert "etp-badge--reattempt" not in md


def test_reattempt_and_due_badges_for_q3(main):
    main.session_state.current_q_index = 2
    main.run()
    md = all_md(main)
    assert "etp-badge--hard" in md
    assert "etp-badge--reattempt" in md and "Reattempt" in md
    assert re.search(r'etp-badge--info">Due \d{4}-\d{2}-\d{2}<', md)


# ------------------------------------------------------------- keyed regions
def test_card_and_submit_containers(main):
    blocks = keyed_blocks(main)
    assert "qcard" in blocks
    assert "nav_submit" in blocks
    assert any(b.key == "btn_sample_q1" for b in blocks["nav_submit"].button)


def test_submit_is_primary_and_has_icon(main):
    btn = main.button(key="btn_sample_q1")
    assert btn.label == "Submit answer"
    assert btn.proto.type == "primary"
    assert btn.proto.icon == ":material/check:"


def test_unsubmitted_next_is_not_primary(main):
    btn = main.button(key="nav_next_simple")
    assert btn.proto.type != "primary"


# --------------------------------------------------------------- after submit
@pytest.mark.parametrize("letter,kind", [("B", "success"), ("A", "danger")])
def test_banner_after_submit(main, letter, kind):
    submit_q1(main, letter)
    assert f"etp-banner--{kind}" in all_md(main)


def test_partial_banner_for_multiselect(main):
    main.session_state.current_q_index = 1
    main.run()
    main.checkbox(key="chk_sample_q2_0").check().run()
    main.button(key="btn_sample_q2").click().run()
    md = all_md(main)
    assert "etp-banner--partial" in md and "Partly correct" in md and "0.67" in md


def test_banner_mentions_next_review(main):
    submit_q1(main, "B")
    assert "Next review" in all_md(main)


def test_no_analysis_header_and_no_radio_after_submit(main):
    submit_q1(main, "B")
    assert "Analysis" not in all_md(main)
    assert not [h for h in list(main.get("subheader")) + list(main.get("header"))
                if "Analysis" in h.value]
    assert "radio_sample_q1" not in [r.key for r in main.radio]


def test_option_rows_states_correct_answer_picked(main):
    submit_q1(main, "B")
    keys = set(keyed_blocks(main))
    assert "opt_correct_sample_q1_1" in keys
    assert {"opt_neutral_sample_q1_0", "opt_neutral_sample_q1_2",
            "opt_neutral_sample_q1_3"} <= keys
    assert not [k for k in keys if k.startswith(("opt_wrong_", "opt_missed_"))]


def test_option_rows_states_wrong_pick(main):
    submit_q1(main, "A")
    keys = set(keyed_blocks(main))
    assert "opt_wrong_sample_q1_0" in keys
    assert "opt_missed_sample_q1_1" in keys
    md = all_md(main)
    for word in ("Your pick", "Missed"):
        assert word in md


def test_option_row_status_word_for_correct(main):
    submit_q1(main, "B")
    assert "Correct" in all_md(main)


def test_multiselect_rows(q2_done):
    keys = set(keyed_blocks(q2_done))
    assert {"opt_correct_sample_q2_0", "opt_correct_sample_q2_2",
            "opt_neutral_sample_q2_1", "opt_neutral_sample_q2_3"} <= keys


def test_explanation_container(main):
    submit_q1(main, "B")
    blocks = keyed_blocks(main)
    assert "explain_sample_q1" in blocks
    inner = " ".join(m.value for m in blocks["explain_sample_q1"].markdown)
    assert "Paris is the capital of France" in inner
    assert "Explanation" in inner


def test_nav_buttons_in_keyed_containers(q2_done):
    """retry / hard retry live in keyed containers. nav_prev / nav_next cannot: Streamlit
    forbids a container reusing a widget key, so the buttons' own keys are the CSS hooks
    (.st-key-nav_prev / .st-key-nav_next)."""
    blocks = keyed_blocks(q2_done)
    assert "retry_sample_q2" in [b.key for b in blocks["nav_retry"].button]
    assert "hard_retry_sample_q2" in [b.key for b in blocks["nav_hard"].button]
    keys = [b.key for b in q2_done.button]
    assert "nav_prev" in keys and "nav_next" in keys


def test_next_after_submit_is_primary(q2_done):
    assert q2_done.button(key="nav_next").proto.type == "primary"


def test_nav_button_icons(q2_done):
    assert q2_done.button(key="retry_sample_q2").proto.icon == ":material/replay:"
    assert q2_done.button(key="hard_retry_sample_q2").proto.icon == ":material/restart_alt:"


def test_notes_expander(main):
    submit_q1(main, "B")
    found = [e for e in expanders(main) if e.label == "My notes & diagram"]
    assert found, [e.label for e in expanders(main)]
    exp = found[0]
    assert exp.proto.icon == ":material/edit_note:"
    assert "diagram_sample_q1" in [t.key for t in exp.text_area]
    assert "save_notes_sample_q1" in [b.key for b in exp.button]


def test_no_nested_expander_error(main):
    submit_q1(main, "B")
    assert not main.exception


# -------------------------------------------------------- code-like question
def test_code_stem_markdown_is_escaped(code_main):
    stem = [v for v in md_values(code_main) if "AgentState" in v]
    assert stem, "stem must be rendered through st.markdown"
    assert "\\_\\_init\\_\\_" in stem[0]
    assert "list\\[AnyMessage\\]" in stem[0]
    assert "    messages" not in stem[0]  # indentation survives as nbsp, not plain spaces


def test_code_question_submits(code_main, workspace):
    code_main.radio(key="radio_sample_code_q1").set_value("B").run()
    code_main.button(key="btn_sample_code_q1").click().run()
    assert not code_main.exception
    assert "etp-banner--success" in all_md(code_main)


# ------------------------------------------------------------------- sidebar
def test_sidebar_radios_horizontal(main):
    assert all(r.proto.horizontal for r in main.sidebar.radio)


def test_sidebar_progress_bar_uses_tokens(main):
    sidebar_md = "\n".join(m.value for m in main.sidebar.markdown)
    for key in ("success", "warning", "danger"):
        assert ui_helpers.TOKENS[key] in sidebar_md
    assert "#2d8f4a" not in sidebar_md and "#b84040" not in sidebar_md


# ----------------------------------------------------------------- empty states
def test_no_questions_message(workspace, app):
    (workspace / "questions" / "sample" / "sample.json").unlink()
    at = app("app.py").run()
    assert not at.exception
    assert_no_emoji(at)


def test_all_done_message_no_emoji(workspace, app):
    from utils import archive_manager
    import json
    for q in json.loads((workspace / "questions/sample/sample.json").read_text(encoding="utf-8")):
        archive_manager.archive_question(q)
    at = app("app.py").run()
    assert not at.exception
    assert any("All done for today" in m.value for m in at.markdown)      # the done card (Batch 10b.3)
    assert_no_emoji(at)
