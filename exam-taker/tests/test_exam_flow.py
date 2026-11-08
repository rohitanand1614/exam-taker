"""Behaviour contract of the exam page and its sibling practice pages.
Widget keys are the REAL ones from the code (see CLAUDE.md: never rename)."""
import json
import pytest

from utils import bookmark_manager

pytestmark = pytest.mark.flow


def log_of(ws, qid):
    p = ws / "logs" / "attempts" / f"{qid}.log.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def registry(ws, folder):
    return json.loads((ws / folder / "registry.json").read_text(encoding="utf-8"))


def sample_q(ws, i):
    return json.loads((ws / "questions/sample/sample.json").read_text(encoding="utf-8"))[i]


def button_keys(at):
    return [b.key for b in at.button]


# --------------------------------------------------------------------------
# Pages sharing the same exam widgets: app.py, Practice_Incorrect, Practice_Bookmarks
# --------------------------------------------------------------------------
@pytest.fixture(params=["app.py", "pages/Practice_Incorrect.py", "pages/Practice_Bookmarks.py"])
def exam(request, workspace, app):
    if request.param.endswith("Practice_Bookmarks.py"):
        bookmark_manager.save_bookmark(sample_q(workspace, 0), "Important (Red)")
    at = app(request.param).run()
    assert not at.exception
    assert at.session_state.questions[0]["id"] == "sample_q1"
    return at


def answer_q1_correctly(at):
    at.radio(key="radio_sample_q1").set_value("B").run()
    at.button(key="btn_sample_q1").click().run()
    assert not at.exception


def test_single_correct_writes_log(exam, workspace):
    answer_q1_correctly(exam)
    log = log_of(workspace, "sample_q1")
    assert log is not None
    assert log["attempts"][-1]["score"] == 1.0
    assert log["attempts"][-1]["selected_indices"] == [1]
    assert log["summary"]["correct_count"] == 1
    assert exam.session_state.submitted["sample_q1"] is True


def test_single_wrong_scores_zero(exam, workspace):
    exam.radio(key="radio_sample_q1").set_value("A").run()
    exam.button(key="btn_sample_q1").click().run()
    log = log_of(workspace, "sample_q1")
    assert log["attempts"][-1]["score"] == 0.0
    assert log["summary"]["wrong_count"] == 1


def test_simple_retry_removes_last_attempt(exam, workspace):
    answer_q1_correctly(exam)
    exam.button(key="retry_sample_q1").click().run()
    assert not exam.exception
    assert log_of(workspace, "sample_q1")["attempts"] == []
    assert "sample_q1" not in exam.session_state.submitted


def test_hard_retry_resets_history(exam, workspace):
    answer_q1_correctly(exam)
    exam.button(key="hard_retry_sample_q1").click().run()
    assert not exam.exception
    assert log_of(workspace, "sample_q1") is None
    assert "sample_q1" not in exam.session_state.submitted


def test_next_and_prev_change_index(exam):
    if "nav_next_simple" not in button_keys(exam):
        pytest.skip("only one question on this page")
    assert exam.session_state.current_q_index == 0
    exam.button(key="nav_next_simple").click().run()
    assert exam.session_state.current_q_index == 1
    exam.button(key="nav_prev_simple").click().run()
    assert exam.session_state.current_q_index == 0


def test_next_after_submit_uses_submitted_key(exam):
    if len(exam.session_state.questions) < 2:
        pytest.skip("only one question on this page")
    answer_q1_correctly(exam)
    exam.button(key="nav_next").click().run()
    assert exam.session_state.current_q_index == 1
    # NOTE: AppTest keeps Q1's result widgets in its tree after this rerun, so
    # we do not click further from this tree (harness limitation, not app bug).


def test_prev_after_submit_uses_submitted_key(exam):
    if len(exam.session_state.questions) < 2:
        pytest.skip("only one question on this page")
    exam.button(key="nav_next_simple").click().run()
    assert exam.session_state.current_q_index == 1
    # Q2 is multi-select on app pages: tick one box and submit
    exam.checkbox(key="chk_sample_q2_0").check().run()
    exam.button(key="btn_sample_q2").click().run()
    exam.button(key="nav_prev").click().run()
    assert exam.session_state.current_q_index == 0


def test_bookmark_writes_registry(exam, workspace):
    exam.button(key="bm_btn_sample_q1").click().run()
    reg = registry(workspace, "bookmarks")
    assert reg["sample_q1"]["color"] == "Important (Red)"
    assert reg["sample_q1"]["data"]["id"] == "sample_q1"


def test_bookmark_color_and_remove(exam, workspace):
    [g for g in exam.get("button_group") if g.key == "bm_sel_sample_q1"][0].set_value(["Hard (Purple)"])
    exam.button(key="bm_btn_sample_q1").click().run()
    assert registry(workspace, "bookmarks")["sample_q1"]["color"] == "Hard (Purple)"
    exam.button(key="bm_rm_sample_q1").click().run()
    assert "sample_q1" not in registry(workspace, "bookmarks")


def test_archive_writes_registry(exam, workspace):
    if "arch_btn_sample_q1" not in button_keys(exam):
        pytest.skip("no archive button on this page")
    exam.button(key="arch_btn_sample_q1").click().run()
    assert "sample_q1" in registry(workspace, "archives")


# --------------------------------------------------------------------------
# app.py only
# --------------------------------------------------------------------------
@pytest.fixture
def main(workspace, app):
    at = app("app.py").run()
    assert not at.exception
    return at


def test_app_sidebar_selects_sample(main):
    assert main.sidebar.selectbox[0].options == ["sample"]
    assert main.session_state.current_exam_folder == "sample"
    assert main.session_state.current_q_index == 0


