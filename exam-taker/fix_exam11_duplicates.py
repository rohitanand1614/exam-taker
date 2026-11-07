import json
import os

files = [
    r"f:\my_exam\exam-taker\questions\nvidia-exam\Exam11\regressive_test_batch1.json",
    r"f:\my_exam\exam-taker\questions\nvidia-exam\Exam11\regressive_test_batch2.json",
    r"f:\my_exam\exam-taker\questions\nvidia-exam\Exam11\regressive_test_batch3.json"
]

seen_ids = set()

for fpath in files:
    print(f"Processing {os.path.basename(fpath)}...")
    if not os.path.exists(fpath):
        print(f"  File not found: {fpath}")
        continue
        
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        modified = False
        for i, item in enumerate(data):
            if 'id' in item:
                original_id = item['id']
                if original_id in seen_ids:
                    # Rename
                    counter = 1
                    new_id = f"{original_id}_dup_{counter}"
                    while new_id in seen_ids:
                        counter += 1
                        new_id = f"{original_id}_dup_{counter}"
                    
                    print(f"  Fixing duplicate: {original_id} -> {new_id}")
                    item['id'] = new_id
                    modified = True
                    seen_ids.add(new_id)
                else:
                    seen_ids.add(original_id)
        
        if modified:
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            print(f"  Saved {os.path.basename(fpath)}")
        else:
            print("  No duplicates found in this file relative to previous processed files.")
            
    except Exception as e:
        print(f"  Error: {e}")
