import streamlit as st
import os
import datetime
import random
from pathlib import Path
from streamlit_quill import st_quill
from streamlit_mermaid import st_mermaid

# Import utils
from utils import file_manager, scoring, srs, bookmark_manager, archive_manager

# -----------------------------------------------------------------------------
# CONFIG & STYLES
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Exam Taker Pro", page_icon=":material/menu_book:", layout="wide")

from utils import ui_helpers, ui_components, exam_view
ui_helpers.inject_global_css()
ui_helpers.inject_quill_dark_mode()

# -----------------------------------------------------------------------------
# HELPER: DAILY SESSION LOGIC
# -----------------------------------------------------------------------------
def process_daily_session(questions):
    """
    Filters out questions based on the following rule:
    - If answered correctly AND NOT bookmarked within the last 48 hours -> Skip.
    - Otherwise -> Show.
    
    Also marks questions as 'is_reattempt' if attempted today but not answered correctly.
    """
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    filtered_questions = []
    
    for q in questions:
        q_id = q.get("id")
        if not q_id:
            filtered_questions.append(q)
            continue
            
        # 1. Check Archive Status
        if archive_manager.is_archived(q_id):
            continue

        # 2. Check Bookmark Status
        is_bookmarked = bookmark_manager.get_bookmark_status(q_id) is not None
        
        # 3. Load History
        log_data = file_manager.load_question_log(q_id)
        attempts = log_data.get("attempts", [])
        
        # 3. Check 48h Rule (Standard Spaced Repetition)
        should_skip = False
        
        # Find all correct attempts timestamps
        correct_attempts_timestamps = []
        for a in attempts:
            if a.get("score", 0) == 1.0:
                try:
                    ts = datetime.datetime.fromisoformat(a["timestamp"])
                    correct_attempts_timestamps.append(ts)
                except ValueError:
                    continue
        
        correct_attempts_timestamps.sort()
        
        if correct_attempts_timestamps:
            last_correct_time = correct_attempts_timestamps[-1]
            
            # Rule A: 48h cooldown if NOT bookmarked
            if not is_bookmarked:
                delta = now - last_correct_time
                if delta.total_seconds() < 48 * 3600: # 48 hours
                    should_skip = True
            
            # Rule B: 24h cooldown if 4 correct attempts within 1 hour (regardless of bookmark)
            # This prevents spamming/cramming even for bookmarked items
            if not should_skip and len(correct_attempts_timestamps) >= 4:
                # Check the window of the last 4 correct attempts
                # We look at the span between the 4th-to-last and the last
                fourth_last = correct_attempts_timestamps[-4]
                span = last_correct_time - fourth_last
                
                if span.total_seconds() <= 3600: # Within 1 hour
                    # Check if we are currently in the 24h cooldown from the last correct
                    if (now - last_correct_time).total_seconds() < 24 * 3600:
                        should_skip = True

        if should_skip:
            continue
            
        # 4. Reattempt Badge Logic (for today's session)
        attempts_today = [
            a for a in attempts 
            if a.get("timestamp", "").startswith(today_str)
        ]
        
        # If attempted today and NOT correct today, mark as reattempt
        has_correct_today = any(a.get("score", 0) == 1.0 for a in attempts_today)
        
        if attempts_today and not has_correct_today:
            q["is_reattempt"] = True
        else:
            q["is_reattempt"] = False
            
        filtered_questions.append(q)
        
    return filtered_questions

# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
if 'current_exam_folder' not in st.session_state:
    st.session_state.current_exam_folder = None
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'current_q_index' not in st.session_state:
    st.session_state.current_q_index = 0
if 'answers' not in st.session_state:
    st.session_state.answers = {} # {q_id: selected_indices}
if 'submitted' not in st.session_state:
    st.session_state.submitted = {} # {q_id: bool}
if 'mode' not in st.session_state:
    st.session_state.mode = "Standard" # Standard, SRS, Weakest
if 'all_completed_today' not in st.session_state:
    st.session_state.all_completed_today = False

