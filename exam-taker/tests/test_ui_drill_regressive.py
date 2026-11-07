"""Batch 4.3: Targeted_Drill and Regressive_Practice restyled in place.

Buttons are found by KEY (added in 4.3 step 8, no behaviour change).
Batch 0 labels that must survive: "Submit Answer" (Regressive), "Start New Session",
"Next Question" (both pages) - see tests/test_exam_flow.py.
"""
import json
import re

import pytest

from utils import ui_helpers

pytestmark = pytest.mark.ui

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿←-⇿️]")


# ------------------------------------------------------------------ helpers
def walk(node):
    yield node
    for child in getattr(node, "children", {}).values():
        yield from walk(child)


def block_key(block):
    ident = getattr(getattr(block, "proto", None), "id", "") or ""
    return ident.split("-", 2)[2] if ident.startswith("$$ID-") else None


def keyed_blocks(at):
    return {block_key(b): b for b in walk(at.main) if block_key(b)}


def md_values(at):
    return [m.value for m in at.get("markdown") if not m.value.lstrip().startswith("<style>")]


def all_md(at):
    return "\n".join(md_values(at))


def visible_strings(at):
    out = []
    for kind in ("button", "markdown", "title", "caption", "subheader", "header", "expander",
                 "status", "radio", "checkbox", "info", "success", "warning", "error",
                 "metric", "text_area"):
        for el in at.get(kind):
            for attr in ("label", "value", "body"):
                v = getattr(el, attr, None)
                if isinstance(v, str):
                    out.append(v)
            opts = getattr(el, "options", None)
            if isinstance(opts, (list, tuple)):
                out.extend(o for o in opts if isinstance(o, str))
    return out


def assert_no_emoji(at):
    bad = [s for s in visible_strings(at) if EMOJI.search(s)]
    assert not bad, bad


def iframe_html(at):
    return "\n".join(str(getattr(e.proto, "srcdoc", "")) for e in at.get("iframe"))


def sample_questions(ws):
    return json.loads((ws / "questions/sample/sample.json").read_text(encoding="utf-8"))


def rule_bodies(selector):
    css = ui_helpers._GLOBAL_CSS
    return [m.group(2) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css) if selector in m.group(1)]


# ====================================================================== drill
@pytest.fixture
def drill(workspace, app):
    at = app("pages/Targeted_Drill.py")
    at.session_state["drill_questions"] = sample_questions(workspace)
    at.run()
    assert not at.exception
    return at


def drill_submit(at, letter):
    at.radio(key="drill_radio_sample_q1_0").set_value(letter).run()
    at.button(key="drill_btn_sample_q1_0").click().run()
    assert not at.exception


def test_drill_keys_exist(drill):
    keys = [b.key for b in drill.button]
    assert "drill_exit" in keys
    assert "drill_next_sample_q1_0" in keys
    assert "drill_btn_sample_q1_0" in keys


def test_drill_dashboard_key_in_empty_state(workspace, app):
    at = app("pages/Targeted_Drill.py").run()
    assert "drill_dashboard" in [b.key for b in at.button]
    assert_no_emoji(at)


def test_drill_finish_key_on_last_question(workspace, app):
    at = app("pages/Targeted_Drill.py")
    at.session_state["drill_questions"] = sample_questions(workspace)[:1]
    at.run()
    assert "drill_finish" in [b.key for b in at.button]
    assert_no_emoji(at)
    assert any("Drill complete" in s.value for s in at.success)


def test_drill_no_emoji(drill):
    assert_no_emoji(drill)
    drill_submit(drill, "A")
    assert_no_emoji(drill)


def test_drill_title_and_badges(drill):
    assert [t.value for t in drill.title] == ["Targeted drill"]
    md = all_md(drill)
    assert "etp-badge--easy" in md and "geography" in md


def test_drill_banner_and_rows_after_submit(drill):
    drill_submit(drill, "A")
    md = all_md(drill)
    assert "etp-banner--danger" in md and "Your pick" in md and "Missed" in md
    keys = set(keyed_blocks(drill))
    assert any(k.startswith("opt_wrong_") for k in keys)
    assert any(k.startswith("opt_missed_") for k in keys)


def test_drill_correct_banner(drill):
    drill_submit(drill, "B")
    assert "etp-banner--success" in all_md(drill)


def test_drill_explanation_container_markdown(drill):
    drill_submit(drill, "B")
    blocks = keyed_blocks(drill)
    key = next(k for k in blocks if k.startswith("explain_"))
    assert "Paris is the capital of France" in " ".join(m.value for m in blocks[key].markdown)
    assert "Paris is the capital" not in iframe_html(drill)


def test_drill_notes_expander_keeps_keys(drill):
    drill_submit(drill, "B")
    found = [e for e in list(drill.get("expander")) + list(drill.get("status"))
             if e.label == "My notes & diagram"]
    assert found
    assert "drill_diagram_sample_q1" in [t.key for t in found[0].text_area]
    assert "drill_save_notes_sample_q1" in [b.key for b in found[0].button]


