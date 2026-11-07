import json
import pytest
from utils import file_manager as fm

pytestmark = pytest.mark.logic

SRS = {"repetitions": 1, "interval_days": 1, "ef": 2.6, "next_due": "2030-01-01"}


def _attempt(score, quality, ts="2030-01-01T10:00:00"):
    return {"attempt_id": "x", "timestamp": ts, "selected_indices": [1],
            "score": score, "quality": quality}


def test_get_folders_and_files(workspace):
    assert fm.get_exam_folders("questions") == ["sample"]
    assert fm.get_exam_files("questions") == [str(__import__("pathlib").Path("sample/sample.json"))]


def test_load_questions_folder_and_file(workspace):
    by_folder = fm.load_questions("questions", "sample")
    by_file = fm.load_questions("questions", "sample/sample.json")
    assert [q["id"] for q in by_folder] == ["sample_q1", "sample_q2", "sample_q3"]
    assert [q["id"] for q in by_file] == [q["id"] for q in by_folder]
    assert by_folder[0]["source_file"].replace("\\", "/") == "sample/sample.json"
    assert fm.load_questions("questions", "nope") == []


def test_load_log_missing_returns_default(workspace):
    log = fm.load_question_log("sample_q1")
    assert log["attempts"] == []
    assert log["summary"]["total_attempts"] == 0
    assert log["summary"]["srs"]["ef"] == 2.5


def test_save_attempt_log_and_summary(workspace):
    fm.save_attempt_log("sample_q1", _attempt(1.0, 5), SRS)
    fm.save_attempt_log("sample_q1", _attempt(0.0, 0, "2030-01-01T11:00:00"), SRS)
    path = workspace / "logs" / "attempts" / "sample_q1.log.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    s = data["summary"]
    assert (s["total_attempts"], s["correct_count"], s["wrong_count"]) == (2, 1, 1)
    assert s["avg_score"] == 0.5
    assert s["last_attempted_at"] == "2030-01-01T11:00:00"
    assert s["srs"] == SRS
    assert len(data["attempts"]) == 2


def test_load_question_log_existing_fixture(workspace):
    log = fm.load_question_log("sample_q3")
    assert log["summary"]["wrong_count"] == 1
    assert log["attempts"][0]["score"] == 0.0


def test_delete_last_attempt(workspace):
    fm.save_attempt_log("sample_q1", _attempt(1.0, 5), SRS)
    fm.save_attempt_log("sample_q1", _attempt(0.0, 0, "2030-01-01T11:00:00"), SRS)
    fm.delete_last_attempt("sample_q1")
    log = fm.load_question_log("sample_q1")
    assert len(log["attempts"]) == 1
    assert log["summary"]["total_attempts"] == 1
    assert log["summary"]["correct_count"] == 1
    assert log["summary"]["wrong_count"] == 0
    assert log["summary"]["avg_score"] == 1.0
    fm.delete_last_attempt("sample_q1")
    log = fm.load_question_log("sample_q1")
    assert log["attempts"] == []
    assert log["summary"]["last_attempted_at"] is None
    assert log["summary"]["avg_score"] == 0.0
    fm.delete_last_attempt("sample_q1")  # no attempts: no-op, no crash


def test_reset_question_log(workspace):
    fm.save_attempt_log("sample_q1", _attempt(1.0, 5), SRS)
    path = workspace / "logs" / "attempts" / "sample_q1.log.json"
    assert path.exists()
    fm.reset_question_log("sample_q1")
    assert not path.exists()
    fm.reset_question_log("sample_q1")  # idempotent


def test_update_user_notes(workspace):
    fm.update_user_notes("sample_q1", "<p>hi</p>", "graph TD; A-->B;")
    log = fm.load_question_log("sample_q1")
    assert log["user_notes"] == "<p>hi</p>"
    assert log["user_diagram"] == "graph TD; A-->B;"
    fm.update_user_notes("sample_q1", "new")  # diagram None -> untouched
    log = fm.load_question_log("sample_q1")
    assert log["user_notes"] == "new"
    assert log["user_diagram"] == "graph TD; A-->B;"


def test_safe_id_sanitised(workspace):
    assert fm.get_log_path("a/b..c").name == "abc.log.json"


def test_id_to_file_map(workspace):
    m = fm.get_question_id_to_file_map("questions")
    assert set(m) == {"sample_q1", "sample_q2", "sample_q3"}