def test_app_q3_is_marked_reattempt(main):
    qs = {q["id"]: q for q in main.session_state.questions}
    assert qs["sample_q3"]["is_reattempt"] is True
    assert qs["sample_q1"]["is_reattempt"] is False


def test_multiselect_full_credit(main, workspace):
    main.button(key="nav_next_simple").click().run()
    assert main.session_state.current_q_index == 1
    main.checkbox(key="chk_sample_q2_0").check()
    main.checkbox(key="chk_sample_q2_2").check()
    main.run()
    main.button(key="btn_sample_q2").click().run()
    assert not main.exception
    entry = log_of(workspace, "sample_q2")["attempts"][-1]
    assert entry["selected_indices"] == [0, 2]
    assert entry["score"] == 1.0


def test_multiselect_partial_credit(main, workspace):
    main.button(key="nav_next_simple").click().run()
    main.checkbox(key="chk_sample_q2_0").check().run()
    main.button(key="btn_sample_q2").click().run()
    entry = log_of(workspace, "sample_q2")["attempts"][-1]
    assert entry["score"] == 0.67 and entry["quality"] == 3


def test_latex_question_renders_and_submits(main, workspace):
    main.button(key="nav_next_simple").click().run()
    main.button(key="nav_next_simple").click().run()
    assert main.session_state.current_q_index == 2
    main.radio(key="radio_sample_q3").set_value("B").run()
    main.button(key="btn_sample_q3").click().run()
    assert not main.exception
    attempts = log_of(workspace, "sample_q3")["attempts"]
    assert len(attempts) == 2  # fixture's earlier wrong attempt + this one
    assert attempts[-1]["score"] == 1.0


def test_first_question_has_no_prev_button(main):
    keys = button_keys(main)
    assert "nav_prev_simple" not in keys and "nav_next_simple" in keys


def test_submit_button_gone_after_submit(main, workspace):
    answer_q1_correctly(main)
    assert "btn_sample_q1" not in button_keys(main)
    assert len(log_of(workspace, "sample_q1")["attempts"]) == 1


def test_archived_question_leaves_daily_session(workspace, app):
    from utils import archive_manager
    archive_manager.archive_question(sample_q(workspace, 0))
    at = app("app.py").run()
    assert [q["id"] for q in at.session_state.questions] == ["sample_q2", "sample_q3"]


# --------------------------------------------------------------------------
# Targeted_Drill
# --------------------------------------------------------------------------
@pytest.fixture
def drill(workspace, app):
    qs = json.loads((workspace / "questions/sample/sample.json").read_text(encoding="utf-8"))
    at = app("pages/Targeted_Drill.py")
    at.session_state["drill_questions"] = qs
    at.run()
    assert not at.exception
    return at


def test_drill_correct_writes_log_with_drill_flag(drill, workspace):
    drill.radio(key="drill_radio_sample_q1_0").set_value("B").run()
    drill.button(key="drill_btn_sample_q1_0").click().run()
    assert not drill.exception
    entry = log_of(workspace, "sample_q1")["attempts"][-1]
    assert entry["score"] == 1.0 and entry["drill_mode"] is True
    assert len(drill.session_state.drill_questions) == 3


def test_drill_wrong_requeues_question(drill, workspace):
    drill.radio(key="drill_radio_sample_q1_0").set_value("A").run()
    drill.button(key="drill_btn_sample_q1_0").click().run()
    assert len(drill.session_state.drill_questions) == 4
    assert drill.session_state.drill_questions[-1]["id"] == "sample_q1"


def test_drill_next_question_button(drill):
    nxt = [b for b in drill.sidebar.button if "Next question" in b.label][0]
    nxt.click().run()
    assert drill.session_state.drill_index == 1


def test_drill_bookmark(drill, workspace):
    drill.button(key="drill_bm_btn_sample_q1_0").click().run()
    assert "sample_q1" in registry(workspace, "bookmarks")


# --------------------------------------------------------------------------
# Regressive_Practice  (ephemeral: must NOT write attempt logs)
# --------------------------------------------------------------------------
@pytest.fixture
def regressive(workspace, app):
    at = app("pages/Regressive_Practice.py").run()
    [b for b in at.sidebar.button if "Start new session" in b.label][0].click().run()
    assert not at.exception
    # Make the random pick deterministic: single-select sample_q1
    at.session_state.regressive_current_q = sample_q(workspace, 0)
    at.run()
    return at


def _answer(at, letter):
    q = at.session_state.regressive_current_q
    attempts = at.session_state.regressive_stats[q["id"]]["attempts"]
    at.radio(key=f"opt_{q['id']}_{attempts}").set_value(letter).run()
    [b for b in at.button if b.label == "Submit answer"][0].click().run()
    assert not at.exception


def test_regressive_correct_increments_streak_without_logging(regressive, workspace):
    _answer(regressive, "B")
    assert regressive.session_state.regressive_stats["sample_q1"]["streak"] == 1
    assert regressive.session_state.regressive_result == "correct"
    assert log_of(workspace, "sample_q1") is None


def test_regressive_wrong_resets_streak(regressive):
    regressive.session_state.regressive_stats["sample_q1"]["streak"] = 1
    _answer(regressive, "A")
    assert regressive.session_state.regressive_stats["sample_q1"]["streak"] == 0
    assert regressive.session_state.regressive_result == "wrong"


def test_regressive_mastered_after_two_correct(regressive, workspace):
    regressive.session_state.regressive_stats["sample_q1"]["streak"] = 1
    _answer(regressive, "B")
    assert regressive.session_state.regressive_stats["sample_q1"]["streak"] == 2
    [b for b in regressive.button if "Next question" in b.label][0].click().run()
    assert regressive.session_state.regressive_mastered_count == 1
    assert "sample_q1" not in [x["id"] for x in regressive.session_state.regressive_queue]
