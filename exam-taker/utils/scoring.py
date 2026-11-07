import math

def calculate_f1_score(selected_indices: list[int], correct_indices: list[int]) -> float:
    """
    Calculates the F1 score for a multi-select question.
    
    TP = |selected ∩ correct|
    precision = TP / |selected|
    recall    = TP / |correct|
    score = 2 * precision * recall / (precision + recall)
    
    Returns:
        float: Score between 0.0 and 1.0
    """
    if not correct_indices:
        return 1.0 if not selected_indices else 0.0
    
    selected_set = set(selected_indices)
    correct_set = set(correct_indices)
    
    tp = len(selected_set.intersection(correct_set))
    
    if len(selected_set) == 0:
        precision = 0.0
    else:
        precision = tp / len(selected_set)
        
    if len(correct_set) == 0:
        recall = 0.0 # Should be covered by initial check, but for safety
    else:
        recall = tp / len(correct_set)
        
    if precision + recall == 0:
        return 0.0
        
    return 2 * (precision * recall) / (precision + recall)

def score_to_quality(score: float) -> int:
    """
    Converts a 0.0-1.0 score to a 0-5 SM-2 quality scale.
    
    Mapping logic:
    1.0 -> 5 (Perfect)
    0.8-0.99 -> 4 (Good)
    0.6-0.79 -> 3 (Pass)
    0.4-0.59 -> 2 (Fail/Hard)
    0.2-0.39 -> 1 (Fail/Very Hard)
    0.0-0.19 -> 0 (Complete Blackout)
    """
    if score >= 1.0: return 5
    if score >= 0.8: return 4
    if score >= 0.6: return 3
    if score >= 0.4: return 2
    if score >= 0.2: return 1
    return 0
