"""Batch 8.1: the grouped navigation entry (main.py) with st.navigation.

AppTest cannot prove everything a browser does, so the same 13 routes are also opened in a real server by
tests/visual/shoot.py. Here: every page runs through main.py, switch_page / page_link resolve, and the
pages' own st.set_page_config is accepted under navigation.
"""
import re
import shutil
from pathlib import Path

import pytest

from tests.test_insights_flow import spread, no_network, select_suite, by_label  # noqa: F401
from utils import navigation

pytestmark = pytest.mark.flow

# a string that only that page renders (so a wrong page / the default page would fail the test)
MARKER = {
    "app.py": "radio_sample_q1",
    "pages/Targeted_Drill.py": "No active drill session",
    "pages/Regressive_Practice.py": "<h1>Regressive practice</h1>",
    "pages/Practice_Incorrect.py": "<h1>Practice incorrect</h1>",
    "pages/Practice_Bookmarks.py": "<h1>Practice bookmarks</h1>",
    "pages/Wrong_Answers.py": "<h1>Review mistakes</h1>",
    "pages/Bookmarks.py": "<h1>Bookmarks</h1>",
    "pages/Notes_Review.py": "<h1>Notes review</h1>",
    "pages/Search_Questions.py": "<h1>Search questions</h1>",
    "pages/Progress_Dashboard.py": "<h1>Progress dashboard</h1>",
    "pages/Topic_Analysis.py": "<h1>Topic analysis</h1>",
    "pages/Similar_Questions_Management.py": "<h1>Similar questions</h1>",
    "pages/Archived_Questions.py": "<h1>Archived questions</h1>",
}
ALL_PAGES = [e["path"] for g in navigation.nav_spec().values() for e in g]


def page_text(at):
    parts = [m.value for m in at.get("markdown")] + [i.value for i in at.info]
    parts += [r.key or "" for r in at.radio]
    return "\n".join(parts)


@pytest.fixture
def nav(workspace, app):
    at = app("main.py").run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_marker_table_covers_every_page():
    assert sorted(MARKER) == sorted(ALL_PAGES) and len(ALL_PAGES) == 13


def test_default_page_is_the_exam(nav):
    assert "radio_sample_q1" in page_text(nav)
    assert nav.session_state.current_exam_folder == "sample"


@pytest.mark.parametrize("path", ALL_PAGES)
def test_every_page_runs_through_navigation(nav, path):
    nav.switch_page(path).run()
    assert not nav.exception, (path, [e.value for e in nav.exception])
    assert MARKER[path] in page_text(nav), path


def test_set_page_config_in_pages_is_accepted_under_navigation(nav):
    """main.py calls st.set_page_config, and so does every page: no exception on either."""
    for path in ALL_PAGES:
        src = (Path(__file__).resolve().parent.parent / path).read_text(encoding="utf-8")
        assert "set_page_config" in src, path
        nav.switch_page(path).run()
        assert not nav.exception, path


def test_view_detailed_stats_link_resolves_to_the_progress_page(nav):
    links = [e for e in nav.sidebar.get("page_link") if "detailed stats" in e.proto.label.lower()]
    assert links, "exam sidebar must offer the link"
    assert links[0].proto.page == navigation.entry_for("pages/Progress_Dashboard.py")["url_path"]
    assert links[0].proto.page_script_hash        # resolved to a registered page, not an external URL
    assert not links[0].proto.external


def test_app_py_fallback_still_resolves_the_same_link(workspace, app):
    """`streamlit run app.py` (no main.py): Streamlit's automatic pages/ sidebar is used."""
    at = app("app.py").run()
    assert not at.exception
    links = [e for e in at.sidebar.get("page_link") if "detailed stats" in e.proto.label.lower()]
    assert links and links[0].proto.page == "Progress_Dashboard" and not links[0].proto.external


def test_drill_start_from_topic_analysis_reaches_targeted_drill(spread, app):
    at = app("main.py").run()
    at.switch_page("pages/Topic_Analysis.py").run()
    select_suite(at)
    by_label(at.selectbox, "Select Topic to Drill")[0].select("Sample Set").run()
    by_label(at.button, "Start Targeted Drill")[0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    ids = sorted(q["id"] for q in at.session_state.drill_questions)
    assert ids == ["sample_q2", "sample_q2", "sample_q3", "sample_q3"]
    # the switch landed on the drill page: its own header + first question are on screen
    assert [h.value for h in at.sidebar.header] == ["Drill status"]
    assert "drill_radio_" in " ".join(r.key or "" for r in at.radio) or any(
        (c.key or "").startswith("drill_") for c in at.checkbox)


def test_exit_drill_switches_back_to_topic_analysis(workspace, app):
    """(A drill session is seeded: driving it through the Topic page first leaves that page's unkeyed
    widgets in AppTest's tree after the in-script switch_page, which is a harness quirk.)"""
    import json
    qs = json.loads((workspace / "questions/sample/sample.json").read_text(encoding="utf-8"))
    at = app("main.py").run()
    at.session_state["drill_questions"] = qs
    at.switch_page("pages/Targeted_Drill.py").run()
    assert [h.value for h in at.sidebar.header] == ["Drill status"]
    at.button(key="drill_exit").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert "<h1>Topic analysis</h1>" in page_text(at)
    assert "drill_questions" not in at.session_state


def test_drill_dashboard_button_switches_to_topic_analysis(workspace, app):
    at = app("main.py").run()
    at.switch_page("pages/Targeted_Drill.py").run()
    at.button(key="drill_dashboard").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert "<h1>Topic analysis</h1>" in page_text(at)


def test_main_entry_page_config_is_the_app_config():
    src = (Path(__file__).resolve().parent.parent / "main.py").read_text(encoding="utf-8")
    assert 'page_title="Exam Taker Pro"' in src
    assert 'page_icon=":material/menu_book:"' in src
    assert 'layout="wide"' in src
    assert "inject_global_css()" in src
    assert "st.navigation(" in src and ".run()" in src
    # Streamlit shows only 10 items and hides the rest behind "View 3 more"; the app has 13
    assert "expanded=True" in src
