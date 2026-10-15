"""Small CSS tweaks Streamlit has no option for. Selectors use widget keys (``st-key-*``)."""

from __future__ import annotations

import streamlit as st

DASHBOARD_CSS = """
<style>
/* Less empty space above the chat and the drawing. */
[data-testid="stMainBlockContainer"] { padding-top: 2.5rem; }

/* Sidebar as a full-height column: chat list fills the middle, account box at the bottom. */
[data-testid="stSidebarContent"] { display: flex; flex-direction: column; }
[data-testid="stSidebarUserContent"] { flex: 1; display: flex; flex-direction: column;
                                       padding-bottom: 1rem; }
[data-testid="stSidebarUserContent"] > div { flex: 1; display: flex; flex-direction: column; }
[data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] { flex: 1; }
[data-testid="stLayoutWrapper"]:has(> .st-key-chat_list) { flex: 1 1 0; min-height: 0;
                                                          overflow-y: auto; }

/* Chat titles: one left-aligned line with an ellipsis. */
.st-key-chat_list button { justify-content: flex-start; text-align: left; }
.st-key-chat_list button div,
.st-key-chat_list button p { overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
                             max-width: 100%; }
</style>
"""


def dashboard() -> None:
    st.html(DASHBOARD_CSS)
