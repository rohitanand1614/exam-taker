"""Shared exam card for Exam Taker Pro (app.py, Practice_Incorrect, Practice_Bookmarks).

Pure presentation + button wiring. Scoring, SRS and logging stay in the page's own
`handle_submission` (passed in as `submit_fn`) and in utils.file_manager.

Differences between the pages are parameters of render_question():
    submit_fn            page-local handle_submission(q_data, user_selection)
    show_archive         Practice_Bookmarks has no archive button
    completed_state_key  only app.py has the "all done for today" state
    empty_state          callable drawing the page-specific "nothing to show" message

Helpers (render_option_row / render_banner / render_explanation / render_notes) are
also used by Targeted_Drill and Regressive_Practice, which keep their own flow.
"""
import datetime

import streamlit as st
import streamlit.components.v1 as components
from streamlit_quill import st_quill
from streamlit_mermaid import st_mermaid

from utils import archive_manager, bookmark_manager, file_manager, scoring, shortcuts, ui_components, ui_helpers

STATUS_WORD = {"correct": "Correct", "missed": "Missed", "wrong": "Your pick"}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def option_md(letter, text):
    """Markdown for one answer option: bold letter + option text without its "A) " prefix."""
    return f"**{letter}**  " + ui_components.md_text(ui_components.option_label(text))


def render_option_row(row_id, idx, letter, text, state, ratio=(8, 1.3)):
    """One result row. Container key: opt_<state>_<row_id>_<idx> (CSS hook).
    `ratio` = (text, status) column widths; narrow layouts pass a larger status share so "Correct" never wraps."""
    with st.container(key=f"opt_{state}_{row_id}_{idx}"):
        col_text, col_status = st.columns(list(ratio))
        with col_text:
            st.markdown(option_md(letter, text))
        with col_status:
            if state in STATUS_WORD:
                st.markdown(STATUS_WORD[state])


def render_banner(score, correct_letters, body_suffix=""):
    kind, title, body = ui_components.feedback(score, correct_letters)
    if body_suffix:
        body = f"{body} {body_suffix}"
    st.markdown(ui_components.feedback_banner_html(kind, title, body), unsafe_allow_html=True)


def render_explanation(row_id, text):
    """Explanation panel: container key explain_<row_id>, native markdown, grows to fit."""
    if not text:
        return
    with st.container(key=f"explain_{row_id}"):
        st.markdown('<div class="etp-explain__head">Explanation</div>', unsafe_allow_html=True)
        st.markdown(ui_components.md_text(text))


def render_notes(q_id, key_prefix=""):
    """Notes + diagram in ONE expander (Streamlit forbids nested expanders).
    Widget keys: <prefix>notes_<id>, <prefix>diagram_<id>, <prefix>save_notes_<id>."""
    log_data = file_manager.load_question_log(q_id)
    existing_notes = log_data.get("user_notes", "")
    existing_diagram = log_data.get("user_diagram", "")
    with st.expander("My notes & diagram", icon=":material/edit_note:"):
        user_notes = st_quill(
            value=existing_notes,
            placeholder="Add your findings or additional explanation here...",
            html=True,
            key=f"{key_prefix}notes_{q_id}",
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
            key=f"{key_prefix}diagram_{q_id}",
            help="Mermaid syntax, for example: graph TD; A-->B;",
        )

        if st.button("Save notes & diagram", key=f"{key_prefix}save_notes_{q_id}",
                     icon=":material/save:"):
            file_manager.update_user_notes(q_id, user_notes, user_diagram)
            st.toast("Notes and diagram saved.", icon=":material/check_circle:")
            st.rerun()


def render_review_card(row_id, q_data, selected=None):
    """Read-only card for the list pages: option rows + explanation.

    selected=None  -> no attempt to show: right answers in the "correct" style
    selected=[...] -> your picks: Correct / Missed / Your pick, as on the exam page
    `row_id` must be unique on the page (it is part of the container keys).
    """
    options = q_data.get("options", [])
    correct = q_data.get("correct_indices", [])
    if not isinstance(correct, list):
        correct = [correct]
    for idx, opt in enumerate(options):
        if selected is None:
            state = "correct" if idx in correct else "neutral"
        else:
            state = ui_components.option_state(idx, correct, selected)
        render_option_row(row_id, idx, chr(65 + idx), opt, state)
    render_explanation(row_id, q_data.get("explanation"))


# ---------------------------------------------------------------------------
# button callbacks: run BEFORE the next script run, so no st.rerun() is needed
# ---------------------------------------------------------------------------
def _cb_step(delta):
    st.session_state.current_q_index += delta


def _cb_submit(q_data, letters, is_multiselect, submit_fn):
    q_id = q_data.get("id", "unknown")
    if is_multiselect:
        selection = [i for i in range(len(letters)) if st.session_state.get(f"chk_{q_id}_{i}")]
    else:
        letter = st.session_state.get(f"radio_{q_id}")
        selection = [letters.index(letter)] if letter in letters else []
    submit_fn(q_data, selection)


