import streamlit as st
from utils import file_manager, ui_helpers
import os
from pathlib import Path

st.set_page_config(page_title="Search Questions", page_icon="🔍", layout="wide")

ui_helpers.inject_global_css()
st.markdown("""
<style>
    .question-header {
        font-size: 1.05rem;
        font-weight: 600;
        color: #edf2f8;
        margin-bottom: 0.5rem;
    }
    .meta-tag {
        background-color: #0e1118;
        padding: 4px 8px;
        border-radius: 6px;
        border: 1px solid #252e42;
        font-size: 0.78rem;
        color: #6b7a90;
        display: inline-block;
        margin-right: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔍 Search Questions")
st.caption("Filter and search through your exam question bank.")

# --- Session State Initialization ---
if "folder_search" not in st.session_state:
    st.session_state.folder_search = "All"
if "file_search" not in st.session_state:
    st.session_state.file_search = "All"
if "keyword_search" not in st.session_state:
    st.session_state.keyword_search = ""
if "search_triggered" not in st.session_state:
    st.session_state.search_triggered = False

# --- Helper Functions ---
def reset_filters():
    st.session_state.folder_search = "All"
    st.session_state.file_search = "All"
    st.session_state.keyword_search = ""
    st.session_state.search_triggered = False

# --- Filters Section ---
with st.container():
    col1, col2, col3 = st.columns([1, 1, 2])
    
    # 1. Folder Filter
    all_folders_raw = file_manager.get_exam_folders(file_manager.QUESTIONS_ROOT)
    # Filter out sub-folders if needed, or just keep them all. 
    # Usually "Folder" means the specific directory containing the JSON or a parent. 
    # get_exam_folders returns all folders with JSONs.
    all_folders = ["All"] + all_folders_raw
    
    with col1:
        # We need to handle the case where the stored "folder_search" might not be in the list anymore
        # though unlikely in this session.
        idx = 0
        if st.session_state.folder_search in all_folders:
            idx = all_folders.index(st.session_state.folder_search)
            
        selected_folder = st.selectbox(
            "📁 Folder Filter", 
            all_folders, 
            index=idx,
            key="folder_search"
        )

    # 2. File Filter (Dynamic)
    all_files_raw = file_manager.get_exam_files(file_manager.QUESTIONS_ROOT)
    
    if selected_folder == "All":
        filtered_files_raw = all_files_raw
    else:
        # Robust filtering using pathlib to handle nested folders and slash differences
        filtered_files_raw = []
        target_folder_path = Path(selected_folder)
        for f in all_files_raw:
            try:
                # Check if file is inside the selected folder structure
                Path(f).relative_to(target_folder_path)
                filtered_files_raw.append(f)
            except ValueError:
                continue

    files_options = ["All"] + filtered_files_raw
    
    with col2:
        # Reset file selection if it's not in the new options (e.g. folder changed)
        # We should check if the current session state file is in the new list.
        # If not, default to "All".
        current_file_idx = 0
        if st.session_state.file_search in files_options:
            current_file_idx = files_options.index(st.session_state.file_search)
        else:
             # If previously selected file is not compatible with new folder, reset it visually to "All"
             # But we can't change the widget key value mid-render easily without a rerun loop or callback.
             # However, passing `index` usually works.
             if st.session_state.file_search not in files_options:
                 st.session_state.file_search = "All"
                 current_file_idx = 0

        selected_file = st.selectbox(
            "📄 File Filter", 
            files_options, 
            index=current_file_idx,
            key="file_search"
        )

    # 3. Keyword Filter
    with col3:
        keyword = st.text_input(
            "ABC Keyword Search", 
            placeholder="Search in question text, options...",
            key="keyword_search"
        )

# --- Action Buttons ---
col_btn1, col_btn2 = st.columns([1, 10])
with col_btn1:
    search_clicked = st.button("Search", type="primary", use_container_width=True)
with col_btn2:
    st.button("Reset Filter", on_click=reset_filters)

# Update state if search clicked
if search_clicked:
    st.session_state.search_triggered = True

# --- Results Display ---
st.divider()

if not st.session_state.search_triggered:
    st.info("Select filters and click **Search** to view questions.")
else:
    # Perform Search
    
    # 1. Determine files to load
    files_to_load = []
    
    if selected_file != "All":
        # Specific file selected
        files_to_load = [selected_file]
    elif selected_folder != "All":
        # Specific folder selected, load all valid files in it
        files_to_load = filtered_files_raw
    else:
        # All folders, All files
        files_to_load = all_files_raw
        
    if not files_to_load:
        st.warning("No files found matching the criteria.")
        st.stop()
        
    found_questions = []
    
    with st.spinner(f"Searching in {len(files_to_load)} files..."):
        # Load and Filter
        for f_path in files_to_load:
            # We use the utility to load questions. 
            # Note: load_questions() takes the relative path if root is provided
            try:
                qs = file_manager.load_questions(file_manager.QUESTIONS_ROOT, f_path)
                
                for q in qs:
                    # Filter by Keyword
                    if keyword:
                        # Simple case-insensitive match
                        kw = keyword.lower()
                        text_match = kw in q.get("question", "").lower()
                        # Check options
                        options_match = any(kw in str(opt).lower() for opt in q.get("options", []))
                        # Check explanation
                        explanation_match = kw in q.get("explanation", "").lower()
                        
                        if text_match or options_match or explanation_match:
                            found_questions.append(q)
                    else:
                        # No keyword, add all
                        found_questions.append(q)
            except Exception as e:
                st.error(f"Error reading {f_path}: {e}")
                
    # Display Results
    if not found_questions:
        st.warning("No questions found matching your criteria.")
    else:
        st.success(f"Found **{len(found_questions)}** questions.")
        
        # Pagination could be added here if too many results, but for now list all (capped at say 100? No, user didn't ask)
        # Showing first 100 to avoid browser crash if user accidentally selects ALL + Empty Keyword
        MAX_DISPLAY = 200
        if len(found_questions) > MAX_DISPLAY:
             st.warning(f"Showing first {MAX_DISPLAY} results for performance. Refine your search.")
        
        for q in found_questions[:MAX_DISPLAY]:
            with st.container():
                st.markdown('<div class="question-card">', unsafe_allow_html=True)
                
                # Meta info
                source_file = q.get("source_file", "Unknown")
                q_id = q.get("id", "Unknown")
                
                st.markdown(f'''
                    <div>
                        <span class="meta-tag">📄 {source_file}</span>
                        <span class="meta-tag">🆔 {q_id}</span>
                    </div>
                ''', unsafe_allow_html=True)
                
                # Question
                ui_helpers.render_math_text(
                    ui_helpers.prepare_math_text(q.get('question', '')),
                    font_size="1.1rem", font_weight="600",
                    height=max(60, len(q.get('question', '')) // 3 + 40)
                )

                # Options
                if "options" in q:
                    for i, opt in enumerate(q["options"]):
                        ui_helpers.render_math_text(
                            ui_helpers.prepare_math_text(f"{chr(65+i)}. {opt}"), height=50
                        )

                # Create an expander for Answer/Explanation
                with st.expander("View Answer"):
                    correct = q.get("correct_indices", [])
                    st.write(f"**Correct Answer:** {correct}")
                    if "explanation" in q:
                        st.markdown("**Explanation:**")
                        ui_helpers.render_math_text(
                            ui_helpers.prepare_math_text(q['explanation']),
                            height=min(400, max(80, len(q['explanation']) // 5 + 40))
                        )
                        
                st.markdown('</div>', unsafe_allow_html=True)
