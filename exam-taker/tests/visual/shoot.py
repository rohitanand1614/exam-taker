"""Manual screenshot tool (NOT collected by pytest).

    python tests/visual/shoot.py [label]          # label defaults to "batch1"

Copies tests/fixtures/workspace and .streamlit/ to a temp dir (Streamlit reads
config.toml from the working directory), starts the app there, screenshots
"/" and every page in pages/, then stops the server (even on error).
Output: tests/.artifacts/screens/<label>/*.png
"""
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwright missing.\n  pip install playwright && python -m playwright install chromium")

APP_DIR = Path(__file__).resolve().parents[2]
PORT = 8765
BASE = f"http://localhost:{PORT}"
VIEWPORT = {"width": 1440, "height": 1000}


def wait_for_server(timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(BASE, timeout=2)
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("Streamlit did not start in time")


def settle(page, extra=2000):
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    page.wait_for_timeout(extra)


def shot(page, out_dir, name):
    """Streamlit scrolls inside <section stMain>, so full_page alone is cut off:
    grow the viewport to the content height first (capped), then restore it."""
    path = out_dir / f"{name}.png"
    try:
        h = page.evaluate(
            "() => { const m = document.querySelector('section[data-testid=\"stMain\"]');"
            " return m ? m.scrollHeight : document.body.scrollHeight; }")
    except Exception:
        h = VIEWPORT["height"]
    h = max(VIEWPORT["height"], min(int(h), 6000))
    page.set_viewport_size({"width": VIEWPORT["width"], "height": h})
    page.wait_for_timeout(500)
    page.screenshot(path=str(path), full_page=True)
    page.set_viewport_size(VIEWPORT)
    print("saved", path)


def exam_after_wrong_submit(page, out_dir):
    """app.py: 'sample' is auto-selected (only folder); answer Q1 wrong, submit."""
    page.goto(BASE + "/")
    settle(page)
    # Pick "sample" explicitly in the sidebar selectbox (no-op if already selected)
    sidebar = page.locator('section[data-testid="stSidebar"]')
    box = sidebar.locator('[data-baseweb="select"]').first
    if box.count():
        if "sample" not in box.inner_text():
            box.click()
            page.get_by_role("option", name="sample").click()
            settle(page, 1000)
    # Option A is wrong for Q1 (correct is B)
    page.locator('section[data-testid="stMain"] [role="radiogroup"] label').nth(0).click()
    page.wait_for_timeout(500)
    page.get_by_role("button", name="Submit answer").click()
    settle(page)
    shot(page, out_dir, "exam_after_submit")


def exam_code_question(page, out_dir):
    """Navigate to the code-like fixture question (4th), shoot it, answer wrong,
    open the notes expander (shows the Quill editor) and shoot again."""
    page.goto(BASE + "/")
    settle(page)
    for _ in range(3):
        page.get_by_role("button", name="Next").first.click()
        page.wait_for_timeout(900)
    settle(page, 1000)
    shot(page, out_dir, "exam_code_question")
    page.locator('section[data-testid="stMain"] [role="radiogroup"] label').nth(0).click()
    page.wait_for_timeout(400)
    page.get_by_role("button", name="Submit answer").click()
    settle(page)
    page.get_by_text("My notes & diagram").first.click()
    settle(page, 3500)
    shot(page, out_dir, "exam_code_notes_open")


MAIN_RADIO = 'section[data-testid="stMain"] [role="radiogroup"] label'
MAIN_CHECKBOX = 'section[data-testid="stMain"] [data-testid="stCheckbox"] label'


def pick_first_option(page):
    """Click the first answer (radio or checkbox) of whatever question is showing."""
    if page.locator(MAIN_RADIO).count():
        page.locator(MAIN_RADIO).nth(0).click()
    else:
        page.locator(MAIN_CHECKBOX).first.click()
    page.wait_for_timeout(500)


def practice_incorrect_after_wrong(page, out_dir):
    page.goto(BASE + "/Practice_Incorrect")
    settle(page)
    pick_first_option(page)  # A is wrong for Q1
    page.get_by_role("button", name="Submit answer").click()
    settle(page)
    shot(page, out_dir, "practice_incorrect_after_wrong")


def practice_bookmarks(page, out_dir):
    page.goto(BASE + "/Practice_Bookmarks")
    settle(page)
    shot(page, out_dir, "practice_bookmarks")
    pick_first_option(page)  # whichever bookmarked question comes first (radio or checkbox)
    page.get_by_role("button", name="Submit answer").click()
    settle(page)
    shot(page, out_dir, "practice_bookmarks_after_submit")


def regressive_flow(page, out_dir):
    page.goto(BASE + "/Regressive_Practice")
    settle(page)
    page.get_by_role("button", name="Start New Session").click()
    settle(page)
    shot(page, out_dir, "regressive_started")
    pick_first_option(page)
    page.get_by_role("button", name="Submit Answer").click()
    settle(page)
    shot(page, out_dir, "regressive_after_submit")


DRILL_ENTRY = """import json, sys
from pathlib import Path
sys.path.insert(0, r"{app}")
import streamlit as st
qs = json.loads(Path("questions/sample/sample.json").read_text(encoding="utf-8"))
n = int(st.query_params.get("n", "3"))
if "drill_questions" not in st.session_state:
    st.session_state.drill_questions = qs[:n]
exec(compile(open(r"{page}", encoding="utf-8").read(), r"{page}", "exec"))
"""


def drill_flow(page, base, out_dir):
    page.goto(base + "/")
    settle(page)
    shot(page, out_dir, "drill_question")
    pick_first_option(page)  # A is wrong for Q1 -> question gets re-queued
    page.get_by_role("button", name="Submit answer").click()
    settle(page)
    shot(page, out_dir, "drill_after_submit")
    page.goto(base + "/?n=1")  # single question = last question: finish screen
    settle(page)
    shot(page, out_dir, "drill_finish")


def bookmarks_flow(page, out_dir):
    page.goto(BASE + "/Bookmarks")
    settle(page)
    shot(page, out_dir, "bookmarks_all")
    # filter: switch one colour pill off, open the first review card
    page.locator('[data-testid="stButtonGroup"] button', has_text="Important").first.click()
    settle(page, 1200)
    page.get_by_text("Show answer").first.click()
    page.wait_for_timeout(800)
    shot(page, out_dir, "bookmarks_filtered_open")


def archived_flow(page, out_dir):
    page.goto(BASE + "/Archived_Questions")
    settle(page)
    page.get_by_text("Show answer").first.click()
    page.wait_for_timeout(800)
    shot(page, out_dir, "archived_open")


def wrong_flow(page, out_dir):
    page.goto(BASE + "/Wrong_Answers")
    settle(page)
    page.get_by_text("Review answer").first.click()
    page.wait_for_timeout(800)
    shot(page, out_dir, "wrong_answers_open")


def search_flow(page, out_dir):
    page.goto(BASE + "/Search_Questions")
    settle(page)
    page.get_by_placeholder("Search in question text").fill("France")
    page.keyboard.press("Enter")
    page.wait_for_timeout(500)
    page.get_by_role("button", name="Search").first.click()
    settle(page)
    page.get_by_text("View answer").first.click()
    page.wait_for_timeout(800)
    shot(page, out_dir, "search_with_query")


def notes_flow(page, out_dir):
    page.goto(BASE + "/Notes_Review")
    settle(page)
    page.get_by_role("button", name="Expand all").click()
    settle(page, 1200)
    shot(page, out_dir, "notes_review_expanded")


def start_server(script, port, cwd):
    return subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(script),
         "--server.headless", "true", "--server.port", str(port),
         "--browser.gatherUsageStats", "false"],
        cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def wait_url(url, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"{url} did not start in time")


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "batch1"
    out_dir = APP_DIR / "tests" / ".artifacts" / "screens" / label
    out_dir.mkdir(parents=True, exist_ok=True)

    work = Path(tempfile.mkdtemp(prefix="etp_shoot_"))
    shutil.copytree(APP_DIR / "tests" / "fixtures" / "workspace", work, dirs_exist_ok=True)
    shutil.copytree(APP_DIR / ".streamlit", work / ".streamlit", dirs_exist_ok=True)
    # extra fixture: code-like question (tests/fixtures/extras), only used by this script
    shutil.copytree(APP_DIR / "tests" / "fixtures" / "extras", work, dirs_exist_ok=True)
    # fixture log holds placeholders (see tests/conftest.py)
    sys.path.insert(0, str(APP_DIR / "tests"))
    import conftest
    conftest._fill_placeholders(work)

    # one bookmarked question (the LaTeX one) so Practice_Bookmarks has something to show
    import json
    sample_qs = json.loads((work / "questions/sample/sample.json").read_text(encoding="utf-8"))
    q2, q3 = sample_qs[1], sample_qs[2]
    (work / "bookmarks").mkdir(exist_ok=True)
    (work / "bookmarks" / "registry.json").write_text(json.dumps({
        q3["id"]: {"color": "Hard (Purple)", "data": q3, "timestamp": "2030-01-01T00:00:00"},
        q2["id"]: {"color": "Important (Red)", "data": q2, "timestamp": "2030-01-02T00:00:00"}}),
        encoding="utf-8")
    # one archived question that is NOT in questions/ (so the exam session is unchanged)
    archived_demo = dict(sample_qs[0], id="archived_demo_q9", question="Which planet is known as the Red Planet?",
                         options=["A) Venus", "B) Mars", "C) Jupiter", "D) Saturn"], correct_indices=[1],
                         explanation="Mars looks red because of iron oxide on its surface.", tags=["astronomy"])
    (work / "archives").mkdir(exist_ok=True)
    (work / "archives" / "registry.json").write_text(json.dumps({
        "archived_demo_q9": {"data": archived_demo, "timestamp": "2030-01-03T00:00:00"}}), encoding="utf-8")
    # notes on two questions (Notes_Review); default log summary keeps the exam page unchanged
    (work / "logs" / "attempts").mkdir(parents=True, exist_ok=True)
    empty_summary = {"total_attempts": 0, "correct_count": 0, "wrong_count": 0, "avg_score": 0.0,
                     "last_attempted_at": None, "srs": {"repetitions": 0, "interval_days": 0, "ef": 2.5, "next_due": None}}
    for qid, note in (("sample_q1", "<p>Paris is the <b>capital</b> and largest city of France.</p>"),
                      ("sample_q2", "<p>Primes: 2, 3, 5, 7. Remember that <i>1 is not prime</i>.</p>")):
        (work / "logs" / "attempts" / f"{qid}.log.json").write_text(json.dumps({
            "summary": empty_summary, "attempts": [], "user_notes": note, "user_diagram": ""}), encoding="utf-8")
    # Targeted_Drill needs a seeded session: tiny wrapper entry on a second server
    drill_port = PORT + 1
    (work / "drill_entry.py").write_text(
        DRILL_ENTRY.format(app=str(APP_DIR), page=str(APP_DIR / "pages" / "Targeted_Drill.py")),
        encoding="utf-8")

    pages = sorted(p.stem for p in (APP_DIR / "pages").glob("*.py"))
    server = start_server(APP_DIR / "app.py", PORT, work)
    drill_server = start_server(work / "drill_entry.py", drill_port, work)
    try:
        wait_for_server()
        wait_url(f"http://localhost:{drill_port}")
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
            page = ctx.new_page()

            page.goto(BASE + "/")
            settle(page)
            shot(page, out_dir, "home")

            for name in pages:
                try:
                    page.goto(f"{BASE}/{name}")
                    settle(page)
                    shot(page, out_dir, name)
                except Exception as e:  # keep going; report at the end
                    print(f"FAILED {name}: {e}")

            exam_after_wrong_submit(page, out_dir)
            exam_code_question(page, out_dir)
            for name, flow in (("practice_incorrect", practice_incorrect_after_wrong),
                               ("practice_bookmarks", practice_bookmarks),
                               ("regressive", regressive_flow),
                               ("bookmarks", bookmarks_flow),
                               ("archived", archived_flow),
                               ("wrong_answers", wrong_flow),
                               ("search", search_flow),
                               ("notes", notes_flow)):
                try:
                    flow(page, out_dir)
                except Exception as e:
                    print(f"FAILED {name}: {e}")
            try:
                drill_flow(page, f"http://localhost:{drill_port}", out_dir)
            except Exception as e:
                print(f"FAILED drill: {e}")
            browser.close()
    finally:
        for srv in (server, drill_server):
            srv.terminate()
            try:
                srv.wait(timeout=10)
            except subprocess.TimeoutExpired:
                srv.kill()
        shutil.rmtree(work, ignore_errors=True)
    print(f"\nScreenshots: {out_dir}")


if __name__ == "__main__":
    main()
