"""Manual screenshot tool (NOT collected by pytest).

    python tests/visual/shoot.py [label]          # label defaults to "batch1"

Copies tests/fixtures/workspace and .streamlit/ to a temp dir (Streamlit reads
config.toml from the working directory), starts the app there, screenshots
"/" and every page in pages/, then stops the server (even on error).
Output: tests/.artifacts/screens/<label>/*.png
"""
import re
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
sys.path.insert(0, str(APP_DIR))
from utils import navigation  # noqa: E402  (pure module)

# page file stem -> route under main.py's st.navigation ("" = the default Exam page)
URL = {Path(e["path"]).stem: ("" if e["default"] else e["url_path"])
       for group in navigation.nav_spec().values() for e in group}
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
    page.goto(f"{BASE}/{URL['Practice_Incorrect']}")
    settle(page)
    pick_first_option(page)  # A is wrong for Q1
    page.get_by_role("button", name="Submit answer").click()
    settle(page)
    shot(page, out_dir, "practice_incorrect_after_wrong")


def practice_bookmarks(page, out_dir):
    page.goto(f"{BASE}/{URL['Practice_Bookmarks']}")
    settle(page)
    shot(page, out_dir, "practice_bookmarks")
    pick_first_option(page)  # whichever bookmarked question comes first (radio or checkbox)
    page.get_by_role("button", name="Submit answer").click()
    settle(page)
    shot(page, out_dir, "practice_bookmarks_after_submit")


def regressive_flow(page, out_dir):
    page.goto(f"{BASE}/{URL['Regressive_Practice']}")
    settle(page)
    page.get_by_role("button", name="Start new session").click()
    settle(page)
    shot(page, out_dir, "regressive_started")
    page.keyboard.press("a")                 # keyboard shortcuts: answer A, Enter = Submit answer
    page.wait_for_timeout(500)
    page.keyboard.press("Enter")
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


BM_TRIGGER = '.st-key-qcard [data-testid="stPopover"] button'


def drill_flow(page, base, out_dir):
    page.goto(base + "/")
    settle(page)
    shot(page, out_dir, "drill_question")
    page.locator(BM_TRIGGER).first.click()          # bookmark colour pills (Batch 10a)
    page.wait_for_timeout(700)
    page.screenshot(path=str(out_dir / "drill_bookmark_popover.png"))
    print("saved", out_dir / "drill_bookmark_popover.png")
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    page.keyboard.press("a")  # A is wrong for Q1 -> question gets re-queued (keyboard: answer A, Enter)
    page.wait_for_timeout(500)
    page.keyboard.press("Enter")
    settle(page)
    shot(page, out_dir, "drill_after_submit")
    page.goto(base + "/?n=1")  # single question = last question: finish screen
    settle(page)
    shot(page, out_dir, "drill_finish")


def bookmarks_flow(page, out_dir):
    page.goto(f"{BASE}/{URL['Bookmarks']}")
    settle(page)
    shot(page, out_dir, "bookmarks_all")
    # filter: switch one colour pill off, open the first review card
    page.locator('[data-testid="stButtonGroup"] button', has_text="Important").first.click()
    settle(page, 1200)
    page.get_by_text("Show answer").first.click()
    page.wait_for_timeout(800)
    shot(page, out_dir, "bookmarks_filtered_open")


def archived_flow(page, out_dir):
    page.goto(f"{BASE}/{URL['Archived_Questions']}")
    settle(page)
    page.get_by_text("Show answer").first.click()
    page.wait_for_timeout(800)
    shot(page, out_dir, "archived_open")


def wrong_flow(page, out_dir):
    page.goto(f"{BASE}/{URL['Wrong_Answers']}")
    settle(page)
    page.get_by_text("Show answer").first.click()
    page.wait_for_timeout(800)
    shot(page, out_dir, "wrong_answers_open")


def search_flow(page, out_dir):
    page.goto(f"{BASE}/{URL['Search_Questions']}")
    settle(page)
    page.get_by_placeholder("Search in question text").fill("France")
    page.keyboard.press("Enter")
    page.wait_for_timeout(500)
    page.get_by_role("button", name="Search").first.click()
    settle(page)
    page.get_by_text("Show answer").first.click()
    page.wait_for_timeout(800)
    shot(page, out_dir, "search_with_query")


def notes_flow(page, out_dir):
    page.goto(f"{BASE}/{URL['Notes_Review']}")
    settle(page)
    page.get_by_role("button", name="Expand all").click()
    settle(page, 1200)
    shot(page, out_dir, "notes_review_expanded")


