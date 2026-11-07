import datetime

def get_initial_srs():
    """Returns the default state for a new question."""
    return {
        "repetitions": 0,
        "interval_days": 0,
        "ef": 2.5,  # Easiness Factor
        "next_due": datetime.date.today().isoformat()
    }

def update_srs(current_srs: dict, quality: int) -> dict:
    """
    Updates the SRS state based on the SM-2 algorithm.
    
    Args:
        current_srs (dict): The current SRS state.
        quality (int): The quality of the response (0-5).
        
    Returns:
        dict: The updated SRS state.
    """
    repetitions = current_srs.get("repetitions", 0)
    ef = current_srs.get("ef", 2.5)
    interval = current_srs.get("interval_days", 0)
    
    if quality >= 3:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = math_round(interval * ef)
        
        repetitions += 1
    else:
        repetitions = 0
        interval = 1
        
    # Update EF
    # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    new_ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if new_ef < 1.3:
        new_ef = 1.3
        
    next_due_date = datetime.date.today() + datetime.timedelta(days=interval)
    
    return {
        "repetitions": repetitions,
        "interval_days": interval,
        "ef": round(new_ef, 3),
        "next_due": next_due_date.isoformat()
    }

def math_round(n):
    """Standard rounding (0.5 rounds up) unlike Python's round-to-even."""
    return int(n + 0.5)
