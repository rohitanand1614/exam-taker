import hashlib
import json
from typing import List, Dict, Any, Tuple
from utils import file_manager, archive_manager

def generate_content_hash(question: Dict[str, Any]) -> str:
    """
    Generates a deterministic hash for a question based on its content:
    - Question Text
    - Options (sorted)
    - Correct Indices (sorted) or Answer
    - Type
    """
    # Normalize text
    q_text = question.get("question", "").strip()
    
    # Normalize options
    options = question.get("options", [])
    if options:
        # We don't sort options themselves as order matters for indices, 
        # but if the goal is "semantically same", order implies different indices.
        # "Exactly same questions and answer is also same" implies exact structure.
        # So we keep order.
        options_str = json.dumps(options)
    else:
        options_str = ""
        
    # Normalize answer
    # Some have correct_indices, some might have other formats.
    correct_indices = question.get("correct_indices", [])
    if isinstance(correct_indices, list):
        correct_indices.sort()
    correct_hash = json.dumps(correct_indices)
    
    q_type = question.get("type", "multiple_choice")
    
    # Create unique string
    content_str = f"{q_text}|{options_str}|{correct_hash}|{q_type}"
    
    return hashlib.md5(content_str.encode("utf-8")).hexdigest()

def find_duplicates(suite_name: str = None) -> List[List[Dict[str, Any]]]:
    """
    Finds exact duplicates across the specified suite (or all questions).
    Returns a list of groups, where each group is a list of identical question objects.
    """
    # 1. Load all questions
    all_questions = []
    
    # Get all potential files
    if suite_name and suite_name != "All":
        # Assuming suite_name maps to a directory in questions root
        # We need to list files recursively in that directory
        # file_manager doesn't have a direct "get_all_questions_in_suite" but we can approximate
        # by scanning everything and filtering source_file.
        # OR better: iterate suites.
        pass
    
    # Loading everything is safer for finding cross-suite duplicates,
    # but the requirement says "User should have an option to select the exam suite."
    # AND "The similarity should be one the basis of exact similar questions across the provided exam suites"
    # This might mean "Find duplicates WITHIN this suite" OR "Find duplicates involving this suite".
    # usually duplicates are interesting within a scope.
    
    # Let's load ALL questions first to be robust.
    # We can optimize later if it's too slow (unlikely for <10k questions).
    root = file_manager.QUESTIONS_ROOT
    all_files = file_manager.get_exam_files(root)
    
    for relative_path in all_files:
        # Filter by suite if needed (assuming first folder in path is suite)
        if suite_name and suite_name != "All":
            normalized_path = relative_path.replace("\\", "/")
            if not normalized_path.startswith(suite_name + "/"):
                 continue
                 
        qs = file_manager.load_questions(root, relative_path)
        all_questions.extend(qs)
        
    # 2. Group by Hash
    hash_map: Dict[str, List[Dict[str, Any]]] = {}
    
    for q in all_questions:
        # Skip if already archived
        if archive_manager.is_archived(q["id"]):
            continue
            
        q_hash = generate_content_hash(q)
        if q_hash not in hash_map:
            hash_map[q_hash] = []
        hash_map[q_hash].append(q)
        
    # 3. Filter groups with size > 1
    duplicates = []
    for q_list in hash_map.values():
        if len(q_list) > 1:
            duplicates.append(q_list)
            
    return duplicates

    return duplicates

import math
import difflib

