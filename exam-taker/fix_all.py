import os

files = [
    "aws-skillbuilder-domain-1-mcq.json",
    "aws-skillbuilder-domain-3-mcq.json",
    "aws-skillbuilder-domain-4-mcq.json",
    "aws-skillbuilder-domain-5-mcq.json"
]

base_dir = r"f:\my_exam\exam-taker\questions\2026-aws-cert"

for file in files:
    path = os.path.join(base_dir, file)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = content.replace('"type": "multi_select"', '"type": "multiple_choice"')
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {file}")
    else:
        print(f"Not found: {file}")
