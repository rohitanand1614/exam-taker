import streamlit as st
import random
import json
from pathlib import Path
from utils import file_manager, ui_helpers, bookmark_manager

# --- Page Config ---
st.set_page_config(page_title="Regressive Practice", page_icon="🔁", layout="wide")

# --- CSS Injection ---
ui_helpers.inject_global_css()
st.markdown("""
<style>
    .status-metric {
        background-color: #1e2538;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #252e42;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)
ui_helpers.inject_quill_dark_mode()

# --- Session State Management ---
if "regressive_active" not in st.session_state:
    st.session_state.regressive_active = False
if "regressive_queue" not in st.session_state:
    st.session_state.regressive_queue = [] # List of Q IDs
if "regressive_stats" not in st.session_state:
    st.session_state.regressive_stats = {} # {qid: {streak: 0, attempts: 0}}
if "regressive_mastered_count" not in st.session_state:
    st.session_state.regressive_mastered_count = 0
if "regressive_current_q" not in st.session_state:
    st.session_state.regressive_current_q = None # Current Question Object
if "regressive_submitted" not in st.session_state:
    st.session_state.regressive_submitted = False
if "regressive_feedback" not in st.session_state:
    st.session_state.regressive_feedback = None # "correct" or "wrong"

QUESTIONS_ROOT = Path("questions").resolve()

def reset_session():
    st.session_state.regressive_active = False
    st.session_state.regressive_queue = []
    st.session_state.regressive_stats = {}
    st.session_state.regressive_mastered_count = 0
    st.session_state.regressive_current_q = None
    st.session_state.regressive_submitted = False
    st.session_state.regressive_feedback = None

# --- sidebar ---
with st.sidebar:
    st.title("🔁 Regressive Practice")
    st.markdown("Practice a specific file until you master every question (2 correct answers required).")
    st.divider()

    # File Selector
    # file_manager.get_exam_files returns relative paths from root
    all_files = file_manager.get_exam_files(str(QUESTIONS_ROOT))
    
    # Use relative paths directly
    short_names = all_files
    
    selected_file_short = st.selectbox("Select a File to Practice", short_names, disabled=st.session_state.regressive_active)
    
    if st.button("🚀 Start New Session", type="primary", disabled=st.session_state.regressive_active):
        if selected_file_short:
            # Load questions
            full_path = QUESTIONS_ROOT / selected_file_short
            questions = file_manager.load_questions(str(QUESTIONS_ROOT), str(full_path))
            
            if not questions:
                st.error("No questions found in file.")
            else:
                # Init Session
                st.session_state.regressive_active = True
                st.session_state.regressive_queue = [q for q in questions] # Copy
                st.session_state.regressive_stats = {q["id"]: {"streak": 0, "attempts": 0} for q in questions}
                st.session_state.regressive_mastered_count = 0
                st.session_state.regressive_submitted = False
                
                # Pick first random question
                st.session_state.regressive_current_q = random.choice(st.session_state.regressive_queue)
                st.rerun()

    if st.session_state.regressive_active:
        st.divider()
        st.subheader("Session Stats")
        
        q_remaining = len(st.session_state.regressive_queue)
        q_mastered = st.session_state.regressive_mastered_count
        
        col1, col2 = st.columns(2)
        with col1:
             st.markdown(f"<div class='status-metric'><h3>{q_remaining}</h3><p>Queue</p></div>", unsafe_allow_html=True)
        with col2:
             st.markdown(f"<div class='status-metric'><h3>{q_mastered}</h3><p>Mastered</p></div>", unsafe_allow_html=True)

        st.progress(q_mastered / (q_mastered + q_remaining) if (q_mastered + q_remaining) > 0 else 0)
        
        st.divider()
        if st.button("🔴 End Session"):
            reset_session()
            st.rerun()

# --- Main Content ---

if not st.session_state.regressive_active:
    st.info("👈 Select a file and click 'Start New Session' to begin.")
    st.markdown("""
    ### How it works:
    1. **Load a file**: Focus on one specific topic or exam set.
    2. **Regressive Loop**: Questions repeat until you answer them correctly **2 times**.
    3. **No Long-term Traces**: Your main logs (history, attempts) are **NOT updated**. This session is purely ephemeral.
    4. **Focus**: Ideal for cramming or drilling weak areas without affecting your global stats.
    """)
    st.stop()

if not st.session_state.regressive_queue:
    st.success("🎉 Session Complete! You have mastered all questions in this set.")
    if st.button("Start Over"):
        reset_session()
        st.rerun()
    st.stop()

# Get Current Question
q = st.session_state.regressive_current_q
q_id = q["id"]
stats = st.session_state.regressive_stats[q_id]

# Layout
st.markdown(f'<div class="question-card">', unsafe_allow_html=True)

# Question Header (Tags + Streak Info)
cols = st.columns([3, 1])
with cols[0]:
    tags = q.get("tags", [])
    st.caption(f"🏷️ {', '.join(tags)}")
with cols[1]:
    streak = stats["streak"]
    # Visual indicator of streak
    stars = "⭐" * streak + "⚪" * (2 - streak)
    st.caption(f"Mastery: {stars} ({streak}/2)")

# Question Text
ui_helpers.render_math_text(
    ui_helpers.prepare_math_text(q["question"]),
    font_size="1.2rem", font_weight="600",
    height=max(70, len(q["question"]) // 3 + 40)
)

# Options
options = q.get("options", [])
correct_indices = q.get("correct_indices", [])
if not isinstance(correct_indices, list):
    correct_indices = [correct_indices]

is_multiselect = len(correct_indices) > 1

user_selected_indices = []
letters = [chr(65 + i) for i in range(len(options))]

if is_multiselect:
    st.write("Assertion: **Select all that apply**")
    for idx, opt in enumerate(options):
        ui_helpers.render_math_text(ui_helpers.prepare_math_text(opt), height=55)
        chk_key = f"chk_{q_id}_{stats['attempts']}_{idx}"
        is_checked = st.checkbox(
            f"Select {letters[idx]}",
            key=chk_key,
            disabled=st.session_state.regressive_submitted
        )
        if is_checked:
            user_selected_indices.append(idx)
else:
    # Single Select
    for opt in options:
        ui_helpers.render_math_text(ui_helpers.prepare_math_text(opt), height=55)
    selection = st.radio(
        "Select your answer:",
        letters,
        key=f"opt_{q_id}_{stats['attempts']}",
        disabled=st.session_state.regressive_submitted,
        index=None
    )
    if selection:
        user_selected_indices.append(letters.index(selection))

submit_col, next_col = st.columns([1, 4])

# Submit Logic
if not st.session_state.regressive_submitted:
    # Disable if empty selection
    if st.button("Submit Answer", type="primary", disabled=len(user_selected_indices) == 0):
        st.session_state.regressive_submitted = True
        
        # Check Answer (Set Comparison)
        is_correct = set(user_selected_indices) == set(correct_indices)
        
        # Update Stats
        st.session_state.regressive_stats[q_id]["attempts"] += 1
        
        if is_correct:
            st.session_state.regressive_result = "correct"
            st.session_state.regressive_stats[q_id]["streak"] += 1
        else:
            st.session_state.regressive_result = "wrong"
            st.session_state.regressive_stats[q_id]["streak"] = 0 # Reset streak on failure! Regressive.
        
        st.rerun()

# Post-Submit View
else:
    # Color the options
    if st.session_state.regressive_result == "correct":
        st.markdown(f"<div class='success-box'>✅ <b>Correct!</b> Streak: {stats['streak']}/2</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='error-box'>❌ <b>Incorrect.</b> Streak reset to 0.<br><b>Correct Answer(s):</b></div>", unsafe_allow_html=True)
        for i in correct_indices:
            ui_helpers.render_math_text(ui_helpers.prepare_math_text(options[i]), height=55)

    # Explanation
    if q.get("explanation"):
        with st.expander("📖 View Explanation", expanded=True):
            ui_helpers.render_math_text(
                ui_helpers.prepare_math_text(q["explanation"]),
                height=min(500, max(100, len(q["explanation"]) // 5 + 40))
            )
            
    # Next Button
    # Next Button
    is_mastered = st.session_state.regressive_stats[q_id]["streak"] >= 2
    if is_mastered:
        st.success("🎓 Question Mastered! Removing from queue.")
    
    if st.button("Next Question ➡️", type="primary"):
        # Logic to pick next
        if is_mastered:
            st.session_state.regressive_mastered_count += 1
            # Remove from queue
            st.session_state.regressive_queue = [x for x in st.session_state.regressive_queue if x["id"] != q_id]
            
        # Reset submission state
        st.session_state.regressive_submitted = False
        st.session_state.regressive_result = None
        
        # Pick new random question if queue not empty
        if st.session_state.regressive_queue:
            st.session_state.regressive_current_q = random.choice(st.session_state.regressive_queue)
        
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
