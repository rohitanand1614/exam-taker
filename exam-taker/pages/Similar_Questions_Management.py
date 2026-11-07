import streamlit as st
from utils import file_manager, similarity, archive_manager, ui_helpers
import os
from pathlib import Path

st.set_page_config(page_title="Similar Questions", page_icon="👯", layout="wide")

ui_helpers.inject_global_css()
st.markdown("""
<style>
    .duplicate-group {
        background-color: #1a1f2e;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #252e42;
        margin-bottom: 2rem;
    }
    .duplicate-header {
        font-size: 1.05rem;
        font-weight: 600;
        color: #edf2f8;
        margin-bottom: 1rem;
        border-bottom: 1px solid #252e42;
        padding-bottom: 0.5rem;
    }
    .instance-card {
        background-color: #0e1118;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #252e42;
        margin-bottom: 0.5rem;
    }
    .file-path {
        color: #6b7a90;
        font-size: 0.82rem;
        font-family: monospace;
        word-break: break-all;
    }
    .highlight-diff {
        background-color: rgba(200, 160, 10, 0.18);
        padding: 2px 4px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

st.title("👯 Similar Questions Management")
st.caption("Identify and manage exact duplicates across your exam suites. Archived questions will be excluded from drills.")

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
    
    selected_suite = st.selectbox("Select Exam Suite", ["All"] + sorted_suites)
    
    st.info("Currently detection is based on **Exact Content Match** (Text + Options + Answer).")

from utils.llm_client import LLMClient

# --- Sidebar: Algorithm Selection ---
with st.sidebar:
    st.divider()
    st.header("Detection Mode")
    mode = st.radio("Method", ["Exact Content Match", "Contextual Match (LLM)"])
    
    if mode == "Exact Content Match":
        st.info("Fast. Finds 100% identical duplicates based on Hash (Text + Options + Answer).")
    else:
        st.info("Advanced. Uses Vector Embeddings (all-minilm) to find semantic duplicates.")
        threshold = st.slider("Similarity Threshold", 0.70, 0.99, 0.85, 0.01, help="Higher = stricter matching.")

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
    # If "All" was selected during scan, we might have mixed data.
    # Ideally, we should detect which suite a group belongs to, but if the user ran 
    # a scan on "All", we save it under "All" key or just overwrite?
    # Better approach: If user scans "All", we save under "All" key. 
    # If user scans "Nvidia", we save under "Nvidia".
    
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
        st.success("✨ No exact duplicates found! Your question bank is clean.")
        st.stop()
        
    # st.write(f"Found **{len(duplicate_groups)}** groups of duplicate questions.")

else: # Contextual Match
    st.write("### 🧠 Contextual Similarity Analysis (Embeddings)")
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
         st.info(f"📂 Showing results for **{selected_suite}** (Last scan: {st.session_state.contextual_scan_time})")
    elif selected_suite != "All":
         st.warning(f"No previous scan data found for **{selected_suite}**.")
        
    if st.button("🚀 Start Scan"):
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
        if stop_btn_placeholder.button("🛑 STOP SCAN", key="stop_scan_btn"):
            st.session_state.cancel_scan = True
        
        def update_progress(p, text):
            # Check stopping condition
            # Note: The button click in Streamlit triggers a rerun, so usually 'stop' logic needs
            # carefully placed 'st.empty' or check session state.
            # In a synchronous function loop, the button click won't register until the function yields or finishes
            # UNLESS we use a trick or the user presses the native "Stop" in top right.
            # But the user asked for an option.
            # Realistically, Streamlit scripts lock the thread. The "Stop" button won't be clickable 
            # while the loop is crunching Python code unless we use `await` or `st.rerun` magic.
            # The standard Streamlit "Stop" button in the UI header is the most reliable.
            # However, we can simulate checking a shared file or flag if we were async.
            # For now, let's just update feedback.
            progress_bar.progress(min(p, 1.0))
            status_text.text(text)

        # To ACTUALLY make it cancellable in a sync loop in Streamlit is hard without threading.
        # But we can at least provide visually the standard "Stop" advice or use a placeholder that might
        # catch an interaction if the loop yields control (it doesn't heavily here).
        
        # Actually, let's trust the user knows Streamlit's native "Stop" button works.
        # But to be helpful, let's add a "Cancel" text.
        
        try:
            # We can't easily detect a button click mid-loop in standard Streamlit sync execution.
            # Only option is `st.empty` update, but input events are processed between runs.
            # We will rely on native stop, but add a message.
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
            st.success(f"Scan Complete! Found {len(results)} groups.")
        except Exception as e:
            st.error(f"Scan stopped or error: {e}")
        except Exception as e:
            st.error(f"Error during scan: {e}")
            
    # Use stored results
    if st.session_state.contextual_results:
        duplicate_groups = st.session_state.contextual_results
        st.divider()
        # st.write(f"Found **{len(duplicate_groups)}** semantically similar groups.")
    else:
        st.info("Click 'Start Deep Scan' to begin analysis.")
        st.stop()

# Display Groups (Common for both modes)
# --- Bulk Actions ---
if duplicate_groups:
    st.divider()
    col_info, col_btn = st.columns([0.7, 0.3])
    with col_info:
        st.markdown(f"Showing **{len(duplicate_groups)}** duplicate clusters.")
    with col_btn:
        if st.button("🗄️ Archive Selected", type="primary", use_container_width=True):
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
                        # Keep groups that still have items (orphan items are no longer duplicates, but we keep them for visibility or remove?)
                        # Logic: If only 1 instance remains, it's not a duplicate group anymore.
                        if len(new_grp) >= 2:
                            cleaned_results.append(new_grp)
                    
                    st.session_state.contextual_results = cleaned_results
                    save_cached_results(cleaned_results, selected_suite)
                
                st.success(f"Archived {count} questions.")
                st.rerun()
            else:
                st.warning("No questions selected.")

# Display Groups (Common for both modes)
for group_idx, group in enumerate(duplicate_groups):
    first_q = group[0]
    
    with st.container():
        st.markdown(f'<div class="duplicate-group">', unsafe_allow_html=True)
        
        # Header: The Common Question Text
        # For contextual, they might differ, so maybe show generic header or Q1
        st.markdown(f'<div class="duplicate-header">Cluster {group_idx + 1}</div>', unsafe_allow_html=True)
        
        # Instances
        cols = st.columns(len(group))
        
        for i, q in enumerate(group):
            with cols[i]:
                st.markdown(f'<div class="instance-card">', unsafe_allow_html=True)
                
                # Checkbox + Header
                c1, c2 = st.columns([0.15, 0.85])
                with c1:
                    st.checkbox("Select", key=f"select_{group_idx}_{i}_{q.get('id', 'unknown')}", label_visibility="collapsed")
                with c2:
                    st.markdown(f"**Instance {i+1}**")
                
                # Question Text
                ui_helpers.render_math_text(
                    ui_helpers.prepare_math_text(q["question"]),
                    height=max(60, len(q["question"]) // 3 + 40)
                )

                # Options
                st.write("**Options:**")
                for o_idx, opt in enumerate(q.get("options", [])):
                    ui_helpers.render_math_text(
                        ui_helpers.prepare_math_text(f"{o_idx+1}. {opt}"), height=50
                    )

                # Correct Answer
                c_indices = q.get("correct_indices", [])
                st.write(f"**Correct:** {c_indices}")

                # Explanation (if any)
                if "explanation" in q:
                    expl = q['explanation']
                    ui_helpers.render_math_text(
                        ui_helpers.prepare_math_text(expl[:200] + ("..." if len(expl) > 200 else "")),
                        height=80
                    )
                
                st.divider()

                # Source File
                source = q.get("source_file", "Unknown")
                st.markdown(f'<div class="file-path">📁 {source}</div>', unsafe_allow_html=True)
                
                # ID
                st.caption(f"ID: {q['id']}")
                
                st.divider()
                
                # Action: Archive
                # Unique key: group_idx + instance_idx + q_id
                btn_key = f"archive_{group_idx}_{i}_{q['id']}"
                
                if st.button("📦 Archive", key=btn_key, type="secondary"):
                    archive_manager.archive_question(q)
                    st.toast(f"Archived question {q['id']}", icon="📦")
                    
                    # Update session state if in contextual mode to reflect removal immediately
                    if mode != "Exact Content Match" and st.session_state.contextual_results:
                         st.session_state.contextual_results[group_idx].pop(i)
                         if len(st.session_state.contextual_results[group_idx]) < 2:
                             st.session_state.contextual_results.pop(group_idx)
                             
                    st.rerun()
                    
                st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)