import os
import re

md_file = r"f:\my_exam\100days of ml summary (1) 315664fb264f8001a3c2d5f5f5e97f22.md"

def clean_title(title):
    title = title.lower()
    title = re.sub(r'[^a-z0-9]+', '-', title)
    title = title.strip('-')
    return title

def main():
    dirs = {
        'basics': r"f:\my_exam\exam-taker\questions\CampusXDeepLearning-Basics",
        'cnn': r"f:\my_exam\exam-taker\questions\CampusXDeepLearning-CNN-RNN",
        'attention': r"f:\my_exam\exam-taker\questions\CampusXDeepLearning-Attention"
    }
    
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
        
    with open(md_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    for line in lines:
        if line.strip().startswith('|') and not line.startswith('| # |') and not line.startswith('| --- |'):
            parts = line.split('|')
            if len(parts) >= 3:
                num_str = parts[1].strip()
                title_str = parts[2].strip()
                try:
                    num = int(num_str)
                except ValueError:
                    continue
                    
                if num < 3:
                    continue
                
                # Check target dir based on prompt logic
                if 3 <= num <= 39:
                    target = dirs['basics']
                elif 40 <= num <= 67:
                    target = dirs['cnn']
                else:
                    target = dirs['attention']
                    
                c_title = clean_title(title_str)
                fname = f"{num:02d}-{c_title}.json"
                fpath = os.path.join(target, fname)
                
                if not os.path.exists(fpath):
                    with open(fpath, "w", encoding="utf-8") as out:
                        out.write("{\n    \n}")
                        print(f"Created: {fpath}")

if __name__ == "__main__":
    main()
