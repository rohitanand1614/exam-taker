"""pytest plugin (registered in pytest.ini): keep AppTest runs independent of each other.

Streamlit stores `PagesManager.uses_pages_directory` as a process-wide CLASS attribute. It is computed once,
on the first PagesManager created (True only when the main script's folder has a `pages/` subfolder), and
st.navigation() sets it to False for the rest of the process. Both make a LATER app.py run lose the page
list that st.page_link needs (KeyError: 'url_pathname').

Fix: reset the flag to None right before every PagesManager is created (one is created per AppTest run), and
restore it after each test. conftest.py is not touched.
"""
import pytest


@pytest.fixture(autouse=True)
def _fresh_streamlit_pages_state(monkeypatch):
    from streamlit.runtime import pages_manager

    manager = pages_manager.PagesManager
    original_init = manager.__init__

    def init_with_fresh_flag(self, *args, **kwargs):
        manager.uses_pages_directory = None      # recomputed from THIS run's main script
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(manager, "__init__", init_with_fresh_flag)
    monkeypatch.setattr(manager, "uses_pages_directory", None)   # also undone after the test
    yield
