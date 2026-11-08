import streamlit as st
from utils import file_manager, similarity, archive_manager, ui_helpers, ui_components, exam_view
import os
from pathlib import Path

st.set_page_config(page_title="Similar questions", page_icon=":material/content_copy:", layout="wide")

ui_helpers.inject_global_css()

ui_components.render_page_head(
    "Similar questions",
    "Identify and manage exact duplicates across your exam suites. Archived questions will be excluded from drills.")

# --- Sidebar: Filters ---
with st.sidebar:
    st.header("Filters")

    # Get Exam Suites (Root Folders)
    all_folders = file_manager.get_exam_folders(file_manager.QUESTIONS_ROOT)
    # Extract top-level folders
    suites = set()
    for f in all_folders:
        parts = Path(f).parts
        if parts:
            suites.add(parts[0])

    sorted_suites = sorted(list(suites))

    selected_suite = st.selectbox("Select exam suite", ["All"] + sorted_suites)

    st.info("Currently detection is based on **Exact Content Match** (Text + Options + Answer).",
            icon=":material/info:")

from utils.llm_client import LLMClient

# --- Sidebar: Algorithm Selection ---
with st.sidebar:
    st.divider()
    st.header("Detection mode")
    mode = st.radio("Method", ["Exact Content Match", "Contextual Match (LLM)"])

    if mode == "Exact Content Match":
        st.info("Fast. Finds 100% identical duplicates based on Hash (Text + Options + Answer).",
                icon=":material/bolt:")
    else:
        st.info("Advanced. Uses Vector Embeddings (all-minilm) to find semantic duplicates.",
                icon=":material/psychology:")
        threshold = st.slider("Similarity threshold", 0.70, 0.99, 0.85, 0.01, help="Higher = stricter matching.")

# --- Main Logic ---

duplicate_groups = []

import json
import os
from datetime import datetime

RESULTS_CACHE_FILE = Path("user_data/contextual_duplicates.json")

def load_cached_results(suite_name="All"):
    if RESULTS_CACHE_FILE.exists():
        try:
            with open(RESULTS_CACHE_FILE, "r", encoding="utf-8") as f:
                full_data = json.load(f)

            if suite_name == "All":
                # Aggregate EVERYTHING
                all_groups = []
                last_time = ""
                for s_name, data in full_data.items():
                    all_groups.extend(data.get("groups", []))
                    if data.get("timestamp", "") > last_time:
                        last_time = data.get("timestamp", "")
                return all_groups, last_time
            else:
                # Return specific suite data
                data = full_data.get(suite_name, {})
                return data.get("groups", []), data.get("timestamp", "")
        except:
            return None, None
    return None, None

