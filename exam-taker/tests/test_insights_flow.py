"""Behaviour contract of the insight pages (frozen once green, like Batch 0 / review_flow).

Pages: Progress_Dashboard, Topic_Analysis, Similar_Questions_Management.
Written against the ORIGINAL pages and kept valid after the restyle: widgets are located by
KEY or LABEL (substring, any container), tab/metric values by regex, and chart data is decoded
from the Plotly spec JSON so styling can be proven not to change what is plotted.

No LLM / embedding / network call: the tag clustering LLM, the similarity scan and
requests are mocked.
"""
import base64
import json
import re
import shutil
from pathlib import Path

import numpy as np
import pytest

from utils import archive_manager, file_manager

pytestmark = pytest.mark.flow

EXTRAS = Path(__file__).resolve().parent / "fixtures" / "extras"
SRS = {"repetitions": 0, "interval_days": 1, "ef": 2.5, "next_due": "2030-01-01"}


# ------------------------------------------------------------------ data
def attempt(correct, ts="2030-01-01T10:00:00"):
    return {"attempt_id": "x", "timestamp": ts, "selected_indices": [0],
            "score": 1.0 if correct else 0.0, "quality": 5 if correct else 0}


def log_attempts(qid, *outcomes):
    for i, ok in enumerate(outcomes):
        file_manager.save_attempt_log(qid, attempt(ok, f"2030-01-01T10:0{i}:00"), SRS)


def make_question(qid, tag, text):
    return {"id": qid, "question": text, "type": "multiple_choice",
            "options": ["A) one", "B) two"], "correct_indices": [1], "tags": [tag],
            "difficulty": "easy", "explanation": f"Because {qid}."}


@pytest.fixture
def spread(workspace):
    """Known spread over 10 questions (see tests for the numbers).

    sample_q1 mastered, sample_q2 mixed, sample_q3 all wrong (fixture log), sample_code_q1 new,
    ta1/ta2 correct + ta3 wrong, tb1..tb3 correct."""
    shutil.copytree(EXTRAS, workspace, dirs_exist_ok=True)
    extra = ([make_question(f"ta{i}", "t_a", f"Topic A question {i}?") for i in (1, 2, 3)]
             + [make_question(f"tb{i}", "t_b", f"Topic B question {i}?") for i in (1, 2, 3)])
    (workspace / "questions" / "sample" / "topic_extra.json").write_text(json.dumps(extra), encoding="utf-8")
    log_attempts("sample_q1", True, True)          # mastered
    log_attempts("sample_q2", True, False)         # mixed
    log_attempts("ta1", True)
    log_attempts("ta2", True)
    log_attempts("ta3", False)
    for i in (1, 2, 3):
        log_attempts(f"tb{i}", True)
    return workspace


MAPPING = {"geography": "Geography", "sample": "Sample Set", "math": "Maths", "calculus": "Maths",
           "t_a": "Topic A", "t_b": "Topic B"}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """The only LLM call in these pages is tag clustering: answer deterministically from the prompt."""
    from utils import llm_client
    import requests

    def fake_generate(self, prompt, system_prompt=""):
        tags = json.loads(prompt.split("New Tags to group:")[1].strip())
        return json.dumps({t: MAPPING.get(t, "LangGraph") for t in tags})

    def boom(*a, **k):
        raise ConnectionError("network disabled in tests")

    monkeypatch.setattr(llm_client.LLMClient, "generate_response", fake_generate)
    monkeypatch.setattr(llm_client.LLMClient, "get_embedding", lambda self, *a, **k: [0.0, 0.0])
    monkeypatch.setattr(requests, "post", boom)
    monkeypatch.setattr(requests, "get", boom)


# ------------------------------------------------------------------ helpers
def by_label(elements, text):
    return [e for e in elements if text.lower() in (getattr(e, "label", "") or "").lower()]


def tab_counts(at):
    """{'Mastered': n, ...} from tab labels, tolerant of a leading emoji dot."""
    out = {}
    for t in at.tabs:
        m = re.search(r"([A-Za-z]+)\s*\((\d+)\)", t.label)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def decode(v):
    if isinstance(v, dict) and "bdata" in v:
        return np.frombuffer(base64.b64decode(v["bdata"]), dtype=np.dtype(v["dtype"])).tolist()
    return v


