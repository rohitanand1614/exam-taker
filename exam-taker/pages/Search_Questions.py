import streamlit as st
from utils import file_manager, ui_helpers, ui_components, exam_view
import os
from pathlib import Path

st.set_page_config(page_title="Search", page_icon=":material/search:", layout="wide")

ui_helpers.inject_global_css()

ui_components.render_page_head("Search", "Filter and search through your exam question bank.")

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

# --- Search box (page head area) ---
keyword = st.text_input(
    "Keyword search",
    placeholder="Search in question text, options and explanations...",
    key="keyword_search",
    label_visibility="collapsed",
    icon=":material/search:",
)

# --- Filters row (one row under the search box) ---
col1, col2, col_btn1, col_btn2 = st.columns([2, 2, 1.2, 1.6], vertical_alignment="bottom")

# 1. Folder Filter
all_folders_raw = file_manager.get_exam_folders(file_manager.QUESTIONS_ROOT)
# get_exam_folders returns all folders with JSONs.
all_folders = ["All"] + all_folders_raw

with col1:
    # We need to handle the case where the stored "folder_search" might not be in the list anymore
    # though unlikely in this session.
    idx = 0
    if st.session_state.folder_search in all_folders:
        idx = all_folders.index(st.session_state.folder_search)

    selected_folder = st.selectbox(
        "Folder",
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
    current_file_idx = 0
    if st.session_state.file_search in files_options:
        current_file_idx = files_options.index(st.session_state.file_search)
    else:
        # If previously selected file is not compatible with new folder, reset it visually to "All"
        if st.session_state.file_search not in files_options:
            st.session_state.file_search = "All"
            current_file_idx = 0

    selected_file = st.selectbox(
        "File",
        files_options,
        index=current_file_idx,
        key="file_search"
    )

# --- Action Buttons ---
with col_btn1:
    search_clicked = st.button("Search", type="primary", icon=":material/search:", use_container_width=True)
with col_btn2:
    st.button("Reset filter", on_click=reset_filters, icon=":material/restart_alt:", use_container_width=True)

# Update state if search clicked
if search_clicked:
    st.session_state.search_triggered = True

# --- Results Display ---
if not st.session_state.search_triggered:
    st.info("Select filters and click **Search** to view questions.", icon=":material/info:")
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
        st.success(f"Found **{len(found_questions)}** questions.", icon=":material/check_circle:")

        # Showing first 200 to avoid browser crash if user accidentally selects ALL + Empty Keyword
        MAX_DISPLAY = 200
        if len(found_questions) > MAX_DISPLAY:
            st.warning(f"Showing first {MAX_DISPLAY} results for performance. Refine your search.")

        for i, q in enumerate(found_questions[:MAX_DISPLAY]):
            q_id = q.get("id", "Unknown")
            row_id = f"{i}_{q_id}"      # unique even if two files share a question id
            with st.container(border=True, key=f"row_{row_id}"):
                st.markdown(
                    ui_components.list_row_html(
                        q.get("question", ""),
                        [q.get("source_file", "Unknown"), q.get("difficulty"), q_id]),
                    unsafe_allow_html=True)

                # "Show answer": options with the right answer(s) in the success style + explanation
                with st.expander("Show answer", icon=":material/visibility:"):
                    exam_view.render_review_card(row_id, q)