def save_cached_results(groups, suite_name="All"):
    RESULTS_CACHE_FILE.parent.mkdir(exist_ok=True, parents=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Load existing to preserve other suites
    try:
        with open(RESULTS_CACHE_FILE, "r", encoding="utf-8") as f:
            full_data = json.load(f)
    except:
        full_data = {}

    # Update specific suite
    # If the user scans "All", we save under the "All" key; if they scan one suite, under that suite.
    full_data[suite_name] = {
        "timestamp": timestamp,
        "groups": groups
    }

    with open(RESULTS_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(full_data, f)
    return timestamp

if mode == "Exact Content Match":
    # Load Duplicates
    with st.spinner("Scanning for duplicates..."):
        # Pass suite_name only if specific one selected
        suite_arg = selected_suite if selected_suite != "All" else None
        duplicate_groups = similarity.find_duplicates(suite_arg)

    if not duplicate_groups:
        st.success("No exact duplicates found. Your question bank is clean.", icon=":material/check_circle:")
        st.stop()

else: # Contextual Match
    st.subheader("Contextual similarity analysis")
    st.markdown("""
    This tool will:
    1. Generate **Semantic Embeddings** for each question (Text + Options + Answer).
    2. Compute **Cosine Similarity** between all pairs.
    3. Group questions with similarity score > **Threshold**.
    """)

    # Initialize session state for results if not present
    # We always re-check cache when suite changes, so we don't rely solely on st.session_state persistence logic for data
    # BUT we do want to avoid flickering.

    # Logic: If state.current_suite != selected_suite, reload from cache.
    if "contextual_suite" not in st.session_state:
        st.session_state.contextual_suite = None

    if st.session_state.contextual_suite != selected_suite:
        # Suite changed, try load from cache
        st.session_state.contextual_suite = selected_suite
        cached_groups, cached_time = load_cached_results(selected_suite)
        st.session_state.contextual_results = cached_groups
        st.session_state.contextual_scan_time = cached_time

    # Show cache status
    if st.session_state.contextual_scan_time:
        st.info(f"Showing results for **{selected_suite}** (Last scan: {st.session_state.contextual_scan_time})",
                icon=":material/history:")
    elif selected_suite != "All":
        st.warning(f"No previous scan data found for **{selected_suite}**.")

    if st.button("Start scan", type="primary", icon=":material/radar:"):
        st.session_state.cancel_scan = False
        suite_arg = selected_suite if selected_suite != "All" else None

        # Load questions...
        root = file_manager.QUESTIONS_ROOT
        all_files = file_manager.get_exam_files(root)
        questions = []
        for relative_path in all_files:
            if suite_arg and not relative_path.replace("\\", "/").startswith(suite_arg + "/"):
                continue
            questions.extend(file_manager.load_questions(root, relative_path))

        llm = LLMClient(provider="ollama", model_name="all-minilm:l6-v2")

        progress_bar = st.progress(0.0)
        status_text = st.empty()
        stop_btn_placeholder = st.empty()

        # STOP BUTTON
        if stop_btn_placeholder.button("Stop scan", key="stop_scan_btn", icon=":material/stop_circle:"):
            st.session_state.cancel_scan = True

        def update_progress(p, text):
            # A button click only registers between script runs, so a running scan cannot be
            # cancelled from here; Streamlit's own Stop control in the header is the reliable way.
            progress_bar.progress(min(p, 1.0))
            status_text.text(text)

        try:
            status_text.text("Prescreening...")

            results = similarity.find_contextual_duplicates(
                questions,
                llm,
                threshold=threshold,
                progress_callback=update_progress
            )

            # Save results to persistence
            timestamp = save_cached_results(results, selected_suite)
            st.session_state.contextual_results = results
            st.session_state.contextual_scan_time = timestamp

            stop_btn_placeholder.empty() # Clear stop button
            st.success(f"Scan Complete! Found {len(results)} groups.", icon=":material/check_circle:")
        except Exception as e:
            st.error(f"Scan stopped or error: {e}")

    # Use stored results
    if st.session_state.contextual_results:
        duplicate_groups = st.session_state.contextual_results
        st.divider()
    else:
        st.info("Click 'Start scan' to begin analysis.", icon=":material/info:")
        st.stop()

# Display Groups (Common for both modes)
# --- Bulk Actions ---
if duplicate_groups:
    st.divider()
    col_info, col_btn = st.columns([0.7, 0.3], vertical_alignment="center")
    with col_info:
        st.markdown(f"Showing **{len(duplicate_groups)}** duplicate clusters.")
    with col_btn:
        if st.button("Archive selected", key="archive_selected", icon=":material/archive:",
                     use_container_width=True):
            count = 0
            to_archive_ids = set()

            # 1. Identify items to archive by checking session state keys
            for g_idx, grp in enumerate(duplicate_groups):
                for q_idx, q in enumerate(grp):
                    # Key must match the checkbox key generation logic
                    key = f"select_{g_idx}_{q_idx}_{q.get('id', 'unknown')}"
                    if st.session_state.get(key, False):
                        archive_manager.archive_question(q)
                        to_archive_ids.add(q['id'])
                        count += 1

            # 2. Update Contextual State if applicable
            if count > 0:
                if mode != "Exact Content Match" and "contextual_results" in st.session_state:
                    current_results = st.session_state.contextual_results
                    cleaned_results = []
                    for grp in current_results:
                        # Filter out archived questions
                        new_grp = [q for q in grp if q['id'] not in to_archive_ids]
                        # If only 1 instance remains, it's not a duplicate group anymore.
                        if len(new_grp) >= 2:
                            cleaned_results.append(new_grp)

                    st.session_state.contextual_results = cleaned_results
                    save_cached_results(cleaned_results, selected_suite)

                st.success(f"Archived {count} questions.", icon=":material/check_circle:")
                st.rerun()
            else:
                st.warning("No questions selected.")

# Display Groups (Common for both modes): one bordered card per cluster, questions side by side
for group_idx, group in enumerate(duplicate_groups):
    n_selected = sum(
        1 for q_idx, q in enumerate(group)
        if st.session_state.get(f"select_{group_idx}_{q_idx}_{q.get('id', 'unknown')}", False))

    with st.container(border=True, key=f"simgroup_{group_idx}"):
        st.markdown(f"**Cluster {group_idx + 1}**")
        st.caption(f"{n_selected} selected")

        # Instances
        cols = st.columns(len(group))

        for i, q in enumerate(group):
            with cols[i]:
                # Checkbox (same key as before) doubles as the instance title
                st.checkbox(f"Instance {i + 1}", key=f"select_{group_idx}_{i}_{q.get('id', 'unknown')}")

                # Question Text
                st.markdown(ui_components.md_text(q["question"]))

                # Options, with the right answer(s) in the shared success style
                c_indices = q.get("correct_indices", [])
                if not isinstance(c_indices, list):
                    c_indices = [c_indices]
                for o_idx, opt in enumerate(q.get("options", [])):
                    exam_view.render_option_row(
                        f"sim{group_idx}_{i}", o_idx, chr(65 + o_idx), opt,
                        "correct" if o_idx in c_indices else "neutral", ratio=(3, 1.5))

                # Explanation (if any)
                if "explanation" in q:
                    expl = q['explanation']
                    st.markdown(ui_components.md_text(expl[:200] + ("..." if len(expl) > 200 else "")))

                # Source File and ID
                st.caption(f"{q.get('source_file', 'Unknown')}")
                st.caption(f"ID: {q['id']}")

                # Action: Archive
                # Unique key: group_idx + instance_idx + q_id
                btn_key = f"archive_{group_idx}_{i}_{q['id']}"

                if st.button("Archive", key=btn_key, type="tertiary", icon=":material/archive:"):
                    archive_manager.archive_question(q)
                    st.toast(f"Archived question {q['id']}", icon=":material/archive:")

                    # Update session state if in contextual mode to reflect removal immediately
                    if mode != "Exact Content Match" and st.session_state.contextual_results:
                        st.session_state.contextual_results[group_idx].pop(i)
                        if len(st.session_state.contextual_results[group_idx]) < 2:
                            st.session_state.contextual_results.pop(group_idx)

                    st.rerun()
