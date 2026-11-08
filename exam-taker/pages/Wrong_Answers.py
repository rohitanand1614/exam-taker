import streamlit as st
import sys
import os
import datetime

# Ensure the root directory is in the path so we can import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import file_manager, ui_helpers, ui_components, exam_view

st.set_page_config(page_title="Wrong answers", page_icon=":material/cancel:", layout="wide")

ui_helpers.inject_global_css()

# The page head shows the count, so reserve its place first and fill it below.
head_slot = st.empty()


def _last_on(timestamp):
    """'last on 5 Nov' from an ISO timestamp (falls back to the raw text)."""
    try:
        dt = datetime.datetime.fromisoformat(timestamp)
        return f"last on {dt.day} {dt:%b}"
    except (TypeError, ValueError):
        return f"last on {timestamp}" if timestamp else "last attempt unknown"


# Filters (main area)
f_mode, f_source, f_criteria = st.columns([1.1, 1.6, 1.6])
with f_mode:
    selection_mode = st.radio("Load by", ["Folder", "Specific File"], index=0, horizontal=True)

if selection_mode == "Folder":
    available_options = file_manager.get_exam_folders("questions")
    label = "Choose a subject/topic"
else:
    available_options = file_manager.get_exam_files("questions")
    label = "Choose a JSON file"

with f_source:
    selected_option = st.selectbox(label, available_options)
with f_criteria:
    filter_mode = st.radio("Filter criteria", ["Last Attempt Incorrect", "Ever Incorrect"], index=0,
                           horizontal=True)

if not selected_option:
    head_slot.markdown(ui_components.page_head_html("Wrong answers", "Pick a source to see your mistakes"),
                       unsafe_allow_html=True)
    st.info("Select a folder or file to view mistakes.", icon=":material/info:")
    st.stop()

# Load Questions
questions = file_manager.load_questions("questions", selected_option)
wrong_questions = []

# Filter Questions
for q in questions:
    q_id = q.get("id")
    if not q_id:
        continue

    log_data = file_manager.load_question_log(q_id)
    attempts = log_data.get("attempts", [])

    if not attempts:
        continue

    is_wrong = False

    if filter_mode == "Last Attempt Incorrect":
        # Check if the last attempt had a score < 1.0
        last_attempt = attempts[-1]
        if last_attempt["score"] < 1.0:
            is_wrong = True
            q["display_attempt"] = last_attempt
    else:
        # Check if any attempt had a score < 1.0
        # We will display the *latest* attempt for context, even if the user eventually got it right?
        # Or maybe the latest *wrong* attempt?
        # Let's show the latest attempt regardless, but include it if *any* were wrong.
        if log_data.get("summary", {}).get("wrong_count", 0) > 0:
            is_wrong = True
            q["display_attempt"] = attempts[-1]

    if is_wrong:
        q["wrong_count"] = log_data.get("summary", {}).get("wrong_count", 0)  # already in the log
        wrong_questions.append(q)

head_slot.markdown(
    ui_components.page_head_html(
        "Wrong answers",
        f"{len(wrong_questions)} mistake{'s' if len(wrong_questions) != 1 else ''} in '{selected_option}'"
        f" · {filter_mode.lower()}"),
    unsafe_allow_html=True)

if not wrong_questions:
    st.success("No mistakes found. Great job.", icon=":material/check_circle:")
else:
    for i, q in enumerate(wrong_questions):
        q_id = q["id"]
        row_id = f"{i}_{q_id}"          # unique even if two files share a question id
        display_attempt = q.get("display_attempt", {})
        last_selected = display_attempt.get("selected_indices", [])
        n_wrong = q.get("wrong_count", 0)

        with st.container(border=True, key=f"row_{row_id}"):
            st.markdown(
                ui_components.list_row_html(
                    q["question"],
                    # wrong_count only counts attempts below quality 3; a listed question with 0
                    # there had a partial-credit last attempt, so say that instead of "wrong 0 times"
                    [f"wrong {n_wrong} time{'s' if n_wrong != 1 else ''}" if n_wrong else "partly correct",
                     _last_on(display_attempt.get("timestamp")),
                     q.get("source_file", "")]),
                unsafe_allow_html=True)

            # Review card: your pick (Your pick / Correct) + the right answer (Missed) + explanation
            with st.expander("Show answer", icon=":material/visibility:"):
                exam_view.render_review_card(row_id, q, selected=last_selected)
                st.caption(f"Attempted: {display_attempt.get('timestamp', 'Unknown')} | "
                           f"Score: {display_attempt.get('score', 0)}")
