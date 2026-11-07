import streamlit as st
import random
import json
from pathlib import Path
from utils import file_manager, ui_helpers, bookmark_manager, ui_components, exam_view

# --- Page Config ---
st.set_page_config(page_title="Regressive Practice", page_icon=":material/sync:", layout="wide")

# --- CSS Injection ---
ui_helpers.inject_global_css()
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
if "regressive_selection" not in st.session_state:
    st.session_state.regressive_selection = [] # indices picked at submit (display only)

QUESTIONS_ROOT = Path("questions").resolve()

def reset_session():
    st.session_state.regressive_active = False
    st.session_state.regressive_queue = []
    st.session_state.regressive_stats = {}
    st.session_state.regressive_mastered_count = 0
    st.session_state.regressive_current_q = None
    st.session_state.regressive_submitted = False
    st.session_state.regressive_feedback = None
    st.session_state.regressive_selection = []


# --- Button callbacks (run before the next script run; no st.rerun() needed) ---
def _cb_submit(q, attempts):
    """Same rules as before: streak +1 on an exact match, else streak resets to 0."""
    q_id = q["id"]
    options = q.get("options", [])
    letters = [chr(65 + i) for i in range(len(options))]
    correct_indices = q.get("correct_indices", [])
    if not isinstance(correct_indices, list):
        correct_indices = [correct_indices]

    if len(correct_indices) > 1:
        selected = [i for i in range(len(options))
                    if st.session_state.get(f"chk_{q_id}_{attempts}_{i}")]
    else:
        letter = st.session_state.get(f"opt_{q_id}_{attempts}")
        selected = [letters.index(letter)] if letter in letters else []
    if not selected:
        return

    st.session_state.regressive_submitted = True
    st.session_state.regressive_selection = selected

    # Check Answer (Set Comparison)
    is_correct = set(selected) == set(correct_indices)

    # Update Stats
    st.session_state.regressive_stats[q_id]["attempts"] += 1

    if is_correct:
        st.session_state.regressive_result = "correct"
        st.session_state.regressive_stats[q_id]["streak"] += 1
    else:
        st.session_state.regressive_result = "wrong"
        st.session_state.regressive_stats[q_id]["streak"] = 0 # Reset streak on failure! Regressive.


def _cb_next(q_id):
    is_mastered = st.session_state.regressive_stats[q_id]["streak"] >= 2
    # Logic to pick next
    if is_mastered:
        st.session_state.regressive_mastered_count += 1
        # Remove from queue
        st.session_state.regressive_queue = [x for x in st.session_state.regressive_queue if x["id"] != q_id]

    # Reset submission state
    st.session_state.regressive_submitted = False
    st.session_state.regressive_result = None
    st.session_state.regressive_selection = []

    # Pick new random question if queue not empty
    if st.session_state.regressive_queue:
        st.session_state.regressive_current_q = random.choice(st.session_state.regressive_queue)


# --- sidebar ---
with st.sidebar:
    st.title("Regressive practice")
    st.caption("Practice a specific file until you master every question (2 correct answers required).")
    st.divider()

    # File Selector
    # file_manager.get_exam_files returns relative paths from root
    all_files = file_manager.get_exam_files(str(QUESTIONS_ROOT))

    # Use relative paths directly
    short_names = all_files

    selected_file_short = st.selectbox("Select a File to Practice", short_names, disabled=st.session_state.regressive_active)

    if st.button("Start New Session", type="primary", icon=":material/play_arrow:",
                 disabled=st.session_state.regressive_active, key="reg_start"):
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
        q_remaining = len(st.session_state.regressive_queue)
        q_mastered = st.session_state.regressive_mastered_count
        st.progress(q_mastered / (q_mastered + q_remaining) if (q_mastered + q_remaining) > 0 else 0)

        if st.button("End session", key="reg_end", icon=":material/stop_circle:"):
            reset_session()
            st.rerun()

# --- Main Content ---

if not st.session_state.regressive_active:
    st.info("Select a file and click 'Start New Session' to begin.", icon=":material/info:")
    st.markdown("""
    ### How it works
    1. **Load a file**: Focus on one specific topic or exam set.
    2. **Regressive loop**: Questions repeat until you answer them correctly **2 times**.
    3. **No long-term traces**: Your main logs (history, attempts) are **NOT updated**. This session is purely ephemeral.
    4. **Focus**: Ideal for cramming or drilling weak areas without affecting your global stats.
    """)
    st.stop()

