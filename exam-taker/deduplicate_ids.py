import os
import json
from collections import defaultdict

base_dir = r"f:\\my_exam\\exam-taker\\questions"
log_file = r"f:\\my_exam\\exam-taker\\dedup_log.txt"

def log(msg):
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception as e:
        print(f"Logging error: {e}")
    print(msg)

# Clear log file
try:
    with open(log_file, "w") as f:
        f.write("Starting global deduplication...\n")
except Exception as e:
    print(f"Error clearing log file: {e}")

log(f"Scanning directories in {base_dir}...")

global_id_map = defaultdict(list)
all_file_data = {}
dirty_files = set()

# Load Phase: Scan all files and build the global map
for root, dirs, files in os.walk(base_dir):
    for fname in files:
        if fname.endswith('.json'):
            fpath = os.path.join(root, fname)
            log(f"Scanning file: {fpath}")
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    
                if isinstance(content, list):
                    all_file_data[fpath] = content
                    for idx, item in enumerate(content):
                        if isinstance(item, dict) and 'id' in item:
                            global_id_map[item['id']].append((fpath, idx))
            except Exception as e:
                log(f"Error reading {fpath}: {e}")

log(f"Total unique IDs found: {len(global_id_map)}")

# Deduplication Phase
for qid, locations in global_id_map.items():
    if len(locations) > 1:
        log(f"Duplicate ID '{qid}' found {len(locations)} times.")
        
        # Sort by file path, then index to ensure deterministic behavior
        locations.sort()
        
        # Keep the first occurrence as is, rename the rest
        for i, (fpath, idx) in enumerate(locations[1:], 1):
            new_id = f"{qid}_v{i}"
            fname = os.path.basename(fpath)
            log(f"  Renaming in {fname} (idx {idx}): {qid} -> {new_id}")
            
            # Update the data in memory
            all_file_data[fpath][idx]['id'] = new_id
            dirty_files.add(fpath)

# Save Phase
if not dirty_files:
    log("No duplicates found. No files updated.")
else:
    log(f"Saving updates to {len(dirty_files)} files...")
    for fpath in dirty_files:
        try:
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(all_file_data[fpath], f, indent=4)
            log(f"  Saved {os.path.basename(fpath)}")
        except Exception as e:
            log(f"Error writing {fpath}: {e}")

log("Global deduplication complete.")
