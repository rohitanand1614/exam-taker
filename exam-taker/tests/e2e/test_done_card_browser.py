"""Batch 10b.3 in a real browser: the 'All done for today' card, and that 'Choose another exam' moves focus to the
sidebar exam select without changing anything. Skipped when Playwright or Chromium is missing."""
import datetime
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from tests.e2e.ports import free_port

pw_sync = pytest.importorskip("playwright.sync_api")

APP_DIR = Path(__file__).resolve().parents[2]
pytestmark = [pytest.mark.e2e]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """A workspace where every question was answered correctly just now (so the exam is 'done for today')."""
    work = tmp_path_factory.mktemp("etp_done")
    shutil.copytree(APP_DIR / "tests" / "fixtures" / "workspace", work, dirs_exist_ok=True)
    shutil.copytree(APP_DIR / ".streamlit", work / ".streamlit", dirs_exist_ok=True)
    (work / "bookmarks").mkdir(exist_ok=True)
    (work / "bookmarks" / "registry.json").write_text("{}", encoding="utf-8")     # bookmarked questions are never skipped
    shutil.rmtree(work / "logs" / "attempts", ignore_errors=True)
    (work / "logs" / "attempts").mkdir(parents=True)
    now = datetime.datetime.now().isoformat()
    for f in (work / "questions").rglob("*.json"):
        for q in json.loads(f.read_text(encoding="utf-8")):
            entry = {"attempt_id": "e2e", "timestamp": now, "selected_indices": q.get("correct_indices", [0]),
                     "score": 1.0, "quality": 5}
            (work / "logs" / "attempts" / f"{q['id']}.log.json").write_text(json.dumps({
                "summary": {"total_attempts": 1, "correct_count": 1, "wrong_count": 0, "avg_score": 1.0,
                            "last_attempted_at": now,
                            "srs": {"repetitions": 1, "interval_days": 1, "ef": 2.5, "next_due": "2030-01-01"}},
                "attempts": [entry]}), encoding="utf-8")
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(APP_DIR / "main.py"), "--server.headless", "true",
         "--server.port", str(port), "--browser.gatherUsageStats", "false"],
        cwd=work, stdout=open(work / "server.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT)
    url = f"http://localhost:{port}"
    for _ in range(150):
        try:
            urllib.request.urlopen(url + "/_stcore/health", timeout=2)
            break
        except Exception:
            time.sleep(0.4)
    else:
        proc.terminate()
        pytest.skip("streamlit did not start in time")
    try:
        yield url
    finally:
        proc.terminate()


@pytest.fixture(scope="module")
def browser():
    with pw_sync.sync_playwright() as pw:
        try:
            b = pw.chromium.launch()
        except Exception as e:
            pytest.skip(f"Chromium not available: {e}")
        yield b
        b.close()


@pytest.fixture
def page(browser, server):
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    pg = ctx.new_page()
    pg.console_log = []
    pg.on("console", lambda m: pg.console_log.append(f"{m.type}: {m.text}"))
    pg.goto(server + "/")
    pg.wait_for_selector(".st-key-all_done", timeout=60000)
    yield pg
    ctx.close()


def test_the_done_card_shows_title_count_and_button(page):
    card = page.locator(".st-key-all_done")
    assert "All done for today" in card.inner_text()
    assert "questions answered today in sample." in card.inner_text()
    assert card.get_by_role("button", name="Choose another exam").is_visible()
    assert page.locator('[data-testid="stSidebar"] [data-baseweb="select"]').count() >= 1


def test_choose_another_exam_focuses_the_sidebar_select_and_changes_nothing(page):
    select = '[data-testid="stSidebar"] [data-baseweb="select"]'
    before = page.locator(select).first.inner_text()
    page.get_by_role("button", name="Choose another exam").click()
    page.wait_for_function(
        """sel => { const a = document.activeElement; return !!(a && a.closest && a.closest(sel)); }""",
        arg=select, timeout=15000)                                       # condition: focus really is in the select
    assert page.locator(select).first.inner_text() == before             # same exam still selected
    assert page.locator(".st-key-all_done").is_visible()                 # same card, no state change