def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculates using SequenceMatcher (Levenshtein-like)."""
    return difflib.SequenceMatcher(None, text1, text2).ratio()

# Try importing numpy for speed, fall back to pure python if missing
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

def calculate_cosine_similarity(v1, v2) -> float:
    """Calculates cosine similarity between two vectors."""
    if not v1 or not v2:
        return 0.0
        
    if HAS_NUMPY:
        # Assuming v1 and v2 are lists, convert to array if not already
        a = np.array(v1)
        b = np.array(v2)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return np.dot(a, b) / (norm_a * norm_b)
    else:
        # Pure Python fallback
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm_a = math.sqrt(sum(a * a for a in v1))
        norm_b = math.sqrt(sum(b * b for b in v2))
        return dot_product / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0.0

def find_contextual_duplicates(
    questions: List[Dict[str, Any]], 
    llm_client, 
    threshold: float = 0.85,
    progress_callback=None
) -> List[List[Dict[str, Any]]]:
    """
    Finds semantically similar duplicates using Embeddings + Cosine Similarity.
    Input Text = Question + Options + Correct Answer (to ensure full logic match).
    """
    # 0. Filter out questions that are already archived OR are exact duplicates
    # We want Contextual Mode to show ONLY fuzzy matches, not 100% exact ones (which belong in the other tab).
    
    # First, find exact duplicates to exclude them
    exact_groups = find_duplicates(None) # Scan all
    exact_duplicate_ids = set()
    for group in exact_groups:
        for q in group:
            exact_duplicate_ids.add(q['id'])
            
    active_qs = [
        q for q in questions 
        if not archive_manager.is_archived(q["id"]) and q["id"] not in exact_duplicate_ids
    ]
    
    n = len(active_qs)
    
    if n < 2:
        return []
        
    # 1. Text Similarity Filtering (Pre-screen)
    # We identify which questions are even worth embedding.
    
    if progress_callback:
        progress_callback(0.0, "Phase 1: Pre-screening text similarity...")
        
    # Cache text and their lengths for speed
    texts = [q.get("question", "").strip() for q in active_qs]
    lengths = [len(t) for t in texts]
    
    candidate_pairs = [] # List of (i, j)
    indices_to_embed = set()
    
    total_pairs = (n * (n - 1)) // 2
    processed_text = 0
    
    for i in range(n):
        len_i = lengths[i]
        
        for j in range(i + 1, n):
            processed_text += 1
            if progress_callback and processed_text % 10000 == 0: # Update less freq to save UI cycles
                 progress_callback(0.1 * (processed_text / total_pairs), f"Prescreening pair {processed_text}/{total_pairs}...")

            # OPTIMIZATION: Length Filter
            # If lengths differ by more than 30%, they can't have >50% overlap ratio.
            # abs(len_i - len_j) check is instant. SequenceMatcher is slow.
            len_j = lengths[j]
            max_len = max(len_i, len_j)
            if max_len == 0: continue
            
            diff_ratio = abs(len_i - len_j) / max_len
            if diff_ratio > 0.4: # Relaxed to 40% len diff to be safe
                continue
                
            # Check Text Ratio (Expensive)
            if calculate_text_similarity(texts[i], texts[j]) >= 0.5:
                # Potential match
                candidate_pairs.append((i, j))
                indices_to_embed.add(i)
                indices_to_embed.add(j)

    if not candidate_pairs:
        return []

    # 2. Generate Embeddings (ONLY for candidates)
    # Map from index -> embedding vector
    embedding_map = {}
    
    sorted_indices = sorted(list(indices_to_embed))
    num_to_embed = len(sorted_indices)
    
    if progress_callback:
        progress_callback(0.2, f"Phase 2: Generating embeddings for {num_to_embed} candidates...")
        
    for k, idx in enumerate(sorted_indices):
        q = active_qs[idx]
        text_repr = f"Question: {q.get('question', '')}\nOptions: {q.get('options', [])}\nCorrect Answer Indices: {q.get('correct_indices', [])}"
        
        embedding_map[idx] = llm_client.get_embedding(text_repr)
        
        if progress_callback and k % 5 == 0:
            progress = 0.2 + 0.7 * (k / num_to_embed)
            progress_callback(progress, f"Embedding {k+1}/{num_to_embed}...")

    # 3. Vector Similarity Check (Refine)
    if progress_callback:
        progress_callback(0.9, "Phase 3: Verifying vector similarity...")
        
    adj = {i: [] for i in range(n)}
    pair_count = 0
    
    for i, j in candidate_pairs:
        vec_a = embedding_map.get(i)
        vec_b = embedding_map.get(j)
        
        if not vec_a or not vec_b:
            continue
            
        sim = calculate_cosine_similarity(vec_a, vec_b)
        
        if sim >= threshold:
            adj[i].append(j)
            adj[j].append(i)
            pair_count += 1
            
    if progress_callback:
        progress_callback(0.95, f"Found {pair_count} semantic matches...")

    # 3. Connected Components Grouping
    visited = set()
    groups = []
    
    for i in range(n):
        if i not in visited and adj[i]: # Only group if it has connections
            stack = [i]
            visited.add(i)
            component = []
            
            while stack:
                node = stack.pop()
                component.append(active_qs[node])
                
                for neighbor in adj[node]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        stack.append(neighbor)
            
            if len(component) > 1:
                groups.append(component)
                
    return groups