def chart_data(at):
    """Plotted data of every plotly_chart, independent of colours/layout:
    [(orientation, trace name, {label: value})]  (labels = the categorical axis)."""
    out = []
    for c in at.get("plotly_chart"):
        spec = json.loads(c.proto.spec)
        for t in spec["data"]:
            x, y = decode(t.get("x")), decode(t.get("y"))
            if t.get("orientation") == "h":
                pairs = dict(zip(y, [round(v, 2) for v in x]))
            else:
                pairs = dict(zip(x, y))
            out.append((t.get("orientation"), t.get("name"), pairs))
    return out


def select_suite(at, suite="sample"):
    at.selectbox(key="topic_analysis_suite_selector").select(suite).run()
    assert not at.exception
    return at


# ========================================================== Progress_Dashboard
@pytest.fixture
def progress(spread, app):
    at = app("pages/Progress_Dashboard.py").run()
    assert not at.exception
    return at


def test_progress_exam_select_and_default(progress):
    sel = by_label(progress.selectbox, "Select Exam")[0]
    assert sel.options[0] == "sample" and sel.value == "sample"


def test_progress_tab_counts(progress):
    # mastered: q1, ta1, ta2, tb1-3 | mixed: q2 | struggling: q3, ta3 | unattempted: the code question
    assert tab_counts(progress) == {"Mastered": 6, "Mixed": 1, "Struggling": 2, "Unattempted": 1}


def test_progress_four_tabs_render(progress):
    assert len(list(progress.tabs)) == 4


def test_progress_questions_listed_in_the_right_tab(progress):
    """Layout-neutral: a question's text appears in its tab (expander label or list row)."""
    tabs = list(progress.tabs)

    def texts(tab):
        labels = [e.label for e in tab.expander if e.label]
        rows = [m.value for m in tab.markdown]
        return " ".join(labels + rows)

    assert "capital of France" in texts(tabs[0])                    # mastered
    assert "Select all prime" in texts(tabs[1])                     # mixed
    assert "derivative" in texts(tabs[2])                           # struggling
    assert "compliance agent" in texts(tabs[3])                     # unattempted (code question)
    assert "derivative" not in texts(tabs[0])


def test_progress_changing_exam_changes_counts(spread, app):
    at = app("pages/Progress_Dashboard.py").run()
    sel = by_label(at.selectbox, "Select Exam")[0]
    target = [o for o in sel.options if o.replace("\\", "/") == "sample/topic_extra.json"][0]
    sel.select(target).run()
    assert tab_counts(at) == {"Mastered": 5, "Mixed": 0, "Struggling": 1, "Unattempted": 0}


def test_progress_empty_tab_message(spread, app):
    at = app("pages/Progress_Dashboard.py").run()
    sel = by_label(at.selectbox, "Select Exam")[0]
    target = [o for o in sel.options if o.replace("\\", "/") == "sample/topic_extra.json"][0]
    sel.select(target).run()
    tabs = list(at.tabs)
    assert any("No questions" in i.value for i in tabs[1].info)   # Mixed is empty here


# ============================================================== Topic_Analysis
@pytest.fixture
def topic(spread, app):
    at = app("pages/Topic_Analysis.py").run()
    assert not at.exception
    return select_suite(at)


def test_topic_requires_a_suite(spread, app):
    at = app("pages/Topic_Analysis.py").run()
    assert any("select a specific" in w.value.lower() for w in at.warning)
    assert not list(at.get("plotly_chart"))


def test_topic_overview_metrics(topic):
    metrics = {m.label: m.value for m in topic.metric}
    assert metrics == {"Total questions": "10", "Overall accuracy": "60.0%", "Topics identified": "6"}


def test_topic_analysis_loaded_message(topic):
    assert any("Analysis loaded for sample" in s.value for s in topic.success)


def test_topic_weak_areas_chart_data(topic):
    weak = [c for c in chart_data(topic) if c[0] == "h"]
    assert len(weak) == 1
    assert weak[0][2] == {"Sample Set": 33.33, "Topic A": 66.67, "Topic B": 100.0}  # topics with 3+ questions


