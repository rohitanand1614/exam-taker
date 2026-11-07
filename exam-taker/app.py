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

from utils import ui_helpers, ui_components
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

def option_md(letter, text):
    """Markdown for one answer option: bold letter + option text without its "A) " prefix."""
    return f"**{letter}**  " + ui_components.md_safe(ui_helpers.prepare_math_text(ui_components.option_label(text)))


# Button callbacks run BEFORE the next script run, so no st.rerun() is needed for
# navigation / submit / retry (no half-drawn first pass, cleaner for AppTest too).
def _cb_step(delta):
    st.session_state.current_q_index += delta


def _cb_submit(q_data, letters, is_multiselect):
    q_id = q_data.get("id", "unknown")
    if is_multiselect:
        selection = [i for i in range(len(letters)) if st.session_state.get(f"chk_{q_id}_{i}")]
    else:
        letter = st.session_state.get(f"radio_{q_id}")
        selection = [letters.index(letter)] if letter in letters else []
    handle_submission(q_data, selection)


def _cb_simple_retry(q_id):
    file_manager.delete_last_attempt(q_id)
    if q_id in st.session_state.answers: del st.session_state.answers[q_id]
    if q_id in st.session_state.submitted: del st.session_state.submitted[q_id]


def _cb_hard_retry(q_id):
    file_manager.reset_question_log(q_id)
    if q_id in st.session_state.answers: del st.session_state.answers[q_id]
    if q_id in st.session_state.submitted: del st.session_state.submitted[q_id]


