import streamlit as st
import random
import datetime
from utils import file_manager, scoring, srs, bookmark_manager, archive_manager
from utils import ui_helpers
from streamlit_quill import st_quill
from streamlit_mermaid import st_mermaid

st.set_page_config(page_title="Targeted Drill", page_icon="🎯", layout="wide")

ui_helpers.inject_global_css()
ui_helpers.inject_quill_dark_mode()

st.title("🎯 Targeted Drill Session")

if "drill_questions" not in st.session_state or not st.session_state.drill_questions:
    st.info("No active drill session. Please start a drill from the 'Topic Analysis' dashboard.")
    if st.button("Go to Dashboard"):
        st.switch_page("pages/Topic_Analysis.py")
    st.stop()

# Initialize drill variables
if "drill_index" not in st.session_state:
    st.session_state.drill_index = 0
if "drill_answers" not in st.session_state:
    st.session_state.drill_answers = {}
if "drill_submitted" not in st.session_state:
    st.session_state.drill_submitted = {}

# Main Render Logic
current_q = st.session_state.drill_questions[st.session_state.drill_index]
q_id = current_q["id"]
# Use a unique key for storage valid only for this specific step in the drill
# This ensures that if the same question appears later, it treats it as a fresh blank slate.
step_key = f"{q_id}_{st.session_state.drill_index}"

# Sidebar Info
with st.sidebar:
    st.header("Drill Status")
    total = len(st.session_state.drill_questions)
    current = st.session_state.drill_index + 1
    progress = current / total
    st.write(f"Question **{current}** of **{total}**")
    st.progress(progress)
    
    if st.button("❌ Exit Drill", type="primary"):
        # Clear drill state
        del st.session_state.drill_questions
        del st.session_state.drill_index
        del st.session_state.drill_answers
        del st.session_state.drill_submitted
        st.switch_page("pages/Topic_Analysis.py")
        

         
    # Next Button
    if st.session_state.drill_index < len(st.session_state.drill_questions) - 1:
        if st.button("Next Question ➡️", type="primary"):
            st.session_state.drill_index += 1
            st.rerun()
    else:
        st.success("🎉 Drill Complete! You have mastered this session.")
        if st.button("Finish & Return to Dashboard"):
            del st.session_state.drill_questions
            del st.session_state.drill_index
            del st.session_state.drill_answers
            del st.session_state.drill_submitted
            st.switch_page("pages/Topic_Analysis.py")

# Render Question
st.markdown(f'<div class="question-card">', unsafe_allow_html=True)

# Header
tags = current_q.get("tags", [])
st.caption(f"🏷️ {', '.join(tags)}")

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
        key=f"drill_bm_sel_{step_key}",
        label_visibility="collapsed"
    )
with bm_cols[1]:
    col_add, col_remove = st.columns([1, 1])
    with col_add:
        if st.button("🔖 Bookmark", key=f"drill_bm_btn_{step_key}"):
            bookmark_manager.save_bookmark(current_q, selected_bm_color)
            st.toast(f"Bookmarked as {selected_bm_color}!", icon="✅")
            st.rerun()
    with col_remove:
        if current_bookmark:
            if st.button("🗑️ Remove", key=f"drill_bm_rm_{step_key}"):
                bookmark_manager.remove_bookmark(q_id)
                st.toast("Bookmark removed!", icon="🗑️")
                st.rerun()

ui_helpers.render_math_text(
    ui_helpers.prepare_math_text(current_q["question"]),
    font_size="1.2rem", font_weight="600",
    height=max(70, len(current_q["question"]) // 3 + 40)
)

options = current_q.get("options", [])
q_type = current_q.get("type", "multiple_choice")
is_submitted = st.session_state.drill_submitted.get(step_key, False)

user_selection = []

correct_indices = current_q.get("correct_indices", [])
if not isinstance(correct_indices, list):
    correct_indices = [correct_indices]
is_multiselect = len(correct_indices) > 1
letters = [chr(65 + i) for i in range(len(options))]

if is_multiselect:
    st.write("Assertion: **Select all that apply**")
    prev_indices = st.session_state.drill_answers.get(step_key, [])

    for idx, opt in enumerate(options):
        is_selected = is_submitted and idx in prev_indices
        ui_helpers.render_math_text(ui_helpers.prepare_math_text(opt), height=55)
        checked = st.checkbox(
            f"Select {letters[idx]}",
            value=is_selected,
            key=f"drill_chk_{step_key}_{idx}",
            disabled=is_submitted
        )
        if checked:
            user_selection.append(idx)
else:
    # Single Select -> Radio
    default_idx = None
    if is_submitted:
        if step_key in st.session_state.drill_answers and st.session_state.drill_answers[step_key]:
            default_idx = st.session_state.drill_answers[step_key][0]

    for opt in options:
        ui_helpers.render_math_text(ui_helpers.prepare_math_text(opt), height=55)

    selected_letter = st.radio(
        "Select your answer:",
        letters,
        index=default_idx,
        key=f"drill_radio_{step_key}",
        disabled=is_submitted
    )

    if not is_submitted:
        user_selection = [letters.index(selected_letter)] if selected_letter in letters else []
    else:
        user_selection = st.session_state.drill_answers.get(step_key, [])

if not is_submitted:
    if st.button("Submit Answer", key=f"drill_btn_{step_key}"):
        # Calculate Score
        correct_indices = current_q.get("correct_indices", [])
        score = scoring.calculate_f1_score(user_selection, correct_indices)
        
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
            st.toast("Incorrect. Question re-queued for mastery!", icon="🔄")
            
        st.rerun()
else:
    # Render Results
    correct_indices = set(current_q.get("correct_indices", []))
    score = scoring.calculate_f1_score(st.session_state.drill_answers.get(step_key, []), list(correct_indices))
    
    if score == 1.0:
        st.markdown('<div class="success-box">✅ Correct!</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="error-box">❌ Incorrect.</div>', unsafe_allow_html=True)
        
    if "explanation" in current_q:
        st.markdown("**💡 Explanation:**")
        ui_helpers.render_math_text(
            ui_helpers.prepare_math_text(current_q["explanation"]),
            extra_style="border-left:4px solid #58a6ff;padding:1rem;background:#21262d;border-radius:0 8px 8px 0;",
            height=min(500, max(100, len(current_q["explanation"]) // 5 + 40))
        )

    # --- Notes & Diagrams ---
    st.write("### 📝 My Notes & Research")
    
    # Load existing notes
    log_data = file_manager.load_question_log(current_q["id"])
    existing_notes = log_data.get("user_notes", "")
    existing_diagram = log_data.get("user_diagram", "")
    
    # Text Area (Rich Text with Quill)
    user_notes = st_quill(
        value=existing_notes,
        placeholder="Add your findings or additional explanation here...",
        html=True,
        key=f"drill_notes_{current_q['id']}"
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
            key=f"drill_diagram_{current_q['id']}"
        )
    
    if st.button("💾 Save Notes & Diagram", key=f"drill_save_notes_{current_q['id']}"):
        file_manager.update_user_notes(current_q["id"], user_notes, user_diagram)
        st.toast("Notes & Diagram saved successfully!", icon="✅")
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)
