#!/usr/bin/env python3
"""
sync_to_github.py — Export exam-taker user state to sync/ and push to GitHub.

Usage:
    python sync_to_github.py           # full export + git push
    python sync_to_github.py --dry-run # export only, skip git push

The sync/ folder is the GitHub-synced contract between the desktop app (Python)
and the mobile app (Flutter). Desktop is always the source of truth.

Output files:
    sync/user_state.json  — all SRS states, bookmarks, archives
    sync/notes.json       — per-question notes and diagrams
    sync/manifest.json    — deck index with question counts
    sync/questions/       — full copy of questions/ folder
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Active folders ────────────────────────────────────────────────────────────
# Explicitly included question bank folders.
# Any folder whose name starts with "CampusX" is also auto-included without
# needing to be listed here.

ACTIVE_FOLDERS = [
    "nvidia-exam",
    "2026 LLM Job",
    "CampusXDeepLearning-Basics",
    "CampusXDeepLearning-Attention",
    "CampusXDeepLearning-CNN-RNN",
    "genai-llm-books",
]

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent                   # f:\my_exam\
APP  = ROOT / "exam-taker"                     # f:\my_exam\exam-taker\
SYNC = ROOT / "sync"                           # f:\my_exam\sync\

LOGS_DIR      = APP / "logs" / "attempts"
QUESTIONS_DIR = APP / "questions"
BOOKMARKS     = APP / "bookmarks" / "registry.json"
ARCHIVES      = APP / "archives"  / "registry.json"

SYNC_USER_STATE = SYNC / "user_state.json"
SYNC_NOTES      = SYNC / "notes.json"
SYNC_MANIFEST   = SYNC / "manifest.json"
SYNC_QUESTIONS  = SYNC / "questions"

# ── Helpers ───────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> dict | list:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_non_empty(value) -> bool:
    """True if value is a non-None, non-empty string."""
    return bool(value and str(value).strip())


# ── Build user_state.json ─────────────────────────────────────────────────────

def build_user_state() -> tuple[dict, int]:
    """
    Walk logs/attempts/ and consolidate every question's SRS state.
    Returns (user_state_dict, count_of_states).
    """
    srs_states: dict = {}

    if not LOGS_DIR.exists():
        print(f"  [!!]  logs/attempts/ not found at {LOGS_DIR}")
        return {}, 0

    for log_file in sorted(LOGS_DIR.glob("*.log.json")):
        try:
            data = load_json(log_file)
            summary = data.get("summary", {})
            srs     = summary.get("srs", {})

            # Derive question ID from filename: strip ".log.json" suffix
            q_id = log_file.name[: -len(".log.json")]

            srs_states[q_id] = {
                "repetitions":       srs.get("repetitions", 0),
                "interval_days":     srs.get("interval_days", 0),
                "ef":                srs.get("ef", 2.5),
                "next_due":          srs.get("next_due", ""),
                "total_attempts":    summary.get("total_attempts", 0),
                "correct_count":     summary.get("correct_count", 0),
                "wrong_count":       summary.get("wrong_count", 0),
                "avg_score":         summary.get("avg_score", 0.0),
                "last_attempted_at": summary.get("last_attempted_at", ""),
            }
        except Exception as e:
            print(f"  [!!]  Skipping {log_file.name}: {e}")

    bookmarks = load_json(BOOKMARKS)
    archives  = load_json(ARCHIVES)

    user_state = {
        "version":     1,
        "exported_at": now_iso(),
        "srs_states":  srs_states,
        "bookmarks":   bookmarks,
        "archives":    archives,
    }

    return user_state, len(srs_states)


# ── Build notes.json ──────────────────────────────────────────────────────────

def build_notes() -> tuple[dict, int]:
    """
    Walk logs/attempts/ and collect questions that have user_notes or user_diagram.
    Returns (notes_dict, count_with_notes).
    """
    notes: dict = {}

    if not LOGS_DIR.exists():
        return {}, 0

    for log_file in sorted(LOGS_DIR.glob("*.log.json")):
        try:
            data  = load_json(log_file)
            n     = data.get("user_notes", "")
            d     = data.get("user_diagram", "")

            if is_non_empty(n) or is_non_empty(d):
                q_id = log_file.name[: -len(".log.json")]
                notes[q_id] = {
                    "user_notes":   n or "",
                    "user_diagram": d or "",
                }
        except Exception as e:
            print(f"  [!!]  Skipping {log_file.name}: {e}")

    notes_export = {
        "version":     1,
        "exported_at": now_iso(),
        "notes":       notes,
    }

    return notes_export, len(notes)


# ── Build manifest.json ───────────────────────────────────────────────────────

def _deck_id(path: Path) -> str:
    """
    Turn a relative path like 'nvidia-exam/Exam1/filename.json'
    into a slug like 'nvidia-exam-exam1-filename'.
    """
    parts = list(path.parts)
    raw   = "-".join(parts).replace(".json", "")
    return re.sub(r"[^a-zA-Z0-9\-_]", "-", raw).lower()


def _deck_name(path: Path) -> str:
    """
    Turn a path into a human-readable name.
    'nvidia-exam / Exam1 / Deep_Learning.json' -> 'nvidia-exam / Exam1 / Deep Learning'
    """
    parts      = list(path.parts)
    stem       = Path(parts[-1]).stem.replace("_", " ").replace("-", " ").title()
    folder_parts = " / ".join(parts[:-1])
    return f"{folder_parts} / {stem}" if folder_parts else stem


def count_questions(json_path: Path) -> int:
    try:
        data = load_json(json_path)
        return len(data) if isinstance(data, list) else 0
    except Exception:
        return 0


def _is_active_folder(top_level_name: str) -> tuple[bool, bool]:
    """
    Returns (included, is_campusx_auto).
    included        — True if this folder should be in the manifest.
    is_campusx_auto — True if it was auto-included via the CampusX prefix rule
                      (i.e. NOT already in ACTIVE_FOLDERS explicitly).
    """
    in_list  = top_level_name in ACTIVE_FOLDERS
    campusx  = top_level_name.startswith("CampusX") and not in_list
    return (in_list or campusx), campusx


def build_manifest() -> tuple[dict, int, int, int, int]:
    """
    Walk questions/ folder, filter by ACTIVE_FOLDERS + CampusX auto-rule,
    and produce a flat deck list (empty decks excluded from manifest but
    their files are still copied to sync/questions/).

    Returns:
        manifest dict
        n_active_folders   — unique top-level folder names that are in ACTIVE_FOLDERS
        n_campusx_auto     — unique top-level folders included via CampusX prefix rule
        n_empty_skipped    — deck files with 0 questions excluded from manifest
        n_decks            — deck files included in manifest
    """
    decks: list       = []
    n_empty_skipped   = 0
    active_seen: set  = set()
    campusx_seen: set = set()

    if not QUESTIONS_DIR.exists():
        print(f"  [!!]  questions/ not found at {QUESTIONS_DIR}")
        return {}, 0, 0, 0, 0

    for json_file in sorted(QUESTIONS_DIR.rglob("*.json")):
        rel        = json_file.relative_to(QUESTIONS_DIR)
        top_folder = rel.parts[0] if len(rel.parts) > 1 else ""

        included, is_auto = _is_active_folder(top_folder)
        if not included:
            continue

        # Track which top-level folders were seen
        if is_auto:
            campusx_seen.add(top_folder)
        else:
            active_seen.add(top_folder)

        count = count_questions(json_file)
        if count == 0:
            n_empty_skipped += 1
            continue  # omit from manifest, but file is still copied

        decks.append({
            "id":             _deck_id(rel),
            "name":           _deck_name(rel),
            "path":           f"questions/{rel.as_posix()}",
            "question_count": count,
        })

    manifest = {
        "version":     1,
        "exported_at": now_iso(),
        "decks":       decks,
    }

    return manifest, len(active_seen), len(campusx_seen), n_empty_skipped, len(decks)


# ── Copy questions/ ───────────────────────────────────────────────────────────

def copy_questions() -> int:
    """
    Mirror questions/ into sync/questions/ using shutil.
    Returns number of files copied.
    """
    if not QUESTIONS_DIR.exists():
        print(f"  [!!]  questions/ not found — skipping copy")
        return 0

    if SYNC_QUESTIONS.exists():
        shutil.rmtree(SYNC_QUESTIONS)

    shutil.copytree(QUESTIONS_DIR, SYNC_QUESTIONS)

    count = sum(1 for _ in SYNC_QUESTIONS.rglob("*.json"))
    return count


# ── Git operations ────────────────────────────────────────────────────────────

def git_push(dry_run: bool) -> bool:
    """
    Stage sync/, commit with timestamp, push.
    Returns True on success.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check if sync/ is inside a git repo
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--is-inside-work-tree"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("\n  [!!]  Not a git repository. Run `git init && git remote add origin <url>` first.")
        print("       Skipping git push (state files are still written to sync/).")
        return False

    if dry_run:
        print("\n  [dry-run] Would run:")
        print(f"    git -C {ROOT} add sync/")
        print(f"    git -C {ROOT} commit -m \"session sync {timestamp}\"")
        print(f"    git -C {ROOT} push")
        return True

    cmds = [
        ["git", "-C", str(ROOT), "add", "sync/"],
        ["git", "-C", str(ROOT), "commit", "-m", f"session sync {timestamp}"],
        ["git", "-C", str(ROOT), "push"],
    ]

    for cmd in cmds:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            # "nothing to commit" is not a real error
            if "nothing to commit" in r.stdout or "nothing to commit" in r.stderr:
                print("  [--]  Nothing new to commit — sync/ is already up to date.")
                return True
            print(f"\n  [FAIL] Git command failed: {' '.join(cmd[2:])}")
            print(f"     {r.stderr.strip()}")
            return False

    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Sync exam-taker state to GitHub")
    parser.add_argument("--dry-run", action="store_true",
                        help="Build sync/ files but skip git push")
    args = parser.parse_args()

    print("=" * 55)
    print("  exam-taker -> sync  export")
    print("=" * 55)

    # 1. user_state.json
    print("\n[1/4] Building user_state.json ...")
    user_state, n_srs = build_user_state()
    write_json(SYNC_USER_STATE, user_state)
    n_bookmarks = len(user_state.get("bookmarks", {}))
    n_archives  = len(user_state.get("archives",  {}))
    print(f"   OK  {n_srs} SRS states")
    print(f"   OK  {n_bookmarks} bookmarks")
    print(f"   OK  {n_archives} archived questions")

    # 2. notes.json
    print("\n[2/4] Building notes.json ...")
    notes_data, n_notes = build_notes()
    write_json(SYNC_NOTES, notes_data)
    print(f"   OK  {n_notes} questions with notes/diagrams")

    # 3. manifest.json
    print("\n[3/4] Building manifest.json ...")
    manifest, n_active_folders, n_campusx_auto, n_empty_skipped, n_decks = build_manifest()
    write_json(SYNC_MANIFEST, manifest)
    total_q = sum(d["question_count"] for d in manifest.get("decks", []))
    print(f"   OK  {n_active_folders} active folders  +  {n_campusx_auto} CampusX auto-included")
    print(f"   OK  {n_decks} decks in manifest  ({total_q} questions)")
    if n_empty_skipped:
        print(f"   --  {n_empty_skipped} empty decks excluded from manifest (files still copied)")

    # 4. Copy questions/
    print("\n[4/4] Copying questions/ -> sync/questions/ ...")
    n_copied = copy_questions()
    print(f"   OK  {n_copied} question files copied")

    # 5. Git push
    print("\n[git] Pushing to GitHub ...")
    ok = git_push(dry_run=args.dry_run)

    # Summary
    print("\n" + "=" * 55)
    print("  SUMMARY")
    print("=" * 55)
    print(f"  [OK] Active folders synced: {n_active_folders}")
    print(f"  [OK] Auto-included CampusX folders: {n_campusx_auto}")
    print(f"  [--] Empty decks excluded from manifest: {n_empty_skipped}")
    print(f"  [OK] Total decks in manifest: {n_decks}  ({total_q} questions)")
    print(f"  [OK] Synced {n_srs} SRS states")
    print(f"  [OK] Synced {n_notes} notes")
    print(f"  [OK] Synced {n_bookmarks} bookmarks")
    print(f"  [OK] Synced {n_archives} archived questions")
    if args.dry_run:
        print("  [--] dry-run: git push skipped")
    elif ok:
        print("  [OK] Pushed to GitHub")
    else:
        print("  [!!] Git push failed or skipped (files still written)")
    print()


if __name__ == "__main__":
    main()