# -----------------------------------------------------------------------------
# SIDEBAR: SELECTION & STATS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("Exam Taker Pro")
    
    # 1. Selection Mode
    st.subheader("Selection Mode")
    selection_mode = st.radio("Load by:", ["Folder", "Specific File"], index=0, horizontal=True)
    
    st.divider()
    
    # 2. Exam Selection
    st.subheader("Select Exam")
    
    available_options = []
    if selection_mode == "Folder":
        available_options = file_manager.get_exam_folders("questions")
        label = "Choose a Subject/Topic"
    else:
        available_options = file_manager.get_exam_files("questions")
        label = "Choose a JSON File"
    
    if not available_options:
        st.warning(f"No {selection_mode.lower()}s found in 'questions/' folder.")
        st.info("Add content to get started.")
    else:
        # Handle state persistence when switching modes
        if 'last_mode' not in st.session_state:
            st.session_state.last_mode = selection_mode
            
        # Reset selection if mode changed
        index = 0
        if st.session_state.last_mode == selection_mode:
             if st.session_state.current_exam_folder in available_options:
                 index = available_options.index(st.session_state.current_exam_folder)
        else:
            st.session_state.last_mode = selection_mode
            
        selected_option = st.selectbox(
            label,
            available_options,
            index=index
        )
        
        # Load Questions Trigger
        if selected_option != st.session_state.current_exam_folder:
            st.session_state.current_exam_folder = selected_option
            raw_questions = file_manager.load_questions("questions", selected_option)
            st.session_state.questions = process_daily_session(raw_questions)
            
            # Check if all completed
            if raw_questions and not st.session_state.questions:
                st.session_state.all_completed_today = True
            else:
                st.session_state.all_completed_today = False
                
            st.session_state.current_q_index = 0
            st.session_state.answers = {}
            st.session_state.submitted = {}
            st.rerun()

    st.divider()
    
    # 2. Mode Selection (Simple for now)
    st.subheader("Study Mode")
    mode = st.radio("Mode", ["Standard", "Shuffled"], index=0, horizontal=True)
    if mode == "Shuffled" and st.session_state.mode != "Shuffled":
        random.shuffle(st.session_state.questions)
        st.session_state.mode = "Shuffled"
        st.session_state.current_q_index = 0
        st.rerun()
    elif mode == "Standard" and st.session_state.mode != "Standard":
        # Reload to restore order
        raw_questions = file_manager.load_questions("questions", st.session_state.current_exam_folder)
        st.session_state.questions = process_daily_session(raw_questions)
        st.session_state.mode = "Standard"
        st.session_state.current_q_index = 0
        st.rerun()

    st.divider()
    
    # 3. Progress
    if st.session_state.questions:
        total = len(st.session_state.questions)
        current = st.session_state.current_q_index + 1
        progress = current / total
        st.write(f"Question **{current}** of **{total}**")
        st.progress(progress)

    st.divider()
    
    # 4. Overall Stats (Visual Bar)
    if 'current_exam_folder' in st.session_state and st.session_state.current_exam_folder:
        # We need raw questions to calculate total stats, not just the daily filtered ones.
        # Ideally we shouldn't reload this every rerun for performance, but for now it's safe.
        # To optimize, we could cache this in session state, but let's keep it simple.
        stats_questions = file_manager.load_questions("questions", st.session_state.current_exam_folder)
        
        if stats_questions:
            g, y, r, gr = 0, 0, 0, 0
            total_q = len(stats_questions)
            
            for q in stats_questions:
                q_id = q.get("id")
                if not q_id: continue
                
                log = file_manager.load_question_log(q_id)
                attempts = log.get("attempts", [])
                
                if not attempts:
                    gr += 1
                else:
                    correct = sum(1 for a in attempts if a.get("score", 0) == 1.0)
                    wrong = len(attempts) - correct
                    
                    if correct > 0 and wrong == 0: g += 1
                    elif correct > 0 and wrong > 0: y += 1
                    elif correct == 0 and wrong > 0: r += 1
                    else: gr += 1 # Fallback
            
            # Calculate percentages
            pg = (g / total_q) * 100
            py = (y / total_q) * 100
            pr = (r / total_q) * 100
            pgr = (gr / total_q) * 100
            
            st.caption("Overall Progress")
            
            # Custom HTML Bar (colours from design tokens)
            tk = ui_helpers.TOKENS
            bar_html = f"""
            <div style="display: flex; width: 100%; height: 8px; border-radius: 999px; overflow: hidden; background-color: {tk['surface_raised']};">
                <div style="width: {pg}%; background-color: {tk['success']};" title="Mastered: {g} ({pg:.1f}%)"></div>
                <div style="width: {py}%; background-color: {tk['warning']};" title="Mixed: {y} ({py:.1f}%)"></div>
                <div style="width: {pr}%; background-color: {tk['danger']};" title="Struggling: {r} ({pr:.1f}%)"></div>
                <div style="width: {pgr}%; background-color: {tk['border_strong']};" title="Unattempted: {gr} ({pgr:.1f}%)"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: {tk['ink_muted']}; margin-top: 4px;">
                <span style="color: {tk['success']};">{pg:.0f}%</span>
                <span style="color: {tk['warning']};">{py:.0f}%</span>
                <span style="color: {tk['danger']};">{pr:.0f}%</span>
                <span>{pgr:.0f}%</span>
            </div>
            """
            st.markdown(bar_html, unsafe_allow_html=True)

            # Link to Dashboard
            # Using st.page_link if available (Streamlit 1.31+), else fallback to info
            try:
                st.page_link("pages/Progress_Dashboard.py", label="View detailed stats", icon=":material/bar_chart:")
            except AttributeError:
                st.info("Go to 'Progress Dashboard' page for details.")



# -----------------------------------------------------------------------------
# MAIN CONTENT
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
    # Load existing SRS state or get default
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

# Run App
# The exam card lives in utils/exam_view.py (shared with the practice pages).
if __name__ == "__main__":
    exam_view.render_question(submit_fn=handle_submission)
