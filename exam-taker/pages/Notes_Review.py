import streamlit as st
import sys
import os
import datetime
from pathlib import Path
from fpdf import FPDF
import numpy as np

# Ensure the root directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import file_manager, similarity, ui_helpers, ui_components, exam_view
from utils.llm_client import LLMClient

st.set_page_config(page_title="Notes review", page_icon=":material/sticky_note_2:", layout="wide")
ui_helpers.inject_global_css()

# The page head shows the notes count, so reserve its place first and fill it below.
head_slot = st.empty()

# --- Helper Functions ---

import hashlib
import json

CACHE_FILE = Path("user_data/notes_embedding_cache.json")

def load_embedding_cache():
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_embedding_cache(cache):
    CACHE_FILE.parent.mkdir(exist_ok=True, parents=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f)

def reorder_notes_conceptually(notes_list):
    """
    Reorders notes based on semantic similarity of their content + question.
    Uses persistent caching to avoid re-embedding unchanged notes.
    """
    if not notes_list:
        return []
        
    llm = LLMClient(provider="ollama", model_name="all-minilm:l6-v2")
    cache = load_embedding_cache()
    
    # 1. Generate/Fetch Embeddings
    progress = st.progress(0.0)
    status = st.empty()
    status.text("Checking cache & Embedding new notes...")
    
    embeddings = []
    new_embeddings_count = 0
    total = len(notes_list)
    
    # Pre-calculate hashes and identify missing ones
    items_to_process = []
    
    for i, item in enumerate(notes_list):
        # Unique Key: Q_ID + Note Content (if note changes, we re-embed)
        # We strip whitespace to be safe
        content_key = f"{item.get('id')}|{item.get('user_notes', '').strip()}"
        note_hash = hashlib.md5(content_key.encode("utf-8")).hexdigest()
        
        items_to_process.append((i, item, note_hash))

    # Process
    for idx, (original_idx, item, note_hash) in enumerate(items_to_process):
        
        if note_hash in cache:
            vec = cache[note_hash]
        else:
            # Generate new
            text = f"{item.get('question', '')} \n {item.get('user_notes', '')}"
            vec = llm.get_embedding(text)
            cache[note_hash] = vec
            new_embeddings_count += 1
            
        embeddings.append(vec)
        
        # Update progress occasionally
        if idx % 5 == 0:
            progress.progress((idx + 1) / total)

    # Save cache if we added anything
    if new_embeddings_count > 0:
        save_embedding_cache(cache)
        
    status.text(f"Processed {total} notes ({new_embeddings_count} new embedded). Reorganizing...")
        
    # 2. Sort using Nearest Neighbor Chain
    if not embeddings:
        return notes_list
    
    ordered_indices = [0]
    visited = {0}
    current_idx = 0
    
    n = len(notes_list)
    while len(ordered_indices) < n:
        best_next = -1
        best_sim = -1.0
        
        current_vec = embeddings[current_idx]
        
        for i in range(n):
            if i in visited:
                continue
            
            sim = similarity.calculate_cosine_similarity(current_vec, embeddings[i])
            if sim > best_sim:
                best_sim = sim
                best_next = i
        
        if best_next != -1:
            ordered_indices.append(best_next)
            visited.add(best_next)
            current_idx = best_next
        else:
            remain = [x for x in range(n) if x not in visited]
            if remain:
                nxt = remain[0]
                ordered_indices.append(nxt)
                visited.add(nxt)
                current_idx = nxt
                
    status.empty()
    progress.empty()
    
    return [notes_list[i] for i in ordered_indices]

from bs4 import BeautifulSoup

def clean_html_text(raw_html):
    """
    Strips HTML tags and attributes to return clean, readable text.
    Handles 'Dark Reader' artifacts by extracting only text content.
    """
    if not raw_html:
        return ""
    try:
        # Use HTML parser to extract text
        soup = BeautifulSoup(raw_html, "html.parser")
        return soup.get_text(separator="\n").strip()
    except Exception:
        return raw_html # Fallback

def generate_pdf(notes_list):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="Exam Notes Summary", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=11)
    
    for item in notes_list:
        # Question Header
        pdf.set_font("Arial", "B", 11)
        q_text = item.get('question', '')
        # Clean question text if it has HTML (rare but possible)
        q_text = clean_html_text(q_text)
        q_text = q_text.encode('latin-1', 'replace').decode('latin-1')
        
        pdf.multi_cell(0, 7, f"Q: {q_text}")
        pdf.ln(2)
        
        # Notes
        raw_notes = item.get('user_notes', '')
        # CLEAN HTML HERE
        clean_notes = clean_html_text(raw_notes)
        
        # Encode for PDF compatibility
        clean_notes = clean_notes.encode('latin-1', 'replace').decode('latin-1')
        
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 6, clean_notes)
        pdf.ln(5)
        
        # Divider
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
    return pdf.output(dest='S').encode('latin-1')

