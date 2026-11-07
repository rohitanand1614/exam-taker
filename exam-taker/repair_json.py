import json
import re
import os

target_file = r"f:\my_exam\exam-taker\questions\nvidia-exam\Exam10\nca_genl_questions.json"

def repair():
    with open(target_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # The file has valid JSON up to line 1439
    # Line 1439 is "  },"
    # But wait, the viewer showed:
    # 1438:     "explanation": "..."
    # 1439:   },
    # 1440:   {
    
    # We will split strictly.
    # Lines 0 to 1439 are the "prefix" (items 0 to N-1).
    # BUT, the file likely starts with `[`.
    # And we need to remove the comma possibly at the end of the last valid item if we are appending.
    
    # Let's inspect line 1439.
    print(f"Line 1439: {lines[1439]}")
    
    # The new content starts at 1440.
    raw_new = "".join(lines[1440:])
    
    # Fixes for the new content:
    # 1. Remove newlines that break strings. We'll replace them with spaces.
    #    However, we must preserve structural newlines if they formatted the json? 
    #    The pasted content has newlines INSIDE strings (explanations).
    #    It also has structure `{"id":...`.
    #    We can just remove ALL newlines in the new block and rely on `"},{"` to find boundaries later if needed, 
    #    or just treat it as one text blob to clean.
    
    clean_new = raw_new.replace("\n", " ")
    
    # 2. Fix encoded double quotes `""` -> `\"`
    #    But be careful not to break empty strings `""` or mismatched things.
    #    The user input has `""Calculate...""`.
    #    We will use specific regex for this?
    #    Or simple replace: `""` -> `\"`
    #    Is `""` used locally as empty string?
    #    Regex lookaround: (?<=[^\\"]")" (quote preceded by quote?)
    #    Let's just replace `""` with `\"`.
    
    clean_new = clean_new.replace('""', '\\"')
    
    # 3. There might be some extra spaces or weird chars.
    
    # 4. Now we try to parse the "new" part.
    #    The new part starts with `, {` or `{`.
    #    Line 1440 was `  {`.
    #    So `clean_new` starts with `{`.
    #    It ends with `]`. (Line 1586).
    #    It effectively represents a list of objects without the opening `[`.
    #    Wait, look at line 1439: `  },`.
    #    So `clean_new` continues the list.
    
    # let's try to parse it by wrapping it in `[` and `]`.
    # But `clean_new` already ends with `]`.
    # So we prepend `[` and see if it parses.
    
    test_str = "[" + clean_new.strip()
    # It might have a leading comma if line 1439 had one?
    # Line 1439 is `  },`.
    # So `clean_new` starts with `{`.
    
    try:
        new_items = json.loads(test_str)
        print("Success! Parsed new items.")
    except json.JSONDecodeError as e:
        print(f"JSON Error: {e}")
        # Manual fix strategies
        # Maybe missing commas between `}` and `{`?
        # The pattern `}{` occurs?
        clean_new = clean_new.replace("}{", "},{")
        
        # Try again
        test_str = "[" + clean_new.strip()
        try:
            new_items = json.loads(test_str)
            print("Success after adding commas!")
        except Exception as e2:
            print(f"Still failing: {e2}")
            # regex approach to extract objects
            pass

    # Reconstruct whole file
    # Load the top part (valid)
    # We assume lines 0-1439 form a valid snippet if we add `]`.
    top_str = "".join(lines[:1440]) 
    if top_str.strip().endswith(","):
        top_str = top_str.strip()[:-1] # Remove trailing comma
    
    if not top_str.strip().endswith("]"):
         top_str += "\n]"
         
    try:
        old_items = json.loads(top_str)
        print(f"Loaded {len(old_items)} old items.")
    except Exception as e:
        print(f"Failed to load old items: {e}")
        return

    # If new items parsed
    if 'new_items' in locals():
        combined = old_items + new_items
        
        # Write back nicely formatted
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(combined, f, indent=2)
        print("File repaired and saved.")
    else:
        print("Could not parse new items data, aborting write.")

if __name__ == "__main__":
    repair()
