"""Streamlit wrapper around ``geo_draw.pipeline.draw`` that shows progress in ``st.status``."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from geo_draw.pipeline import DrawingOutcome
from geo_draw.pipeline import draw as run_pipeline
from streamlit_app.settings import DrawOptions


def draw(problem: str, options: DrawOptions, folder: Path,
         previous_code: str | None = None) -> DrawingOutcome:
    if options.uses_ai and not options.ai.api_key:
        return DrawingOutcome(False, "Cần DeepSeek API key. Mở **Cài đặt** ở cuối thanh bên để nhập key.")
    with st.status("Đang vẽ hình...", expanded=False) as status:
        outcome = run_pipeline(
            problem, folder, ai=options.ai if options.uses_ai else None,
            quality=options.quality, animate=options.animate, previous_code=previous_code,
            on_progress=lambda stage, label: status.update(label=label),
        )
        status.update(label="Đã vẽ xong" if outcome.ok else "Không vẽ được",
                      state="complete" if outcome.ok else "error")
    return outcome
