import sys
import os
# Add current dir to path
sys.path.append(os.getcwd())

from utils.file_manager import load_questions, get_exam_files, QUESTIONS_ROOT

def estimate():
    print("Scanning questions...")
    all_files = get_exam_files(str(QUESTIONS_ROOT))
    all_q = []
    for f in all_files:
        all_q.extend(load_questions(str(QUESTIONS_ROOT), f))
        
    all_tags = set()
    for q in all_q:
        if "tags" in q:
            all_tags.update(q["tags"])
            
    tag_list = list(all_tags)
    tag_str = str(tag_list)
    
    # Rough estimation: 1 token ~= 4 chars, but for code/JSON it's often 3 chars
    est_tokens = len(tag_str) // 3
    
    print(f"Total Questions: {len(all_q)}")
    print(f"Total Unique Tags: {len(all_tags)}")
    print(f"Estimated Input Tokens (Tags Only): ~{est_tokens}")
    print(f"Estimated Output Tokens (JSON Map): ~{est_tokens * 1.5}") # Output is usually larger due to "Topic" strings
    print(f"Total Estimated Cost (GPT-3.5): ~${(est_tokens + est_tokens*1.5) / 1000 * 0.0015:.4f}")

if __name__ == "__main__":
    estimate()
