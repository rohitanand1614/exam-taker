"""Every page (and app.py) loads in a temp workspace without exception.
Where a page needs a selection / session to show content, a second pass
selects "sample" (or seeds the session) and re-runs."""
import json
import pytest

from utils import bookmark_manager

pytestmark = pytest.mark.smoke

PAGES = [
    "app.py",
    "pages/Archived_Questions.py",
    "pages/Bookmarks.py",
    "pages/Notes_Review.py",
    "pages/Practice_Bookmarks.py",
    "pages/Practice_Incorrect.py",
    "pages/Progress_Dashboard.py",
    "pages/Regressive_Practice.py",
    "pages/Search_Questions.py",
    "pages/Similar_Questions_Management.py",
    "pages/Targeted_Drill.py",
    "pages/Topic_Analysis.py",
    "pages/Wrong_Answers.py",
]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """No LLM / embedding / HTTP call may leave the machine."""
    from utils import llm_client
    import requests

    def boom(*a, **k):
        raise ConnectionError("network disabled in tests")

    monkeypatch.setattr(llm_client.LLMClient, "generate_response",
                        lambda self, *a, **k: "stub response")
    monkeypatch.setattr(llm_client.LLMClient, "get_embedding",
                        lambda self, *a, **k: [0.0, 0.0, 0.0])
    monkeypatch.setattr(requests, "post", boom)
    monkeypatch.setattr(requests, "get", boom)


def _assert_clean(at, name):
    assert not at.exception, f"{name}: {[e.value for e in at.exception]}"


def _select_sample(at):
    """Select 'sample' in every selectbox (sidebar or main) that offers it."""
    changed = False
    for sb in list(at.sidebar.selectbox) + list(at.selectbox):
        if "sample" in sb.options:
            sb.select("sample")
            changed = True
        elif "sample/sample.json" in sb.options or r"sample\sample.json" in sb.options:
            sb.select(sb.options[0])
            changed = True
    return changed


@pytest.mark.parametrize("page", PAGES)
def test_page_loads(workspace, app, page):
    at = app(page).run()
    _assert_clean(at, page)


@pytest.mark.parametrize("page", PAGES)
def test_page_loads_with_sample_selected(workspace, app, page):
    at = app(page).run()
    if _select_sample(at):
        at.run()
    _assert_clean(at, page + " (sample selected)")


def test_app_shows_first_question(workspace, app):
    at = app("app.py").run()
    assert at.session_state.current_exam_folder == "sample"
    assert [q["id"] for q in at.session_state.questions] == [
        "sample_q1", "sample_q2", "sample_q3"]
    assert at.radio(key="radio_sample_q1") is not None


def test_practice_incorrect_shows_questions(workspace, app):
    at = app("pages/Practice_Incorrect.py").run()
    assert not at.exception
    assert at.session_state.practice_incorrect_folder == "sample"
    assert len(at.session_state.questions) == 3  # no history -> wrong>=correct


def test_practice_bookmarks_with_bookmark(workspace, app):
    import json as _j
    q = _j.loads((workspace / "questions/sample/sample.json").read_text(encoding="utf-8"))[0]
    bookmark_manager.save_bookmark(q, "Important (Red)")
    at = app("pages/Practice_Bookmarks.py").run()
    assert not at.exception
    assert [x["id"] for x in at.session_state.questions] == ["sample_q1"]
    assert at.radio(key="radio_sample_q1") is not None


def test_regressive_start_session(workspace, app):
    at = app("pages/Regressive_Practice.py").run()
    start = [b for b in at.sidebar.button if "Start new session" in b.label][0]
    start.click().run()
    assert not at.exception
    assert at.session_state.regressive_active is True
    assert len(at.session_state.regressive_queue) == 3


def test_targeted_drill_with_seeded_session(workspace, app):
    qs = json.loads((workspace / "questions/sample/sample.json").read_text(encoding="utf-8"))
    at = app("pages/Targeted_Drill.py")
    at.session_state["drill_questions"] = qs
    at.run()
    assert not at.exception
    assert at.radio(key="drill_radio_sample_q1_0") is not None
