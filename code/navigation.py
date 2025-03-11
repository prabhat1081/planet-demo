import streamlit as st
st.set_page_config(layout="wide", page_title='PlaNet Demo', initial_sidebar_state="collapsed")
import os

def main(mode: str):
    main_page = st.Page("1_Run PlaNet.py", title="Run PlaNet", icon=":material/play_arrow:", default=True)

    lookup_page = st.Page(
        "app_pages/2_lookup.py", title="Lookup Requests", icon=":material/search:"
    )
    explorer = st.Page("app_pages/3_explorer.py", title="Explore Requests", icon=":material/admin_panel_settings:")
    result = st.Page(
        "app_pages/4_result.py", title="Predicted Results", icon=":material/analytics:"
    )

    if mode == 'admin':
        pg = st.navigation([main_page, lookup_page, result, explorer])
    else:
        pg = st.navigation([main_page, lookup_page, result], position="hidden")

    pg.run()

if __name__ == "__main__":
    mode = os.getenv('APP_MODE', 'user')
    main(mode)