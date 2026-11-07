#!/usr/bin/env python3
"""
Question JSON Validator
=======================
Validates question JSON files for schema compliance and LaTeX formatting.

Usage:
  python validate_questions.py                       # Validate all files
  python validate_questions.py path/to/file.json     # Validate specific file(s)
  python validate_questions.py --since 2026-03-20    # Files modified since date
  python validate_questions.py --fix                 # Reformat all files (pretty-print)
  python validate_questions.py --fix path/to/f.json  # Reformat specific file
  python validate_questions.py --summary             # Only totals, no per-issue detail
  python validate_questions.py --errors-only         # Suppress warnings, show errors only

Exit code: 0 = all clear, 1 = errors found, 2 = bad CLI args.
"""

import json
import os
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime, date

QUESTIONS_DIR = Path(__file__).parent / "questions"

# ── Schema definition ────────────────────────────────────────────────────────

REQUIRED_FIELDS = {
    "id":              str,
    "question":        str,
    "type":            str,
    "options":         list,
    "correct_indices": list,
    "tags":            list,
    "difficulty":      str,
    "explanation":     str,
}

VALID_TYPES       = {"multiple_choice"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}

# Fields that contain text which may include LaTeX
LATEX_TEXT_FIELDS = ("question", "explanation")


# ── Issue data class ─────────────────────────────────────────────────────────

class Issue:
    def __init__(self, filepath, q_idx, field, message, is_error=True):
        self.filepath = filepath
        self.q_idx   = q_idx   # None = file-level, int = 0-based question index
        self.field   = field   # None or field name string
        self.message = message
        self.is_error = is_error

    def __str__(self):
        loc   = f"Q#{self.q_idx + 1}" if self.q_idx is not None else "FILE"
        field = f".{self.field}"       if self.field              else ""
        kind  = "ERROR" if self.is_error else "WARN "
        return f"  {kind} [{loc}{field}] {self.message}"


def err(filepath, q_idx, field, msg):
    return Issue(filepath, q_idx, field, msg, is_error=True)

def warn(filepath, q_idx, field, msg):
    return Issue(filepath, q_idx, field, msg, is_error=False)


# ── LaTeX checks ─────────────────────────────────────────────────────────────

def check_latex(text: str) -> list[str]:
    """
    Return a list of LaTeX issue strings found in *text*.
    The caller prefixes with the field name.
    """
    issues = []

    # 1. Dollar signs must come in pairs
    dollar_positions = [i for i, ch in enumerate(text) if ch == "$"]
    if len(dollar_positions) % 2 != 0:
        issues.append(
            f"Odd number of $ signs ({len(dollar_positions)}) — unmatched LaTeX delimiter"
        )
        # Can't reliably find blocks, stop here
        return issues

    # 2. Extract every $...$ span and inspect it
    #    re.DOTALL so multi-line expressions are caught (and flagged)
    for m in re.finditer(r'\$(.*?)\$', text, re.DOTALL):
        inner = m.group(1)
        snippet = (inner[:35] + "…") if len(inner) > 35 else inner

        # 2a. Empty expression: $$
        if not inner.strip():
            issues.append("Empty LaTeX expression: $$")
            continue

        # 2b. Unbalanced curly braces
        opens  = inner.count("{")
        closes = inner.count("}")
        if opens != closes:
            issues.append(
                f"Unbalanced braces in $…$: {opens}{{ vs {closes}}}  "
                f"(near: ${snippet}$)"
            )

        # 2c. Raw newline inside inline math — breaks most renderers
        if "\n" in inner:
            issues.append(
                f"Newline inside LaTeX expression — wrap in display math or fix: "
                f"${snippet}$"
            )

        # 2d. Lone backslash sequences that look like unescaped JSON escapes
        #     e.g. the string "\alpha" (one backslash) in Python means the
        #     JSON file had "\\alpha" which is correct.
        #     BUT if the JSON file had a literal tab or carriage-return it
        #     will show up here as \t or \r in the Python string.
        for bad in ("\t", "\r"):
            if bad in inner:
                issues.append(
                    f"Control character (\\t or \\r) inside LaTeX — likely a "
                    f"JSON escape leak: ${snippet}$"
                )
                break

    return issues


# ── Per-question validation ──────────────────────────────────────────────────