def generate_markdown(notes_list):
    md = "# Exam Notes Summary\n\n"
    for item in notes_list:
        # Clean HTML from question and notes
        q_clean = clean_html_text(item.get('question', ''))
        n_clean = clean_html_text(item.get('user_notes', ''))
        
        md += f"### {q_clean}\n\n"
        md += f"{n_clean}\n\n"
        if item.get('user_diagram'):
             md += "*(Contains Diagram - See App)*\n\n"
        md += "---\n\n"
    return md

# --- Main UI ---

# Get available options
folders = file_manager.get_exam_folders("questions")
files = file_manager.get_exam_files("questions")

# Expand folders...
expanded_folders = set()
for f in folders:
    p = Path(f)
    expanded_folders.add(str(p))
    for parent in p.parents:
        if str(parent) != ".":
            expanded_folders.add(str(parent))

all_options = sorted(list(expanded_folders)) + files
default_idx = 0
current_selection = st.session_state.get('current_exam_folder')
if current_selection and current_selection in all_options:
    default_idx = all_options.index(current_selection)

selected_option = st.selectbox("Select exam to review notes", all_options, index=default_idx)

# Load questions
questions = file_manager.load_questions("questions", selected_option)

# Filter questions with notes
questions_with_notes = []
for q in questions:
    q_id = q.get("id")
    if not q_id: continue
    log_data = file_manager.load_question_log(q_id)
    user_notes = log_data.get("user_notes")
    user_diagram = log_data.get("user_diagram")

    if (user_notes and user_notes.strip()) or (user_diagram and user_diagram.strip()):
        q["user_notes"] = user_notes
        q["user_diagram"] = user_diagram
        questions_with_notes.append(q)

head_slot.markdown(
    ui_components.page_head_html("Notes review", f"{len(questions_with_notes)} with notes"),
    unsafe_allow_html=True)

# --- Feature: Contextual Organization ---

if "ordered_notes" not in st.session_state:
    st.session_state.ordered_notes = None

# Determine display source
display_data = st.session_state.ordered_notes if st.session_state.ordered_notes else questions_with_notes
is_reordered = st.session_state.ordered_notes is not None

# Toolbar: count tile | reorganize | export (near the page head, not in an expander)
st.metric("Questions with notes", len(questions_with_notes), width=260)
t_reorg, t_md, t_pdf = st.columns([2, 1.6, 1.4])
with t_reorg:
    if st.button("Reorganize contextually", icon=":material/auto_awesome:", use_container_width=True):
        with st.spinner("Analyzing semantic flow..."):
            ordered = reorder_notes_conceptually(questions_with_notes)
            st.session_state.ordered_notes = ordered
            st.rerun()
if display_data:
    with t_md:
        md_data = generate_markdown(display_data)
        st.download_button("Download Markdown", md_data, file_name="exam_notes.md", mime="text/markdown",
                           icon=":material/download:", use_container_width=True)
    with t_pdf:
        try:
            pdf_bytes = generate_pdf(display_data)
            st.download_button("Download PDF", pdf_bytes, file_name="exam_notes.pdf", mime="application/pdf",
                               icon=":material/picture_as_pdf:", use_container_width=True)
        except Exception as e:
            st.error(f"PDF Generation Error (font/encoding): {e}")

if is_reordered:
    st.success("Notes are now organized by topic flow.", icon=":material/auto_awesome:")
    if st.button("Reset view"):
        st.session_state.ordered_notes = None
        st.rerun()

# --- Clean / Standard View ---

view_mode = "Standard"
if is_reordered:
    view_mode = st.radio("View mode", ["Standard (Cards)", "Clean Text (Read Mode)"], horizontal=True)

if not display_data:
    st.info("No notes found.", icon=":material/info:")
else:
    if view_mode == "Clean Text (Read Mode)":
        st.markdown("## Consolidated notes")
        for q in display_data:
            st.markdown(f"#### Q: {q.get('question')}")
            st.markdown(q.get("user_notes"))
            st.markdown("---")

    else:
        # Standard Card View
        if 'notes_expanded' not in st.session_state:
            st.session_state['notes_expanded'] = False

        c_btn1, c_btn2 = st.columns(2)
        if c_btn1.button("Expand all", use_container_width=True):
            st.session_state['notes_expanded'] = True
            st.rerun()
        if c_btn2.button("Collapse all", use_container_width=True):
            st.session_state['notes_expanded'] = False
            st.rerun()

        for i, q in enumerate(display_data):
            row_id = f"{i}_{q.get('id', '')}"          # unique even if two files share a question id
            label = " ".join(q.get('question', '').split())[:100] + "..."
            with st.expander(label, icon=":material/sticky_note_2:", expanded=st.session_state['notes_expanded']):
                # Notes in a reading-style panel
                with st.container(key=f"notepanel_{row_id}"):
                    st.markdown(ui_components.md_text(q.get('question', '')))
                    if q.get("user_notes"):
                        st.markdown(q["user_notes"], unsafe_allow_html=True)
                    if q.get("user_diagram"):
                        st.code(q["user_diagram"], language="mermaid")
                with st.expander("Details"):
                    exam_view.render_review_card(row_id, q)
