"""Per-browser-session state: signed-in user, workspace folder and the open conversation."""

from __future__ import annotations

import uuid
from pathlib import Path

import streamlit as st

from geo_draw.conversations import ConversationStore
from geo_draw.history import import_into_conversations

from streamlit_app import config

GUEST_OWNER = "guest"


def current_user_id() -> str | None:
    # The URL keeps a random session token (?session=...), so a page reload stays signed in
    # without putting the name itself in the URL, which would bypass the password.
    if "user_id" not in st.session_state:
        token = st.query_params.get("session", "")
        user_id = config.ACCOUNTS.session_user(token)
        st.session_state["user_id"] = user_id or ""
        st.session_state["session_token"] = token if user_id else ""
        if token and not user_id:
            st.query_params.pop("session", None)
    return st.session_state["user_id"] or None


def workspace() -> Path:
    """Logged-in users keep one folder across sessions; each anonymous session gets its own."""
    user_id = current_user_id()
    if user_id:
        return config.USERS_DIR / user_id
    session_id = st.session_state.setdefault("anonymous_session_id", uuid.uuid4().hex[:16])
    return config.SESSIONS_DIR / session_id


def owner() -> str:
    return current_user_id() or GUEST_OWNER


def conversations() -> ConversationStore:
    """Signed-in users share one store; a guest's store lives in their session folder."""
    user_id = current_user_id()
    if not user_id:
        return ConversationStore(workspace())
    if st.session_state.get("history_imported_for") != user_id:
        import_into_conversations(config.HISTORY, config.CONVERSATIONS, user_id)
        st.session_state["history_imported_for"] = user_id
    return config.CONVERSATIONS


# Open conversation and the drawing shown on the right --------------------------------

def current_conversation_id() -> str | None:
    return st.session_state.get("conversation_id") or None


def open_conversation(conversation_id: str | None) -> None:
    st.session_state["conversation_id"] = conversation_id or ""
    st.session_state.pop("viewing_message_id", None)
    reset_manual_edits()


def new_conversation() -> None:
    open_conversation(None)


def view_message(message_id: str) -> None:
    st.session_state["viewing_message_id"] = message_id
    reset_manual_edits()


def reset_manual_edits() -> None:
    """Make the manual editor reload the saved edits of whichever drawing it shows next."""
    st.session_state.pop("edits_for", None)
