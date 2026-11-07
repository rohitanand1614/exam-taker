"""Batch 8.2: page chrome is consistent on every page.

- every set_page_config uses a Material page_icon (never an emoji);
- every st.title / page head is sentence case without emoji (the brand name is the one exception);
- no emoji in ANY string literal of the UI code (catches branches a run does not reach) ...
- ... nor in anything RENDERED, on all 13 pages, before and after a basic action.
"""
import ast
import json
import re
from pathlib import Path

import pytest

from tests.test_insights_flow import no_network  # noqa: F401  (deterministic LLM stub, autouse)
from tests.test_review_flow import seeded  # noqa: F401
from utils import navigation

pytestmark = pytest.mark.ui

ROOT = Path(__file__).resolve().parent.parent
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿←-⇿️]")
BRAND = {"Exam Taker Pro"}

PAGE_FILES = ["app.py", "main.py"] + sorted(f"pages/{p.name}" for p in (ROOT / "pages").glob("*.py"))
UI_FILES = PAGE_FILES + ["utils/exam_view.py", "utils/ui_components.py", "utils/navigation.py"]


def tree(rel):
    return ast.parse((ROOT / rel).read_text(encoding="utf-8"))


def calls_named(rel, name):
    return [n for n in ast.walk(tree(rel)) if isinstance(n, ast.Call)
            and ((isinstance(n.func, ast.Attribute) and n.func.attr == name)
                 or (isinstance(n.func, ast.Name) and n.func.id == name))]


# ------------------------------------------------------------------ static checks
@pytest.mark.parametrize("rel", PAGE_FILES)
def test_page_icon_is_a_material_icon(rel):
    for call in calls_named(rel, "set_page_config"):
        icon = next((k.value for k in call.keywords if k.arg == "page_icon"), None)
        assert icon is not None, f"{rel}: set_page_config without page_icon"
        value = ast.literal_eval(icon)
        assert re.fullmatch(r":material/[a-z0-9_]+:", value), f"{rel}: page_icon={value!r}"


@pytest.mark.parametrize("rel", PAGE_FILES)
def test_titles_and_page_heads_are_sentence_case_without_emoji(rel):
    titles = []
    for name in ("title", "render_page_head", "page_head_html"):
        for call in calls_named(rel, name):
            if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
                titles.append(call.args[0].value)
    for t in titles:
        assert not EMOJI.search(t), (rel, t)
        if t in BRAND:
            continue
        assert t == t[0].upper() + t[1:].lower(), f"{rel}: {t!r} is not sentence case"


@pytest.mark.parametrize("rel", UI_FILES)
def test_no_emoji_in_any_string_literal(rel):
    bad = [n.value for n in ast.walk(tree(rel)) if isinstance(n, ast.Constant)
           and isinstance(n.value, str) and EMOJI.search(n.value)]
    assert not bad, f"{rel}: {bad}"


def test_every_nav_page_has_a_set_page_config_with_material_icon():
    assert len(PAGE_FILES) == 2 + 12
    for e in (x for g in navigation.nav_spec().values() for x in g):
        assert calls_named(e["path"], "set_page_config"), e["path"]


# ------------------------------------------------------------- rendered, all 13 pages
def visible_strings(at):
    out = []
    for kind in ("button", "markdown", "title", "caption", "subheader", "header", "expander", "status",
                 "radio", "checkbox", "selectbox", "multiselect", "info", "success", "warning", "error",
                 "metric", "text_input", "text_area", "slider", "tab", "toggle"):
        for el in at.get(kind):
            for attr in ("label", "value", "body", "placeholder"):
                v = getattr(el, attr, None)
                if isinstance(v, str):
                    out.append(v)
            opts = getattr(el, "options", None)
            if isinstance(opts, (list, tuple)):
                out.extend(o for o in opts if isinstance(o, str))
    out.extend(t.label for t in at.tabs)
    for el in at.get("download_button"):
        out.append(el.proto.label)
    return out


def assert_clean(at, where):
    bad = [s for s in visible_strings(at) if EMOJI.search(s)]
    assert not bad, f"{where}: {bad}"
    assert not at.exception, f"{where}: {[e.value for e in at.exception]}"


def by_label(elements, text):
    return [e for e in elements if text.lower() in (getattr(e, "label", "") or "").lower()]


def act_exam(at, ws):
    at.radio(key="radio_sample_q1").set_value("A").run()
    at.button(key="btn_sample_q1").click().run()


def act_practice(at, ws):
    at.radio(key="radio_sample_q1").set_value("A").run()
    at.button(key="btn_sample_q1").click().run()


def act_drill(at, ws):
    at.radio(key="drill_radio_sample_q1_0").set_value("A").run()
    at.button(key="drill_btn_sample_q1_0").click().run()


