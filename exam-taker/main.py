"""Exam Taker Pro - entry point with grouped navigation.

    streamlit run main.py

The pages themselves are unchanged (app.py is the Exam page, the others live in pages/).
`streamlit run app.py` still works as before, using Streamlit's automatic pages/ sidebar.
"""
import streamlit as st

# The entry script owns the page config for the whole app; the pages skip theirs when run through here.
st.set_page_config(page_title="Exam Taker Pro", page_icon=":material/menu_book:", layout="wide")

from utils import navigation, ui_helpers

ui_helpers.inject_global_css()

pages = {
    group: [
        st.Page(e["path"], title=e["title"], icon=e["icon"], url_path=e["url_path"], default=e["default"])
        for e in entries
    ]
    for group, entries in navigation.nav_spec().items()
}

page = st.navigation(pages, position="top")   # 4 group menus on top; the sidebar is left to each page
page.run()