def write_log(work, qid, outcomes, notes=""):
    """A question log with the given attempt outcomes (True = correct), dated long ago so the
    exam's 48-hour rule does not hide the question. Same shape as file_manager.save_attempt_log."""
    import json
    attempts = [{"attempt_id": f"seed{i}", "timestamp": f"2025-01-0{i + 1}T10:00:00", "selected_indices": [0],
                 "score": 1.0 if ok else 0.0, "quality": 5 if ok else 0} for i, ok in enumerate(outcomes)]
    n_ok = sum(1 for ok in outcomes if ok)
    log = {"summary": {"total_attempts": len(outcomes), "correct_count": n_ok, "wrong_count": len(outcomes) - n_ok,
                       "avg_score": (n_ok / len(outcomes)) if outcomes else 0.0,
                       "last_attempted_at": attempts[-1]["timestamp"] if attempts else None,
                       "srs": {"repetitions": 0, "interval_days": 0, "ef": 2.5, "next_due": None}},
           "attempts": attempts}
    if notes:
        log["user_notes"], log["user_diagram"] = notes, ""
    (work / "logs" / "attempts").mkdir(parents=True, exist_ok=True)
    (work / "logs" / "attempts" / f"{qid}.log.json").write_text(json.dumps(log), encoding="utf-8")


def seed_insights(work):
    """Data for the insight pages: a spread of mastered / mixed / weak questions, notes, a suite with
    enough topics for the charts, a duplicate pair, and a pre-filled topic cache (never calls an LLM)."""
    import json
    # sample suite: q1 mastered, q2 mixed (+ notes on both); q3 keeps the fixture's wrong attempt
    write_log(work, "sample_q1", [True, True], "<p>Paris is the <b>capital</b> and largest city of France.</p>")
    write_log(work, "sample_q2", [True, False], "<p>Primes: 2, 3, 5, 7. Remember that <i>1 is not prime</i>.</p>")

    # topics-demo suite: three topics (4 / 4 / 3 questions) with different mastery, plus a duplicate pair
    def q(qid, tag, text, correct=1):
        return {"id": qid, "question": text, "type": "multiple_choice",
                "options": ["A) first", "B) second", "C) third"], "correct_indices": [correct],
                "tags": [tag], "difficulty": "medium", "explanation": f"Explanation for {qid}."}
    suite = work / "questions" / "topics-demo"
    suite.mkdir(parents=True, exist_ok=True)
    demo = ([q(f"alpha{i}", "t_alpha", f"Alpha topic question {i}?") for i in range(1, 5)]
            + [q(f"beta{i}", "t_beta", f"Beta topic question {i}?") for i in range(1, 5)]
            + [q(f"gamma{i}", "t_gamma", f"Gamma topic question {i}?") for i in range(1, 4)])
    (suite / "demo.json").write_text(json.dumps(demo), encoding="utf-8")
    dup = q("dup_a", "t_gamma", "Which layer type applies a causal mask in a decoder?")
    (suite / "dup_a.json").write_text(json.dumps([dup]), encoding="utf-8")
    (suite / "dup_b.json").write_text(json.dumps([dict(dup, id="dup_b")]), encoding="utf-8")
    outcomes = {"alpha1": [True], "alpha2": [False], "alpha3": [False], "alpha4": [False],      # 25%
                "beta1": [True], "beta2": [True], "beta3": [True], "beta4": [False],            # 75%
                "gamma1": [True], "gamma2": [True], "gamma3": [False]}                          # 67%
    for qid, outs in outcomes.items():
        write_log(work, qid, outs)
    cache = {"tag_map": {"t_alpha": "Alpha topic", "t_beta": "Beta topic", "t_gamma": "Gamma topic"},
             "topics": {}, "suite": "topics-demo"}
    (work / "logs" / "attempts" / "topic_analysis_cache_topics-demo.json").write_text(json.dumps(cache), encoding="utf-8")


def progress_flow(page, out_dir):
    page.goto(f"{BASE}/{URL['Progress_Dashboard']}")
    settle(page)
    shot(page, out_dir, "progress_mastered")
    for name in ("Mixed", "Struggling", "Unattempted"):
        page.get_by_role("tab", name=re.compile(name)).click()
        page.wait_for_timeout(700)
        shot(page, out_dir, f"progress_{name.lower()}")


def topic_flow(page, out_dir):
    page.goto(f"{BASE}/{URL['Topic_Analysis']}")
    settle(page)
    page.locator('section[data-testid="stSidebar"] [data-baseweb="select"]').first.click()
    page.get_by_role("option", name="topics-demo").click()
    settle(page, 3500)
    shot(page, out_dir, "topic_analysis_demo_suite")


def similar_flow(page, out_dir):
    page.goto(f"{BASE}/{URL['Similar_Questions_Management']}")
    settle(page)
    shot(page, out_dir, "similar_questions")
    page.locator('section[data-testid="stMain"] [data-testid="stCheckbox"] label').first.click()
    settle(page, 1200)
    shot(page, out_dir, "similar_selected")


