"""Batch 8.0: AppTest runs must not leak Streamlit page state into each other.

Streamlit keeps `PagesManager.uses_pages_directory` as a PROCESS-WIDE class attribute. It is set once,
on the first PagesManager created, from "does the main script's folder contain pages/", and
st.navigation() sets it to False for good. So a pages/*.py AppTest first, or a main.py (navigation)
test, made a later app.py run raise KeyError 'url_pathname' in st.page_link.
tests/plugins/isolation.py resets it before every PagesManager is created.
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_pages_script_first_then_app_in_one_test(app, workspace):
    page = app("pages/Archived_Questions.py").run()
    assert not page.exception
    main = app("app.py").run()
    assert not main.exception, [e.value for e in main.exception]
    assert main.radio(key="radio_sample_q1") is not None


def test_app_survives_a_stale_false_flag(app, workspace):
    from streamlit.runtime.pages_manager import PagesManager
    PagesManager.uses_pages_directory = False          # what a pages/ script or st.navigation leaves behind
    at = app("app.py").run()
    assert not at.exception, [e.value for e in at.exception]


def test_navigation_does_not_poison_the_next_app_run(app, workspace):
    from streamlit.runtime.pages_manager import PagesManager
    PagesManager.uses_pages_directory = False          # st.navigation() does exactly this
    first = app("app.py").run()
    second = app("pages/Bookmarks.py").run()
    third = app("app.py").run()
    assert not (first.exception or second.exception or third.exception)


def test_isolation_plugin_is_registered_in_pytest_ini():
    ini = (ROOT / "pytest.ini").read_text(encoding="utf-8")
    assert "-p tests.plugins.isolation" in ini
    assert (ROOT / "tests" / "plugins" / "isolation.py").exists()


def test_flag_is_reset_between_tests_part_1():
    from streamlit.runtime.pages_manager import PagesManager
    PagesManager.uses_pages_directory = False          # leak it on purpose


def test_flag_is_reset_between_tests_part_2():
    from streamlit.runtime.pages_manager import PagesManager
    assert PagesManager.uses_pages_directory is None   # the previous test's leak did not survive