def test_topic_mastery_stacked_chart_data(topic):
    stacked = {name: pairs for orient, name, pairs in chart_data(topic) if orient == "v"}
    assert stacked["Correct"] == {"Geography": 1, "Sample Set": 1, "Maths": 0, "LangGraph": 0,
                                  "Topic A": 2, "Topic B": 3}
    assert stacked["Wrong"] == {"Geography": 0, "Sample Set": 2, "Maths": 2, "LangGraph": 0,
                                "Topic A": 1, "Topic B": 0}
    assert stacked["Unattempted"] == {"Geography": 0, "Sample Set": 0, "Maths": 0, "LangGraph": 1,
                                      "Topic A": 0, "Topic B": 0}


def test_topic_two_charts_present(topic):
    assert len(list(topic.get("plotly_chart"))) == 2


def test_topic_detailed_dataframe_rows(topic):
    frames = [f.value for f in topic.get("arrow_data_frame")]
    detail = [f for f in frames if "Accuracy" in f.columns][0]
    assert list(detail.columns) == ["Topic", "Total", "Correct", "Wrong", "Unattempted", "Accuracy"]
    rows = {r["Topic"]: (r["Total"], r["Correct"], r["Wrong"], r["Unattempted"], round(r["Accuracy"], 1))
            for r in detail.to_dict("records")}
    assert rows == {"Geography": (1, 1, 0, 0, 100.0), "Sample Set": (3, 1, 2, 0, 33.3),
                    "Maths": (2, 0, 2, 0, 0.0), "LangGraph": (1, 0, 0, 1, 0.0),
                    "Topic A": (3, 2, 1, 0, 66.7), "Topic B": (3, 3, 0, 0, 100.0)}


def test_topic_tag_mapping_table(topic):
    frames = [f.value for f in topic.get("arrow_data_frame")]
    tags = [f for f in frames if "Mapped Topic" in f.columns][0]
    assert dict(zip(tags["Tag"], tags["Mapped Topic"])) == {
        "geography": "Geography", "sample": "Sample Set", "math": "Maths", "calculus": "Maths",
        "langgraph": "LangGraph", "state_reducers": "LangGraph", "t_a": "Topic A", "t_b": "Topic B"}


def test_topic_tag_mapping_lives_in_an_expander(topic):
    assert by_label(list(topic.get("expander")) + list(topic.get("status")), "Tag to Topic")


def test_topic_drill_topic_options_sorted_weakest_first(topic):
    sel = by_label(topic.selectbox, "Select Topic to Drill")[0]
    assert sel.options == ["Maths", "LangGraph", "Sample Set", "Topic A", "Geography", "Topic B"]


def test_topic_drill_start_builds_the_same_session(topic):
    by_label(topic.selectbox, "Select Topic to Drill")[0].select("Sample Set").run()
    by_label(topic.button, "Start Targeted Drill")[0].click().run()
    # st.switch_page ends the run; the session is what the drill page reads
    ids = sorted(q["id"] for q in topic.session_state.drill_questions)
    assert ids == ["sample_q2", "sample_q2", "sample_q3", "sample_q3"]   # wrong questions, double loop
    assert topic.session_state.drill_index == 0
    assert topic.session_state.drill_answers == {}
    assert topic.session_state.drill_submitted == {}


def test_topic_drill_options_respected(topic):
    by_label(topic.selectbox, "Select Topic to Drill")[0].select("Sample Set").run()
    by_label(topic.checkbox, "Double-Loop")[0].uncheck().run()
    by_label(topic.button, "Start Targeted Drill")[0].click().run()
    assert sorted(q["id"] for q in topic.session_state.drill_questions) == ["sample_q2", "sample_q3"]


def test_topic_drill_no_matching_questions_warns(topic):
    by_label(topic.selectbox, "Select Topic to Drill")[0].select("Topic B").run()   # all correct
    by_label(topic.button, "Start Targeted Drill")[0].click().run()
    assert any("No questions match" in w.value for w in topic.warning)
    assert "drill_questions" not in topic.session_state