def act_regressive(at, ws):
    at.button(key="reg_start").click().run()
    q = at.session_state.regressive_current_q
    attempts = at.session_state.regressive_stats[q["id"]]["attempts"]
    if len(q["correct_indices"]) > 1:
        at.checkbox(key=f"chk_{q['id']}_{attempts}_0").check().run()
    else:
        at.radio(key=f"opt_{q['id']}_{attempts}").set_value("A").run()
    [b for b in at.button if b.key and b.key.startswith("reg_submit_")][0].click().run()


def act_wrong(at, ws):
    by_label(at.radio, "Filter Criteria")[0].set_value("Ever Incorrect").run()


def act_bookmarks(at, ws):
    by_label(at.multiselect, "source")[0].set_value([]).run()


def act_archived(at, ws):
    by_label(at.multiselect, "source")[0].set_value([]).run()


def act_notes(at, ws):
    by_label(at.button, "Reorganize")[0].click().run()


def act_search(at, ws):
    at.text_input(key="keyword_search").set_value("France").run()
    by_label(at.button, "Search")[0].click().run()


def act_progress(at, ws):
    by_label(at.selectbox, "Select Exam")[0].select("sample").run()


def act_topic(at, ws):
    at.selectbox(key="topic_analysis_suite_selector").select("sample").run()


def act_similar(at, ws):
    by_label(at.radio, "Method")[0].set_value("Contextual Match (LLM)").run()


ACTIONS = {
    "app.py": act_exam,
    "pages/Practice_Incorrect.py": act_practice,
    "pages/Practice_Bookmarks.py": act_practice,
    "pages/Targeted_Drill.py": act_drill,
    "pages/Regressive_Practice.py": act_regressive,
    "pages/Wrong_Answers.py": act_wrong,
    "pages/Bookmarks.py": act_bookmarks,
    "pages/Archived_Questions.py": act_archived,
    "pages/Notes_Review.py": act_notes,
    "pages/Search_Questions.py": act_search,
    "pages/Progress_Dashboard.py": act_progress,
    "pages/Topic_Analysis.py": act_topic,
    "pages/Similar_Questions_Management.py": act_similar,
}


def test_every_nav_page_has_an_action():
    assert sorted(ACTIONS) == sorted(e["path"] for g in navigation.nav_spec().values() for e in g)


@pytest.mark.parametrize("path", sorted(ACTIONS))
def test_no_emoji_rendered_before_and_after_an_action(path, seeded, app):
    ws = seeded
    at = app(path)
    if path == "pages/Targeted_Drill.py":
        at.session_state["drill_questions"] = json.loads(
            (ws / "questions/sample/sample.json").read_text(encoding="utf-8"))
    at.run()
    assert_clean(at, f"{path} (before)")
    ACTIONS[path](at, ws)
    assert_clean(at, f"{path} (after)")


def test_no_emoji_through_main_py_navigation_chrome(seeded, app):
    at = app("main.py").run()
    assert_clean(at, "main.py")


# ------------------------------------------------------------- 8.3 label consistency
OLD_LABELS = {"Submit Answer": "Submit answer", "Next Question": "Next question",
              "Start New Session": "Start new session"}


@pytest.mark.parametrize("rel", UI_FILES)
def test_no_title_case_variants_of_the_shared_button_labels(rel):
    literals = [n.value for n in ast.walk(tree(rel)) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    for old, new in OLD_LABELS.items():
        assert not any(old in s for s in literals), f"{rel}: use {new!r}, not {old!r}"


def test_shared_labels_are_used_on_the_real_buttons(seeded, app):
    ws = seeded
    reg = app("pages/Regressive_Practice.py").run()
    assert reg.button(key="reg_start").label == "Start new session"
    reg.button(key="reg_start").click().run()
    submit = [b for b in reg.button if b.key and b.key.startswith("reg_submit_")][0]
    assert submit.label == "Submit answer"
    assert any("Start new session" in i.value for i in app("pages/Regressive_Practice.py").run().info)

    drill = app("pages/Targeted_Drill.py")
    drill.session_state["drill_questions"] = json.loads(
        (ws / "questions/sample/sample.json").read_text(encoding="utf-8"))
    drill.run()
    assert [b.label for b in drill.sidebar.button if b.key and b.key.startswith("drill_next_")] == ["Next question"]


def test_wrong_answers_has_no_duplicate_count_heading(seeded, app):
    at = app("pages/Wrong_Answers.py").run()
    assert not at.exception
    assert not [s for s in at.get("subheader") if "Found" in s.value]
    head = [m.value for m in at.get("markdown") if m.value.lstrip().startswith('<div class="etp-pagehead"')][0]
    assert re.search(r"1 mistake in 'sample'", head)             # count + source live in the page head only
