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