def test_topic_generate_button_path(spread, app, monkeypatch):
    """When loading the analysis RAISES (e.g. unreadable cache) the page offers
    'Generate Analysis for <suite>', which runs the analyzer with force_refresh=True.
    (The case where the load succeeds but returns an empty result is covered by
    test_topic_generate_button_after_empty_cache_load.)"""
    from utils.topic_analyzer import TopicAnalyzer
    real = TopicAnalyzer.get_analysis_for_suite
    calls = []

    def fake(self, suite, force_refresh=False):
        calls.append(force_refresh)
        if not force_refresh:
            raise RuntimeError("cache unreadable")
        return real(self, suite, force_refresh=True)

    monkeypatch.setattr(TopicAnalyzer, "get_analysis_for_suite", fake)
    at = app("pages/Topic_Analysis.py").run()
    select_suite(at)
    assert any("Failed to load cache" in e.value for e in at.error)
    assert not list(at.get("plotly_chart"))
    by_label(at.button, "Generate Analysis for sample")[0].click().run()
    assert not at.exception
    assert calls == [False, False, True]
    assert len(list(at.get("plotly_chart"))) == 2


def test_topic_generate_button_after_empty_cache_load(spread, app, monkeypatch):
    """Batch 9.4: the cache loads fine but holds nothing. The page offers 'Generate Analysis for <suite>';
    clicking it must run the analysis (force_refresh=True) and show the charts. It used to do nothing:
    the empty result was stored under the page's session key, so the next run skipped the whole block."""
    from utils.topic_analyzer import TopicAnalyzer
    real = TopicAnalyzer.get_analysis_for_suite
    calls = []

    def fake(self, suite, force_refresh=False):
        calls.append(force_refresh)
        if not force_refresh:
            return {}                                   # loaded fine, nothing cached
        return real(self, suite, force_refresh=True)

    monkeypatch.setattr(TopicAnalyzer, "get_analysis_for_suite", fake)
    at = app("pages/Topic_Analysis.py").run()
    select_suite(at)
    assert not list(at.get("plotly_chart"))
    assert any("No analysis found" in i.value for i in at.info)
    by_label(at.button, "Generate Analysis for sample")[0].click().run()
    assert not at.exception
    assert calls[-1] is True                            # the analysis really ran
    assert len(list(at.get("plotly_chart"))) == 2


def test_topic_refresh_button_reruns_the_analysis_even_with_a_cache(spread, app, monkeypatch):
    """Batch 9.4 (same cause): with a good cached analysis on screen, 'Refresh analysis' must re-run it
    (force_refresh=True). It did nothing, because the cached result made the page skip the whole block."""
    from utils.topic_analyzer import TopicAnalyzer
    real = TopicAnalyzer.get_analysis_for_suite
    calls = []

    def fake(self, suite, force_refresh=False):
        calls.append(force_refresh)
        return real(self, suite, force_refresh=force_refresh)

    monkeypatch.setattr(TopicAnalyzer, "get_analysis_for_suite", fake)
    at = app("pages/Topic_Analysis.py").run()
    select_suite(at)
    assert len(list(at.get("plotly_chart"))) == 2            # analysis is showing
    before = list(calls)
    by_label(at.button, "Refresh analysis")[0].click().run()
    assert not at.exception
    assert calls[len(before):].count(True) >= 1, calls


def test_topic_unknown_suite_filter_folder(topic):
    folder = by_label(topic.selectbox, "Filter by Folder")[0]
    assert folder.options == ["All", "sample"]


# ================================================= Similar_Questions_Management
@pytest.fixture
def groups(workspace):
    q1, q2, q3 = file_manager.load_questions("questions", "sample")

    def twin(q, new_id):
        d = dict(q)
        d["id"] = new_id
        d["source_file"] = "other/copy.json"
        return d

    return [[q1, twin(q1, "dup_q1")], [q2, twin(q2, "dup_q2"), twin(q2, "dup_q2b")]]


@pytest.fixture
def similar(groups, app, monkeypatch):
    from utils import similarity
    monkeypatch.setattr(similarity, "find_duplicates", lambda suite=None: [list(g) for g in groups])
    at = app("pages/Similar_Questions_Management.py").run()
    assert not at.exception
    return at