if not st.session_state.regressive_queue:
    st.success("Session complete. You have mastered all questions in this set.",
               icon=":material/check_circle:")
    if st.button("Start over", key="reg_restart", type="primary"):
        reset_session()
        st.rerun()
    st.stop()

# Get Current Question
q = st.session_state.regressive_current_q
q_id = q["id"]
stats = st.session_state.regressive_stats[q_id]

# Session stats as tiles above the card
tile_queue, tile_mastered, tile_streak = st.columns(3)
tile_queue.metric("In queue", len(st.session_state.regressive_queue))
tile_mastered.metric("Mastered", st.session_state.regressive_mastered_count)
tile_streak.metric("Streak", f"{stats['streak']} of 2")

options = q.get("options", [])
correct_indices = q.get("correct_indices", [])
if not isinstance(correct_indices, list):
    correct_indices = [correct_indices]
is_multiselect = len(correct_indices) > 1
letters = [chr(65 + i) for i in range(len(options))]
is_submitted = st.session_state.regressive_submitted

user_selected_indices = []

with st.container(border=True, key="qcard"):
    # Header: difficulty + mastery badges, tags
    tags = q.get("tags", [])
    meta = (
        '<div class="etp-meta">'
        + ui_components.difficulty_badge(q.get("difficulty", "medium"))
        + ui_components.badge("info", f"Mastery {stats['streak']} of 2")
        + (f'<span class="etp-tag">{" · ".join(ui_components._esc(t) for t in tags)}</span>' if tags else "")
        + "</div>"
    )
    st.markdown(meta, unsafe_allow_html=True)

    # "Question N": how many questions this session has shown (attempts are counted at submit)
    n_shown = sum(s["attempts"] for s in st.session_state.regressive_stats.values()) + (0 if is_submitted else 1)
    st.markdown(f'<div class="etp-qnum">Question {n_shown}</div>', unsafe_allow_html=True)

    with st.container(key="qstem"):
        st.markdown(ui_components.md_text(q["question"]))

    with st.container(key="answers"):
        if is_submitted:
            selected = st.session_state.regressive_selection
            is_correct = st.session_state.get("regressive_result") == "correct"
            correct_letters = [letters[i] for i in sorted(set(correct_indices)) if 0 <= i < len(letters)]
            if is_correct:
                kind, title, body = "success", "Correct", f"Streak {stats['streak']} of 2."
            else:
                kind, title, fb_body = ui_components.feedback(0.0, correct_letters)
                body = f"{fb_body} Streak reset to 0."
            st.markdown(ui_components.feedback_banner_html(kind, title, body), unsafe_allow_html=True)
            for idx, opt in enumerate(options):
                state = ui_components.option_state(idx, correct_indices, selected)
                exam_view.render_option_row(f"{q_id}_{stats['attempts']}", idx, letters[idx], opt, state)
            exam_view.render_explanation(q_id, q.get("explanation"))
            if stats["streak"] >= 2:
                st.success("Question mastered. Removing from queue.", icon=":material/school:")
        elif is_multiselect:
            st.caption("Select all that apply")
            for idx, opt in enumerate(options):
                chk_key = f"chk_{q_id}_{stats['attempts']}_{idx}"
                is_checked = st.checkbox(exam_view.option_md(letters[idx], opt), key=chk_key)
                if is_checked:
                    user_selected_indices.append(idx)
        else:
            # Single Select
            selection = st.radio(
                "Select your answer",
                letters,
                key=f"opt_{q_id}_{stats['attempts']}",
                index=None,
                format_func=lambda L: exam_view.option_md(L, options[ord(L) - 65]),
                label_visibility="collapsed",
                width="stretch",
            )
            if selection:
                user_selected_indices.append(letters.index(selection))

# Action bar
col_gap, col_action = st.columns([3, 1.4])
with col_action:
    if not is_submitted:
        with st.container(key="nav_submit"):
            st.button("Submit Answer", type="primary", icon=":material/check:",
                      disabled=len(user_selected_indices) == 0,
                      key=f"reg_submit_{q_id}_{stats['attempts']}",
                      on_click=_cb_submit, args=(q, stats["attempts"]))
    else:
        st.button("Next Question", type="primary", icon=":material/chevron_right:",
                  key="reg_next", on_click=_cb_next, args=(q_id,))
