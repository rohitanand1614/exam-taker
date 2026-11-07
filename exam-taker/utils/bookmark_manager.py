import json
import os
from pathlib import Path
from datetime import datetime

BOOKMARKS_DIR = Path("bookmarks")
BOOKMARKS_FILE = BOOKMARKS_DIR / "registry.json"

BOOKMARK_COLORS = {
    "Important (Red)": "🔴",
    "Review Later (Orange)": "🟠",
    "Interesting (Blue)": "🔵",
    "Hard (Purple)": "🟣",
    "Solved (Green)": "🟢"
}

def init_bookmarks():
    BOOKMARKS_DIR.mkdir(exist_ok=True)
    if not BOOKMARKS_FILE.exists():
        with open(BOOKMARKS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

def get_all_bookmarks():
    init_bookmarks()
    try:
        with open(BOOKMARKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_bookmark(question_data, color_label):
    """
    Saves or updates a bookmark.
    """
    bookmarks = get_all_bookmarks()
    q_id = question_data["id"]
    
    bookmarks[q_id] = {
        "color": color_label,
        "data": question_data,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(BOOKMARKS_FILE, "w", encoding="utf-8") as f:
        json.dump(bookmarks, f, indent=2)

def remove_bookmark(q_id):
    bookmarks = get_all_bookmarks()
    if q_id in bookmarks:
        del bookmarks[q_id]
        with open(BOOKMARKS_FILE, "w", encoding="utf-8") as f:
            json.dump(bookmarks, f, indent=2)
            return True
    return False

def get_bookmark_status(q_id):
    bookmarks = get_all_bookmarks()
    if q_id in bookmarks:
        return bookmarks[q_id]["color"]
    return None
