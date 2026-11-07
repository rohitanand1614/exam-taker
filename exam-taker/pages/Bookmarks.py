import streamlit as st
import math
from utils import bookmark_manager, file_manager, archive_manager, ui_helpers

st.set_page_config(page_title="Bookmarks Review", page_icon="🔖", layout="wide")

ui_helpers.inject_global_css()
st.markdown("""
<style>
    .bookmark-card {
        background-color: #1a1f2e;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #252e42;
        margin-bottom: 1rem;
    }
    .q-text { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.75rem; color: #edf2f8; }
    .meta-text { font-size: 0.85rem; color: #6b7a90; }
</style>
""", unsafe_allow_html=True)

st.title("🔖 Bookmarked Questions")

# 1. Load Data
all_bookmarks = bookmark_manager.get_all_bookmarks()
if not all_bookmarks:
    st.info("No bookmarks found. Go back to the exam and bookmark some questions!")
    st.stop()

# Convert to list for filtering
bookmark_list = [{"id": k, **v} for k, v in all_bookmarks.items()]

# Backfill source_file if missing
if any("source_file" not in b["data"] for b in bookmark_list):
    id_map = file_manager.get_question_id_to_file_map("questions")
    for b in bookmark_list:
        if "source_file" not in b["data"]:
            b["data"]["source_file"] = id_map.get(b["id"], "Unknown")

# 2. Sidebar Filters
with st.sidebar:
    st.header("Filters")
    
    # Color Filter
    available_colors = list(set(b["color"] for b in bookmark_list))
    selected_colors = st.multiselect("Filter by Color", available_colors, default=available_colors)
    
    # Apply Filter
    # Source Filter
    available_sources = list(set(b["data"].get("source_file", "Unknown") for b in bookmark_list))
    available_sources.sort()
    selected_sources = st.multiselect("Filter by Source", available_sources, default=available_sources)

    # Apply Filter
    filtered_bookmarks = [
        b for b in bookmark_list 
        if b["color"] in selected_colors
        and b["data"].get("source_file", "Unknown") in selected_sources
        and not archive_manager.is_archived(b["id"])
    ]
    
    st.metric("Total Bookmarks", len(bookmark_list))
    st.metric("Showing", len(filtered_bookmarks))

# 3. Pagination Logic
ITEMS_PER_PAGE = 5
if "page" not in st.session_state:
    st.session_state.page = 0

total_pages = math.ceil(len(filtered_bookmarks) / ITEMS_PER_PAGE)
# Ensure page is valid
if st.session_state.page >= total_pages:
    st.session_state.page = max(0, total_pages - 1)

start_idx = st.session_state.page * ITEMS_PER_PAGE
end_idx = start_idx + ITEMS_PER_PAGE
current_batch = filtered_bookmarks[start_idx:end_idx]

# 4. Render List
if not current_batch:
    st.warning("No bookmarks match your filter.")
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
        color_label = item["color"]
        
        with st.container():
            st.markdown(f"""
            <div class="bookmark-card">
                <div style="float:right; font-size: 1.2rem">{color_label.split(' ')[0]}</div>
                <div class="meta-text">ID: {q_id} | Type: {q_data.get('type', 'Unknown')} | Source: {q_data.get('source_file', 'Unknown')}</div>
            </div>
            """, unsafe_allow_html=True)
            ui_helpers.render_math_text(
                ui_helpers.prepare_math_text(q_data.get('question', 'No Question Text')),
                font_weight="600",
                height=max(60, len(q_data.get('question', '')) // 3 + 40)
            )

            # Expander for details
            with st.expander("Show Details & Options"):
                # Options
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
                
                # Remove Button
                c1, c2 = st.columns([1, 1])
                with c1:
                    if st.button("🗑️ Remove Bookmark", key=f"rem_{q_id}"):
                        bookmark_manager.remove_bookmark(q_id)
                        st.rerun()
                with c2:
                    if st.button("🗄️ Archive", key=f"arch_{q_id}"):
                        archive_manager.archive_question(q_data)
                        st.toast("Question archived!", icon="🗄️")
                        st.rerun()
            
            st.write("") # Spacer

    st.divider()