def test_drill_stem_is_markdown(drill):
    assert any("capital of France" in v for v in md_values(drill))
    assert "capital of France" not in iframe_html(drill)


def test_drill_next_primary_exit_not_primary(drill):
    assert drill.button(key="drill_next_sample_q1_0").proto.type == "primary"
    assert drill.button(key="drill_exit").proto.type != "primary"


def test_drill_submit_in_keyed_container(drill):
    blocks = keyed_blocks(drill)
    assert "drill_submit_sample_q1_0" in blocks
    assert "drill_btn_sample_q1_0" in [b.key for b in blocks["drill_submit_sample_q1_0"].button]
    assert drill.button(key="drill_btn_sample_q1_0").proto.type == "primary"


def test_exit_drill_css_is_danger_outline():
    body = " ".join(rule_bodies(".st-key-drill_exit button"))
    assert "--etp-danger" in body and "transparent" in body


# ================================================================ regressive
@pytest.fixture
def reg(workspace, app):
    at = app("pages/Regressive_Practice.py").run()
    at.button(key="reg_start").click().run()
    assert not at.exception
    at.session_state.regressive_current_q = sample_questions(workspace)[0]  # deterministic
    at.run()
    return at


def reg_submit(at, letter):
    at.radio(key="opt_sample_q1_0").set_value(letter).run()
    at.button(key="reg_submit_sample_q1_0").click().run()
    assert not at.exception


def test_regressive_keys_exist(reg):
    keys = [b.key for b in reg.button]
    assert {"reg_start", "reg_end", "reg_submit_sample_q1_0"} <= set(keys)


def test_regressive_labels_kept_for_batch0(reg):
    assert reg.button(key="reg_start").label.endswith("Start New Session")
    assert reg.button(key="reg_submit_sample_q1_0").label == "Submit Answer"


def test_regressive_no_emoji_everywhere(workspace, app):
    at = app("pages/Regressive_Practice.py").run()
    assert_no_emoji(at)  # idle screen
    at.button(key="reg_start").click().run()
    at.session_state.regressive_current_q = sample_questions(workspace)[0]
    at.run()
    assert_no_emoji(at)  # started
    at.radio(key="opt_sample_q1_0").set_value("A").run()
    at.button(key="reg_submit_sample_q1_0").click().run()
    assert_no_emoji(at)  # after wrong submit


def test_regressive_stat_tiles_above_card(reg):
    labels = [m.label for m in reg.metric]
    assert labels == ["In queue", "Mastered", "Streak"]
    assert [m.value for m in reg.metric][:2] == ["3", "0"]
    assert "status-metric" not in all_md(reg)  # old hard-coded HTML tiles are gone


def test_regressive_badges(reg):
    md = all_md(reg)
    assert "etp-badge--easy" in md and "geography" in md


def test_regressive_stem_markdown(reg):
    assert any("capital of France" in v for v in md_values(reg))
    assert "capital of France" not in iframe_html(reg)


def test_regressive_start_primary_end_not(reg):
    assert reg.button(key="reg_end").proto.type != "primary"
    assert reg.button(key="reg_submit_sample_q1_0").proto.type == "primary"


def test_regressive_correct_banner_and_explanation(reg):
    reg_submit(reg, "B")
    md = all_md(reg)
    assert "etp-banner--success" in md and "Streak 1 of 2" in md
    blocks = keyed_blocks(reg)
    assert "explain_sample_q1" in blocks
    assert "Paris is the capital of France" in " ".join(m.value for m in blocks["explain_sample_q1"].markdown)
    assert "View Explanation" not in [e.label for e in reg.expander]
    assert reg.button(key="reg_next").proto.type == "primary"


def test_regressive_wrong_banner_shows_right_answer(reg):
    reg_submit(reg, "A")
    md = all_md(reg)
    assert "etp-banner--danger" in md and "The right answer is B" in md and "Streak reset to 0" in md
    keys = set(keyed_blocks(reg))
    assert any(k.startswith("opt_wrong_sample_q1") for k in keys)   # the pick (A)
    assert any(k.startswith("opt_missed_sample_q1") for k in keys)  # the right answer (B)


def test_regressive_complete_screen(reg):
    reg.session_state.regressive_queue = []
    reg.run()
    assert "reg_restart" in [b.key for b in reg.button]
    assert_no_emoji(reg)


def test_end_session_css_is_danger_outline():
    body = " ".join(rule_bodies(".st-key-reg_end button"))
    assert "--etp-danger" in body and "transparent" in body


def test_primary_css_for_reg_start_and_next():
    for sel in (".st-key-reg_start button", ".st-key-reg_next button", '[class*="st-key-drill_next_"] button'):
        assert any("--etp-fill" in b for b in rule_bodies(sel)), sel
