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
st.set_page_config(page_title="Exam Taker Pro", page_icon="📝", layout="wide")

from utils import ui_helpers
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
    st.title("📚 Exam Taker Pro")
    
    # 1. Selection Mode
    st.subheader("Selection Mode")
    selection_mode = st.radio("Load by:", ["Folder", "Specific File"], index=0)
    
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
    mode = st.radio("Mode", ["Standard", "Shuffled"], index=0)
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
            
            # Custom HTML Bar
            bar_html = f"""
            <div style="display: flex; width: 100%; height: 20px; border-radius: 10px; overflow: hidden; background-color: #252e42;">
                <div style="width: {pg}%; background-color: #2d8f4a;" title="Mastered: {g} ({pg:.1f}%)"></div>
                <div style="width: {py}%; background-color: #8a6e00;" title="Mixed: {y} ({py:.1f}%)"></div>
                <div style="width: {pr}%; background-color: #b84040;" title="Struggling: {r} ({pr:.1f}%)"></div>
                <div style="width: {pgr}%; background-color: #3a4558;" title="Unattempted: {gr} ({pgr:.1f}%)"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #6b7a90; margin-top: 4px;">
                <span style="color: #52c46e;">{pg:.0f}%</span>
                <span style="color: #c9a227;">{py:.0f}%</span>
                <span style="color: #d96060;">{pr:.0f}%</span>
                <span>{pgr:.0f}%</span>
            </div>
            """
            st.markdown(bar_html, unsafe_allow_html=True)
            
            # Link to Dashboard
            # Using st.page_link if available (Streamlit 1.31+), else fallback to info
            try:
                st.page_link("pages/Progress_Dashboard.py", label="View Detailed Stats", icon="📊")
            except AttributeError:
                st.info("Go to 'Progress Dashboard' page for details.")



# -----------------------------------------------------------------------------
# MAIN CONTENT
# -----------------------------------------------------------------------------

def render_question():
    if st.session_state.all_completed_today:
        st.success("🎉 All questions from this section are completed for today! Great job.")
        st.info("Select another exam from the sidebar to continue studying.")
        return

    if not st.session_state.questions:
        st.info("👈 Select an exam from the sidebar to begin.")
        return

    q_data = st.session_state.questions[st.session_state.current_q_index]
    q_id = q_data.get("id", "unknown")
    
    # Load previous history for context (SRS status)
    log_data = file_manager.load_question_log(q_id)
    srs_info = log_data.get("summary", {}).get("srs", {})
    
    # Container
    st.markdown(f'<div class="question-card">', unsafe_allow_html=True)
    
    # Header: Tags & Difficulty
    cols = st.columns([3, 1])
    with cols[0]:
        tags = q_data.get("tags", [])
        reattempt_badge = "🔄 **REATTEMPT** | " if q_data.get("is_reattempt") else ""
        st.caption(f"{reattempt_badge}🏷️ {', '.join(tags)} | 📅 Next Due: {srs_info.get('next_due', 'New')}")
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

    # If already submitted, disable inputs
    is_submitted = st.session_state.submitted.get(q_id, False)

    letters = [chr(65 + i) for i in range(len(options))]

    if is_multiselect:
        st.write("Assertion: **Select all that apply**")
        prev_indices = st.session_state.answers.get(q_id, [])
        for idx, opt in enumerate(options):
            ui_helpers.render_math_text(ui_helpers.prepare_math_text(opt), height=55)
            checked = st.checkbox(
                f"Select {letters[idx]}",
                value=(idx in prev_indices),
                key=f"chk_{q_id}_{idx}",
                disabled=is_submitted
            )
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

        selected_letter = st.radio(
            "Select your answer:",
            letters,
            index=default_index,
            key=f"radio_{q_id}",
            disabled=is_submitted
        )
        if selected_letter in letters:
            user_selection = [letters.index(selected_letter)]

    # Submit Button
    if not is_submitted:
        if st.button("Submit Answer", key=f"btn_{q_id}"):
            handle_submission(q_data, user_selection)
            st.rerun()
    else:
        # Show Results
        render_results(q_data, st.session_state.answers.get(q_id, []))

    st.markdown('</div>', unsafe_allow_html=True) # End card

    # Navigation & Actions
    st.markdown('<span id="nav-buttons-marker"></span>', unsafe_allow_html=True)
    
    if is_submitted:
        # 4 Columns: Previous | Simple Retry | Hard Retry | Next
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
        # 2 Columns: Previous | Next
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
        # We need to get the value from the text area inside the expander
        # Streamlit widgets inside expanders are accessible via session state or return value if not rerunning immediately
        # Here we use the variable 'user_diagram' which holds the current value
        file_manager.update_user_notes(q_data["id"], user_notes, user_diagram)
        st.toast("Notes & Diagram saved successfully!", icon="✅")
        st.rerun()

# Run App
if __name__ == "__main__":
    render_question()
