"""Batch 10a: the bookmark control in the exam card shows coloured chips with filled dots (design: BookmarkChip).
Same colour directives as the Bookmarks page pills; the stored value is still the BOOKMARK_COLORS key."""
import json
from pathlib import Path
import re

import pytest

from tests.test_ui_practice import EMOJI
from utils import bookmark_manager, ui_components, ui_helpers

pytestmark = pytest.mark.ui

COLOURS = list(bookmark_manager.BOOKMARK_COLORS)                      # storage order
SHORT = ["Important", "Review later", "Interesting", "Hard", "Solved"]
DIRECTIVES = ["red", "orange", "blue", "violet", "green"]
EXPECTED = [f":{d}[●] {s}" for d, s in zip(DIRECTIVES, SHORT)]

# (page, selector key, save key, remove key, how to get the question id/suffix)
PAGES = {
    "exam": ("app.py", "bm_sel_sample_q1", "bm_btn_sample_q1", "bm_rm_sample_q1"),
    "incorrect": ("pages/Practice_Incorrect.py", "bm_sel_sample_q1", "bm_btn_sample_q1", "bm_rm_sample_q1"),
    "bookmarks": ("pages/Practice_Bookmarks.py", "bm_sel_sample_q1", "bm_btn_sample_q1", "bm_rm_sample_q1"),
    "drill": ("pages/Targeted_Drill.py", "drill_bm_sel_sample_q1_0", "drill_bm_btn_sample_q1_0",
              "drill_bm_rm_sample_q1_0"),
}


def questions(ws):
    return json.loads((ws / "questions/sample/sample.json").read_text(encoding="utf-8"))


def registry(ws):
    return json.loads((ws / "bookmarks" / "registry.json").read_text(encoding="utf-8"))


def open_page(app, ws, name, bookmarked=None):
    path = PAGES[name][0]
    if bookmarked or name == "bookmarks":
        bookmark_manager.save_bookmark(questions(ws)[0], bookmarked or COLOURS[0])
    at = app(path)
    if name == "drill":
        at.session_state["drill_questions"] = questions(ws)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def group(at, key):
    found = [g for g in at.get("button_group") if g.key == key]
    assert len(found) == 1, (key, [g.key for g in at.get("button_group")])
    return found[0]


def _walk(block, out):
    for child in getattr(block, "children", {}).values():
        out.append(child)
        _walk(child, out)


def popover_labels(at):
    blocks = []
    _walk(at.main, blocks)
    return [b.proto.popover.label for b in blocks if b.type == "popover"]


def caption_texts(at):
    return [c.value for c in at.caption]


@pytest.fixture(params=list(PAGES))
def name(request):
    return request.param


# ------------------------------------------------------------------ the control
def test_colour_picker_is_a_single_select_pills_group(name, workspace, app):
    at = open_page(app, workspace, name)
    g = group(at, PAGES[name][1])
    assert g.proto.click_mode == 0                                  # SINGLE
    assert not list(at.selectbox) or PAGES[name][1] not in [s.key for s in at.selectbox]


def test_five_options_in_bookmark_colours_order_with_dot_and_short_name(name, workspace, app):
    at = open_page(app, workspace, name)
    g = group(at, PAGES[name][1])
    assert [o.content for o in g.proto.options] == EXPECTED
    assert [o.content for o in g.proto.options] == [ui_components.bookmark_pill_label(c) for c in COLOURS]


def test_pill_labels_use_the_same_directives_as_the_bookmarks_page(workspace, app):
    src = (Path(__file__).parent.parent / "pages" / "Bookmarks.py").read_text(encoding="utf-8")
    page_map = dict(re.findall(r'"([A-Za-z ]+ \([A-Za-z]+\))": "([a-z]+)"', src))
    assert page_map == ui_components.BOOKMARK_DIRECTIVE


def test_labels_have_no_emoji(name, workspace, app):
    at = open_page(app, workspace, name, bookmarked=COLOURS[1])
    labels = [o.content for o in group(at, PAGES[name][1]).proto.options] + popover_labels(at) + caption_texts(at)
    assert not [s for s in labels if EMOJI.search(s)], labels


def test_default_is_the_first_option_when_not_bookmarked(name, workspace, app):
    at = open_page(app, workspace, name)
    assert group(at, PAGES[name][1]).value == [COLOURS[0]]


@pytest.mark.parametrize("colour", COLOURS)
def test_default_is_the_current_bookmark(name, colour, workspace, app):
    if name == "bookmarks":
        pytest.skip("Practice bookmarks seeds its own bookmark")
    at = open_page(app, workspace, name, bookmarked=colour)
    assert group(at, PAGES[name][1]).value == [colour]


# ------------------------------------------------------------------ saving / removing (stored value unchanged)
@pytest.mark.parametrize("colour", COLOURS)
def test_save_stores_the_chosen_colour_key(name, colour, workspace, app):
    at = open_page(app, workspace, name)
    _, sel, save, _ = PAGES[name][0], *PAGES[name][1:]
    group(at, sel).set_value([colour]).run()   # AppTest wants a list, even for single select
    at.button(key=save).click().run()
    assert not at.exception
    assert registry(workspace)["sample_q1"]["color"] == colour


