import os
import json
from collections import defaultdict

def scan_folder(root_dir):
    issues = []
    id_map = defaultdict(list)
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".json"):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for idx, q in enumerate(data):
                                q_id = q.get("id")
                                
                                # Check for missing/empty ID
                                if q_id is None:
                                    issues.append(f"MISSING ID: {path} (Index {idx})")
                                    # Treat as "None" for duplicate checking
                                    id_map["None"].append(f"{path} (Index {idx})")
                                elif str(q_id).strip() == "":
                                    issues.append(f"EMPTY ID: {path} (Index {idx})")
                                    id_map["EMPTY"].append(f"{path} (Index {idx})")
                                else:
                                    id_map[str(q_id)].append(f"{path} (Index {idx})")
                        elif isinstance(data, dict):
                             # Sometimes a single object?
                             q_id = data.get("id")
                             if not q_id:
                                 issues.append(f"MISSING/EMPTY ID in root dict: {path}")
                except Exception as e:
                    issues.append(f"ERROR reading {path}: {str(e)}")

    # Check for duplicates
    for q_id, occurrences in id_map.items():
        if len(occurrences) > 1:
            issues.append(f"DUPLICATE ID '{q_id}': Found in {len(occurrences)} places: {occurrences}")

    return issues

if __name__ == "__main__":
    target_dir = r"f:\my_exam\exam-taker\questions\nvidia-exam\Exam11"
    with open("debug_result.txt", "w") as out:
        out.write(f"Scanning {target_dir}...\n")
        found_issues = scan_folder(target_dir)
        
        if found_issues:
            out.write(f"Found {len(found_issues)} issues:\n")
            for issue in found_issues:
                out.write(issue + "\n")
        else:
            out.write("No ID issues found.\n")
