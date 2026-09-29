"""Sidebar: chat history on top, a compact account box at the bottom."""

from __future__ import annotations

import streamlit as st

from web import auth, config, session
from web.components.settings_dialog import settings_dialog


def sidebar(user_id: str | None) -> None:
    with st.sidebar:
        st.markdown("### 📐 geo-draw")
        st.button("✏️ Cuộc trò chuyện mới", key="new_chat", width="stretch",
                  on_click=session.new_conversation)
        # styles.DASHBOARD_CSS makes this list fill the free height (account box at the bottom).
        with st.container(border=False, key="chat_list"):
            _conversation_list()
        _account_box(user_id)


def _conversation_list() -> None:
    conversations = session.conversations().list(session.owner())
    current_id = session.current_conversation_id()
    if not conversations:
        st.caption("Chưa có cuộc trò chuyện nào.")
        return
    st.caption("Gần đây")
    for conversation in conversations:
        st.button(
            conversation.title, key=f"conv_{conversation.id}", width="stretch",
            type="primary" if conversation.id == current_id else "tertiary",
            on_click=session.open_conversation, args=(conversation.id,),
        )


def _account_box(user_id: str | None) -> None:
    with st.container(border=True, key="account_box"):
        if user_id:
            name = config.ACCOUNTS.display_name(user_id) or "Người dùng"
            with st.popover(f"👤 {name}", width="stretch"):
                if st.button("⚙️ Cài đặt", key="open_settings", type="tertiary"):
                    settings_dialog()
                st.button("↪ Đăng xuất", key="logout", type="tertiary", on_click=auth.logout)
        else:
            st.caption("Đăng nhập để lưu lại lịch sử hỏi đáp")
            with st.container(horizontal=True):
                st.button("Đăng nhập", key="guest_login", type="primary",
                          on_click=auth.go_to_login)
                if st.button("⚙️", key="open_settings", help="Cài đặt"):
                    settings_dialog()
