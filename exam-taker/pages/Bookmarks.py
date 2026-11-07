import streamlit as st
import math
from utils import bookmark_manager, file_manager, archive_manager, ui_helpers, ui_components, exam_view

st.set_page_config(page_title="Bookmarks Review", page_icon=":material/bookmark:", layout="wide")

ui_helpers.inject_global_css()

# The page head needs the filtered count, so reserve its place first and fill it below.
head_slot = st.empty()

# 1. Load Data
all_bookmarks = bookmark_manager.get_all_bookmarks()
if not all_bookmarks:
    head_slot.markdown(ui_components.page_head_html("Bookmarks", ui_components.count_line(0, 0, "saved")),
                       unsafe_allow_html=True)
    st.info("No bookmarks found. Go back to the exam and bookmark some questions.", icon=":material/info:")
    st.stop()

# Convert to list for filtering
bookmark_list = [{"id": k, **v} for k, v in all_bookmarks.items()]

# Backfill source_file if missing
if any("source_file" not in b["data"] for b in bookmark_list):
    id_map = file_manager.get_question_id_to_file_map("questions")
    for b in bookmark_list:
        if "source_file" not in b["data"]:
            b["data"]["source_file"] = id_map.get(b["id"], "Unknown")

# 2. Filters (main area): colour pills + compact source multiselect.
#    Same defaults and meaning as the old sidebar multiselects: everything selected.
_present = set(b["color"] for b in bookmark_list)
# same set of colours as before, but in the fixed order of the colour palette (a set shuffles)
available_colors = [c for c in bookmark_manager.BOOKMARK_COLORS if c in _present] + sorted(
    c for c in _present if c not in bookmark_manager.BOOKMARK_COLORS)
available_sources = list(set(b["data"].get("source_file", "Unknown") for b in bookmark_list))
available_sources.sort()

# st.pills colour directives; purple is "violet" in Streamlit markdown
_DIRECTIVE = {"Important (Red)": "red", "Review Later (Orange)": "orange", "Interesting (Blue)": "blue",
              "Hard (Purple)": "violet", "Solved (Green)": "green"}


def _pill_label(color_name):
    label = ui_components.bookmark_style(color_name)[1]
    return f":{_DIRECTIVE.get(color_name, 'gray')}[:material/fiber_manual_record:] {label}"


filter_colors, filter_sources = st.columns([3, 2])
with filter_colors:
    selected_colors = st.pills(
        "Filter by colour", available_colors, selection_mode="multi", default=available_colors,
        format_func=_pill_label, label_visibility="collapsed",
    ) or []
with filter_sources:
    selected_sources = st.multiselect("Filter by source", available_sources, default=available_sources,
                                      label_visibility="collapsed", placeholder="Filter by source")

# Apply Filter
filtered_bookmarks = [
    b for b in bookmark_list
    if b["color"] in selected_colors
    and b["data"].get("source_file", "Unknown") in selected_sources
    and not archive_manager.is_archived(b["id"])
]

head_slot.markdown(
    ui_components.page_head_html("Bookmarks", ui_components.count_line(
        len(bookmark_list), len(filtered_bookmarks), "saved")),
    unsafe_allow_html=True)

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


def _cb_page(delta):
    st.session_state.page += delta


# 4. Render List
if not current_batch:
    st.warning("No bookmarks match your filter.", icon=":material/filter_alt_off:")
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
        color_label = item["color"]
        dot_colour, short_label = ui_components.bookmark_style(color_label)

        with st.container(border=True, key=f"row_{q_id}"):
            c_row, c_rem, c_arch = st.columns([5, 2, 2], vertical_alignment="center")
            with c_row:
                st.markdown(
                    ui_components.list_row_html(
                        q_data.get("question", "No Question Text"),
                        [short_label, q_data.get("difficulty"), q_data.get("source_file", "Unknown")],
                        dot_colour),
                    unsafe_allow_html=True)
            with c_rem:
                if st.button("Remove", key=f"rem_{q_id}", type="tertiary", icon=":material/delete:",
                             help="Remove this bookmark"):
                    bookmark_manager.remove_bookmark(q_id)
                    st.rerun()
            with c_arch:
                if st.button("Archive", key=f"arch_{q_id}", type="tertiary", icon=":material/archive:",
                             help="Move to Archive (remove from active practice)"):
                    archive_manager.archive_question(q_data)
                    st.toast("Question archived.", icon=":material/archive:")
                    st.rerun()

            # Review card: options with the right answer(s) in the success style + explanation
            with st.expander("Show answer", icon=":material/visibility:"):
                exam_view.render_review_card(q_id, q_data)