def render_question():
    if st.session_state.all_completed_today:
        st.success("All questions from this section are completed for today. Great job.",
                   icon=":material/check_circle:")
        st.info("Select another exam from the sidebar to continue studying.", icon=":material/info:")
        return

    if not st.session_state.questions:
        st.info("Select an exam in the sidebar to begin.", icon=":material/info:")
        return

    q_data = st.session_state.questions[st.session_state.current_q_index]
    q_id = q_data.get("id", "unknown")
    total_questions = len(st.session_state.questions)

    # Load previous history for context (SRS status)
    log_data = file_manager.load_question_log(q_id)
    srs_info = log_data.get("summary", {}).get("srs", {})

    options = q_data.get("options", [])
    correct_indices = q_data.get("correct_indices", [])
    if not isinstance(correct_indices, list):
        correct_indices = [correct_indices]
    is_multiselect = len(correct_indices) > 1
    is_submitted = st.session_state.submitted.get(q_id, False)
    letters = [chr(65 + i) for i in range(len(options))]
    current_bookmark = bookmark_manager.get_bookmark_status(q_id)

    user_selection = []

    with st.container(border=True, key="qcard"):
        # Header: badges + tags (left), bookmark / archive tools (right)
        head_left, head_right = st.columns([3, 2])
        with head_left:
            st.markdown(
                ui_components.meta_row(
                    q_data.get("tags", []),
                    q_data.get("difficulty", "medium"),
                    bool(q_data.get("is_reattempt")),
                    srs_info.get("next_due"),
                ),
                unsafe_allow_html=True,
            )
        with head_right:
            bm_col, arch_col = st.columns(2)
            with bm_col:
                with st.popover(
                    "Bookmarked" if current_bookmark else "Bookmark",
                    icon=":material/bookmark_added:" if current_bookmark else ":material/bookmark:",
                    use_container_width=True,
                ):
                    bm_options = list(bookmark_manager.BOOKMARK_COLORS.keys())
                    default_idx = 0
                    if current_bookmark in bm_options:
                        default_idx = bm_options.index(current_bookmark)
                    selected_bm_color = st.selectbox(
                        "Colour",
                        bm_options,
                        index=default_idx,
                        key=f"bm_sel_{q_id}",
                    )
                    if st.button("Save bookmark", key=f"bm_btn_{q_id}", icon=":material/bookmark:"):
                        bookmark_manager.save_bookmark(q_data, selected_bm_color)
                        st.toast(f"Bookmarked as {selected_bm_color}.", icon=":material/check_circle:")
                        st.rerun()
                    if current_bookmark:
                        st.caption(f"Currently bookmarked as: {current_bookmark}")
                        if st.button("Remove bookmark", key=f"bm_rm_{q_id}", icon=":material/delete:"):
                            bookmark_manager.remove_bookmark(q_id)
                            st.toast("Bookmark removed.", icon=":material/delete:")
                            st.rerun()
            with arch_col:
                if st.button("Archive", key=f"arch_btn_{q_id}", type="tertiary",
                             icon=":material/archive:",
                             help="Move to Archive (remove from active practice)"):
                    archive_manager.archive_question(q_data)
                    st.toast("Question archived.", icon=":material/archive:")
                    st.rerun()

        # "Question N of M" overline, then the stem (native markdown + LaTeX)
        st.markdown(
            f'<div class="etp-qnum">Question {st.session_state.current_q_index + 1} of {total_questions}</div>',
            unsafe_allow_html=True,
        )
        with st.container(key="qstem"):
            st.markdown(ui_components.md_safe(ui_helpers.prepare_math_text(q_data["question"])))

        # One keyed container for the whole answer area, so switching question / state
        # replaces it as a unit (no leftovers from a longer previous question).
        with st.container(key="answers"):
            if is_submitted:
                # Results are drawn on the option rows themselves (no radio / checkboxes).
                render_results(q_data, st.session_state.answers.get(q_id, []))
            elif is_multiselect:
                st.caption("Select all that apply")
                prev_indices = st.session_state.answers.get(q_id, [])
                for idx, opt in enumerate(options):
                    checked = st.checkbox(
                        option_md(letters[idx], opt),
                        value=(idx in prev_indices),
                        key=f"chk_{q_id}_{idx}",
                    )
                    if checked:
                        user_selection.append(idx)
            else:
                # Single select -> radio; values stay letters, labels show the option text
                prev_ans_idx_list = st.session_state.answers.get(q_id, [None])
                prev_ans_idx = prev_ans_idx_list[0] if prev_ans_idx_list else None

                default_index = None
                if prev_ans_idx is not None and 0 <= prev_ans_idx < len(options):
                    default_index = prev_ans_idx

                selected_letter = st.radio(
                    "Select your answer",
                    letters,
                    index=default_index,
                    key=f"radio_{q_id}",
                    format_func=lambda L: option_md(L, options[ord(L) - 65]),
                    label_visibility="collapsed",
                )
                if selected_letter in letters:
                    user_selection = [letters.index(selected_letter)]

    # Navigation & actions (keyed containers / keyed buttons are the CSS hooks)
    last_index = len(st.session_state.questions) - 1
    if is_submitted:
        col_prev, col_retry, col_hard, col_gap, col_next = st.columns([1.2, 1.2, 1.2, 0.6, 1])

        with col_prev:
            if st.session_state.current_q_index > 0:
                st.button("Previous", key="nav_prev", icon=":material/chevron_left:",
                          on_click=_cb_step, args=(-1,))

        with col_retry:
            with st.container(key="nav_retry"):
                st.button("Simple retry", key=f"retry_{q_id}", icon=":material/replay:",
                          help="Remove last attempt and try again",
                          on_click=_cb_simple_retry, args=(q_id,))

        with col_hard:
            with st.container(key="nav_hard"):
                st.button("Hard retry", key=f"hard_retry_{q_id}", icon=":material/restart_alt:",
                          help="Reset all history for this question",
                          on_click=_cb_hard_retry, args=(q_id,))

        with col_next:
            if st.session_state.current_q_index < last_index:
                # NB: a container may not reuse a widget key, so the button's own key is the hook
                st.button("Next", key="nav_next", type="primary", icon=":material/chevron_right:",
                          on_click=_cb_step, args=(1,))
    else:
        col_prev, col_gap, col_next, col_submit = st.columns([1, 1.6, 1, 1.4])

        with col_prev:
            if st.session_state.current_q_index > 0:
                st.button("Previous", key="nav_prev_simple", icon=":material/chevron_left:",
                          on_click=_cb_step, args=(-1,))

        with col_next:
            if st.session_state.current_q_index < last_index:
                st.button("Next", key="nav_next_simple", icon=":material/chevron_right:",
                          on_click=_cb_step, args=(1,))

        with col_submit:
            with st.container(key="nav_submit"):
                st.button("Submit answer", key=f"btn_{q_id}", type="primary",
                          icon=":material/check:",
                          on_click=_cb_submit, args=(q_data, letters, is_multiselect))

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
    q_id = q_data["id"]
    correct_indices = q_data.get("correct_indices", [])
    if not isinstance(correct_indices, list):
        correct_indices = [correct_indices]
    options = q_data.get("options", [])
    letters = [chr(65 + i) for i in range(len(options))]

    # Score + feedback banner (body mentions the next review date from SRS)
    score = scoring.calculate_f1_score(user_selection, list(correct_indices))
    correct_letters = [letters[i] for i in sorted(set(correct_indices)) if 0 <= i < len(letters)]
    kind, title, body = ui_components.feedback(score, correct_letters)

    log_data = file_manager.load_question_log(q_id)
    next_due = log_data.get("summary", {}).get("srs", {}).get("next_due")
    if next_due:
        body = f"{body} Next review: {next_due}."
    st.markdown(ui_components.feedback_banner_html(kind, title, body), unsafe_allow_html=True)

    # Option rows carry the result: Correct / Missed / Your pick
    status_word = {"correct": "Correct", "missed": "Missed", "wrong": "Your pick"}
    for idx, opt in enumerate(options):
        state = ui_components.option_state(idx, correct_indices, user_selection)
        with st.container(key=f"opt_{state}_{q_id}_{idx}"):
            col_text, col_status = st.columns([8, 1.3])
            with col_text:
                st.markdown(option_md(letters[idx], opt))
            with col_status:
                if state in status_word:
                    st.markdown(status_word[state])

    # Explanation (grows to fit)
    explanation = q_data.get("explanation")
    if explanation:
        with st.container(key=f"explain_{q_id}"):
            st.markdown('<div class="etp-explain__head">Explanation</div>', unsafe_allow_html=True)
            st.markdown(ui_components.md_safe(ui_helpers.prepare_math_text(explanation)))

    # Notes + diagram in one expander (no nested expanders allowed)
    existing_notes = log_data.get("user_notes", "")
    existing_diagram = log_data.get("user_diagram", "")
    with st.expander("My notes & diagram", icon=":material/edit_note:"):
        user_notes = st_quill(
            value=existing_notes,
            placeholder="Add your findings or additional explanation here...",
            html=True,
            key=f"notes_{q_id}"
        )

        st.markdown("**Logic flow**")
        if existing_diagram.strip():
            st_mermaid(existing_diagram, height="300px")
        else:
            st.caption("No diagram added yet.")

        user_diagram = st.text_area(
            "Mermaid code",
            value=existing_diagram,
            height=150,
            key=f"diagram_{q_id}",
            help="Mermaid syntax, for example: graph TD; A-->B;"
        )

        if st.button("Save notes & diagram", key=f"save_notes_{q_id}", icon=":material/save:"):
            file_manager.update_user_notes(q_id, user_notes, user_diagram)
            st.toast("Notes and diagram saved.", icon=":material/check_circle:")
            st.rerun()

# Run App
if __name__ == "__main__":
    render_question()
