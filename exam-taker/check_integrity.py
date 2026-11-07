import json
import os
from pathlib import Path

def check_duplicates():
    root_dir = Path(r"f:\my_exam\exam-taker\questions")
    all_ids = {}
    duplicates = []

    print(f"Scanning {root_dir}...")

    for file_path in root_dir.rglob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    continue
                
                for item in data:
                    if not isinstance(item, dict): continue
                    q_id = item.get("id")
                    if q_id:
                        if q_id in all_ids:
                            duplicates.append({
                                "id": q_id,
                                "file1": all_ids[q_id],
                                "file2": str(file_path)
                            })
                        else:
                            all_ids[q_id] = str(file_path)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    if duplicates:
        print(f"\n❌ Found {len(duplicates)} Duplicate IDs:")
        for d in duplicates:
            print(f"  - ID: {d['id']}")
            print(f"    1st occurrence: {d['file1']}")
            print(f"    2nd occurrence: {d['file2']}")
            print("-" * 40)
    else:
        print("\n✅ No duplicate IDs found across all exam files.")

if __name__ == "__main__":
    check_duplicates()
