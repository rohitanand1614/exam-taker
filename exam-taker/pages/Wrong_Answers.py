import streamlit as st
import sys
import os

# Ensure the root directory is in the path so we can import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import file_manager, ui_helpers

st.set_page_config(page_title="Review Mistakes", page_icon="❌", layout="wide")

ui_helpers.inject_global_css()
st.markdown("""
<style>
    .wrong-answer { color: #d96060; font-weight: bold; }
    .correct-answer { color: #52c46e; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("❌ Review Mistakes")

# Sidebar Selection
with st.sidebar:
    st.subheader("Select Source")
    selection_mode = st.radio("Load by:", ["Folder", "Specific File"], index=0)
    
    if selection_mode == "Folder":
        available_options = file_manager.get_exam_folders("questions")
        label = "Choose a Subject/Topic"
    else:
        available_options = file_manager.get_exam_files("questions")
        label = "Choose a JSON File"
        
    selected_option = st.selectbox(label, available_options)
    
    st.divider()
    filter_mode = st.radio("Filter Criteria:", ["Last Attempt Incorrect", "Ever Incorrect"], index=0)

if not selected_option:
    st.info("Select a folder or file to view mistakes.")
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
        wrong_questions.append(q)

st.subheader(f"Found {len(wrong_questions)} mistakes in '{selected_option}'")

if not wrong_questions:
    st.success("🎉 No mistakes found! Great job.")
else:
    for q in wrong_questions:
        with st.container():
            st.markdown(f'<div class="question-card">', unsafe_allow_html=True)
            ui_helpers.render_math_text(
                ui_helpers.prepare_math_text(q["question"]),
                font_size="1.2rem", font_weight="600",
                height=max(70, len(q["question"]) // 3 + 40)
            )

            # Show Options with Correct/Wrong highlighting based on last attempt
            options = q.get("options", [])
            correct_indices = q.get("correct_indices", [])

            # We use the display attempt to show what they picked
            display_attempt = q.get("display_attempt", {})
            last_selected = display_attempt.get("selected_indices", [])

            for idx, opt in enumerate(options):
                prefix = ""
                style = "color: #6b7a90;"

                if idx in correct_indices:
                    style = "color: #52c46e; font-weight: bold;"
                    prefix = "✅ (Correct Answer)"

                if idx in last_selected:
                    if idx not in correct_indices:
                        style = "color: #d96060; font-weight: bold;"
                        prefix = "❌ (Your Choice)"
                    else:
                        prefix = "✅ (Your Choice)"

                ui_helpers.render_math_text(
                    f"<span style='{style}'>• {ui_helpers.prepare_math_text(opt)} {prefix}</span>",
                    height=55
                )

            # Explanation
            if "explanation" in q:
                st.markdown("**Explanation:**")
                ui_helpers.render_math_text(
                    ui_helpers.prepare_math_text(q["explanation"]),
                    height=min(400, max(80, len(q["explanation"]) // 5 + 40))
                )
                
            st.caption(f"Attempted: {display_attempt.get('timestamp', 'Unknown')} | Score: {display_attempt.get('score', 0)}")
            st.markdown('</div>', unsafe_allow_html=True)
