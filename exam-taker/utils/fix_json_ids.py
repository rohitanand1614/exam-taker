import json
import os

file_path = r"f:\my_exam\exam-taker\questions\nvidia-exam\Exam8\nvidia_suggest_read.json"

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit(1)

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Found {len(data)} items. Renumbering...")

    for i, item in enumerate(data):
        item['id'] = f"suggested_read_{i+1:03d}"

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

    print(f"Successfully updated IDs for {len(data)} items.")

except json.JSONDecodeError as e:
    print(f"Error decoding JSON: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