def _cb_simple_retry(q_id):
    file_manager.delete_last_attempt(q_id)
    if q_id in st.session_state.answers: del st.session_state.answers[q_id]
    if q_id in st.session_state.submitted: del st.session_state.submitted[q_id]


def _cb_hard_retry(q_id):
    file_manager.reset_question_log(q_id)
    if q_id in st.session_state.answers: del st.session_state.answers[q_id]
    if q_id in st.session_state.submitted: del st.session_state.submitted[q_id]


# ---------------------------------------------------------------------------
# "All done for today" card (app.py only)
# ---------------------------------------------------------------------------
_FOCUS_EXAM_SELECT = (
    "<script>(function(){var sel=window.parent.document.querySelector("
    "'[data-testid=\"stSidebar\"] [data-baseweb=\"select\"]');if(!sel)return;"
    "sel.scrollIntoView({block:'center',behavior:'smooth'});"
    "var input=sel.querySelector('input');if(input){input.focus();"
    "input.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true}));}})();</script>"
)


def answered_today(exam):
    """How many questions of this exam have an attempt logged today (same data and date test as app.py)."""
    today = datetime.date.today().isoformat()
    count = 0
    for q in file_manager.load_questions("questions", exam):
        attempts = file_manager.load_question_log(q.get("id")).get("attempts", [])
        if any(str(a.get("timestamp", "")).startswith(today) for a in attempts):
            count += 1
    return count


def render_all_done():
    exam = st.session_state.get("current_exam_folder") or "this exam"
    n = answered_today(exam)
    line = (f"{n} question{'' if n == 1 else 's'} answered today in {exam}." if n
            else f"Nothing is due in {exam} today.")
    with st.container(border=True, key="all_done"):
        st.markdown(":material/check_circle: **All done for today**")
        st.markdown(line)
        # only focuses the sidebar exam select: no state changes (the click just reruns the page)
        if st.button("Choose another exam", key="all_done_choose", icon=":material/menu_book:"):
            components.html(_FOCUS_EXAM_SELECT, height=0)


# ---------------------------------------------------------------------------
# the exam card
# ---------------------------------------------------------------------------
def render_question(*, submit_fn, show_archive=True, completed_state_key="all_completed_today",
                    empty_state=None):
    if completed_state_key and st.session_state.get(completed_state_key):
        render_all_done()
        return

    if not st.session_state.questions:
        if empty_state is not None:
            empty_state()
        else:
            st.info("Select an exam in the sidebar to begin.", icon=":material/info:")
        return

    shortcuts.render()      # keyboard: 1-9/A-H answer, Enter submit, N/P or arrows next/previous, Shift+B bookmark

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
            if show_archive:
                bm_col, arch_col = st.columns([11, 9])  # "Bookmarked" is longer than "Archive", but both must fit
            else:
                bm_col, arch_col = st.container(), None
            with bm_col:
                with st.popover(
                    ui_components.bookmark_pill_label(current_bookmark) if current_bookmark else "Bookmark",
                    icon=None if current_bookmark else ":material/bookmark:",
                    use_container_width=True,
                ):
                    bm_options = list(bookmark_manager.BOOKMARK_COLORS.keys())
                    default_idx = 0
                    if current_bookmark in bm_options:
                        default_idx = bm_options.index(current_bookmark)
                    selected_bm_color = st.pills(
                        "Colour",
                        bm_options,
                        default=bm_options[default_idx],
                        format_func=ui_components.bookmark_pill_label,
                        label_visibility="collapsed",
                        key=f"bm_sel_{q_id}",
                    ) or bm_options[default_idx]
                    if st.button("Save bookmark", key=f"bm_btn_{q_id}", icon=":material/bookmark:"):
                        bookmark_manager.save_bookmark(q_data, selected_bm_color)
                        st.toast(f"Bookmarked as {ui_components.bookmark_style(selected_bm_color)[1]}.", icon=":material/check_circle:")
                        st.rerun()
                    if current_bookmark:
                        st.caption(f"Bookmarked as {ui_components.bookmark_pill_label(current_bookmark)}")
                        if st.button("Remove bookmark", key=f"bm_rm_{q_id}", icon=":material/delete:"):
                            bookmark_manager.remove_bookmark(q_id)
                            st.toast("Bookmark removed.", icon=":material/delete:")
                            st.rerun()
            if arch_col is not None:
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
            st.markdown(ui_components.md_text(q_data["question"]))

        # One keyed container for the whole answer area.
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
                    width="stretch",
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
                          on_click=_cb_submit, args=(q_data, letters, is_multiselect, submit_fn))


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
    log_data = file_manager.load_question_log(q_id)
    next_due = log_data.get("summary", {}).get("srs", {}).get("next_due")
    render_banner(score, correct_letters, f"Next review: {next_due}." if next_due else "")

    # Option rows carry the result: Correct / Missed / Your pick
    for idx, opt in enumerate(options):
        state = ui_components.option_state(idx, correct_indices, user_selection)
        render_option_row(q_id, idx, letters[idx], opt, state)

    render_explanation(q_id, q_data.get("explanation"))
    render_notes(q_id)
