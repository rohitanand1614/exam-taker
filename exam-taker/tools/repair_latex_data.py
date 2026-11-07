"""Repair single-backslash LaTeX that JSON turned into control characters.

    python tools/repair_latex_data.py            # dry run: prints what WOULD change
    python tools/repair_latex_data.py --apply    # writes; a .bak copy is kept next to each changed file

A question file containing  "$4 \\times 3$"  written as  "$4 \times 3$"  decodes to
TAB + "imes". The UI already repairs this for display (utils.ui_components.repair_latex);
this tool fixes the data itself. Only question / options / explanation strings are
touched, only inside $...$ / $$...$$ spans. Files are re-written with json.dumps
(indent=2, ensure_ascii=False), so a changed file may be re-formatted.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.ui_components import repair_latex  # noqa: E402  (pure module, no Streamlit)

FIELDS = ("question", "options", "explanation")


def repair_question(q):
    """Return a list of (field, before, after) for one question dict; mutates q."""
    changes = []
    for field in FIELDS:
        value = q.get(field)
        if isinstance(value, str):
            fixed = repair_latex(value)
            if fixed != value:
                changes.append((field, value, fixed))
                q[field] = fixed
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, str):
                    fixed = repair_latex(item)
                    if fixed != item:
                        changes.append((f"{field}[{i}]", item, fixed))
                        value[i] = fixed
    return changes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--root", default=str(ROOT / "questions"), help="folder to scan")
    args = ap.parse_args(argv)

    root = Path(args.root)
    changed_files = unreadable = total = 0
    for path in sorted(root.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:  # empty or invalid file: report, never touch
            unreadable += 1
            print(f"SKIP (not valid JSON: {e}): {path}")
            continue
        items = data if isinstance(data, list) else [data]
        file_changes = []
        for q in items:
            if isinstance(q, dict):
                for field, before, after in repair_question(q):
                    file_changes.append((q.get("id"), field, before, after))
        if not file_changes:
            continue
        changed_files += 1
        total += len(file_changes)
        print(f"\n{path}")
        for qid, field, before, after in file_changes:
            print(f"  id={qid}  field={field}")
            print(f"    before: {before!r}")
            print(f"    after : {after!r}")
        if args.apply:
            shutil.copy2(path, path.with_name(path.name + ".bak"))
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"  -> written (backup: {path.name}.bak)")

    mode = "APPLIED" if args.apply else "DRY RUN (nothing written; use --apply)"
    print(f"\n{mode}: {total} string(s) in {changed_files} file(s); {unreadable} unreadable file(s) skipped.")


if __name__ == "__main__":
    main()
