"""The "Cài đặt" popup, opened from the account menu at the bottom of the sidebar."""

from __future__ import annotations

import streamlit as st

from geo_draw.geometry_knowledge import GEOMETRY_HELP_VI
from streamlit_app import settings


@st.dialog("⚙️ Cài đặt", width="medium")
def settings_dialog() -> None:
    options = settings.current()
    mode = st.radio(
        "Cách dựng hình", settings.MODES, index=settings.MODES.index(options.mode),
        help="AI phù hợp đề phức tạp; parser nhanh chỉ hiểu các mẫu cơ bản và không cần API.",
    )
    api_key, model = options.api_key, options.model
    if mode == settings.AI_MODE:
        api_key = st.text_input(
            "DeepSeek API key", value=options.api_key, type="password",
            help="Key chỉ được giữ trong phiên làm việc này, không ghi vào mã, log hay ổ đĩa.",
        )
        model = st.selectbox("Mô hình DeepSeek", settings.MODELS,
                             index=settings.MODELS.index(options.model),
                             help="flash: nhanh, hợp đa số đề · pro: ưu tiên chất lượng cho đề phức tạp.")
    left, right = st.columns(2)
    quality = left.selectbox("Chất lượng Manim", settings.QUALITIES,
                             index=settings.QUALITIES.index(options.quality),
                             help="l nhanh nhất; m, h đẹp hơn nhưng chậm hơn.")
    right.space("small")
    animate = right.checkbox("Xuất video hoạt hình", value=options.animate,
                             help="Video cần FFmpeg; ảnh tĩnh chỉ cần Manim.")
    with st.expander("Quy ước hình học THCS"):
        st.markdown(GEOMETRY_HELP_VI)

    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("Hủy"):
            st.rerun()
        if st.button("Lưu", type="primary"):
            settings.save(settings.DrawOptions(mode=mode, api_key=api_key, model=model,
                                               animate=animate, quality=quality))
            st.rerun()
