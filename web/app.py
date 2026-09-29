"""Web app entry: page config and routing between the login screen and the main page."""

from __future__ import annotations

import streamlit as st

from web import session
from web.views.login import login_page
from web.views.main import main_page


def main() -> None:
    st.set_page_config(page_title="geo-draw", layout="wide")
    user_id = session.current_user_id()
    if user_id is None and not st.session_state.get("anonymous_mode"):
        login_page()
    else:
        main_page(user_id)
