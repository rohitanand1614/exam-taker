import streamlit as st
import sys
import os
import datetime
from pathlib import Path

# Ensure the root directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import file_manager, ui_helpers, ui_components, exam_view

st.set_page_config(page_title="Progress", page_icon=":material/bar_chart:", layout="wide")
ui_helpers.inject_global_css()
ui_helpers.apply_plotly_theme()

# The page head shows the question count, so reserve its place first and fill it below.
head_slot = st.empty()

# Get available options
folders = file_manager.get_exam_folders("questions")
files = file_manager.get_exam_files("questions")

# Expand folders to include parents (for aggregated view)
expanded_folders = set()
for f in folders:
    p = Path(f)
    expanded_folders.add(str(p))
    for parent in p.parents:
        if str(parent) != ".":
            expanded_folders.add(str(parent))

all_options = sorted(list(expanded_folders)) + files

# Determine default index
default_idx = 0
current_selection = st.session_state.get('current_exam_folder')
if current_selection and current_selection in all_options:
    default_idx = all_options.index(current_selection)

selected_option = st.selectbox("Select exam to analyze", all_options, index=default_idx)

# Load all questions
questions = file_manager.load_questions("questions", selected_option)

# Categorize
green_list = []   # All Correct
yellow_list = []  # Mixed
red_list = []     # All Incorrect
grey_list = []    # Unattempted

for q in questions:
    q_id = q.get("id")
    if not q_id:
        continue

    log_data = file_manager.load_question_log(q_id)
    attempts = log_data.get("attempts", [])

    if not attempts:
        grey_list.append(q)
        continue

    correct_count = sum(1 for a in attempts if a.get("score", 0) == 1.0)
    wrong_count = len(attempts) - correct_count

    if correct_count > 0 and wrong_count == 0:
        green_list.append(q)
    elif correct_count > 0 and wrong_count > 0:
        yellow_list.append(q)
    elif correct_count == 0 and wrong_count > 0:
        red_list.append(q)
    else:
        # Should not happen if attempts > 0
        grey_list.append(q)

n_total = len(green_list) + len(yellow_list) + len(red_list) + len(grey_list)
head_slot.markdown(
    ui_components.page_head_html("Progress", f"{n_total} questions in {selected_option}"),
    unsafe_allow_html=True)

# Stat tiles (same numbers as the tab labels)
tile_cols = st.columns(4)
for col, (label, items) in zip(tile_cols, (("Mastered", green_list), ("Mixed", yellow_list),
                                           ("Struggling", red_list), ("Unattempted", grey_list))):
    col.metric(label, len(items))

# The selected tab takes its status colour from the design tokens
_t = ui_helpers.TOKENS
st.markdown(f"""
<style>
    div[data-baseweb="tab-list"] button:nth-child(1)[aria-selected="true"],
    div[data-baseweb="tab-list"] button:nth-child(1)[aria-selected="true"] p {{ color: {_t['success']} !important; }}
    div[data-baseweb="tab-list"] button:nth-child(2)[aria-selected="true"],
    div[data-baseweb="tab-list"] button:nth-child(2)[aria-selected="true"] p {{ color: {_t['warning']} !important; }}
    div[data-baseweb="tab-list"] button:nth-child(3)[aria-selected="true"],
    div[data-baseweb="tab-list"] button:nth-child(3)[aria-selected="true"] p {{ color: {_t['danger']} !important; }}
</style>
""", unsafe_allow_html=True)

# Tabs for lists (plain-text labels with the counts)
tab1, tab2, tab3, tab4 = st.tabs([
    f"Mastered ({len(green_list)})",
    f"Mixed ({len(yellow_list)})",
    f"Struggling ({len(red_list)})",
    f"Unattempted ({len(grey_list)})"
])


def render_list(q_list, status_label):
    if not q_list:
        st.info(f"No questions in '{status_label}' category.", icon=":material/info:")
        return

    for i, q in enumerate(q_list):
        row_id = f"{status_label}_{i}_{q.get('id')}"      # unique even if two files share an id
        with st.container(border=True, key=f"row_{row_id}"):
            st.markdown(
                ui_components.list_row_html(
                    q.get('question', 'Unknown Question'),
                    [q.get('difficulty'), ", ".join(q.get('tags', [])), q.get('source_file', '')]),
                unsafe_allow_html=True)
            with st.expander("Show answer", icon=":material/visibility:"):
                st.caption(f"ID: {q.get('id')}")
                exam_view.render_review_card(row_id, q)


with tab1:
    st.success("Questions with ALL correct attempts.", icon=":material/check_circle:")
    render_list(green_list, "Mastered")

with tab2:
    st.warning("Questions with both correct and incorrect attempts.", icon=":material/rule:")
    render_list(yellow_list, "Mixed")

with tab3:
    st.error("Questions with ALL incorrect attempts.", icon=":material/cancel:")
    render_list(red_list, "Struggling")

with tab4:
    st.caption("Questions never attempted.")
    render_list(grey_list, "Unattempted")