def validate_question(q: dict, idx: int, filepath: Path) -> list[Issue]:
    issues = []

    # Required fields & types
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in q:
            issues.append(err(filepath, idx, field, "Missing required field"))
            continue

        value = q[field]
        if not isinstance(value, expected_type):
            issues.append(err(
                filepath, idx, field,
                f"Expected {expected_type.__name__}, got {type(value).__name__}"
            ))
            continue

        if expected_type is str and not value.strip():
            issues.append(err(filepath, idx, field, "Value is empty or only whitespace"))

    # Enum checks
    if "type" in q and isinstance(q["type"], str):
        if q["type"] not in VALID_TYPES:
            issues.append(err(
                filepath, idx, "type",
                f"Unknown type '{q['type']}' — expected one of {sorted(VALID_TYPES)}"
            ))

    if "difficulty" in q and isinstance(q["difficulty"], str):
        if q["difficulty"].lower() not in VALID_DIFFICULTIES:
            issues.append(err(
                filepath, idx, "difficulty",
                f"Unknown difficulty '{q['difficulty']}' — expected one of "
                f"{sorted(VALID_DIFFICULTIES)}"
            ))

    # Options list
    if "options" in q and isinstance(q["options"], list):
        opts = q["options"]
        if len(opts) < 2:
            issues.append(err(
                filepath, idx, "options",
                f"Need at least 2 options, found {len(opts)}"
            ))
        for i, opt in enumerate(opts):
            if not isinstance(opt, str):
                issues.append(err(
                    filepath, idx, f"options[{i}]",
                    f"Must be a string, got {type(opt).__name__}"
                ))
            elif not opt.strip():
                issues.append(err(filepath, idx, f"options[{i}]", "Option is empty"))

    # correct_indices bounds
    if "correct_indices" in q and "options" in q:
        ci   = q["correct_indices"]
        opts = q["options"]
        if isinstance(ci, list):
            if len(ci) == 0:
                issues.append(err(filepath, idx, "correct_indices",
                    "Must contain at least one correct answer index"))
            for i, cidx in enumerate(ci):
                if not isinstance(cidx, int):
                    issues.append(err(
                        filepath, idx, f"correct_indices[{i}]",
                        f"Must be an integer, got {type(cidx).__name__}"
                    ))
                elif isinstance(opts, list):
                    if cidx < 0:
                        issues.append(err(
                            filepath, idx, f"correct_indices[{i}]",
                            f"Negative index {cidx}"
                        ))
                    elif cidx >= len(opts):
                        issues.append(err(
                            filepath, idx, f"correct_indices[{i}]",
                            f"Index {cidx} out of bounds "
                            f"(options has {len(opts)} items, max valid index is {len(opts)-1})"
                        ))

    # tags list
    if "tags" in q and isinstance(q["tags"], list):
        if len(q["tags"]) == 0:
            issues.append(warn(filepath, idx, "tags", "No tags provided"))
        for i, tag in enumerate(q["tags"]):
            if not isinstance(tag, str) or not tag.strip():
                issues.append(err(
                    filepath, idx, f"tags[{i}]",
                    "Tag must be a non-empty string"
                ))

    # LaTeX validation — question, explanation, and each option
    for field in LATEX_TEXT_FIELDS:
        if field in q and isinstance(q[field], str):
            for latex_issue in check_latex(q[field]):
                issues.append(err(filepath, idx, field, f"LaTeX → {latex_issue}"))

    if "options" in q and isinstance(q["options"], list):
        for i, opt in enumerate(q["options"]):
            if isinstance(opt, str):
                for latex_issue in check_latex(opt):
                    issues.append(err(filepath, idx, f"options[{i}]",
                        f"LaTeX → {latex_issue}"))

    return issues


# ── Per-file validation ──────────────────────────────────────────────────────

def validate_file(filepath: Path) -> list[Issue]:
    issues = []

    # Read file
    try:
        raw = filepath.read_text(encoding="utf-8").strip()
    except Exception as e:
        return [err(filepath, None, None, f"Cannot read file: {e}")]

    if not raw:
        return [warn(filepath, None, None, "File is completely empty")]

    # Parse JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return [err(filepath, None, None, f"Invalid JSON — {e}")]

    # Root must be a list
    if isinstance(data, dict):
        if not data:
            return [warn(filepath, None, None, "File contains empty object {} — should be []")]
        issues.append(warn(
            filepath, None, None,
            "Root element is an object {} — should be an array []. Treating as single question."
        ))
        data = [data]
    elif not isinstance(data, list):
        return [err(filepath, None, None,
            f"Root must be an array [], got {type(data).__name__}")]

    if len(data) == 0:
        return [warn(filepath, None, None, "Array is empty — no questions defined")]

    # Duplicate IDs within this file
    seen_ids: dict[str, int] = {}
    for i, q in enumerate(data):
        if isinstance(q, dict) and isinstance(q.get("id"), str):
            qid = q["id"]
            if qid in seen_ids:
                issues.append(err(
                    filepath, i, "id",
                    f"Duplicate ID '{qid}' (also at Q#{seen_ids[qid] + 1})"
                ))
            else:
                seen_ids[qid] = i

    # Validate each question
    for i, q in enumerate(data):
        if not isinstance(q, dict):
            issues.append(err(
                filepath, i, None,
                f"Each question must be a JSON object, got {type(q).__name__}"
            ))
            continue
        issues.extend(validate_question(q, i, filepath))

    return issues


