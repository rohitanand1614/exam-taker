"""Behaviour contract of the list / review pages (frozen like Batch 0 once green).

Pages: Bookmarks, Archived_Questions, Wrong_Answers, Search_Questions, Notes_Review.
Written against the ORIGINAL pages and kept valid after the restyle, so widgets are
located by LABEL (substring, any container) or by KEY - never by position or by the
sidebar - and counts are read from either the old metrics or the new count line.
"""
import ast
import json
import re
from pathlib import Path

import pytest

from utils import archive_manager, bookmark_manager, file_manager

pytestmark = pytest.mark.flow

ROOT = Path(__file__).resolve().parent.parent
RED, PURPLE = "Important (Red)", "Hard (Purple)"


# ------------------------------------------------------------------ data
def sample_questions():
    return file_manager.load_questions("questions", "sample")


def attempt(score, quality, ts):
    return {"attempt_id": "x", "timestamp": ts, "selected_indices": [0],
            "score": score, "quality": quality}


SRS = {"repetitions": 0, "interval_days": 1, "ef": 2.5, "next_due": "2030-01-01"}


@pytest.fixture
def seeded(workspace):
    """q1 red bookmark, q2 purple bookmark, q3 red bookmark AND archived;
    q1: wrong then right, q3: wrong (fixture), q2: right; notes on q1 and q2."""
    q1, q2, q3 = sample_questions()
    bookmark_manager.save_bookmark(q1, RED)
    bookmark_manager.save_bookmark(q2, PURPLE)
    bookmark_manager.save_bookmark(q3, RED)
    archive_manager.archive_question(q3)
    file_manager.save_attempt_log("sample_q1", attempt(0.0, 0, "2030-01-01T10:00:00"), SRS)
    file_manager.save_attempt_log("sample_q1", attempt(1.0, 5, "2030-01-01T11:00:00"), SRS)
    file_manager.save_attempt_log("sample_q2", attempt(1.0, 5, "2030-01-01T12:00:00"), SRS)
    file_manager.update_user_notes("sample_q1", "<p>note one</p>", "")
    file_manager.update_user_notes("sample_q2", "<p>note two</p>", "graph TD; A-->B;")
    return workspace


@pytest.fixture
def other_folder(workspace):
    """A second source folder with one question that also contains 'France'."""
    d = workspace / "questions" / "other"
    d.mkdir(parents=True)
    (d / "other.json").write_text(json.dumps([{
        "id": "other_q1", "question": "France borders which sea to the south?", "type": "multiple_choice",
        "options": ["A) Baltic", "B) Mediterranean"], "correct_indices": [1],
        "tags": ["geography"], "difficulty": "easy", "explanation": "The Mediterranean."}]),
        encoding="utf-8")
    return workspace


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    from utils import llm_client
    import requests
    monkeypatch.setattr(llm_client.LLMClient, "get_embedding", lambda self, *a, **k: [1.0, 0.0])
    monkeypatch.setattr(llm_client.LLMClient, "generate_response", lambda self, *a, **k: "stub")

    def boom(*a, **k):
        raise ConnectionError("network disabled in tests")
    monkeypatch.setattr(requests, "post", boom)
    monkeypatch.setattr(requests, "get", boom)


# ------------------------------------------------------------------ helpers
def by_label(elements, text):
    return [e for e in elements if text.lower() in (getattr(e, "label", "") or "").lower()]


def md_text(at):
    return "\n".join(m.value for m in at.get("markdown") if not m.value.lstrip().startswith("<style>"))


def keys(at):
    return [b.key for b in at.button if b.key]


def counts(at, total_label, noun):
    """(total, showing) from the old sidebar metrics OR the new 'N <noun> · showing M' line."""
    metrics = {m.label: m.value for m in at.metric}
    if total_label in metrics:
        return int(metrics[total_label]), int(metrics["Showing"])
    m = re.search(rf"(\d+) {noun} · showing (\d+)", md_text(at))
    assert m, f"no count found; metrics={metrics}"
    return int(m.group(1)), int(m.group(2))


def set_color_filter(at, colours):
    found = by_label(at.multiselect, "color") + by_label(at.multiselect, "colour")
    if found:
        found[0].set_value(colours).run()
        return
    groups = list(at.get("button_group"))
    assert groups, "colour filter not found"
    groups[0].set_value(colours).run()


def set_source_filter(at, values):
    by_label(at.multiselect, "source")[0].set_value(values).run()


# =================================================================== Bookmarks
def test_bookmarks_counts_exclude_archived(seeded, app):
    at = app("pages/Bookmarks.py").run()
    assert not at.exception
    assert counts(at, "Total Bookmarks", "saved") == (3, 2)


def test_bookmarks_filter_by_colour(seeded, app):
    at = app("pages/Bookmarks.py").run()
    set_color_filter(at, [PURPLE])
    assert not at.exception
    assert counts(at, "Total Bookmarks", "saved") == (3, 1)
    assert "rem_sample_q2" in keys(at) and "rem_sample_q1" not in keys(at)


