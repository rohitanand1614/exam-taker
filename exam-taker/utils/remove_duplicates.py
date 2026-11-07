
import os
import json
import argparse
import logging
from typing import List, Dict, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def remove_duplicate_questions_from_list(data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Removes duplicate questions from a list of question dictionaries.
    Duplicates are identified by the normalized 'question' text.
    
    Args:
        data: List of question dictionaries.
        
    Returns:
        Tuple containing the deduplicated list and the count of removed items.
    """
    seen_questions = set()
    unique_data = []
    removed_count = 0

    for item in data:
        if not isinstance(item, dict):
            # Keep non-dict items (though unexpected in this schema)
            unique_data.append(item)
            continue
            
        question_text = item.get('question', '')
        if not question_text:
            # If no question text, track it as unique or handle as needed. 
            # Assuming we keep items without question text to be safe.
            unique_data.append(item)
            continue
            
        # Normalize: lower case and strip whitespace
        normalized_q = question_text.strip().lower()
        
        if normalized_q in seen_questions:
            removed_count += 1
            # We skip adding this to unique_data, effectively removing it
        else:
            seen_questions.add(normalized_q)
            unique_data.append(item)
            
    return unique_data, removed_count

def process_file(file_path: str) -> None:
    """
    Reads a JSON file, removes duplicate questions, and overwrites the file if duplicates were found.
    
    Args:
        file_path: Absolute path to the JSON file.
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                content = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {file_path}: {e}")
                return

        if not isinstance(content, list):
            logger.warning(f"Skipping {file_path}: Root element is not a list.")
            return

        deduplicated_content, removed_count = remove_duplicate_questions_from_list(content)

        if removed_count > 0:
            logger.info(f"Removing {removed_count} duplicate(s) from {file_path}")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(deduplicated_content, f, indent=4)
        else:
            logger.info(f"No duplicates found in {file_path}")

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")

def process_folder(folder_path: str) -> None:
    """
    Recursively scans a folder for JSON files and removes duplicate questions from each.
    
    Args:
        folder_path: Absolute path to the folder.
    """
    if not os.path.exists(folder_path):
        logger.error(f"Folder not found: {folder_path}")
        return

    logger.info(f"Scanning folder: {folder_path}")
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith('.json'):
                full_path = os.path.join(root, file)
                process_file(full_path)

def main():
    parser = argparse.ArgumentParser(description="Remove duplicate questions from JSON files.")
    parser.add_argument('path', help="Path to a JSON file or a folder containing JSON files.")
    
    args = parser.parse_args()
    path = os.path.abspath(args.path)

    if os.path.isfile(path):
        process_file(path)
    elif os.path.isdir(path):
        process_folder(path)
    else:
        logger.error(f"Invalid path: {path}")

if __name__ == "__main__":
    main()
