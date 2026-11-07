import streamlit as st
import os
import datetime
import random
from pathlib import Path
from streamlit_quill import st_quill
from streamlit_mermaid import st_mermaid

# Import utils
from utils import file_manager, scoring, srs, bookmark_manager

# -----------------------------------------------------------------------------
# CONFIG & STYLES
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Practice Bookmarks", page_icon=":material/bookmark:", layout="wide")

from utils import ui_helpers, ui_components, exam_view
ui_helpers.inject_global_css()
ui_helpers.inject_quill_dark_mode()

# -----------------------------------------------------------------------------
# HELPER: FILTER LOGIC
# -----------------------------------------------------------------------------
def filter_bookmarked_questions(questions, selected_colors):
    """
    Filters questions to keep only those that are bookmarked with one of the selected colors.
    """
    filtered = []
    all_bookmarks = bookmark_manager.get_all_bookmarks()
    
    for q in questions:
        q_id = q.get("id")
        if not q_id: continue
        
        if q_id in all_bookmarks:
            bm_data = all_bookmarks[q_id]
            if bm_data["color"] in selected_colors:
                filtered.append(q)
    return filtered

# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
if 'practice_bm_folder' not in st.session_state:
    st.session_state.practice_bm_folder = None
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
    st.title("Practice bookmarks")
    st.info("Review your bookmarked questions.")
    
    # Selection Mode
    st.subheader("Selection Mode")
    selection_mode = st.radio("Load by:", ["Folder", "Specific File"], index=0, key="bm_mode", horizontal=True)
    
    st.divider()
    
    # Bookmark Type Filter
    st.subheader("Filter by Type")
    all_colors = list(bookmark_manager.BOOKMARK_COLORS.keys())
    selected_colors = st.multiselect("Select Bookmark Types", all_colors, default=all_colors)
    
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
        if 'last_bm_mode' not in st.session_state:
            st.session_state.last_bm_mode = selection_mode
            
        index = 0
        if st.session_state.last_bm_mode == selection_mode:
             if st.session_state.practice_bm_folder in available_options:
                 index = available_options.index(st.session_state.practice_bm_folder)
        else:
            st.session_state.last_bm_mode = selection_mode
            
        selected_option = st.selectbox(
            label,
            available_options,
            index=index,
            key="bm_select"
        )
        
        # Load Trigger
        # We also trigger reload if selected_colors changes, but Streamlit reruns the whole script on interaction.
        # We need to detect if we need to reload.
        # Simplest way: Always reload filtered list based on current selection + colors.
        
        # Check if source changed OR if we just want to ensure consistency
        # Ideally we only reload if source changes, but filtering by color happens on the loaded set.
        
        if selected_option != st.session_state.practice_bm_folder:
            st.session_state.practice_bm_folder = selected_option
            # Load raw
            st.session_state.raw_questions_cache = file_manager.load_questions("questions", selected_option)
            # Filter
            st.session_state.questions = filter_bookmarked_questions(st.session_state.raw_questions_cache, selected_colors)
            
            st.session_state.current_q_index = 0
            st.session_state.answers = {}
            st.session_state.submitted = {}
            st.rerun()
        else:
            # If source is same, check if colors changed? 
            # Actually, if the user changes colors, we should re-filter.
            # We can store the last_colors to check.
            if 'last_colors' not in st.session_state:
                st.session_state.last_colors = selected_colors
            
            if st.session_state.last_colors != selected_colors:
                st.session_state.last_colors = selected_colors
                if 'raw_questions_cache' in st.session_state:
                     st.session_state.questions = filter_bookmarked_questions(st.session_state.raw_questions_cache, selected_colors)
                     st.session_state.current_q_index = 0 # Reset index to avoid out of bounds
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
        if st.session_state.practice_bm_folder:
            st.warning("No bookmarks found matching your criteria.")

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
    if st.session_state.practice_bm_folder:
        st.info("No questions match your filter.", icon=":material/info:")
    else:
        st.info("Select a source from the sidebar to begin.", icon=":material/info:")


if __name__ == "__main__":
    n_questions = len(st.session_state.questions)
    ui_components.render_page_head(
        "Practice bookmarks",
        f"{n_questions} bookmarked question{'s' if n_questions != 1 else ''}"
        if n_questions else "Pick a source in the sidebar to start",
    )
    exam_view.render_question(
        submit_fn=handle_submission,
        show_archive=False,           # this page has never had an archive button
        completed_state_key=None,
        empty_state=_empty_state,
    )
