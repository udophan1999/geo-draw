"""Sign-in, registration and sign-out callbacks (run as Streamlit button callbacks)."""

from __future__ import annotations

import streamlit as st

from geo_draw.accounts import MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH, normalize_name, valid_password

from web import config


def _sign_in(user_id: str) -> None:
    token = config.ACCOUNTS.start_session(user_id)
    st.session_state["user_id"] = user_id
    st.session_state["session_token"] = token
    st.query_params["session"] = token
    st.session_state.pop("anonymous_mode", None)
    _forget_user_state()
    _clear_auth_messages()


def _forget_user_state() -> None:
    """Drop the open chat and settings (incl. a typed API key) when the user changes."""
    for key in ("conversation_id", "viewing_message_id", "edits_for", "settings",
                "history_imported_for"):
        st.session_state.pop(key, None)


def continue_anonymously() -> None:
    st.session_state["anonymous_mode"] = True


def go_to_login() -> None:
    st.session_state.pop("anonymous_mode", None)
    show_auth_view("login")


def _clear_auth_messages() -> None:
    for key in ("login_error", "register_error", "register_suggestions"):
        st.session_state.pop(key, None)


def show_auth_view(view: str) -> None:
    st.session_state["auth_view"] = view
    _clear_auth_messages()


def _locked_message(seconds: int) -> str:
    return f"Nhập sai quá nhiều lần. Hãy thử lại sau {-(-seconds // 60)} phút."


def submit_login() -> None:
    _clear_auth_messages()
    name = normalize_name(st.session_state.get("login_username", ""))
    password = st.session_state.get("login_password", "")
    st.session_state["login_password"] = ""
    if not name or not password:
        st.session_state["login_error"] = "Hãy nhập tên đăng nhập và mật khẩu."
        return
    locked = config.ACCOUNTS.locked_seconds(name)
    user_id = None if locked else config.ACCOUNTS.verify(name, password)
    if user_id is None:
        locked = locked or config.ACCOUNTS.locked_seconds(name)
        st.session_state["login_error"] = (
            _locked_message(locked) if locked else "Sai tên đăng nhập hoặc mật khẩu."
        )
        return
    _sign_in(user_id)


def submit_register() -> None:
    _clear_auth_messages()
    name = normalize_name(st.session_state.get("register_username", ""))
    password = st.session_state.get("register_password", "")
    confirm = st.session_state.get("register_password_confirm", "")
    if not name:
        st.session_state["register_error"] = "Hãy nhập tên đăng nhập."
    elif config.ACCOUNTS.name_exists(name):
        st.session_state["register_error"] = (
            f"Tên đăng nhập «{name}» đã có người dùng. Hãy chọn một tên khác."
        )
        st.session_state["register_suggestions"] = config.ACCOUNTS.suggest_names(name)
    elif not valid_password(password):
        st.session_state["register_error"] = (
            f"Mật khẩu phải có từ {MIN_PASSWORD_LENGTH} đến {MAX_PASSWORD_LENGTH} ký tự."
        )
    elif password != confirm:
        st.session_state["register_error"] = "Hai lần nhập mật khẩu không khớp."
    else:
        try:
            user_id = config.ACCOUNTS.create(name, password)
        except ValueError as exc:  # Someone registered the same name a moment earlier.
            st.session_state["register_error"] = str(exc)
        else:
            st.session_state["register_password"] = ""
            st.session_state["register_password_confirm"] = ""
            _sign_in(user_id)


def use_suggested_name(name: str) -> None:
    st.session_state["register_username"] = name
    st.session_state.pop("register_error", None)
    st.session_state.pop("register_suggestions", None)


def logout() -> None:
    config.ACCOUNTS.end_session(st.session_state.get("session_token", ""))
    st.session_state["user_id"] = ""
    st.session_state["session_token"] = ""
    st.query_params.pop("session", None)
    st.session_state.pop("anonymous_mode", None)
    show_auth_view("login")
    # Shared classroom computers: don't leave the previous user's chat or key on screen.
    _forget_user_state()
