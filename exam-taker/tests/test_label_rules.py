"""Batch 9.2: ONE label rule set, applied everywhere (static: every UI source file; runtime: all 13 pages).

1. Sentence case for every widget label, button, tab, metric label (Title Case detector with an allow-list
   for proper nouns / acronyms).
2. No trailing colon on a label.
3. One verb for revealing an answer: "Show answer".
4. Page head title == navigation title (the descriptive text is the subtitle line).
5. Archive pages: button "Restore", tooltip and toast "Restored".
6. The two buttons that go back to Topic analysis say "Back to topic analysis".
Option VALUES of radios/selectboxes (e.g. "Ever Incorrect") are data the page logic compares, not labels.
"""
import ast
import json
import re
from pathlib import Path

import pytest

from tests.test_insights_flow import no_network  # noqa: F401  (deterministic LLM stub, autouse)
from tests.test_page_chrome import ACTIONS, UI_FILES, tree
from tests.test_review_flow import seeded  # noqa: F401
from utils import navigation

pytestmark = pytest.mark.ui

ROOT = Path(__file__).resolve().parent.parent
NAV = {e["path"]: e["title"] for g in navigation.nav_spec().values() for e in g}

# proper nouns / product names that keep their capital letter (acronyms in ALL CAPS are always fine)
ALLOW = {"GitHub", "Ollama", "OpenAI", "Mermaid", "Markdown", "Streamlit", "Quill", "LaTeX", "Exam Taker Pro"}

LABEL_CALLS = {"button", "radio", "selectbox", "multiselect", "checkbox", "text_input", "text_area", "slider",
               "number_input", "toggle", "expander", "popover", "download_button", "metric", "pills",
               "segmented_control", "page_link", "header", "subheader", "select_slider", "file_uploader"}


# ------------------------------------------------------------------ the rules (pure functions)
def words_after_first(label):
    text = re.sub(r"\{[^}]*\}", " ", label)
    for brand in ALLOW:
        text = text.replace(brand, " ")
    tokens = [t for t in re.split(r"[\s/]+", text.strip()) if t]
    out = []
    for t in tokens[1:]:
        out.extend(p.strip("()[]'\".,:;!?&*") for p in t.split("-"))
    return [w for w in out if w]


def title_case_words(label):
    """Words after the first that start Capital+lowercase and are not allowed (acronyms like SRS/LLM pass)."""
    return [w for w in words_after_first(label) if re.match(r"[A-Z][a-z]", w) and w not in ALLOW]


def label_problems(label):
    problems = []
    if label.rstrip().endswith(":"):
        problems.append("trailing colon")
    bad = title_case_words(label)
    if bad:
        problems.append(f"Title Case word(s) {bad}")
    if re.search(r"\b(show|view|review|reveal)\b.*\banswers?\b", label, re.I) and label != "Show answer":
        problems.append('use "Show answer"')
    return problems


# --------------------------------------------------- detector self-tests (the rules themselves)
@pytest.mark.parametrize("label", ["Start new session", "Include wrong questions", "Filter by source",
                                   "Similarity threshold", "LLM configuration", "Download Markdown",
                                   "Download PDF", "Refresh analysis (trigger LLM)", "Mastered (3)",
                                   "Double-loop mode (recommended)", "Generate analysis for {suite}",
                                   "Select exam", "Provider", "My notes & diagram", "Show answer",
                                   "Connect to GitHub", "Pick OpenAI or Ollama", "Choose a subject/topic"])
def test_detector_accepts_sentence_case(label):
    assert label_problems(label) == []


@pytest.mark.parametrize("label,fragment", [
    ("Select Exam", "Title Case"), ("Include Wrong Questions", "Title Case"),
    ("Double-Loop Mode (Recommended)", "Title Case"), ("Choose a Subject/Topic", "Title Case"),
    ("Load by:", "trailing colon"), ("Select Exam to Analyze:", "trailing colon"),
    ("Review answer", "Show answer"), ("View answer", "Show answer"), ("Reveal the answer", "Show answer"),
])
def test_detector_flags_the_old_style(label, fragment):
    assert any(fragment in p for p in label_problems(label)), label_problems(label)


# ------------------------------------------------------------------ static: every label literal
def _text(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in node.values)
    return None


def static_labels(rel):
    """[(line, call name, label)] of every label literal in the file (first arg / label= / tab list)."""
    out = []
    for n in ast.walk(tree(rel)):
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "label" for t in n.targets)                 and _text(n.value):
            out.append((n.lineno, "label variable", _text(n.value)))        # e.g. label = "Choose a JSON file"
        if not isinstance(n, ast.Call):
            continue
        name = n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
        if name == "tabs" and n.args and isinstance(n.args[0], (ast.List, ast.Tuple)):
            out += [(n.lineno, "tab", _text(e)) for e in n.args[0].elts if _text(e)]
        elif name in LABEL_CALLS:
            label = next((k.value for k in n.keywords if k.arg == "label"), None)
            if label is None and n.args and name != "page_link":
                label = n.args[0]
            if label is not None and _text(label):
                out.append((n.lineno, name, _text(label)))
    return out


