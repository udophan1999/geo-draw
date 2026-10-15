"""Login / register screen (/login)."""

from __future__ import annotations

import streamlit as st

from geo_draw.accounts import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH

from streamlit_app import auth


def login_page() -> None:
    """Entry screen shown before the main page until the user signs in or goes anonymous.

    ``session_state["auth_view"]`` switches the card between "login" and "register".
    """
    view = st.session_state.setdefault("auth_view", "login")
    # A fixed width keeps the card compact on wide screens (a column ratio grows with them).
    page = st.container(horizontal_alignment="center")
    with page, st.container(width=380):
        st.space("small")
        st.markdown(
            "<div style='text-align:center'>"
            "<div style='font-size:2.6rem;line-height:1'>📐</div>"
            "<h1 style='padding:0.4rem 0 0.2rem'>geo-draw</h1>"
            "<p style='opacity:0.65;margin:0'>Vẽ hình học THCS từ đề bài hoặc ảnh chụp</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.space("medium")
        with st.container(border=True):
            if view == "login":
                _login_form()
            else:
                _register_form()
        st.space("small")
        with st.container(horizontal=True, horizontal_alignment="center"):
            st.button("Dùng thử không cần tài khoản →", key="continue_anonymous",
                      type="tertiary", on_click=auth.continue_anonymously)
        st.markdown(
            "<p style='text-align:center;opacity:0.55;font-size:0.85rem;margin-top:-0.6rem'>"
            "Hình vẽ khi dùng thử sẽ không được lưu vào lịch sử.</p>",
            unsafe_allow_html=True,
        )


def _login_form() -> None:
    st.markdown("#### Đăng nhập")
    st.caption("Đăng nhập để xem lại lịch sử hình đã vẽ.")
    with st.form("login_form", border=False):
        st.text_input("Tên đăng nhập", key="login_username", max_chars=40)
        st.text_input("Mật khẩu", key="login_password", type="password",
                      max_chars=MAX_PASSWORD_LENGTH)
        st.form_submit_button("Đăng nhập", type="primary", width="stretch",
                              on_click=auth.submit_login)
    if st.session_state.get("login_error"):
        st.error(st.session_state["login_error"])
    with st.container(horizontal=True, horizontal_alignment="center",
                      vertical_alignment="center", gap="xxsmall"):
        st.caption("Chưa có tài khoản?", width="content")
        st.button(":blue[Đăng ký ngay]", key="to_register", type="tertiary",
                  on_click=auth.show_auth_view, args=("register",))


def _register_form() -> None:
    st.markdown("#### Tạo tài khoản")
    st.caption("Tài khoản giúp lưu lại lịch sử hỏi đáp và hình đã vẽ.")
    with st.form("register_form", border=False):
        st.text_input("Tên đăng nhập", key="register_username", max_chars=40,
                      placeholder="Ví dụ: an.nguyen.7a")
        st.text_input("Mật khẩu", key="register_password", type="password",
                      max_chars=MAX_PASSWORD_LENGTH,
                      placeholder=f"Ít nhất {MIN_PASSWORD_LENGTH} ký tự")
        st.text_input("Nhập lại mật khẩu", key="register_password_confirm",
                      type="password", max_chars=MAX_PASSWORD_LENGTH)
        st.form_submit_button("Đăng ký", type="primary", width="stretch",
                              on_click=auth.submit_register)
    if st.session_state.get("register_error"):
        st.error(st.session_state["register_error"])
    suggestions = st.session_state.get("register_suggestions", [])
    if suggestions:
        st.caption("Gợi ý tên còn trống (bấm để dùng):")
        with st.container(horizontal=True):
            for suggestion in suggestions:
                st.button(suggestion, key=f"suggest_{suggestion}",
                          on_click=auth.use_suggested_name, args=(suggestion,))
    with st.container(horizontal=True, horizontal_alignment="center",
                      vertical_alignment="center", gap="xxsmall"):
        st.caption("Đã có tài khoản?", width="content")
        st.button(":blue[Đăng nhập]", key="to_login", type="tertiary",
                  on_click=auth.show_auth_view, args=("login",))
