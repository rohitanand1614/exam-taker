import streamlit as st
import math
from utils import archive_manager, file_manager, ui_helpers, ui_components, exam_view

st.set_page_config(page_title="Archived Questions", page_icon=":material/archive:", layout="wide")

ui_helpers.inject_global_css()

# The page head needs the filtered count, so reserve its place first and fill it below.
head_slot = st.empty()

# 1. Load Data
all_archives = archive_manager.get_all_archives()
if not all_archives:
    head_slot.markdown(ui_components.page_head_html("Archived questions", ui_components.count_line(0, 0, "archived")),
                       unsafe_allow_html=True)
    st.info("No archived questions found.", icon=":material/info:")
    st.stop()

# Convert to list for filtering
archive_list = [{"id": k, **v} for k, v in all_archives.items()]

# Backfill source_file if missing
if any("source_file" not in b["data"] for b in archive_list):
    id_map = file_manager.get_question_id_to_file_map("questions")
    for b in archive_list:
        if "source_file" not in b["data"]:
            b["data"]["source_file"] = id_map.get(b["id"], "Unknown")

# 2. Filter (main area, compact)
available_sources = list(set(b["data"].get("source_file", "Unknown") for b in archive_list))
available_sources.sort()
selected_sources = st.multiselect("Filter by source", available_sources, default=available_sources,
                                  label_visibility="collapsed", placeholder="Filter by source")

# Apply Filter
filtered_archives = [
    b for b in archive_list
    if b["data"].get("source_file", "Unknown") in selected_sources
]

head_slot.markdown(
    ui_components.page_head_html("Archived questions", ui_components.count_line(
        len(archive_list), len(filtered_archives), "archived")),
    unsafe_allow_html=True)

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


def _cb_page(delta):
    st.session_state.page += delta


# 4. Render List
if not current_batch:
    st.warning("No archived questions match your filter.", icon=":material/filter_alt_off:")
else:
    # Pagination controls (same look as the exam action bar); a single page needs none
    if total_pages > 1:
        c_prev, c_mid, c_next = st.columns([1, 3, 1], vertical_alignment="center")
        with c_prev:
            st.button("Previous", key="page_prev", icon=":material/chevron_left:",
                      disabled=(st.session_state.page == 0), on_click=_cb_page, args=(-1,))
        with c_mid:
            st.caption(f"Page {st.session_state.page + 1} of {total_pages}")
        with c_next:
            st.button("Next", key="page_next", icon=":material/chevron_right:",
                      disabled=(st.session_state.page >= total_pages - 1), on_click=_cb_page, args=(1,))

    for item in current_batch:
        q_data = item["data"]
        q_id = item["id"]

        with st.container(border=True, key=f"row_{q_id}"):
            c_row, c_restore = st.columns([6, 2], vertical_alignment="center")
            with c_row:
                st.markdown(
                    ui_components.list_row_html(
                        q_data.get("question", "No Question Text"),
                        [q_data.get("difficulty"), q_data.get("source_file", "Unknown")]),
                    unsafe_allow_html=True)
            with c_restore:
                if st.button("Restore", key=f"unarch_{q_id}", icon=":material/unarchive:",
                             help="Unarchive: put this question back into practice"):
                    archive_manager.unarchive_question(q_id)
                    st.toast("Question restored.", icon=":material/unarchive:")
                    st.rerun()

            with st.expander("Show answer", icon=":material/visibility:"):
                exam_view.render_review_card(q_id, q_data)