def test_remove_is_unchanged(name, workspace, app):
    at = open_page(app, workspace, name, bookmarked=COLOURS[3])
    at.button(key=PAGES[name][3]).click().run()
    assert "sample_q1" not in registry(workspace)


# ------------------------------------------------------------------ popover label and status line
def test_popover_label_when_not_bookmarked(name, workspace, app):
    if name == "bookmarks":
        pytest.skip("Practice bookmarks only shows bookmarked questions")
    at = open_page(app, workspace, name)
    assert "Bookmark" in popover_labels(at)
    assert not [c for c in caption_texts(at) if "Bookmarked as" in c]


@pytest.mark.parametrize("i", range(5))
def test_popover_label_when_bookmarked_is_dot_and_short_name(name, i, workspace, app):
    if name == "bookmarks":
        pytest.skip("Practice bookmarks seeds its own bookmark")
    at = open_page(app, workspace, name, bookmarked=COLOURS[i])
    assert EXPECTED[i] in popover_labels(at), popover_labels(at)


def test_status_line_inside_the_popover(name, workspace, app):
    at = open_page(app, workspace, name, bookmarked=COLOURS[0])
    assert any(c == f"Bookmarked as {EXPECTED[0]}" for c in caption_texts(at)), caption_texts(at)


# ------------------------------------------------------------------ pill CSS
def css_rules(part):
    return [m.group(2) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", ui_helpers._GLOBAL_CSS)
            if part in m.group(1)]


def test_selected_pill_is_visibly_selected():
    body = " ".join(css_rules('stBaseButton-pillsActive'))
    assert "border-color" in body and "background-color" in body


@pytest.mark.parametrize("hook", ["st-key-bm_sel_", "st-key-drill_bm_sel_"])
@pytest.mark.parametrize("n,tok", [(1, "red"), (2, "orange"), (3, "blue"), (4, "purple"), (5, "green")])
def test_selected_bookmark_pill_edge_uses_its_own_bm_colour(hook, n, tok):
    """The pills sit in the order of BOOKMARK_COLORS, so the n-th active pill takes the n-th bm_* token."""
    rules = [(m.group(1), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", ui_helpers._GLOBAL_CSS)
             if hook in m.group(1) and "pillsActive" in m.group(1) and f"nth-child({n})" in m.group(1)]
    assert rules, (hook, n)
    assert any(f"border-color: var(--etp-bm-{tok})" in body for _, body in rules), rules


# ================================================================== Batch 10a.1: the dots have the EXACT spec colours
SPEC_HEX = ["#d48a80", "#d6a464", "#8ea9cc", "#b4a0cc", "#8cc29f"]       # Important .. Solved (design system)
DIRECTIVE_KEYS = ["red", "orange", "blue", "violet", "green"]


def rgb(hex_):
    return "rgb(%d, %d, %d)" % tuple(int(hex_[i:i + 2], 16) for i in (1, 3, 5))


SPEC_RGB = [rgb(h) for h in SPEC_HEX]


def test_theme_config_has_the_spec_directive_colours():
    """st.pills / :red[...] take their colour from <name>TextColor (Streamlit lightens <name>Color for text)."""
    import tomllib
    theme = tomllib.loads((Path(__file__).parent.parent / ".streamlit" / "config.toml")
                          .read_text(encoding="utf-8"))["theme"]
    for key, hex_ in zip(DIRECTIVE_KEYS, SPEC_HEX):
        assert theme[f"{key}TextColor"].lower() == hex_, key
        assert theme[f"{key}Color"].lower() == hex_, key


def test_theme_tokens_equal_the_spec():
    t = ui_helpers.TOKENS
    assert [t["bm_red"], t["bm_orange"], t["bm_blue"], t["bm_purple"], t["bm_green"]] == SPEC_HEX


# ---------------------------------------------------------------- real browser (skipped without Playwright/Chromium)
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

APP_DIR = Path(__file__).resolve().parent.parent
POPOVER_PILLS = '[class*="st-key-bm_sel_"] [data-baseweb="button-group"] > button, ' \
                '[class*="st-key-drill_bm_sel_"] [data-baseweb="button-group"] > button'
TRIGGER = '.st-key-qcard [data-testid="stPopover"] > div > button, .st-key-qcard [data-testid="stPopover"] button'
DOT_JS = """(els) => els.map(b => {
  const s = b.querySelector('.stMarkdownColoredText');
  if (s) return getComputedStyle(s).color;
  return getComputedStyle(b, '::before').backgroundColor;
})"""
DRILL_ENTRY = """import json, sys
from pathlib import Path
sys.path.insert(0, r"{app}")
import streamlit as st
if "drill_questions" not in st.session_state:
    st.session_state.drill_questions = json.loads(Path("questions/sample/sample.json").read_text(encoding="utf-8"))
exec(compile(open(r"{page}", encoding="utf-8").read(), r"{page}", "exec"))
"""


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start(script, work):
    port = _free_port()
    proc = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(script), "--server.headless", "true",
                             "--server.port", str(port), "--browser.gatherUsageStats", "false"],
                            cwd=work, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://localhost:{port}"
    for _ in range(150):
        try:
            urllib.request.urlopen(url + "/_stcore/health", timeout=2)
            return proc, url
        except Exception:
            time.sleep(0.4)
    proc.terminate()
    pytest.skip("streamlit did not start in time")


