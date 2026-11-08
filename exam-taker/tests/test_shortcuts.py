"""Batch 9.3: keyboard shortcuts (utils/shortcuts.py). Unit tests for the key map + wiring on the 5 exam pages.
The browser behaviour itself is tested in tests/e2e/test_keyboard_flow.py (Playwright, skipped if missing)."""
import json
import re

import pytest

from tests.test_page_chrome import act_drill  # noqa: F401  (keeps the drill seeding identical)
from tests.test_review_flow import seeded  # noqa: F401
from utils import shortcuts, ui_helpers

pytestmark = pytest.mark.ui

EXAM_PAGES = ["app.py", "pages/Practice_Incorrect.py", "pages/Practice_Bookmarks.py",
              "pages/Targeted_Drill.py", "pages/Regressive_Practice.py"]
OTHER_PAGES = ["pages/Bookmarks.py", "pages/Wrong_Answers.py", "pages/Search_Questions.py",
               "pages/Progress_Dashboard.py", "pages/Topic_Analysis.py", "pages/Notes_Review.py",
               "pages/Archived_Questions.py", "pages/Similar_Questions_Management.py"]


# ------------------------------------------------------------------ the key map
@pytest.mark.parametrize("key,idx", [("1", 0), ("2", 1), ("3", 2), ("4", 3), ("a", 0), ("b", 1), ("c", 2),
                                     ("d", 3), ("A", 0), ("D", 3)])
def test_digits_and_letters_select_the_option(key, idx):
    assert shortcuts.action_for(key) == ("option", idx)


def test_enter_submits():
    assert shortcuts.action_for("Enter") == ("submit", None)


@pytest.mark.parametrize("key", ["ArrowRight", "n", "N"])
def test_next_keys(key):
    assert shortcuts.action_for(key) == ("next", None)


@pytest.mark.parametrize("key", ["ArrowLeft", "p", "P"])
def test_previous_keys(key):
    assert shortcuts.action_for(key) == ("prev", None)


def test_bookmark_is_shift_b_because_plain_b_is_the_answer_letter():
    assert shortcuts.action_for("B", shift=True) == ("bookmark", None)
    assert shortcuts.action_for("b") == ("option", 1)
    assert shortcuts.action_for("B") == ("option", 1)          # caps lock, no shift


@pytest.mark.parametrize("key", ["x", "z", "Escape", "Tab", " ", "0", "ArrowUp", "F5", ""])
def test_other_keys_are_ignored(key):
    assert shortcuts.action_for(key) is None


def test_shift_never_selects_an_answer():
    assert shortcuts.action_for("A", shift=True) is None
    assert shortcuts.action_for("1", shift=True) is None


def test_every_option_key_maps_to_a_distinct_index():
    idx = {}
    for k in shortcuts.OPTION_KEYS:
        idx[k] = shortcuts.action_for(k)[1]
    assert sorted(idx.values()) == list(range(len(shortcuts.OPTION_KEYS)))
    assert "n" not in shortcuts.OPTION_LETTERS and "p" not in shortcuts.OPTION_LETTERS


# ------------------------------------------------------------------ the generated script
def test_script_embeds_the_map_and_selectors():
    js = shortcuts.script()
    assert json.loads(re.search(r"KEY_MAP = (\{.*?\}), SEL", js, re.S).group(1))["Enter"] == ["submit", None]
    assert '"st-key-answers' not in js and ".st-key-answers" in js
    for sel in shortcuts.SELECTORS["submit"] + shortcuts.SELECTORS["next"] + shortcuts.SELECTORS["prev"]:
        assert json.dumps(sel)[1:-1] in js


def test_script_ignores_typing_modifiers_and_replaces_its_old_handler():
    js = shortcuts.script()
    for needle in ("textarea", "select", "isContentEditable", "ql-editor", "ctrlKey", "altKey", "metaKey",
                   "removeEventListener", "preventDefault"):
        assert needle in js, needle


