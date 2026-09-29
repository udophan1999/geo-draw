"""Sidebar sections of the main page."""

from __future__ import annotations

import time
from dataclasses import dataclass

import streamlit as st

from geo_draw.ai_codegen import AiSettings
from geo_draw.geometry_knowledge import GEOMETRY_HELP_VI
from web import auth, config, session

AI_MODE = "DeepSeek AI"
PARSER_MODE = "Parser nhanh (không dùng API)"


@dataclass
class DrawOptions:
    mode: str
    ai: AiSettings
    animate: bool
    quality: str

    @property
    def uses_ai(self) -> bool:
        return self.mode == AI_MODE


def account_section(user_id: str) -> None:
    st.header("Tài khoản")
    st.write(f"👤 {config.ACCOUNTS.display_name(user_id) or 'Người dùng'}")
    st.button("Đăng xuất", on_click=auth.logout)
    entries = config.HISTORY.list(user_id)
    with st.expander(f"Lịch sử hỏi đáp ({len(entries)})"):
        if not entries:
            st.caption("Chưa có hình nào được lưu. Hình vẽ thành công sẽ tự lưu vào đây.")
        for entry in entries:
            when = time.strftime("%d/%m %H:%M", time.localtime(entry.created_at))
            title = " ".join(entry.problem.split())
            if len(title) > 48:
                title = title[:48] + "…"
            st.button(
                f"{when} · {title}", key=f"history_{entry.id}", width="stretch",
                on_click=session.open_history_entry, args=(entry,),
            )


def options_section(env: AiSettings) -> DrawOptions:
    st.header("Tùy chọn")
    mode = st.radio(
        "Cách dựng hình",
        [AI_MODE, PARSER_MODE],
        help="AI phù hợp đề phức tạp; parser nhanh chỉ hiểu các mẫu cơ bản.",
    )
    api_key = ""
    model = env.model
    if mode == AI_MODE:
        api_key = st.text_input(
            "DeepSeek API key",
            value=env.api_key,
            type="password",
            help="Key chỉ dùng cho yêu cầu hiện tại và không được ghi vào mã hoặc log.",
        )
        model = st.selectbox(
            "Mô hình DeepSeek",
            ["deepseek-v4-flash", "deepseek-v4-pro"],
            index=1 if env.model == "deepseek-v4-pro" else 0,
        )
    example = st.selectbox("Đề mẫu", list(config.EXAMPLES))
    if st.button("Dùng đề mẫu"):
        st.session_state["problem"] = config.EXAMPLES[example]
    animate = st.checkbox("Xuất video hoạt hình", value=False)
    quality = st.selectbox("Chất lượng Manim", ["l", "m", "h"], index=0)
    st.caption("Chất lượng l nhanh nhất. Video cần FFmpeg; ảnh tĩnh chỉ cần Manim.")
    with st.expander("Quy ước hình học THCS"):
        st.markdown(GEOMETRY_HELP_VI)
    ai = AiSettings(api_key=api_key.strip(), model=model, base_url=env.base_url,
                    vision_model=env.vision_model)
    return DrawOptions(mode=mode, ai=ai, animate=animate, quality=quality)
