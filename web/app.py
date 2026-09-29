"""Web app entry: page config, routes and the access guard.

Routes:
- ``/login``: login / register (switched by ``session_state["auth_view"]``).
- ``/dashboard``: the main drawing page, for signed-in or anonymous users.
- ``/``: redirects to one of the two above.

All redirects happen here, so the views never need to check who may see them.
"""

from __future__ import annotations

import streamlit as st

from web import session
from web.views.dashboard import dashboard_page
from web.views.login import login_page


def _dashboard() -> None:
    dashboard_page(session.current_user_id())


def _home() -> None:
    """Placeholder for ``/``; main() always redirects before it runs."""


def main() -> None:
    st.set_page_config(layout="wide")  # tab titles come from the pages below
    home = st.Page(_home, title="geo-draw", default=True)
    login = st.Page(login_page, title="Đăng nhập · geo-draw", url_path="login")
    dashboard = st.Page(_dashboard, title="geo-draw", url_path="dashboard")
    current = st.navigation([home, login, dashboard], position="hidden")
    can_use_dashboard = (
        session.current_user_id() is not None or st.session_state.get("anonymous_mode", False)
    )
    target = dashboard if can_use_dashboard else login
    if current.url_path != target.url_path:
        # Carry the session token so a reload on the new route stays signed in.
        token = st.session_state.get("session_token", "")
        st.switch_page(target, query_params={"session": token} if token else None)
    current.run()