@pytest.fixture(scope="module")
def apps(tmp_path_factory):
    pytest.importorskip("playwright.sync_api")
    work = tmp_path_factory.mktemp("etp_bmcolours")
    shutil.copytree(APP_DIR / "tests" / "fixtures" / "workspace", work, dirs_exist_ok=True)
    shutil.copytree(APP_DIR / ".streamlit", work / ".streamlit", dirs_exist_ok=True)
    qs = json.loads((work / "questions/sample/sample.json").read_text(encoding="utf-8"))
    (work / "bookmarks").mkdir(exist_ok=True)
    (work / "bookmarks" / "registry.json").write_text(json.dumps({     # all five colours for the Bookmarks page
        f"bm{i}": {"color": c, "data": dict(qs[0], id=f"bm{i}"), "timestamp": f"2030-01-0{i + 1}T00:00:00"}
        for i, c in enumerate(COLOURS)}), encoding="utf-8")
    (work / "drill_entry.py").write_text(DRILL_ENTRY.format(app=str(APP_DIR), page=str(APP_DIR / "pages" / "Targeted_Drill.py")),
                                         encoding="utf-8")
    main, main_url = _start(APP_DIR / "main.py", work)
    drill, drill_url = _start(work / "drill_entry.py", work)
    try:
        yield {"main": main_url, "drill": drill_url, "work": work}
    finally:
        for p in (main, drill):
            p.terminate()


@pytest.fixture(scope="module")
def browser_page(apps):
    sync = pytest.importorskip("playwright.sync_api")
    with sync.sync_playwright() as pw:
        try:
            b = pw.chromium.launch()
        except Exception as e:
            pytest.skip(f"Chromium not available: {e}")
        pg = b.new_context(viewport={"width": 1440, "height": 1000}).new_page()
        yield pg
        b.close()


def _open(pg, url):
    pg.goto(url)
    pg.wait_for_selector(".st-key-qcard", timeout=60000)
    pg.wait_for_timeout(1500)


def _pill_colours(pg):
    return pg.locator(POPOVER_PILLS).evaluate_all(DOT_JS)


def _save_colour(pg, i):
    pg.locator(POPOVER_PILLS).nth(i).click()
    pg.wait_for_timeout(300)
    pg.get_by_role("button", name="Save bookmark").click()
    pg.wait_for_timeout(1800)                     # rerun; the popover stays open


def _trigger_and_status_colours(pg):
    trig = pg.locator('.st-key-qcard [data-testid="stPopover"] button').first.evaluate_all(DOT_JS)
    status = pg.locator('[data-testid="stPopoverBody"] [data-testid="stCaptionContainer"] .stMarkdownColoredText') \
        .evaluate_all("(els) => els.map(e => getComputedStyle(e).color)")
    return trig, status


@pytest.mark.e2e
@pytest.mark.parametrize("which", ["main", "drill"])
def test_popover_dots_trigger_and_status_have_the_exact_spec_colours(which, apps, browser_page):
    pg = browser_page
    _open(pg, apps[which] + "/")
    pg.locator('.st-key-qcard [data-testid="stPopover"] button').first.click()
    pg.wait_for_timeout(800)
    assert _pill_colours(pg) == SPEC_RGB                                   # the five chips, in order
    for i, spec in enumerate(SPEC_RGB):                                    # the trigger + status line after saving each
        _save_colour(pg, i)
        trig, status = _trigger_and_status_colours(pg)
        assert trig == [spec], (which, i, trig)
        assert status == [spec], (which, i, status)
    pg.get_by_role("button", name="Remove bookmark").click()
    pg.wait_for_timeout(1000)


@pytest.mark.e2e
def test_bookmarks_page_pills_have_the_exact_spec_colours(apps, browser_page):
    pg = browser_page
    from utils import navigation
    url_path = [e["url_path"] for g in navigation.nav_spec().values() for e in g if e["path"].endswith("Bookmarks.py")
                and "Practice" not in e["path"]][0]
    pg.goto(apps["main"] + "/" + url_path)
    pg.wait_for_selector('[data-testid="stButtonGroup"] button', timeout=60000)
    pg.wait_for_timeout(1000)
    assert pg.locator('[data-testid="stButtonGroup"] button').evaluate_all(DOT_JS) == SPEC_RGB


# ================================================================== Batch 10a.1: toast says the short name
@pytest.mark.parametrize("i", range(5))
def test_save_toast_uses_the_short_name(name, i, workspace, app):
    at = open_page(app, workspace, name)
    group(at, PAGES[name][1]).set_value([COLOURS[i]]).run()
    at.button(key=PAGES[name][2]).click().run()
    assert not at.exception
    assert [t.value for t in at.toast] == [f"Bookmarked as {SHORT[i]}."], [t.value for t in at.toast]