def test_script_waits_for_streamlit_instead_of_clicking_stale_elements():
    """Found by the e2e test: a key pressed right after a rerun hit a stale/not-yet-drawn element and was lost."""
    js = shortcuts.script()
    for needle in ("stStatusWidget", 'data-stale', "MAX_WAIT_MS", "queue.push", "setTimeout(drain"):
        assert needle in js, needle


def test_no_new_dependency():
    import pathlib
    src = pathlib.Path(shortcuts.__file__).read_text(encoding="utf-8")
    imports = re.findall(r"^(?:import|from)\s+(\S+)", src, re.M)
    assert set(imports) <= {"json", "typing", "streamlit.components.v1"}


# ------------------------------------------------------------------ wiring
def build(app, ws, path):
    at = app(path)
    if path == "pages/Targeted_Drill.py":
        at.session_state["drill_questions"] = json.loads(
            (ws / "questions/sample/sample.json").read_text(encoding="utf-8"))
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    if path == "pages/Regressive_Practice.py":
        at.button(key="reg_start").click().run()
    return at


def shortcut_frames(at):
    return [f for f in at.get("iframe") if "etp-shortcuts-script" in (f.proto.srcdoc or "")]


@pytest.mark.parametrize("path", EXAM_PAGES)
def test_exam_pages_install_the_shortcuts(path, seeded, app):
    at = build(app, seeded, path)
    frames = shortcut_frames(at)
    assert len(frames) == 1, path
    assert frames[0].proto.height == 0


@pytest.mark.parametrize("path", OTHER_PAGES)
def test_other_pages_do_not(path, seeded, app):
    at = app(path).run()
    assert not shortcut_frames(at), path


def test_regressive_before_a_session_has_no_shortcuts(seeded, app):
    at = app("pages/Regressive_Practice.py").run()
    assert not shortcut_frames(at)


# ------------------------------------------------------------------ key hints (CSS, labels untouched)
def css_bodies(selector_part):
    return [m.group(2) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", ui_helpers._GLOBAL_CSS)
            if selector_part in m.group(1)]


def test_etp_kbd_class_exists_and_uses_tokens():
    body = " ".join(css_bodies(".etp-kbd"))
    assert "font-family" in body and "border" in body and "--etp-" in body


@pytest.mark.parametrize("hook,word", [("nav_submit", "\\21B5"), ("drill_submit_", "\\21B5"),
                                       ("nav_next", "N"), ("drill_next_", "N"), ("reg_next", "N"),
                                       ("nav_prev", "P")])
def test_hint_chips_on_the_buttons(hook, word):
    rules = [(m.group(1), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", ui_helpers._GLOBAL_CSS)
             if hook in m.group(1) and "::after" in m.group(1)]
    assert rules, hook
    assert any(f'content: "{word}"' in body for _, body in rules), (hook, rules)


@pytest.mark.parametrize("hook", ["nav_submit", "drill_submit_", "nav_next", "drill_next_", "reg_next", "nav_prev"])
def test_buttons_with_a_hint_never_wrap_their_label(hook):
    """Seen in the v1.1 screenshots: 'Previous' + chip wrapped to 'Previou / s' in the narrow column."""
    nowrap = [sel for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", ui_helpers._GLOBAL_CSS)
              for sel in [m.group(1)] if "white-space: nowrap" in m.group(2) and hook in sel
              and "::after" not in sel]
    assert nowrap, hook


def test_the_zero_height_script_frame_is_hidden():
    assert any("iframe" in sel for sel in re.findall(r"([^{}]+)\{", ui_helpers._GLOBAL_CSS)
               if "display: none" in " ".join(css_bodies(sel.strip())))


def test_button_labels_are_unchanged_by_the_hints(seeded, app):
    at = build(app, seeded, "app.py")
    assert [b.label for b in at.button if b.key and b.key.startswith("btn_")] == ["Submit answer"]
