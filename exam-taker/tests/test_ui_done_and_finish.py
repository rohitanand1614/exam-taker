"""Batch 10b.3 'All done for today' card and 10b.4 drill finish screen (AppTest).
No new logic: counts and tiles come from data the pages already keep / load."""
import datetime
import json
import re

import pytest

from tests.test_review_flow import SRS, attempt, sample_questions as logged_questions
from tests.test_ui_exam import assert_no_emoji
from tests.test_ui_insights import keyed_blocks, md_values, walk
from utils import file_manager

pytestmark = pytest.mark.ui


# ------------------------------------------------------------------ helpers
def block_markdown(block):
    """Markdown texts inside one block, in page order."""
    return [m.value for m in walk(block) if getattr(m, "type", "") == "markdown"]


def clear_attempts(ws):
    for f in (ws / "logs" / "attempts").glob("*.json"):       # the fixture has attempts 'now' for some questions
        f.unlink()


def all_done_app(app, ws, answered=3):
    """The first `answered` questions were answered correctly just now (the 48 h rule skips them) and the rest are
    archived (also skipped) -> 'done for today' with exactly `answered` questions answered today."""
    from utils import archive_manager
    clear_attempts(ws)
    now = datetime.datetime.now().isoformat()
    questions = logged_questions()
    for q in questions[:answered]:
        file_manager.save_attempt_log(q["id"], attempt(1.0, 5, now), SRS)
    for q in questions[answered:]:
        archive_manager.archive_question(q)
    at = app("app.py").run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def card(at):
    blocks = keyed_blocks(at)
    assert "all_done" in blocks, sorted(blocks)
    return blocks["all_done"]


def card_text(at):
    return "\n".join(block_markdown(card(at)))


# ------------------------------------------------------------------ 10b.3: the done card
def test_done_card_is_a_bordered_keyed_container_with_check_icon_and_title(workspace, app):
    at = all_done_app(app, workspace)
    text = card_text(at)
    assert ":material/check_circle:" in text
    assert "All done for today" in text
    assert card(at).proto.flex_container.border is True


def test_done_card_counts_the_questions_answered_today_in_this_exam(workspace, app):
    assert "3 questions answered today in sample." in card_text(all_done_app(app, workspace, answered=3))


def test_done_card_singular_wording(workspace, app):
    assert "1 question answered today in sample." in card_text(all_done_app(app, workspace, answered=1))


def test_done_card_when_nothing_was_answered_today_does_not_say_zero_answered(workspace, app):
    from utils import archive_manager
    clear_attempts(workspace)
    for q in logged_questions():
        archive_manager.archive_question(q)           # skipped, but nothing answered today
    at = app("app.py").run()
    text = card_text(at)
    assert "All done for today" in text
    assert "0 questions" not in text and "Nothing is due in sample today." in text


def test_choose_another_exam_is_a_secondary_button_inside_the_card(workspace, app):
    at = all_done_app(app, workspace)
    buttons = [b for b in walk(card(at)) if getattr(b, "type", "") == "button" and b.key == "all_done_choose"]
    assert len(buttons) == 1
    assert buttons[0].label == "Choose another exam"
    assert buttons[0].proto.type == "secondary"


def test_choose_another_exam_changes_no_state(workspace, app):
    at = all_done_app(app, workspace)
    keys = ("current_exam_folder", "questions", "current_q_index", "answers", "submitted", "all_completed_today", "mode")
    before = {k: json.dumps(at.session_state[k], default=str) for k in keys}
    at.button(key="all_done_choose").click().run()
    assert not at.exception
    assert {k: json.dumps(at.session_state[k], default=str) for k in keys} == before
    assert "all_done" in keyed_blocks(at)              # still the same card


def test_choose_another_exam_focuses_the_sidebar_select_only_after_the_click(workspace, app):
    at = all_done_app(app, workspace)

    def frames(a):
        return [f.proto.srcdoc for f in a.get("iframe") if "stSidebar" in (f.proto.srcdoc or "")]

    assert not frames(at)
    at.button(key="all_done_choose").click().run()
    (doc,) = frames(at)
    assert "focus" in doc and "scrollIntoView" in doc and "select" in doc


