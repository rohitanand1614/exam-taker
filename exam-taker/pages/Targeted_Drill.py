import streamlit as st
import random
import datetime
from utils import file_manager, scoring, srs, bookmark_manager
from utils import ui_helpers, ui_components, exam_view, shortcuts

st.set_page_config(page_title="Targeted drill", page_icon=":material/target:", layout="wide")

ui_helpers.inject_global_css()
ui_helpers.inject_quill_dark_mode()

st.title("Targeted drill")

if "drill_questions" not in st.session_state or not st.session_state.drill_questions:
    st.info("No active drill session. Start a drill from the Topic analysis page.",
            icon=":material/info:")
    if st.button("Back to topic analysis", key="drill_dashboard", icon=":material/arrow_forward:"):
        st.switch_page("pages/Topic_Analysis.py")
    st.stop()

# Initialize drill variables
if "drill_index" not in st.session_state:
    st.session_state.drill_index = 0
if "drill_answers" not in st.session_state:
    st.session_state.drill_answers = {}
if "drill_submitted" not in st.session_state:
    st.session_state.drill_submitted = {}


# -----------------------------------------------------------------------------
# Button callbacks (run before the next script run: no st.rerun() needed)
# -----------------------------------------------------------------------------
def _cb_next():
    st.session_state.drill_index += 1


def _cb_submit(step_key, q_id, current_q, is_multiselect, letters):
    """Same scoring / SRS / logging / re-queue logic as before, driven from widget state."""
    if is_multiselect:
        user_selection = [i for i in range(len(letters))
                          if st.session_state.get(f"drill_chk_{step_key}_{i}")]
    else:
        letter = st.session_state.get(f"drill_radio_{step_key}")
        user_selection = [letters.index(letter)] if letter in letters else []

    # Calculate Score
    correct = current_q.get("correct_indices", [])
    score = scoring.calculate_f1_score(user_selection, correct)

    # Update State using STEP KEY
    st.session_state.drill_answers[step_key] = user_selection
    st.session_state.drill_submitted[step_key] = True

    # Log Attempt
    quality = scoring.score_to_quality(score)
    log_data = file_manager.load_question_log(q_id)
    current_srs = log_data.get("summary", {}).get("srs", srs.get_initial_srs())
    new_srs = srs.update_srs(current_srs, quality)
    attempt_entry = {
        "attempt_id": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        "timestamp": datetime.datetime.now().isoformat(),
        "selected_indices": user_selection,
        "score": round(score, 2),
        "quality": quality,
        "drill_mode": True
    }
    file_manager.save_attempt_log(q_id, attempt_entry, new_srs)

    # Adaptive Logic: If wrong, append copy to end!
    if score < 1.0:
        st.session_state.drill_questions.append(current_q.copy())
        st.toast("Incorrect. Question re-queued for mastery.", icon=":material/replay:")


# Main Render Logic
current_q = st.session_state.drill_questions[st.session_state.drill_index]
q_id = current_q["id"]
# Use a unique key for storage valid only for this specific step in the drill
# This ensures that if the same question appears later, it treats it as a fresh blank slate.
step_key = f"{q_id}_{st.session_state.drill_index}"

# Sidebar Info
with st.sidebar:
    st.header("Drill status")
    total = len(st.session_state.drill_questions)
    current = st.session_state.drill_index + 1
    progress = current / total
    st.write(f"Question **{current}** of **{total}**")
    st.progress(progress)

    if st.button("Exit drill", key="drill_exit", icon=":material/logout:"):
        # Clear drill state
        del st.session_state.drill_questions
        del st.session_state.drill_index
        del st.session_state.drill_answers
        del st.session_state.drill_submitted
        st.switch_page("pages/Topic_Analysis.py")

    # Next Button
    if st.session_state.drill_index < len(st.session_state.drill_questions) - 1:
        st.button("Next question", type="primary", key=f"drill_next_{step_key}",
                  icon=":material/chevron_right:", on_click=_cb_next)
    else:
        st.success("Drill complete. You have mastered this session.", icon=":material/check_circle:")
        if st.button("Back to topic analysis", key="drill_finish"):
            del st.session_state.drill_questions
            del st.session_state.drill_index
            del st.session_state.drill_answers
            del st.session_state.drill_submitted
            st.switch_page("pages/Topic_Analysis.py")

