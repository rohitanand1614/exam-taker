"""Batch 9.3 end-to-end: answer two questions with the KEYBOARD ONLY in a real browser and check the log file.

Starts `streamlit run main.py` on a temporary copy of the fixture workspace (never real data, no LLM/network)
and drives Chromium with Playwright. Skipped when Playwright or its Chromium is not installed.
"""
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
FIXTURE_WS = APP_DIR / "tests" / "fixtures" / "workspace"
pytestmark = [pytest.mark.e2e]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    work = tmp_path_factory.mktemp("etp_e2e")
    shutil.copytree(FIXTURE_WS, work, dirs_exist_ok=True)
    shutil.copytree(APP_DIR / ".streamlit", work / ".streamlit", dirs_exist_ok=True)
    for old in (work / "logs" / "attempts").glob("*.json"):       # start with no attempts at all
        old.unlink()
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(APP_DIR / "main.py"), "--server.headless", "true",
         "--server.port", str(port), "--browser.gatherUsageStats", "false"],
        cwd=work, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://localhost:{port}"
    try:
        end = time.time() + 60
        while time.time() < end:
            try:
                urllib.request.urlopen(url + "/_stcore/health", timeout=2)
                break
            except Exception:
                time.sleep(0.4)
        else:
            pytest.skip("streamlit did not start in time")
        yield url, work
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="module")
def browser():
    with pw_sync.sync_playwright() as pw:
        try:
            b = pw.chromium.launch()
        except Exception as e:                          # browser binary not installed
            pytest.skip(f"Chromium not available: {e}")
        yield b
        b.close()


@pytest.fixture
def page(browser, server):
    url, work = server
    for old in (work / "logs" / "attempts").glob("*.json"):       # every test starts with a fresh daily session
        old.unlink()
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    pg = ctx.new_page()
    pg.goto(url + "/")
    pg.wait_for_selector(".st-key-answers", timeout=60000)
    pg.wait_for_function("() => typeof window.__etpShortcuts === 'function'", timeout=20000)
    yield pg
    ctx.close()


QUESTIONS = {}
for f in (FIXTURE_WS / "questions").rglob("*.json"):
    for q in json.loads(f.read_text(encoding="utf-8")):
        QUESTIONS[q["id"]] = q


def current_question(page):
    text = page.locator(".st-key-qstem").inner_text()
    for q in QUESTIONS.values():
        if q["question"][:20] in text:
            return q
    raise AssertionError(f"unknown question on screen: {text[:80]!r}")


def attempts(work, qid):
    path = work / "logs" / "attempts" / f"{qid}.log.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("attempts", [])


def wait_attempts(work, qid, n, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        got = attempts(work, qid)
        if len(got) >= n:
            return got
        time.sleep(0.2)
    return attempts(work, qid)


IDLE_JS = ("() => !document.querySelector('[data-testid=\"stStatusWidget\"]')"
           " && !document.querySelector('[data-stale=\"true\"]')")


def wait_idle(page, timeout=90000):
    """Streamlit has finished its rerun (no 'Running...' widget, no stale element). A condition, not a sleep:
    the cap is generous because a loaded machine can take many seconds per rerun."""
    page.wait_for_function(IDLE_JS, timeout=timeout)


def wait_selected(page, n, timeout=60000):
    """Exactly the clicked options are marked (a radio or checkbox input is :checked)."""
    page.wait_for_function("n => document.querySelectorAll('.st-key-answers input:checked').length >= n",
                           arg=n, timeout=timeout)


def wait_results(page):
    page.wait_for_selector('[class*="st-key-opt_"]', timeout=60000)       # option rows drawn with results
    wait_idle(page)


def wait_question_changes(page, old_text):
    page.wait_for_function(
        "old => document.querySelector('.st-key-qstem') && document.querySelector('.st-key-qstem').innerText !== old",
        arg=old_text, timeout=60000)


def test_answer_two_questions_with_the_keyboard_only(page, server):
    _, work = server
    done = []
    for step in range(2):
        q = current_question(page)
        stem = page.locator(".st-key-qstem").inner_text()
        for n, idx in enumerate(q["correct_indices"], start=1):
            # first question by letter, second by digit: both key families are exercised
            page.keyboard.press(chr(ord("a") + idx) if step == 0 else str(idx + 1))
            wait_selected(page, n)
        page.keyboard.press("Enter")
        wait_results(page)
        got = wait_attempts(work, q["id"], 1)
        assert len(got) == 1, f"no attempt logged for {q['id']}"
        assert got[0]["score"] == 1.0, got[0]
        assert got[0]["selected_indices"] == sorted(q["correct_indices"])
        done.append(q["id"])
        if step == 0:
            page.keyboard.press("ArrowRight")           # next (the 'n' key is covered in the next test)
            wait_question_changes(page, stem)
    assert len(set(done)) == 2


def test_n_and_p_move_between_questions(page):
    first = page.locator(".st-key-qstem").inner_text()
    page.keyboard.press("n")
    wait_question_changes(page, first)
    second = page.locator(".st-key-qstem").inner_text()
    assert second != first
    page.keyboard.press("p")
    wait_question_changes(page, second)
    assert page.locator(".st-key-qstem").inner_text() == first


def test_shift_b_opens_the_bookmark_popover(page):
    page.keyboard.press("Shift+B")
    page.wait_for_selector('[data-testid="stPopoverBody"]', timeout=10000)
    assert page.locator('[data-testid="stPopoverBody"]').is_visible()


def test_keys_are_ignored_while_typing_in_a_text_area(page, server):
    _, work = server
    q = current_question(page)
    for n, idx in enumerate(q["correct_indices"], start=1):
        page.keyboard.press(str(idx + 1))
        wait_selected(page, n)
    page.keyboard.press("Enter")
    wait_results(page)
    stem = page.locator(".st-key-qstem").inner_text()
    page.get_by_text("My notes & diagram").first.click()
    area = page.locator("textarea").first
    area.click()
    seen = page.evaluate("() => (window.__etpLog || []).length")          # what the script has handled so far
    page.keyboard.type("n p 1 a")                       # would be next / previous / option / option
    page.wait_for_function("v => document.querySelector('textarea').value === v", arg="n p 1 a", timeout=30000)
    wait_idle(page)
    # the script logs every key it ACCEPTS: typing in a text area must add nothing, and nothing may have moved
    assert page.evaluate("() => (window.__etpLog || []).length") == seen
    assert page.locator(".st-key-qstem").inner_text() == stem
    assert "n p 1 a" in area.input_value()


def test_regressive_practice_answers_and_advances_with_the_keyboard(browser, server):
    url, work = server
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    try:
        page.goto(url + "/regressive-practice")
        page.get_by_role("button", name="Start new session").click()        # starting is a mouse action
        page.wait_for_selector(".st-key-answers", timeout=60000)
        page.wait_for_function("() => typeof window.__etpShortcuts === 'function'", timeout=20000)
        stem = page.locator(".st-key-qstem").inner_text()
        q = next(x for x in QUESTIONS.values() if x["question"][:20] in stem)
        for n, idx in enumerate(q["correct_indices"], start=1):
            page.keyboard.press(str(idx + 1))
            wait_selected(page, n)
        page.keyboard.press("Enter")
        page.wait_for_selector('[class*="st-key-reg_next"]', timeout=60000)   # submitted: the Next button is there
        wait_idle(page)
        page.keyboard.press("n")
        page.wait_for_function(
            "() => !document.querySelector('[class*=\"st-key-reg_next\"]')", timeout=60000)
    finally:
        ctx.close()
