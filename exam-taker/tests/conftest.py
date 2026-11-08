"""Shared fixtures. Tests never touch real data: they run in a temp copy of
tests/fixtures/workspace (utils use relative paths, so chdir isolates them)."""
import datetime
import shutil
import sys
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parent.parent
FIXTURE_WS = Path(__file__).resolve().parent / "fixtures" / "workspace"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


def _patch_apptest_single_select_pills():
    """Streamlit 1.51 AppTest bug: a single-select st.pills keeps a scalar (or None) in session state, but
    ButtonGroup.indices iterates it as a list, so ANY rerun of a page with such a widget raises ValueError.
    Present the value as a list, as multi-select does. Test infrastructure only; behaviour of the app is untouched."""
    from streamlit.testing.v1.element_tree import ButtonGroup
    original = ButtonGroup.value.fget
    if getattr(original, "_etp_patched", False):
        return

    def value(self):
        v = original(self)
        return [] if v is None else (v if isinstance(v, list) else [v])

    value._etp_patched = True
    ButtonGroup.value = property(value)


_patch_apptest_single_select_pills()


def _fill_placeholders(root: Path):
    """Fixture logs hold placeholders so 'earlier attempt today' stays true."""
    now = datetime.datetime.now() - datetime.timedelta(seconds=5)
    repl = {
        "__NOW__": now.isoformat(),
        "__ATTEMPT_ID__": now.strftime("%Y%m%d%H%M%S"),
        "__TOMORROW__": (datetime.date.today() + datetime.timedelta(days=1)).isoformat(),
    }
    for f in root.rglob("*.log.json"):
        text = f.read_text(encoding="utf-8")
        for k, v in repl.items():
            text = text.replace(k, v)
        f.write_text(text, encoding="utf-8")


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    shutil.copytree(FIXTURE_WS, tmp_path, dirs_exist_ok=True)
    _fill_placeholders(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def app_path():
    return str(APP_DIR / "app.py")


def make_app(rel_path: str):
    """Build an AppTest for app.py or pages/<name>.py (absolute path)."""
    from streamlit.testing.v1 import AppTest
    return AppTest.from_file(str(APP_DIR / rel_path), default_timeout=60)


@pytest.fixture
def app():
    """Factory: app('app.py') / app('pages/Bookmarks.py') -> AppTest (not yet run)."""
    return make_app
