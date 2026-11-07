import streamlit as st
import os
import datetime
import random
from pathlib import Path

# Import utils
from utils import file_manager, scoring, srs, bookmark_manager, archive_manager

# -----------------------------------------------------------------------------
# CONFIG & STYLES
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Practice Incorrect", page_icon=":material/cancel:", layout="wide")

from utils import ui_helpers, ui_components, exam_view
ui_helpers.inject_global_css()
ui_helpers.inject_quill_dark_mode()

# -----------------------------------------------------------------------------
# HELPER: FILTER LOGIC
# -----------------------------------------------------------------------------
def filter_incorrect_questions(questions):
    """
    Filters questions to keep those where:
    1. The number of wrong attempts is >= number of correct attempts (Historical Struggle)
    OR
    2. The most recent attempt was incorrect (Recent Failure).
    """
    filtered = []
    for q in questions:
        q_id = q.get("id")
        if not q_id: continue
        
        if archive_manager.is_archived(q_id):
            continue

        log_data = file_manager.load_question_log(q_id)
        summary = log_data.get("summary", {})
        attempts = log_data.get("attempts", [])
        
        correct_count = summary.get("correct_count", 0)
        wrong_count = summary.get("wrong_count", 0)
        
        # Condition 1: Historical struggle (More wrong than right, or equal)
        condition_struggle = wrong_count >= correct_count
        
        # Condition 2: Recent failure (Last attempt was wrong)
        condition_recent_fail = False
        if attempts:
            last_attempt = attempts[-1]
            # Score < 1.0 implies it wasn't a perfect answer
            if last_attempt.get("score", 0) < 1.0:
                condition_recent_fail = True
        
        # Combine with OR
        if condition_struggle or condition_recent_fail:
            filtered.append(q)
            
    return filtered

# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
if 'practice_incorrect_folder' not in st.session_state:
    st.session_state.practice_incorrect_folder = None
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'current_q_index' not in st.session_state:
    st.session_state.current_q_index = 0
if 'answers' not in st.session_state:
    st.session_state.answers = {} 
if 'submitted' not in st.session_state:
    st.session_state.submitted = {} 

# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("Practice incorrect")
    st.info("Shows questions where you struggle historically (Wrong >= Correct) OR your last attempt was incorrect.")
    
    # Selection Mode
    st.subheader("Selection Mode")
    selection_mode = st.radio("Load by:", ["Folder", "Specific File"], index=0, key="inc_mode", horizontal=True)
    
    st.divider()
    
    # Exam Selection
    st.subheader("Select Source")
    
    available_options = []
    if selection_mode == "Folder":
        available_options = file_manager.get_exam_folders("questions")
        label = "Choose a Subject/Topic"
    else:
        available_options = file_manager.get_exam_files("questions")
        label = "Choose a JSON File"
    
    if not available_options:
        st.warning(f"No {selection_mode.lower()}s found.")
    else:
        # Handle state persistence
        if 'last_inc_mode' not in st.session_state:
            st.session_state.last_inc_mode = selection_mode
            
        index = 0
        if st.session_state.last_inc_mode == selection_mode:
             if st.session_state.practice_incorrect_folder in available_options:
                 index = available_options.index(st.session_state.practice_incorrect_folder)
        else:
            st.session_state.last_inc_mode = selection_mode
            
        selected_option = st.selectbox(
            label,
            available_options,
            index=index,
            key="inc_select"
        )
        
        # Load Trigger
        if selected_option != st.session_state.practice_incorrect_folder:
            st.session_state.practice_incorrect_folder = selected_option
            raw_questions = file_manager.load_questions("questions", selected_option)
            st.session_state.questions = filter_incorrect_questions(raw_questions)
            
            st.session_state.current_q_index = 0
            st.session_state.answers = {}
            st.session_state.submitted = {}
            st.rerun()

    st.divider()
    
    # Progress
    if st.session_state.questions:
        total = len(st.session_state.questions)
        current = st.session_state.current_q_index + 1
        progress = current / total
        st.write(f"Question **{current}** of **{total}**")
        st.progress(progress)
    else:
        if st.session_state.practice_incorrect_folder:
            st.success("No incorrect questions found in this selection.", icon=":material/check_circle:")

# -----------------------------------------------------------------------------
# MAIN CONTENT (exam card shared via utils/exam_view.py)
# -----------------------------------------------------------------------------

def handle_submission(q_data, user_selection):
    q_id = q_data["id"]
    correct_indices = q_data.get("correct_indices", [])
    
    # 1. Calculate Score
    score = scoring.calculate_f1_score(user_selection, correct_indices)
    quality = scoring.score_to_quality(score)
    
    # 2. Update Session State
    st.session_state.answers[q_id] = user_selection
    st.session_state.submitted[q_id] = True
    
    # 3. Update SRS & Logs
    log_data = file_manager.load_question_log(q_id)
    current_srs = log_data.get("summary", {}).get("srs", srs.get_initial_srs())
    
    new_srs = srs.update_srs(current_srs, quality)
    
    attempt_entry = {
        "attempt_id": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        "timestamp": datetime.datetime.now().isoformat(),
        "selected_indices": user_selection,
        "score": round(score, 2),
        "quality": quality
    }
    
    file_manager.save_attempt_log(q_id, attempt_entry, new_srs)

def _empty_state():
    if st.session_state.practice_incorrect_folder:
        st.info("No incorrect questions found. Good job!", icon=":material/check_circle:")
    else:
        st.info("Select a source from the sidebar to begin.", icon=":material/info:")


if __name__ == "__main__":
    n_questions = len(st.session_state.questions)
    ui_components.render_page_head(
        "Practice incorrect",
        f"{n_questions} question{'s' if n_questions != 1 else ''} you got wrong"
        if n_questions else "Pick a source in the sidebar to start",
    )
    exam_view.render_question(
        submit_fn=handle_submission,
        show_archive=True,            # this page keeps the archive button
        completed_state_key=None,     # no "all done today" state here
        empty_state=_empty_state,
    )
