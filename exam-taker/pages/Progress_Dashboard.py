import streamlit as st
import sys
import os
import datetime
from pathlib import Path

# Ensure the root directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import file_manager, ui_helpers

st.set_page_config(page_title="Progress Dashboard", page_icon="📊", layout="wide")
ui_helpers.inject_global_css()

st.title("📊 Progress Dashboard")

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

selected_option = st.selectbox("Select Exam to Analyze:", all_options, index=default_idx)

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

# Custom CSS to color selected tabs
st.markdown("""
<style>
    /* Mastered - muted green */
    div[data-baseweb="tab-list"] button:nth-child(1)[aria-selected="true"] {
        color: #52c46e !important;
        border-bottom-color: #52c46e !important;
    }
    div[data-baseweb="tab-list"] button:nth-child(1)[aria-selected="true"] p {
        color: #52c46e !important;
    }

    /* Mixed - muted amber */
    div[data-baseweb="tab-list"] button:nth-child(2)[aria-selected="true"] {
        color: #c9a227 !important;
        border-bottom-color: #c9a227 !important;
    }
    div[data-baseweb="tab-list"] button:nth-child(2)[aria-selected="true"] p {
        color: #c9a227 !important;
    }

    /* Struggling - muted coral */
    div[data-baseweb="tab-list"] button:nth-child(3)[aria-selected="true"] {
        color: #d96060 !important;
        border-bottom-color: #d96060 !important;
    }
    div[data-baseweb="tab-list"] button:nth-child(3)[aria-selected="true"] p {
        color: #d96060 !important;
    }
</style>
""", unsafe_allow_html=True)

# Tabs for lists
tab1, tab2, tab3, tab4 = st.tabs([
    f"🟢 Mastered ({len(green_list)})", 
    f"🟡 Mixed ({len(yellow_list)})", 
    f"🔴 Struggling ({len(red_list)})", 
    f"⚪ Unattempted ({len(grey_list)})"
])

def render_list(q_list, status_label):
    if not q_list:
        st.info(f"No questions in '{status_label}' category.")
        return
        
    for q in q_list:
        with st.expander(f"{q.get('question', 'Unknown Question')[:100]}..."):
            st.write(f"**ID:** {q.get('id')}")
            st.markdown("**Question:**")
            ui_helpers.render_math_text(
                ui_helpers.prepare_math_text(q.get('question', '')),
                height=max(60, len(q.get('question', '')) // 3 + 40)
            )
            st.write(f"**Tags:** {', '.join(q.get('tags', []))}")

            options = q.get('options', [])
            if options:
                with st.expander("Show Options"):
                    for opt in options:
                        ui_helpers.render_math_text(ui_helpers.prepare_math_text(f"- {opt}"), height=50)

            if "explanation" in q:
                st.markdown("**Explanation:**")
                ui_helpers.render_math_text(
                    ui_helpers.prepare_math_text(q['explanation']),
                    height=min(400, max(80, len(q['explanation']) // 5 + 40))
                )

with tab1:
    st.success("Questions with ALL correct attempts.")
    render_list(green_list, "Mastered")

with tab2:
    st.warning("Questions with both correct and incorrect attempts.")
    render_list(yellow_list, "Mixed")

with tab3:
    st.error("Questions with ALL incorrect attempts.")
    render_list(red_list, "Struggling")

with tab4:
    st.write("Questions never attempted.")
    render_list(grey_list, "Unattempted")