def nav_top_menus(page, out_dir):
    """The top navigation: closed bar, then the Practice and Insights menus open (on a non-default page)."""
    page.goto(f"{BASE}/{URL['Progress_Dashboard']}")
    settle(page, 1500)
    sections = page.locator('[data-testid="stTopNavSection"]')
    for i, name in ((0, "practice"), (2, "insights")):
        sections.nth(i).click()
        page.wait_for_timeout(700)
        page.screenshot(path=str(out_dir / f"nav_menu_{name}.png"), clip={"x": 0, "y": 0, "width": 760, "height": 330})
        print("saved", out_dir / f"nav_menu_{name}.png")
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)


def exam_bookmark(page, out_dir):
    """Bookmark popover with coloured chips: unbookmarked, then after saving 'Important'."""
    page.goto(BASE + "/")
    settle(page)
    page.locator(BM_TRIGGER).first.click()
    page.wait_for_timeout(700)
    page.screenshot(path=str(out_dir / "exam_bookmark_popover.png"))
    print("saved", out_dir / "exam_bookmark_popover.png")
    page.locator('[class*="st-key-bm_sel_"] button', has_text="Important").first.click()
    page.wait_for_timeout(400)
    page.get_by_role("button", name="Save bookmark").click()
    settle(page, 1200)
    # the popover stays open after Save: status line + Remove are visible
    page.screenshot(path=str(out_dir / "exam_bookmarked_popover.png"))
    print("saved", out_dir / "exam_bookmarked_popover.png")
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    shot(page, out_dir, "exam_bookmarked")                     # closed: the chip shows the coloured dot + name
    page.locator(BM_TRIGGER).first.click()                     # undo, so later flows (drill) start unbookmarked
    page.wait_for_timeout(500)
    page.get_by_role("button", name="Remove bookmark").click()
    settle(page, 1000)


def exam_keyboard(page, out_dir):
    """Key hints on the buttons, a keyboard-selected answer, and the Shift+B bookmark popover."""
    page.goto(BASE + "/")
    settle(page)
    page.keyboard.press("b")
    page.wait_for_timeout(600)
    shot(page, out_dir, "exam_keyboard_selected")
    page.keyboard.press("Shift+B")
    page.wait_for_timeout(900)
    page.screenshot(path=str(out_dir / "exam_keyboard_bookmark_popover.png"))
    print("saved", out_dir / "exam_keyboard_bookmark_popover.png")
    page.keyboard.press("Escape")


def small_laptop(browser, out_dir):
    """1280x800: the top bar must not wrap and a page's sidebar controls must be visible without scrolling."""
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
    pg = ctx.new_page()
    try:
        pg.goto(BASE + "/")
        settle(pg)
        pg.goto(f"{BASE}/{URL['Regressive_Practice']}")
        settle(pg)
        btn = pg.get_by_role("button", name="Start new session")
        box = btn.bounding_box()
        print("1280x800 start button box:", box)
        assert box and box["y"] + box["height"] <= 800, f"Start new session needs a scroll: {box}"
        pg.screenshot(path=str(out_dir / "small_1280x800_regressive.png"))
        print("saved", out_dir / "small_1280x800_regressive.png")
        pg.goto(f"{BASE}/{URL['Progress_Dashboard']}")
        settle(pg)
        bar = pg.locator('[data-testid="stTopNavSection"]')
        ys = {round(bar.nth(i).bounding_box()["y"]) for i in range(bar.count())}
        print("1280x800 top bar rows:", ys)
        assert len(ys) == 1 and bar.count() == 4, f"top bar wraps or hides groups: {ys}"
        pg.screenshot(path=str(out_dir / "small_1280x800_progress.png"))
        print("saved", out_dir / "small_1280x800_progress.png")
    finally:
        ctx.close()


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
    seed_insights(work)
    # Targeted_Drill needs a seeded session: tiny wrapper entry on a second server
    drill_port = PORT + 1
    (work / "drill_entry.py").write_text(
        DRILL_ENTRY.format(app=str(APP_DIR), page=str(APP_DIR / "pages" / "Targeted_Drill.py")),
        encoding="utf-8")

    pages = sorted(p.stem for p in (APP_DIR / "pages").glob("*.py"))
    server = start_server(APP_DIR / "main.py", PORT, work)   # grouped st.navigation entry
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
                    page.goto(f"{BASE}/{URL[name]}")
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
                               ("notes", notes_flow),
                               ("progress", progress_flow),
                               ("topic", topic_flow),
                               ("similar", similar_flow),
                               ("nav", nav_top_menus),
                               ("exam_bookmark", exam_bookmark),
                               ("exam_keyboard", exam_keyboard)):
                try:
                    flow(page, out_dir)
                except Exception as e:
                    print(f"FAILED {name}: {e}")
            try:
                small_laptop(browser, out_dir)
            except Exception as e:
                print(f"FAILED small laptop: {e}")
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
