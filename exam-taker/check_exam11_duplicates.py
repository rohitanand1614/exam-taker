import json
import os

file1 = r"f:\my_exam\exam-taker\questions\nvidia-exam\Exam11\regressive_test_batch2.json"
file2 = r"f:\my_exam\exam-taker\questions\nvidia-exam\Exam11\regressive_test_batch3.json"

def check_file(path):
    print(f"Checking {path}...")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"  Loaded {len(data)} items.")
            ids = []
            for item in data:
                if 'id' in item:
                    ids.append(item['id'])
            return ids
    except Exception as e:
        print(f"  Error: {e}")
        return []


with open("exam11_check.txt", "w") as out:
    def print_log(msg):
        out.write(msg + "\n")
        print(msg)

    ids1 = check_file(file1)
    ids2 = check_file(file2)

    print_log("\nComparing IDs...")
    set1 = set(ids1)
    set2 = set(ids2)
    common = set1.intersection(set2)

    print_log(f"Common IDs: {len(common)}")
    for cid in list(common)[:10]:
        print_log(f"  Duplicate: '{cid}'")