def test_bookmarks_default_colour_selection_shows_all(seeded, app):
    at = app("pages/Bookmarks.py").run()
    assert {"rem_sample_q1", "rem_sample_q2"} <= set(keys(at))
    assert "rem_sample_q3" not in keys(at)  # archived


def test_bookmarks_filter_by_source(seeded, app):
    at = app("pages/Bookmarks.py").run()
    set_source_filter(at, [])
    assert counts(at, "Total Bookmarks", "saved") == (3, 0)
    assert not [k for k in keys(at) if k.startswith("rem_")]


def test_bookmarks_remove_updates_registry(seeded, app):
    at = app("pages/Bookmarks.py").run()
    at.button(key="rem_sample_q1").click().run()
    assert "sample_q1" not in json.loads((seeded / "bookmarks/registry.json").read_text(encoding="utf-8"))
    assert "sample_q2" in json.loads((seeded / "bookmarks/registry.json").read_text(encoding="utf-8"))


def test_bookmarks_archive_updates_registry(seeded, app):
    at = app("pages/Bookmarks.py").run()
    at.button(key="arch_sample_q2").click().run()
    reg = json.loads((seeded / "archives/registry.json").read_text(encoding="utf-8"))
    assert "sample_q2" in reg and "sample_q3" in reg


@pytest.fixture
def seven_bookmarks(workspace):
    for i in range(7):
        bookmark_manager.save_bookmark(
            {"id": f"p{i}", "question": f"Paged question {i}", "options": ["A) x"],
             "correct_indices": [0], "source_file": "paged.json"}, RED)
    return workspace


def test_bookmarks_paging_prev_next(seven_bookmarks, app):
    at = app("pages/Bookmarks.py").run()
    assert not at.exception
    first_page = {k for k in keys(at) if k.startswith("rem_")}
    assert len(first_page) == 5                      # ITEMS_PER_PAGE
    nxt = by_label(at.button, "Next")[0]
    assert not nxt.disabled
    nxt.click().run()
    assert at.session_state.page == 1
    second_page = {k for k in keys(at) if k.startswith("rem_")}
    assert len(second_page) == 2 and not (first_page & second_page)
    by_label(at.button, "Prev")[0].click().run()
    assert at.session_state.page == 0


def test_bookmarks_empty_state(workspace, app):
    at = app("pages/Bookmarks.py").run()
    assert not at.exception
    assert any("No bookmarks" in i.value for i in at.info)


# ============================================================= Archived_Questions
def test_archived_count_and_row(seeded, app):
    at = app("pages/Archived_Questions.py").run()
    assert not at.exception
    assert counts(at, "Total Archived", "archived") == (1, 1)
    assert "unarch_sample_q3" in keys(at)


def test_archived_source_filter(seeded, app):
    at = app("pages/Archived_Questions.py").run()
    set_source_filter(at, [])
    assert counts(at, "Total Archived", "archived") == (1, 0)
    assert "unarch_sample_q3" not in keys(at)


def test_unarchive_restores(seeded, app):
    at = app("pages/Archived_Questions.py").run()
    at.button(key="unarch_sample_q3").click().run()
    assert not archive_manager.is_archived("sample_q3")
    assert json.loads((seeded / "archives/registry.json").read_text(encoding="utf-8")) == {}


def test_archived_empty_state(workspace, app):
    at = app("pages/Archived_Questions.py").run()
    assert not at.exception
    assert any("No archived" in i.value for i in at.info)


# ================================================================ Wrong_Answers
def mistakes(at):
    """(count, source) read from the PAGE HEAD line ("2 mistakes in 'sample' · ..."); since Batch 8 the
    separate "Found N mistakes in '...'" subheader is gone because the head already says it."""
    m = re.search(r"(\d+) mistakes? in '([^']*)'", md_text(at))
    assert m, md_text(at)
    return int(m.group(1)), m.group(2)


def test_wrong_answers_last_attempt_rule(seeded, app):
    at = app("pages/Wrong_Answers.py").run()
    assert not at.exception
    # q3: last attempt wrong -> listed. q1: wrong, then right -> NOT listed. q2: right.
    assert mistakes(at)[0] == 1


def test_wrong_answers_ever_incorrect_rule(seeded, app):
    at = app("pages/Wrong_Answers.py").run()
    by_label(at.radio, "Filter Criteria")[0].set_value("Ever Incorrect").run()
    assert not at.exception
    assert mistakes(at)[0] == 2   # q1 (ever wrong) + q3


def test_wrong_answers_source_select(seeded, other_folder, app):
    (other_folder / "logs" / "attempts").mkdir(parents=True, exist_ok=True)
    file_manager.save_attempt_log("other_q1", attempt(0.0, 0, "2030-02-01T10:00:00"), SRS)
    at = app("pages/Wrong_Answers.py").run()
    src = by_label(at.selectbox, "Choose a Subject")[0]
    assert set(src.options) == {"other", "sample"}
    src.select("other").run()
    assert mistakes(at) == (1, "other")
    src.select("sample").run()
    assert mistakes(at) == (1, "sample")


