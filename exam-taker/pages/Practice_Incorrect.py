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
st.set_page_config(page_title="Practice Incorrect", page_icon="🚫", layout="wide")

from utils import ui_helpers
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
    st.title("🚫 Practice Incorrect")
    st.info("Shows questions where you struggle historically (Wrong >= Correct) OR your last attempt was incorrect.")
    
    # Selection Mode
    st.subheader("Selection Mode")
    selection_mode = st.radio("Load by:", ["Folder", "Specific File"], index=0, key="inc_mode")
    
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
            st.success("No incorrect questions found in this selection! 🎉")

# -----------------------------------------------------------------------------
# MAIN CONTENT (Duplicated logic from app.py)
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

def render_results(q_data, user_selection):
    correct_indices = set(q_data.get("correct_indices", []))
    user_set = set(user_selection)
    options = q_data.get("options", [])
    
    # Score
    score = scoring.calculate_f1_score(user_selection, list(correct_indices))
    
    if score == 1.0:
        st.markdown('<div class="success-box">✅ <b>Perfect!</b> You got it right.</div>', unsafe_allow_html=True)
    elif score > 0:
        st.markdown(f'<div class="error-box">⚠️ <b>Partial Credit.</b> Score: {score:.2f}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="error-box">❌ <b>Incorrect.</b></div>', unsafe_allow_html=True)

    # Detailed Breakdown
    st.write("### Analysis")
    for idx, opt in enumerate(options):
        prefix = ""
        style = "color: #6b7a90;"

        if idx in correct_indices and idx in user_set:
            prefix = "✅ (Correctly Selected)"
            style = "color: #52c46e; font-weight: bold;"
        elif idx in correct_indices and idx not in user_set:
            prefix = "⚠️ (Missed)"
            style = "color: #c9a227; font-weight: bold;"
        elif idx not in correct_indices and idx in user_set:
            prefix = "❌ (Wrongly Selected)"
            style = "color: #d96060; font-weight: bold;"

        ui_helpers.render_math_text(
            f"<span style='{style}'>• {ui_helpers.prepare_math_text(opt)} {prefix}</span>",
            height=55
        )

    # Explanation
    if "explanation" in q_data:
        st.markdown("**💡 Explanation:**")
        ui_helpers.render_math_text(
            ui_helpers.prepare_math_text(q_data["explanation"]),
            extra_style="border-left:4px solid #58a6ff;padding:1rem;background:#21262d;border-radius:0 8px 8px 0;",
            height=min(500, max(100, len(q_data["explanation"]) // 5 + 40))
        )

    # User Notes / Research
    st.write("### 📝 My Notes & Research")
    
    # Load existing notes
    log_data = file_manager.load_question_log(q_data["id"])
    existing_notes = log_data.get("user_notes", "")
    existing_diagram = log_data.get("user_diagram", "")
    
    # Text Area (Rich Text with Quill)
    user_notes = st_quill(
        value=existing_notes,
        placeholder="Add your findings or additional explanation here...",
        html=True,
        key=f"notes_{q_data['id']}"
    )
    
    # Diagram Section
    st.write("#### 🧩 Logic Flow")
    
    # 1. Render Diagram (if exists)
    if existing_diagram.strip():
        st_mermaid(existing_diagram, height="300px")
    else:
        st.info("No diagram added yet.")
        
    # 2. Edit Diagram (Collapsed)
    with st.expander("✏️ Edit/Add Diagram"):
        st.caption("Use Mermaid syntax (e.g., `graph TD; A-->B;`)")
        user_diagram = st.text_area(
            "Mermaid Code",
            value=existing_diagram,
            height=150,
            key=f"diagram_{q_data['id']}"
        )
    
    if st.button("💾 Save Notes & Diagram", key=f"save_notes_{q_data['id']}"):
        file_manager.update_user_notes(q_data["id"], user_notes, user_diagram)
        st.toast("Notes & Diagram saved successfully!", icon="✅")
        st.rerun()

def render_question():
    if not st.session_state.questions:
        if st.session_state.practice_incorrect_folder:
            st.info("No incorrect questions found. Good job!")
        else:
            st.info("👈 Select a source from the sidebar to begin.")
        return

    q_data = st.session_state.questions[st.session_state.current_q_index]
    q_id = q_data.get("id", "unknown")
    
    log_data = file_manager.load_question_log(q_id)
    srs_info = log_data.get("summary", {}).get("srs", {})
    
    # Container
    st.markdown(f'<div class="question-card">', unsafe_allow_html=True)
    
    # Header
    cols = st.columns([3, 1])
    with cols[0]:
        tags = q_data.get("tags", [])
        st.caption(f"🏷️ {', '.join(tags)} | 📅 Next Due: {srs_info.get('next_due', 'New')}")
    with cols[1]:
        diff = q_data.get("difficulty", "medium").upper()
        color = {"EASY": "green", "MEDIUM": "orange", "HARD": "red"}.get(diff, "grey")
        st.markdown(f"<span style='color:{color}; font-weight:bold; float:right'>{diff}</span>", unsafe_allow_html=True)

    # Bookmark Controls
    current_bookmark = bookmark_manager.get_bookmark_status(q_id)
    
    bm_cols = st.columns([1, 3])
    with bm_cols[0]:
        # Bookmark Toggle
        bm_options = list(bookmark_manager.BOOKMARK_COLORS.keys())
        
        # Determine index
        default_idx = 0
        if current_bookmark in bm_options:
            default_idx = bm_options.index(current_bookmark)
            
        selected_bm_color = st.selectbox(
            "Bookmark Color", 
            bm_options, 
            index=default_idx, 
            key=f"bm_sel_{q_id}",
            label_visibility="collapsed"
        )
    with bm_cols[1]:
        col_add, col_remove = st.columns([1, 1])
        with col_add:
            if st.button("🔖 Bookmark", key=f"bm_btn_{q_id}"):
                bookmark_manager.save_bookmark(q_data, selected_bm_color)
                st.toast(f"Bookmarked as {selected_bm_color}!", icon="✅")
                st.rerun()
        with col_remove:
            if current_bookmark:
                if st.button("🗑️ Remove", key=f"bm_rm_{q_id}"):
                    bookmark_manager.remove_bookmark(q_id)
                    st.toast("Bookmark removed!", icon="🗑️")
                    st.rerun()
            
            
    # Archive Control
    if st.button("🗄️ Archive", key=f"arch_btn_{q_id}", help="Move to Archive (remove from active practice)"):
        archive_manager.archive_question(q_data)
        st.toast("Question archived!", icon="🗄️")
        st.rerun()

    if current_bookmark:
        st.caption(f"Currently bookmarked as: {current_bookmark}")

    # Question Text
    q_text = ui_helpers.prepare_math_text(q_data["question"])
    ui_helpers.render_math_text(q_text, font_size="1.2rem", font_weight="600",
                                height=max(70, len(q_data["question"]) // 3 + 40))

    # Options
    options = q_data.get("options", [])
    correct_indices = q_data.get("correct_indices", [])
    if not isinstance(correct_indices, list):
        correct_indices = [correct_indices]
    is_multiselect = len(correct_indices) > 1

    # Input Handling
    user_selection = []
    is_submitted = st.session_state.submitted.get(q_id, False)

    letters = [chr(65 + i) for i in range(len(options))]

    if is_multiselect:
        st.write("Assertion: **Select all that apply**")
        prev_indices = st.session_state.answers.get(q_id, [])
        user_selection = []
        for idx, opt in enumerate(options):
            ui_helpers.render_math_text(ui_helpers.prepare_math_text(opt), height=55)
            checked = st.checkbox(f"Select {letters[idx]}", value=(idx in prev_indices),
                                  key=f"chk_{q_id}_{idx}", disabled=is_submitted)
            if checked:
                user_selection.append(idx)
    else:
        # Single Select -> Radio
        prev_ans_idx_list = st.session_state.answers.get(q_id, [None])
        prev_ans_idx = prev_ans_idx_list[0] if prev_ans_idx_list else None

        default_index = None
        if prev_ans_idx is not None and 0 <= prev_ans_idx < len(options):
            default_index = prev_ans_idx

        for opt in options:
            ui_helpers.render_math_text(ui_helpers.prepare_math_text(opt), height=55)

        selected_letter = st.radio("Select your answer:", letters, index=default_index,
                                   key=f"radio_{q_id}", disabled=is_submitted)
        if selected_letter in letters:
            user_selection = [letters.index(selected_letter)]

    # Submit Button
    if not is_submitted:
        if st.button("Submit Answer", key=f"btn_{q_id}"):
            handle_submission(q_data, user_selection)
            st.rerun()
    else:
        render_results(q_data, st.session_state.answers.get(q_id, []))

    st.markdown('</div>', unsafe_allow_html=True)

    # Navigation & Actions
    st.markdown('<span id="nav-buttons-marker"></span>', unsafe_allow_html=True)
    
    if is_submitted:
        col_prev, col_retry, col_hard, col_next = st.columns([1, 1, 1, 1])
        
        with col_prev:
            if st.session_state.current_q_index > 0:
                if st.button("⬅️ Previous", key="nav_prev"):
                    st.session_state.current_q_index -= 1
                    st.rerun()
                    
        with col_retry:
            if st.button("🔄 Simple Retry", key=f"retry_{q_id}", help="Remove last attempt and try again"):
                file_manager.delete_last_attempt(q_id)
                if q_id in st.session_state.answers: del st.session_state.answers[q_id]
                if q_id in st.session_state.submitted: del st.session_state.submitted[q_id]
                st.rerun()
                
        with col_hard:
            if st.button("🛑 Hard Retry", key=f"hard_retry_{q_id}", type="primary", help="Reset all history for this question"):
                file_manager.reset_question_log(q_id)
                if q_id in st.session_state.answers: del st.session_state.answers[q_id]
                if q_id in st.session_state.submitted: del st.session_state.submitted[q_id]
                st.rerun()
                
        with col_next:
            if st.session_state.current_q_index < len(st.session_state.questions) - 1:
                if st.button("Next ➡️", key="nav_next"):
                    st.session_state.current_q_index += 1
                    st.rerun()
    else:
        col_prev, col_next = st.columns([1, 1])
        with col_prev:
            if st.session_state.current_q_index > 0:
                if st.button("⬅️ Previous", key="nav_prev_simple"):
                    st.session_state.current_q_index -= 1
                    st.rerun()
        with col_next:
            if st.session_state.current_q_index < len(st.session_state.questions) - 1:
                if st.button("Next ➡️", key="nav_next_simple"):
                    st.session_state.current_q_index += 1
                    st.rerun()

if __name__ == "__main__":
    render_question()
