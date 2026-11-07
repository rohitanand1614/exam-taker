import os
import json
import glob
from pathlib import Path
from typing import List, Dict, Optional

QUESTIONS_ROOT = Path("questions")
LOGS_ROOT = Path("logs/attempts")

def get_exam_folders(root_dir: str) -> List[str]:
    """
    Recursively finds all folders containing at least one .json file.
    Returns paths relative to the root_dir.
    """
    exam_folders = set()
    root_path = Path(root_dir)
    
    if not root_path.exists():
        return []

    for path in root_path.rglob("*.json"):
        parent = path.parent
        try:
            rel_path = parent.relative_to(root_path)
            exam_folders.add(str(rel_path))
        except ValueError:
            continue
            
    return sorted(list(exam_folders))

def get_exam_files(root_dir: str) -> List[str]:
    """
    Recursively finds all .json files.
    Returns paths relative to the root_dir.
    """
    exam_files = []
    root_path = Path(root_dir)
    
    if not root_path.exists():
        return []

    for path in root_path.rglob("*.json"):
        try:
            rel_path = path.relative_to(root_path)
            exam_files.append(str(rel_path))
        except ValueError:
            continue
            
    return sorted(exam_files)

def load_questions(root_dir: str, target_path: str) -> List[Dict]:
    """
    Loads questions from a specific folder (all json) or a specific file.
    """
    full_path = Path(root_dir) / target_path
    questions = []
    
    if not full_path.exists():
        return []
        
    # Determine if it's a file or directory
    files_to_process = []
    if full_path.is_dir():
        files_to_process = sorted(list(full_path.rglob("*.json")))
    elif full_path.is_file() and full_path.suffix == '.json':
        files_to_process = [full_path]
        
    for file_path in files_to_process:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Handle list of questions
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "id" in item and "question" in item:
                            try:
                                item["source_file"] = str(file_path.relative_to(Path(root_dir)))
                            except ValueError:
                                item["source_file"] = str(file_path.name)
                            questions.append(item)
                
                # Handle single question
                elif isinstance(data, dict):
                    if "id" in data and "question" in data:
                        try:
                            data["source_file"] = str(file_path.relative_to(Path(root_dir)))
                        except ValueError:
                            data["source_file"] = str(file_path.name)
                        questions.append(data)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            
    return questions

def get_log_path(question_id: str) -> Path:
    """Returns the absolute path to the log file for a given question ID."""
    # Sanitize ID to be safe for filenames
    safe_id = "".join(c for c in question_id if c.isalnum() or c in ('-', '_'))
    return LOGS_ROOT / f"{safe_id}.log.json"

def load_question_log(question_id: str) -> Dict:
    """
    Loads the log history for a specific question.
    Returns a dict with summary and attempts list.
    """
    log_path = get_log_path(question_id)
    
    if not log_path.exists():
        return {
            "summary": {
                "total_attempts": 0,
                "correct_count": 0,
                "wrong_count": 0,
                "avg_score": 0.0,
                "last_attempted_at": None,
                "srs": {
                    "repetitions": 0,
                    "interval_days": 0,
                    "ef": 2.5,
                    "next_due": None
                }
            },
            "attempts": []
        }
        
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {} # Should handle corruption better, but simple for now

def save_attempt_log(question_id: str, attempt_data: Dict, new_srs: Dict):
    """
    Appends a new attempt to the log and updates the summary.
    """
    # Ensure directory exists
    LOGS_ROOT.mkdir(parents=True, exist_ok=True)
    
    current_log = load_question_log(question_id)
    
    # Update attempts
    current_log["attempts"].append(attempt_data)
    
    # Update Summary
    summary = current_log["summary"]
    summary["total_attempts"] += 1
    
    if attempt_data["quality"] >= 3:
        summary["correct_count"] += 1
    else:
        summary["wrong_count"] += 1
        
    # Recalculate average score
    total_score = sum(a["score"] for a in current_log["attempts"])
    summary["avg_score"] = total_score / summary["total_attempts"]
    summary["last_attempted_at"] = attempt_data["timestamp"]
    summary["srs"] = new_srs
    
    # Write back
    log_path = get_log_path(question_id)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(current_log, f, indent=2)

def delete_last_attempt(question_id: str):
    """
    Removes the most recent attempt from the log and updates the summary.
    """
    current_log = load_question_log(question_id)
    if not current_log["attempts"]:
        return

    # Remove last attempt
    removed_attempt = current_log["attempts"].pop()
    
    # Update Summary
    summary = current_log["summary"]
    summary["total_attempts"] = max(0, summary["total_attempts"] - 1)
    
    if removed_attempt["quality"] >= 3:
        summary["correct_count"] = max(0, summary["correct_count"] - 1)
    else:
        summary["wrong_count"] = max(0, summary["wrong_count"] - 1)
        
    # Recalculate average score
    if summary["total_attempts"] > 0:
        total_score = sum(a["score"] for a in current_log["attempts"])
        summary["avg_score"] = total_score / summary["total_attempts"]
        summary["last_attempted_at"] = current_log["attempts"][-1]["timestamp"]
    else:
        summary["avg_score"] = 0.0
        summary["last_attempted_at"] = None
        
    # Write back
    log_path = get_log_path(question_id)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(current_log, f, indent=2)

def reset_question_log(question_id: str):
    """
    Completely deletes the log file for a question.
    """
    log_path = get_log_path(question_id)
    if log_path.exists():
        os.remove(log_path)

def get_question_id_to_file_map(root_dir: str) -> Dict[str, str]:
    """
    Scans all JSON files in the root_dir and returns a mapping of {question_id: relative_file_path}.
    """
    mapping = {}
    root_path = Path(root_dir)
    
    if not root_path.exists():
        return mapping
        
    for file_path in root_path.rglob("*.json"):
        try:
            rel_path = str(file_path.relative_to(root_path))
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "id" in item:
                            mapping[item["id"]] = rel_path
                elif isinstance(data, dict):
                    if "id" in data:
                        mapping[data["id"]] = rel_path
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
            
    return mapping

def update_user_notes(question_id: str, notes: str, diagram: str = None):
    """
    Updates the user notes and diagram for a specific question in its log file.
    """
    # Ensure directory exists
    LOGS_ROOT.mkdir(parents=True, exist_ok=True)
    
    current_log = load_question_log(question_id)
    
    # Update notes
    current_log["user_notes"] = notes
    if diagram is not None:
        current_log["user_diagram"] = diagram
    
    # Write back
    log_path = get_log_path(question_id)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(current_log, f, indent=2)