def test_wrong_answers_no_mistakes_message(workspace, app):
    # fixture log makes q3 wrong; remove it so nothing is wrong
    file_manager.reset_question_log("sample_q3")
    at = app("pages/Wrong_Answers.py").run()
    assert not at.exception
    assert any("No mistakes" in s.value for s in at.success)


# =============================================================== Search_Questions
def click(at, label):
    by_label(at.button, label)[0].click().run()


def found_line(at):
    for s in at.success:
        m = re.search(r"Found \**(\d+)\**", s.value)
        if m:
            return int(m.group(1))
    return None


def test_search_needs_click_first(workspace, app):
    at = app("pages/Search_Questions.py").run()
    assert not at.exception
    assert found_line(at) is None
    assert any("Search" in i.value for i in at.info)


def test_search_all_without_keyword(workspace, app):
    at = app("pages/Search_Questions.py").run()
    click(at, "Search")
    assert found_line(at) == 3


def test_search_keyword_finds_by_question_text(workspace, app):
    at = app("pages/Search_Questions.py").run()
    at.text_input(key="keyword_search").set_value("capital of France").run()
    click(at, "Search")
    assert found_line(at) == 1


def test_search_keyword_no_match(workspace, app):
    at = app("pages/Search_Questions.py").run()
    at.text_input(key="keyword_search").set_value("zzzzzz-nothing").run()
    click(at, "Search")
    assert found_line(at) is None
    assert any("No questions found" in w.value for w in at.warning)


def test_search_folder_filter_narrows(other_folder, app):
    at = app("pages/Search_Questions.py").run()
    at.text_input(key="keyword_search").set_value("France").run()
    click(at, "Search")
    assert found_line(at) == 2                       # sample_q1 + other_q1
    at.selectbox(key="folder_search").select("other").run()
    click(at, "Search")
    assert found_line(at) == 1


def test_search_file_filter_narrows(other_folder, app):
    at = app("pages/Search_Questions.py").run()
    files = at.selectbox(key="file_search").options
    assert files[0] == "All" and len(files) == 3
    target = [f for f in files if f.replace("\\", "/") == "other/other.json"][0]
    at.selectbox(key="file_search").select(target).run()
    click(at, "Search")
    assert found_line(at) == 1


def test_search_reset(workspace, app):
    at = app("pages/Search_Questions.py").run()
    at.text_input(key="keyword_search").set_value("France").run()
    click(at, "Search")
    assert found_line(at) == 1
    click(at, "Reset")
    assert at.text_input(key="keyword_search").value == ""
    assert at.session_state.search_triggered is False
    assert found_line(at) is None


# ================================================================== Notes_Review
def notes_page_function(name):
    tree = ast.parse((ROOT / "pages" / "Notes_Review.py").read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return fn


def load_notes_functions():
    import bs4
    ns = {"BeautifulSoup": bs4.BeautifulSoup}
    for name in ("clean_html_text", "generate_markdown"):
        exec(compile(ast.Module([notes_page_function(name)], []), "Notes_Review.py", "exec"), ns)
    return ns


def test_notes_lists_only_questions_with_notes(seeded, app):
    at = app("pages/Notes_Review.py").run()
    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Questions with notes"] == "2"
    text = md_text(at)
    assert "note one" in text and "note two" in text


def test_notes_empty_state(workspace, app):
    at = app("pages/Notes_Review.py").run()
    assert not at.exception
    assert {m.label: m.value for m in at.metric}["Questions with notes"] == "0"
    assert any("No notes" in i.value for i in at.info)


def test_notes_export_buttons_present(seeded, app):
    at = app("pages/Notes_Review.py").run()
    labels = [e.proto.label for e in at.get("download_button")]
    assert "Download Markdown" in labels and "Download PDF" in labels


def test_notes_export_markdown_content(seeded):
    """Same data as the download: question text + cleaned notes, diagram marker, separators."""
    gen = load_notes_functions()["generate_markdown"]
    items = [
        {"question": "Q one?", "user_notes": "<p>note <b>one</b></p>", "user_diagram": ""},
        {"question": "Q two?", "user_notes": "<p>note two</p>", "user_diagram": "graph TD; A-->B;"},
    ]
    assert gen(items) == (
        "# Exam Notes Summary\n\n"
        "### Q one?\n\nnote \none\n\n---\n\n"
        "### Q two?\n\nnote two\n\n*(Contains Diagram - See App)*\n\n---\n\n"
    )


def test_notes_reorganize_with_mocked_embeddings(seeded, app):
    at = app("pages/Notes_Review.py").run()
    by_label(at.button, "Reorganize")[0].click().run()
    assert not at.exception
    assert at.session_state.ordered_notes is not None
    assert len(at.session_state.ordered_notes) == 2
    assert any("organized by topic flow" in s.value for s in at.success)
    assert (seeded / "user_data" / "notes_embedding_cache.json").exists()  # tmp workspace only
