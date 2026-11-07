import json
import os
from pathlib import Path
from datetime import datetime

ARCHIVES_DIR = Path("archives")
ARCHIVES_FILE = ARCHIVES_DIR / "registry.json"

def init_archives():
    ARCHIVES_DIR.mkdir(exist_ok=True)
    if not ARCHIVES_FILE.exists():
        with open(ARCHIVES_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

def get_all_archives():
    init_archives()
    try:
        with open(ARCHIVES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def archive_question(question_data):
    """
    Archives a question.
    """
    archives = get_all_archives()
    q_id = question_data["id"]
    
    archives[q_id] = {
        "data": question_data,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(ARCHIVES_FILE, "w", encoding="utf-8") as f:
        json.dump(archives, f, indent=2)

def unarchive_question(q_id):
    archives = get_all_archives()
    if q_id in archives:
        del archives[q_id]
        with open(ARCHIVES_FILE, "w", encoding="utf-8") as f:
            json.dump(archives, f, indent=2)
            return True
    return False

def is_archived(q_id):
    archives = get_all_archives()
    return q_id in archives
