"""Grouped navigation for Exam Taker Pro: the single place that defines what the sidebar shows.

`nav_spec()` is a pure function (no Streamlit import) so it can be unit-tested; main.py turns it into
`st.navigation({group: [st.Page(...)]})`. Icons come from the DESIGN_SYSTEM iconography table; the few
pages that table does not name (practice incorrect, ...) use the closest Material Symbols name.

Every file in pages/ must appear exactly once (tests/test_navigation_spec.py checks this), and app.py,
the Exam page, is the default page.
"""
from typing import Dict, List

# group -> ((path, title, Material icon, url_path), ...), in sidebar order
_GROUPS = (
    ("Practice", (
        ("app.py", "Exam", ":material/menu_book:", "exam"),
        ("pages/Targeted_Drill.py", "Targeted drill", ":material/target:", "targeted-drill"),
        ("pages/Regressive_Practice.py", "Regressive practice", ":material/sync:", "regressive-practice"),
        ("pages/Practice_Incorrect.py", "Practice incorrect", ":material/rule:", "practice-incorrect"),
        ("pages/Practice_Bookmarks.py", "Practice bookmarks", ":material/bookmark_added:", "practice-bookmarks"),
    )),
    ("Review", (
        ("pages/Wrong_Answers.py", "Wrong answers", ":material/cancel:", "wrong-answers"),
        ("pages/Bookmarks.py", "Bookmarks", ":material/bookmark:", "bookmarks"),
        ("pages/Notes_Review.py", "Notes review", ":material/edit_note:", "notes-review"),
        ("pages/Search_Questions.py", "Search", ":material/search:", "search"),
    )),
    ("Insights", (
        ("pages/Progress_Dashboard.py", "Progress", ":material/bar_chart:", "progress"),
        ("pages/Topic_Analysis.py", "Topic analysis", ":material/psychology:", "topic-analysis"),
    )),
    ("Manage", (
        ("pages/Similar_Questions_Management.py", "Similar questions", ":material/content_copy:", "similar-questions"),
        ("pages/Archived_Questions.py", "Archived", ":material/archive:", "archived"),
    )),
)

DEFAULT_PATH = "app.py"


def nav_spec() -> Dict[str, List[dict]]:
    """{group: [{path, title, icon, url_path, default}, ...]} - a fresh copy on every call."""
    return {
        group: [{"path": path, "title": title, "icon": icon, "url_path": url_path,
                 "default": path == DEFAULT_PATH}
                for path, title, icon, url_path in items]
        for group, items in _GROUPS
    }


def entry_for(path: str) -> dict:
    """The nav entry for a script path such as "pages/Progress_Dashboard.py" (KeyError if unknown)."""
    for items in nav_spec().values():
        for entry in items:
            if entry["path"] == path:
                return entry
    raise KeyError(path)
