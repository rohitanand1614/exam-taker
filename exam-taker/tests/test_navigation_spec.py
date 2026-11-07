"""Batch 8.1: utils/navigation.nav_spec() - the one place that defines the grouped navigation."""
import re
from pathlib import Path

import pytest

from utils import navigation

pytestmark = pytest.mark.ui

ROOT = Path(__file__).resolve().parent.parent
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿←-⇿️]")

EXPECTED = {
    "Practice": [("app.py", "Exam"), ("pages/Targeted_Drill.py", "Targeted drill"),
                 ("pages/Regressive_Practice.py", "Regressive practice"),
                 ("pages/Practice_Incorrect.py", "Practice incorrect"),
                 ("pages/Practice_Bookmarks.py", "Practice bookmarks")],
    "Review": [("pages/Wrong_Answers.py", "Wrong answers"), ("pages/Bookmarks.py", "Bookmarks"),
               ("pages/Notes_Review.py", "Notes review"), ("pages/Search_Questions.py", "Search")],
    "Insights": [("pages/Progress_Dashboard.py", "Progress"), ("pages/Topic_Analysis.py", "Topic analysis")],
    "Manage": [("pages/Similar_Questions_Management.py", "Similar questions"),
               ("pages/Archived_Questions.py", "Archived")],
}


def entries():
    return [e for group in navigation.nav_spec().values() for e in group]


def test_groups_and_pages_are_as_designed_in_order():
    spec = navigation.nav_spec()
    assert list(spec) == ["Practice", "Review", "Insights", "Manage"]
    got = {g: [(e["path"], e["title"]) for e in items] for g, items in spec.items()}
    assert got == EXPECTED


def test_every_page_file_appears_exactly_once():
    on_disk = sorted(f"pages/{p.name}" for p in (ROOT / "pages").glob("*.py"))
    in_spec = sorted(e["path"] for e in entries() if e["path"] != "app.py")
    assert in_spec == on_disk                       # all 12 pages, none twice, none missing
    assert [e["path"] for e in entries()].count("app.py") == 1


def test_every_path_exists():
    for e in entries():
        assert (ROOT / e["path"]).is_file(), e["path"]


def test_exam_is_the_only_default_page():
    defaults = [e for e in entries() if e.get("default")]
    assert [e["path"] for e in defaults] == ["app.py"]
    assert navigation.nav_spec()["Practice"][0]["path"] == "app.py"


def test_titles_are_plain_sentence_case():
    for e in entries():
        t = e["title"]
        assert not EMOJI.search(t)
        assert t == t[0].upper() + t[1:].lower(), t


def test_icons_are_material_names():
    for e in entries():
        assert re.fullmatch(r":material/[a-z0-9_]+:", e["icon"]), e


@pytest.mark.parametrize("path,icon", [
    ("app.py", ":material/menu_book:"),                      # DESIGN_SYSTEM iconography table
    ("pages/Targeted_Drill.py", ":material/target:"),
    ("pages/Regressive_Practice.py", ":material/sync:"),
    ("pages/Wrong_Answers.py", ":material/cancel:"),
    ("pages/Search_Questions.py", ":material/search:"),
    ("pages/Progress_Dashboard.py", ":material/bar_chart:"),
    ("pages/Topic_Analysis.py", ":material/psychology:"),
    ("pages/Similar_Questions_Management.py", ":material/content_copy:"),
    ("pages/Notes_Review.py", ":material/edit_note:"),
    ("pages/Archived_Questions.py", ":material/archive:"),
    ("pages/Bookmarks.py", ":material/bookmark:"),
    ("pages/Practice_Bookmarks.py", ":material/bookmark_added:"),
])
def test_icons_follow_the_design_system_table(path, icon):
    assert {e["path"]: e["icon"] for e in entries()}[path] == icon


def test_url_paths_are_unique_stable_lowercase_hyphen():
    paths = [e["url_path"] for e in entries()]
    assert len(set(paths)) == len(paths) == 13
    for p in paths:
        assert re.fullmatch(r"[a-z]+(-[a-z]+)*", p), p
    assert {e["path"]: e["url_path"] for e in entries()}["pages/Targeted_Drill.py"] == "targeted-drill"


def test_nav_spec_is_pure_and_fresh_each_call():
    a, b = navigation.nav_spec(), navigation.nav_spec()
    assert a == b and a is not b
    a["Practice"].clear()
    assert navigation.nav_spec()["Practice"]               # callers cannot corrupt the definition


def test_helper_lookup_by_path():
    assert navigation.entry_for("pages/Progress_Dashboard.py")["url_path"] == "progress"
    with pytest.raises(KeyError):
        navigation.entry_for("pages/Nope.py")


# ---------------------------------------------------------------- sidebar CSS (real 1.51 DOM)
def _bodies(selector_part):
    from utils import ui_helpers
    return [m.group(2) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", ui_helpers._GLOBAL_CSS)
            if selector_part in m.group(1)]


def test_group_labels_use_the_label_style_in_ink_faint():
    bodies = _bodies('[data-testid="stNavSectionHeader"]')
    joined = " ".join(bodies)
    assert "uppercase" in joined and "--etp-faint" in joined and "letter-spacing" in joined


def test_nav_items_are_38px_high():
    assert any("min-height: 38px" in b for b in _bodies('[data-testid="stSidebarNavLink"]'))


def test_active_item_is_surface_bold_with_accent_icon():
    active = ' '.join(_bodies('[data-testid="stSidebarNavLink"][aria-current="page"]'))
    assert "--etp-surface" in active and "font-weight" in active
    icon = ' '.join(_bodies('[aria-current="page"] [data-testid="stIconMaterial"]'))
    assert "--etp-accent" in icon


def test_inactive_items_are_muted_and_hover_to_ink():
    css = ' '.join(_bodies('[data-testid="stSidebarNavLink"]'))
    assert "--etp-muted" in css and "--etp-ink" in css