@pytest.mark.parametrize("rel", UI_FILES)
def test_static_labels_follow_the_rules(rel):
    bad = [(line, name, label, label_problems(label)) for line, name, label in static_labels(rel)
           if label_problems(label)]
    assert not bad, f"{rel}: {bad}"


def test_static_extraction_finds_labels():
    assert len(static_labels("pages/Topic_Analysis.py")) >= 8     # guards against a silently empty detector


# ------------------------------------------------------------------ runtime: all 13 pages
def runtime_labels(at):
    out = []
    for kind in ("button", "radio", "checkbox", "selectbox", "multiselect", "text_input", "text_area", "slider",
                 "number_input", "toggle", "metric"):
        for el in at.get(kind):
            label = getattr(el, "label", None)
            if isinstance(label, str) and label and not label.startswith("**"):   # "**A** ..." = option text
                out.append((kind, label))
    out += [("tab", t.label) for t in at.tabs]
    out += [("download_button", el.proto.label) for el in at.get("download_button")]
    return out


@pytest.mark.parametrize("path", sorted(ACTIONS))
def test_rendered_labels_follow_the_rules(path, seeded, app):
    ws = seeded
    at = app(path)
    if path == "pages/Targeted_Drill.py":
        at.session_state["drill_questions"] = json.loads(
            (ws / "questions/sample/sample.json").read_text(encoding="utf-8"))
    at.run()
    labels = runtime_labels(at)
    ACTIONS[path](at, ws)
    labels += runtime_labels(at)
    assert labels, path
    bad = [(k, lab, label_problems(lab)) for k, lab in labels if label_problems(lab)]
    assert not bad, f"{path}: {bad}"


# ------------------------------------------------------------------ 4. page head == nav title
def head_title(at):
    for m in at.get("markdown"):
        found = re.match(r'\s*<div class="etp-pagehead"><div><h1>(.*?)</h1>', m.value)
        if found:
            return found.group(1)
    main_titles = [t.value for t in at.get("title") if t not in list(at.sidebar.get("title"))]
    return main_titles[0] if main_titles else None


@pytest.mark.parametrize("path", sorted(p for p in NAV if p != "app.py"))
def test_page_head_title_equals_nav_title(path, seeded, app):
    ws = seeded
    at = app(path)
    if path == "pages/Targeted_Drill.py":
        at.session_state["drill_questions"] = json.loads(
            (ws / "questions/sample/sample.json").read_text(encoding="utf-8"))
    at.run()
    assert head_title(at) == NAV[path]


def test_exam_page_keeps_the_brand_title_in_the_sidebar(seeded, app):
    at = app("app.py").run()
    assert [t.value for t in at.sidebar.get("title")] == ["Exam Taker Pro"]
    assert NAV["app.py"] == "Exam"


@pytest.mark.parametrize("path", sorted(p for p in NAV if p != "app.py"))
def test_browser_tab_title_equals_nav_title(path):
    call = [n for n in ast.walk(tree(path)) if isinstance(n, ast.Call)
            and getattr(n.func, "attr", "") == "set_page_config"][0]
    title = ast.literal_eval(next(k.value for k in call.keywords if k.arg == "page_title"))
    assert title == NAV[path]


# ------------------------------------------------------------------ 5. Restore / Restored
def string_literals(rel):
    return [n.value for n in ast.walk(tree(rel)) if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and not n.value.startswith(":material/")]


def test_archive_wording_is_restore_restored():
    lits = string_literals("pages/Archived_Questions.py")
    assert "Restore" in lits
    assert not [s for s in lits if re.search(r"unarchive", s, re.I)], "say Restore / Restored, not Unarchive"
    assert any(s.startswith("Restored") for s in lits)                    # toast
    assert any("Restore" in s and s != "Restore" for s in lits)           # tooltip


def test_restore_button_tooltip_and_toast_use_the_same_word(seeded, app):
    at = app("pages/Archived_Questions.py").run()
    btn = [b for b in at.button if b.label == "Restore"][0]
    assert btn.help and "Restore" in btn.help and "narchive" not in btn.help
    btn.click().run()
    assert any(t.value.startswith("Restored") for t in at.toast)


# ------------------------------------------------------------------ 6. Back to topic analysis
@pytest.mark.parametrize("rel", UI_FILES)
def test_no_dashboard_in_button_labels(rel):
    bad = [(ln, lab) for ln, name, lab in static_labels(rel) if name == "button" and "dashboard" in lab.lower()]
    assert not bad, bad


def test_drill_buttons_say_back_to_topic_analysis(seeded, app):
    ws = seeded
    empty = app("pages/Targeted_Drill.py").run()
    assert [b.label for b in empty.button if b.key == "drill_dashboard"] == ["Back to topic analysis"]
    drill = app("pages/Targeted_Drill.py")
    drill.session_state["drill_questions"] = json.loads(
        (ws / "questions/sample/sample.json").read_text(encoding="utf-8"))[:1]
    drill.run()                                  # one question left: the sidebar already offers the way out
    buttons = list(drill.button) + list(drill.sidebar.button)          # the drill controls live in the sidebar
    assert {b.label for b in buttons if b.key == "drill_finish"} == {"Back to topic analysis"}