# ── Auto-fix ─────────────────────────────────────────────────────────────────

def fix_file(filepath: Path) -> tuple[bool, str | None]:
    """Reformat the JSON file with 4-space indentation. Returns (success, error_msg)."""
    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        with open(filepath, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.write("\n")
        return True, None
    except Exception as e:
        return False, str(e)


# ── File collection ──────────────────────────────────────────────────────────

def collect_files(explicit_files: list[str], since_date: date | None) -> list[Path]:
    if explicit_files:
        paths = []
        for f in explicit_files:
            p = Path(f)
            if not p.exists():
                print(f"WARNING: File not found — {f}", file=sys.stderr)
            elif p.is_dir():
                paths.extend(sorted(p.rglob("*.json")))
            elif f.endswith(".json"):
                paths.append(p)
            else:
                print(f"WARNING: Skipping non-JSON file — {f}", file=sys.stderr)
        return paths

    all_files = sorted(QUESTIONS_DIR.rglob("*.json"))

    if since_date:
        cutoff = datetime.combine(since_date, datetime.min.time()).timestamp()
        all_files = [f for f in all_files if f.stat().st_mtime >= cutoff]

    return all_files


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate question JSON files (schema + LaTeX)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
--------
  # Validate everything
  python validate_questions.py

  # Validate one file
  python validate_questions.py questions/CampusX/01-intro.json

  # Only files modified today (or since a specific date)
  python validate_questions.py --since 2026-03-20

  # Pretty-print / reformat all JSON files in place
  python validate_questions.py --fix

  # Reformat a single file
  python validate_questions.py --fix questions/CampusX/01-intro.json

  # CI-friendly: errors only, exit-code check
  python validate_questions.py --errors-only
        """,
    )
    parser.add_argument("files", nargs="*",
        help="Specific .json file(s) to validate (default: all files under questions/)")
    parser.add_argument("--since", metavar="YYYY-MM-DD",
        help="Only validate files modified on or after this date")
    parser.add_argument("--fix", action="store_true",
        help="Reformat valid JSON files in-place (4-space indent, UTF-8, LF line endings)")
    parser.add_argument("--summary", action="store_true",
        help="Print only the summary counts, not individual issue details")
    parser.add_argument("--errors-only", action="store_true",
        help="Suppress warnings; only report errors")

    args = parser.parse_args()

    # Parse --since date
    since_date = None
    if args.since:
        try:
            since_date = date.fromisoformat(args.since)
        except ValueError:
            print(f"ERROR: --since expects YYYY-MM-DD, got '{args.since}'", file=sys.stderr)
            return 2

    files = collect_files(args.files, since_date)

    if not files:
        msg = "No JSON files found"
        if since_date:
            msg += f" modified since {since_date}"
        print(msg + ".")
        return 0

    label = f"{len(files)} file(s)"
    if since_date:
        label += f" modified since {since_date}"
    print(f"Scanning {label}…\n")

    total_errors   = 0
    total_warnings = 0
    files_with_errors   = 0
    files_with_warnings = 0
    fixed_count = 0

    for filepath in files:
        issues = validate_file(filepath)

        errors   = [i for i in issues if i.is_error]
        warnings = [i for i in issues if not i.is_error]

        # Auto-fix: reformat JSON (best-effort; skipped if JSON is unparseable)
        if args.fix:
            is_json_broken = any(
                "Invalid JSON" in i.message for i in errors
            )
            if not is_json_broken:
                ok, fix_err = fix_file(filepath)
                if ok:
                    fixed_count += 1
                else:
                    print(f"  FIX FAILED [{filepath}]: {fix_err}")

        shown = errors + ([] if args.errors_only else warnings)

        if shown:
            rel = filepath.relative_to(Path(__file__).parent) \
                  if Path(__file__).parent in filepath.parents else filepath
            tag = "ERROR" if errors else "WARN "
            print(f"{tag} {rel}")
            if not args.summary:
                for issue in shown:
                    print(str(issue))
            print()

        total_errors   += len(errors)
        total_warnings += len(warnings)
        if errors:
            files_with_errors += 1
        if warnings:
            files_with_warnings += 1

    # ── Summary ──────────────────────────────────────────────────────────────
    print("-" * 64)
    print(f"Files scanned         : {len(files)}")
    print(f"Files with errors     : {files_with_errors}")
    if not args.errors_only:
        print(f"Files with warnings   : {files_with_warnings}")
    print(f"Total errors          : {total_errors}")
    if not args.errors_only:
        print(f"Total warnings        : {total_warnings}")
    if args.fix:
        print(f"Files reformatted     : {fixed_count}")

    if total_errors == 0 and (args.errors_only or total_warnings == 0):
        print("\nAll files passed validation.")
    elif total_errors == 0:
        print("\nNo errors. Review warnings above.")
    else:
        print(f"\nValidation FAILED — {total_errors} error(s) must be fixed.")

    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
