import json

target_file = r"f:\my_exam\exam-taker\questions\nvidia-exam\Exam11\regressive_test_batch3.json"

try:
    print(f"Reading {target_file}...")
    with open(target_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    count = 0
    for item in data:
        if 'id' in item:
            item['id'] = item['id'] + "_batch3"
            count += 1
            
    print(f"Renamed {count} IDs.")
    
    with open(target_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
        
    print("Saved file.")

except Exception as e:
    print(f"Error: {e}")