def test_similar_shows_both_groups_with_checkboxes(similar):
    keys = {c.key for c in similar.checkbox}
    assert {"select_0_0_sample_q1", "select_0_1_dup_q1",
            "select_1_0_sample_q2", "select_1_1_dup_q2", "select_1_2_dup_q2b"} == keys
    assert any("Showing **2** duplicate clusters" in m.value for m in similar.get("markdown"))


def test_similar_suite_select(similar):
    sel = by_label(similar.selectbox, "Select Exam Suite")[0]
    assert sel.options == ["All", "sample"]


def test_similar_archive_selected_archives_exactly_those(similar, workspace):
    similar.checkbox(key="select_0_1_dup_q1").check()
    similar.checkbox(key="select_1_0_sample_q2").check().run()
    by_label(similar.button, "Archive Selected")[0].click().run()
    assert not similar.exception
    reg = json.loads((workspace / "archives" / "registry.json").read_text(encoding="utf-8"))
    assert set(reg) == {"dup_q1", "sample_q2"}


def test_similar_archive_selected_with_nothing_selected_warns(similar, workspace):
    by_label(similar.button, "Archive Selected")[0].click().run()
    assert any("No questions selected" in w.value for w in similar.warning)
    assert json.loads((workspace / "archives" / "registry.json").read_text(encoding="utf-8")) == {}


def test_similar_single_instance_archive_button(similar, workspace):
    similar.button(key="archive_1_2_dup_q2b").click().run()
    assert archive_manager.is_archived("dup_q2b")
    assert not archive_manager.is_archived("dup_q2")


def test_similar_clean_bank_message(workspace, app, monkeypatch):
    from utils import similarity
    monkeypatch.setattr(similarity, "find_duplicates", lambda suite=None: [])
    at = app("pages/Similar_Questions_Management.py").run()
    assert any("No exact duplicates" in s.value for s in at.success)


@pytest.fixture
def contextual(groups, app, monkeypatch):
    from utils import similarity
    calls = {}

    def fake_scan(questions, llm, threshold=0.85, progress_callback=None):
        calls["threshold"], calls["n"] = threshold, len(questions)
        if progress_callback:
            progress_callback(1.0, "done")
        return [list(g) for g in groups]

    monkeypatch.setattr(similarity, "find_contextual_duplicates", fake_scan)
    at = app("pages/Similar_Questions_Management.py").run()
    by_label(at.radio, "Method")[0].set_value("Contextual Match (LLM)").run()
    assert not at.exception
    at.calls = calls
    return at


def test_contextual_mode_shows_threshold_slider(contextual):
    sl = by_label(contextual.slider, "Similarity Threshold")[0]
    assert sl.value == 0.85 and sl.min == 0.70 and sl.max == 0.99


def test_contextual_before_scan_waits_for_click(contextual):
    assert not contextual.checkbox
    assert any("Start" in i.value for i in contextual.info)


def test_contextual_scan_shows_groups_and_clears_stop_button(contextual, workspace):
    contextual.slider[0].set_value(0.9).run()
    by_label(contextual.button, "Start Scan")[0].click().run()
    assert not contextual.exception
    assert contextual.calls["threshold"] == 0.9 and contextual.calls["n"] == 3
    assert any("Scan Complete! Found 2 groups" in s.value for s in contextual.success)
    assert {"select_0_0_sample_q1", "select_1_2_dup_q2b"} <= {c.key for c in contextual.checkbox}
    assert "stop_scan_btn" not in [b.key for b in contextual.button]     # placeholder cleared after the scan
    assert contextual.session_state.cancel_scan is False
    cache = json.loads((workspace / "user_data" / "contextual_duplicates.json").read_text(encoding="utf-8"))
    assert len(cache["All"]["groups"]) == 2


def test_contextual_archive_selected_prunes_groups(contextual, workspace):
    by_label(contextual.button, "Start Scan")[0].click().run()
    contextual.checkbox(key="select_0_1_dup_q1").check().run()
    by_label(contextual.button, "Archive Selected")[0].click().run()
    assert archive_manager.is_archived("dup_q1")
    # group 0 had two members: one left is no longer a duplicate -> pruned from the stored results
    assert len(contextual.session_state.contextual_results) == 1
