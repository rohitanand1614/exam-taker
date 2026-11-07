"""Characterization of app.process_daily_session.

Importing app.py runs Streamlit code (set_page_config, sidebar, ...), so the
function is NOT imported. Its unmodified source is extracted from app.py with
`ast` and exec'd in a clean namespace; nothing is copied into the tests.
"""
import ast
import datetime
import json
from pathlib import Path

import pytest

from utils import archive_manager, bookmark_manager, file_manager

pytestmark = pytest.mark.logic

APP = Path(__file__).resolve().parent.parent / "app.py"
NOW = datetime.datetime.now


@pytest.fixture(scope="module")
def process_daily_session():
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "process_daily_session")
    ns = {"datetime": datetime, "archive_manager": archive_manager,
          "bookmark_manager": bookmark_manager, "file_manager": file_manager}
    exec(compile(ast.Module([fn], []), str(APP), "exec"), ns)
    return ns["process_daily_session"]


def _q(i):
    return {"id": i, "question": "q", "options": ["A) a"], "correct_indices": [0]}


def _log(qid, *attempts):
    """attempts: (hours_ago, score)"""
    entries = [{"attempt_id": "x",
                "timestamp": (NOW() - datetime.timedelta(hours=h)).isoformat(),
                "selected_indices": [0], "score": s, "quality": 5 if s == 1.0 else 0}
               for h, s in attempts]
    p = file_manager.get_log_path(qid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"summary": {"srs": {}}, "attempts": entries}), encoding="utf-8")


def ids(res):
    return [q["id"] for q in res]


def test_no_history_kept_not_reattempt(workspace, process_daily_session):
    res = process_daily_session([_q("n1")])
    assert ids(res) == ["n1"] and res[0]["is_reattempt"] is False


def test_question_without_id_passthrough(workspace, process_daily_session):
    res = process_daily_session([{"question": "x"}])
    assert len(res) == 1 and "is_reattempt" not in res[0]


def test_correct_within_48h_skipped(workspace, process_daily_session):
    _log("c1", (47, 1.0))
    assert process_daily_session([_q("c1")]) == []


def test_correct_after_48h_kept(workspace, process_daily_session):
    _log("c2", (49, 1.0))
    assert ids(process_daily_session([_q("c2")])) == ["c2"]


def test_partial_score_not_counted_as_correct(workspace, process_daily_session):
    _log("p1", (1, 0.67))
    assert ids(process_daily_session([_q("p1")])) == ["p1"]


def test_bookmarked_kept_despite_recent_correct(workspace, process_daily_session):
    _log("b1", (1, 1.0))
    bookmark_manager.save_bookmark(_q("b1"), "Important (Red)")
    assert ids(process_daily_session([_q("b1")])) == ["b1"]


def test_archived_removed(workspace, process_daily_session):
    archive_manager.archive_question(_q("a1"))
    assert process_daily_session([_q("a1"), _q("a2")]) == [
        {**_q("a2"), "is_reattempt": False}]


def test_reattempt_flag_wrong_today(workspace, process_daily_session):
    # wrong attempt a minute ago (same calendar day unless run at 00:00)
    _log("r1", (0.01, 0.0))
    res = process_daily_session([_q("r1")])
    assert res[0]["is_reattempt"] is True


def test_reattempt_false_when_wrong_only_in_past(workspace, process_daily_session):
    _log("r2", (72, 0.0))
    assert process_daily_session([_q("r2")])[0]["is_reattempt"] is False


def test_four_correct_in_1h_blocks_bookmarked_for_24h(workspace, process_daily_session):
    # 4 correct within 1h, last one 2h ago, bookmarked (so rule A is off)
    _log("f1", (2.9, 1.0), (2.6, 1.0), (2.3, 1.0), (2.0, 1.0))
    bookmark_manager.save_bookmark(_q("f1"), "Hard (Purple)")
    assert process_daily_session([_q("f1")]) == []


def test_four_correct_in_1h_released_after_24h(workspace, process_daily_session):
    _log("f2", (30.9, 1.0), (30.6, 1.0), (30.3, 1.0), (30.0, 1.0))
    bookmark_manager.save_bookmark(_q("f2"), "Hard (Purple)")
    assert ids(process_daily_session([_q("f2")])) == ["f2"]


def test_four_correct_spread_over_more_than_1h_not_blocked(workspace, process_daily_session):
    _log("f3", (6, 1.0), (4, 1.0), (3, 1.0), (2, 1.0))
    bookmark_manager.save_bookmark(_q("f3"), "Hard (Purple)")
    assert ids(process_daily_session([_q("f3")])) == ["f3"]
