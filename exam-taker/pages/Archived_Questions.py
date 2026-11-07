import streamlit as st
import math
from utils import archive_manager, file_manager, ui_helpers

st.set_page_config(page_title="Archived Questions", page_icon="🗄️", layout="wide")

ui_helpers.inject_global_css()
st.markdown("""
<style>
    .archive-card {
        background-color: #1a1f2e;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #252e42;
        margin-bottom: 0.5rem;
    }
    .q-text { font-size: 1rem; font-weight: 500; margin-bottom: 0.5rem; color: #edf2f8; }
    .meta-text { font-size: 0.82rem; color: #6b7a90; }
</style>
""", unsafe_allow_html=True)

st.title("🗄️ Archived Questions")

# 1. Load Data
all_archives = archive_manager.get_all_archives()
if not all_archives:
    st.info("No archived questions found.")
    st.stop()

# Convert to list for filtering
archive_list = [{"id": k, **v} for k, v in all_archives.items()]

# Backfill source_file if missing
if any("source_file" not in b["data"] for b in archive_list):
    id_map = file_manager.get_question_id_to_file_map("questions")
    for b in archive_list:
        if "source_file" not in b["data"]:
            b["data"]["source_file"] = id_map.get(b["id"], "Unknown")

# 2. Sidebar Filters
with st.sidebar:
    st.header("Filters")
    
    # Source Filter
    available_sources = list(set(b["data"].get("source_file", "Unknown") for b in archive_list))
    available_sources.sort()
    selected_sources = st.multiselect("Filter by Source", available_sources, default=available_sources)

    # Apply Filter
    filtered_archives = [
        b for b in archive_list 
        if b["data"].get("source_file", "Unknown") in selected_sources
    ]
    
    st.metric("Total Archived", len(archive_list))
    st.metric("Showing", len(filtered_archives))

# 3. Pagination Logic
ITEMS_PER_PAGE = 10
if "page" not in st.session_state:
    st.session_state.page = 0

total_pages = math.ceil(len(filtered_archives) / ITEMS_PER_PAGE)
# Ensure page is valid
if st.session_state.page >= total_pages:
    st.session_state.page = max(0, total_pages - 1)

start_idx = st.session_state.page * ITEMS_PER_PAGE
end_idx = start_idx + ITEMS_PER_PAGE
current_batch = filtered_archives[start_idx:end_idx]

# 4. Render List
if not current_batch:
    st.warning("No archived questions match your filter.")
else:
    # Pagination Controls (Top)
    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        if st.button("⬅️ Prev", disabled=(st.session_state.page == 0)):
            st.session_state.page -= 1
            st.rerun()
    with c2:
        st.markdown(f"<div style='text-align: center; padding-top: 10px'>Page <b>{st.session_state.page + 1}</b> of <b>{max(1, total_pages)}</b></div>", unsafe_allow_html=True)
    with c3:
        if st.button("Next ➡️", disabled=(st.session_state.page >= total_pages - 1)):
            st.session_state.page += 1
            st.rerun()

    st.divider()

    for item in current_batch:
        q_data = item["data"]
        q_id = item["id"]
        
        # Collapsed format using expander as the main container
        with st.expander(f"📄 {q_data.get('question', 'No Question Text')[:80]}... (ID: {q_id})"):
            st.markdown(
                f'<div class="meta-text">ID: {q_id} | Type: {q_data.get("type", "Unknown")} | Source: {q_data.get("source_file", "Unknown")}</div>',
                unsafe_allow_html=True
            )
            ui_helpers.render_math_text(
                ui_helpers.prepare_math_text(q_data.get('question', 'No Question Text')),
                font_weight="600",
                height=max(60, len(q_data.get('question', '')) // 3 + 40)
            )

            st.write("**Options:**")
            for opt in q_data.get("options", []):
                ui_helpers.render_math_text(ui_helpers.prepare_math_text(f"- {opt}"), height=50)

            st.write("---")
            st.write("**Correct Answer Indices:**", q_data.get("correct_indices", []))
            if "explanation" in q_data:
                st.markdown("**Explanation:**")
                ui_helpers.render_math_text(
                    ui_helpers.prepare_math_text(q_data['explanation']),
                    height=min(400, max(80, len(q_data['explanation']) // 5 + 40))
                )
            
            # Unarchive Button
            if st.button("📤 Unarchive (Restore)", key=f"unarch_{q_id}"):
                archive_manager.unarchive_question(q_id)
                st.toast("Question restored!", icon="📤")
                st.rerun()
            
    st.divider()