# -----------------------------------------------------------------------------
# Question card
# -----------------------------------------------------------------------------
options = current_q.get("options", [])
is_submitted = st.session_state.drill_submitted.get(step_key, False)
correct_indices = current_q.get("correct_indices", [])
if not isinstance(correct_indices, list):
    correct_indices = [correct_indices]
is_multiselect = len(correct_indices) > 1
letters = [chr(65 + i) for i in range(len(options))]

log_data = file_manager.load_question_log(q_id)
srs_info = log_data.get("summary", {}).get("srs", {})
current_bookmark = bookmark_manager.get_bookmark_status(q_id)

shortcuts.render()

with st.container(border=True, key="qcard"):
    head_left, head_right = st.columns([3, 2])
    with head_left:
        st.markdown(
            ui_components.meta_row(current_q.get("tags", []), current_q.get("difficulty", "medium"),
                                   False, srs_info.get("next_due")),
            unsafe_allow_html=True,
        )
    with head_right:
        with st.popover(
            ui_components.bookmark_pill_label(current_bookmark) if current_bookmark else "Bookmark",
            icon=None if current_bookmark else ":material/bookmark:",
            use_container_width=True,
        ):
            bm_options = list(bookmark_manager.BOOKMARK_COLORS.keys())
            default_idx = 0
            if current_bookmark in bm_options:
                default_idx = bm_options.index(current_bookmark)
            selected_bm_color = st.pills("Colour", bm_options, default=bm_options[default_idx],
                                         format_func=ui_components.bookmark_pill_label,
                                         label_visibility="collapsed",
                                         key=f"drill_bm_sel_{step_key}") or bm_options[default_idx]
            if st.button("Save bookmark", key=f"drill_bm_btn_{step_key}", icon=":material/bookmark:"):
                bookmark_manager.save_bookmark(current_q, selected_bm_color)
                st.toast(f"Bookmarked as {selected_bm_color}.", icon=":material/check_circle:")
                st.rerun()
            if current_bookmark:
                st.caption(f"Bookmarked as {ui_components.bookmark_pill_label(current_bookmark)}")
                if st.button("Remove bookmark", key=f"drill_bm_rm_{step_key}", icon=":material/delete:"):
                    bookmark_manager.remove_bookmark(q_id)
                    st.toast("Bookmark removed.", icon=":material/delete:")
                    st.rerun()

    st.markdown(f'<div class="etp-qnum">Question {current} of {total}</div>', unsafe_allow_html=True)
    with st.container(key="qstem"):
        st.markdown(ui_components.md_text(current_q["question"]))

    with st.container(key="answers"):
        if is_submitted:
            user_selection = st.session_state.drill_answers.get(step_key, [])
            score = scoring.calculate_f1_score(user_selection, list(correct_indices))
            correct_letters = [letters[i] for i in sorted(set(correct_indices)) if 0 <= i < len(letters)]
            exam_view.render_banner(score, correct_letters)
            for idx, opt in enumerate(options):
                state = ui_components.option_state(idx, correct_indices, user_selection)
                exam_view.render_option_row(step_key, idx, letters[idx], opt, state)
            exam_view.render_explanation(step_key, current_q.get("explanation"))
            exam_view.render_notes(q_id, key_prefix="drill_")
        elif is_multiselect:
            st.caption("Select all that apply")
            for idx, opt in enumerate(options):
                st.checkbox(exam_view.option_md(letters[idx], opt), value=False,
                            key=f"drill_chk_{step_key}_{idx}")
        else:
            st.radio(
                "Select your answer",
                letters,
                index=None,
                key=f"drill_radio_{step_key}",
                format_func=lambda L: exam_view.option_md(L, options[ord(L) - 65]),
                label_visibility="collapsed",
                width="stretch",
            )

if not is_submitted:
    col_gap, col_submit = st.columns([3, 1.4])
    with col_submit:
        with st.container(key=f"drill_submit_{step_key}"):
            st.button("Submit answer", key=f"drill_btn_{step_key}", type="primary",
                      icon=":material/check:",
                      on_click=_cb_submit, args=(step_key, q_id, current_q, is_multiselect, letters))