def test_old_success_and_info_messages_are_gone(workspace, app):
    at = all_done_app(app, workspace)
    assert not any("completed for today" in s.value for s in at.success)
    assert not any("Select another exam" in s.value for s in at.info)


def test_done_card_has_no_emoji(workspace, app):
    assert_no_emoji(all_done_app(app, workspace))


@pytest.mark.parametrize("path", ["pages/Practice_Incorrect.py", "pages/Practice_Bookmarks.py"])
def test_practice_pages_keep_their_own_empty_states(path, workspace, app):
    at = app(path).run()
    assert "all_done" not in keyed_blocks(at)


def test_done_card_css_hook_exists():
    from utils import ui_helpers
    assert ".st-key-all_done" in ui_helpers._GLOBAL_CSS


# ------------------------------------------------------------------ 10b.4: the drill finish screen
def drill_at(app, ws, n=1):
    at = app("pages/Targeted_Drill.py")
    at.session_state["drill_questions"] = json.loads(
        (ws / "questions/sample/sample.json").read_text(encoding="utf-8"))[:n]
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def tiles(at):
    """{label: value} of the stat tiles on the page."""
    out = {}
    for md in md_values(at):
        for label, value in re.findall(
                r'<div class="etp-stat__label">(.*?)</div><div class="etp-stat__value">(.*?)</div>', md):
            out[label] = value
    return out


def submit(at, letter, step="sample_q1_0"):
    at.radio(key=f"drill_radio_{step}").set_value(letter).run()
    at.button(key=f"drill_btn_{step}").click().run()
    assert not at.exception


def test_finish_keeps_the_drill_complete_message_as_the_head_line(workspace, app):
    at = drill_at(app, workspace)
    assert any("Drill complete" in s.value for s in at.success)
    blocks = keyed_blocks(at)
    assert "drill_done" in blocks
    texts = [e.value for e in walk(blocks["drill_done"]) if getattr(e, "type", "") in ("success", "markdown")]
    assert "Drill complete" in texts[0]                                # the head line comes first in the card


def test_finish_shows_answered_correct_and_accuracy_tiles(workspace, app):
    at = drill_at(app, workspace)
    submit(at, "B")                                                     # B is correct for sample_q1
    assert tiles(at) == {"Answered": "1", "Correct": "1", "Accuracy": "100%"}


def test_finish_tiles_after_a_wrong_answer_and_a_retry(workspace, app):
    at = drill_at(app, workspace)
    submit(at, "A")                                                     # wrong: the question is re-queued
    assert not tiles(at)                                                # not finished yet (2 questions in the queue)
    at.button(key="drill_next_sample_q1_0").click().run()
    assert tiles(at) == {"Answered": "1", "Correct": "0", "Accuracy": "0%"}
    submit(at, "B", step="sample_q1_1")
    assert tiles(at) == {"Answered": "2", "Correct": "1", "Accuracy": "50%"}


def test_finish_tiles_before_any_answer_show_a_dash_for_accuracy(workspace, app):
    assert tiles(drill_at(app, workspace)) == {"Answered": "0", "Correct": "0", "Accuracy": "—"}


def test_finish_back_button_is_primary_and_keeps_its_key_and_label(workspace, app):
    at = drill_at(app, workspace)
    (btn,) = [b for b in at.button if b.key == "drill_finish"]
    assert btn.label == "Back to topic analysis"
    assert btn.proto.type == "primary"


def test_no_tiles_while_the_drill_is_running(workspace, app):
    at = drill_at(app, workspace, n=3)
    assert not tiles(at) and "drill_done" not in keyed_blocks(at)


def test_finish_screen_has_no_emoji(workspace, app):
    at = drill_at(app, workspace)
    assert_no_emoji(at)
    submit(at, "B")
    assert_no_emoji(at)


def test_finish_card_css_hook_exists():
    from utils import ui_helpers
    assert ".st-key-drill_done" in ui_helpers._GLOBAL_CSS
