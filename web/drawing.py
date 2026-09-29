"""One drawing turn: problem text → DeepSeek or parser → Manim render (with AI repairs)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from geo_draw.ai_codegen import generate_manim_code, missing_reference_figure_points
from geo_draw.renderer import render_scene
from web.rendering import parser_scene, render_error_summary
from web.settings import DrawOptions

REPAIR_ATTEMPTS = 3


@dataclass
class DrawingOutcome:
    ok: bool
    message: str
    scene_path: Path | None = None
    image_path: Path | None = None
    video_path: Path | None = None
    log: str = ""


def draw(problem: str, options: DrawOptions, folder: Path,
         previous_code: str | None = None) -> DrawingOutcome:
    """Draw ``problem`` into ``folder`` (``scene.py`` + ``media/``), showing progress."""
    if options.uses_ai:
        if not options.ai.api_key:
            return DrawingOutcome(False, "Cần DeepSeek API key. Mở **Cài đặt** ở cuối thanh bên để nhập key.")
        missing_points = missing_reference_figure_points(problem)
        if missing_points:
            return DrawingOutcome(
                False,
                "Đề nhắc đến hình minh họa nhưng chưa nêu vị trí các điểm "
                + ", ".join(missing_points)
                + ". Hãy gửi ảnh có đầy đủ hình vẽ hoặc bổ sung các quan hệ "
                "của những điểm này vào đề.",
            )

    folder.mkdir(parents=True, exist_ok=True)
    scene_path = folder / "scene.py"
    media_dir = folder / "media"

    def render():
        return render_scene(scene_path, media_dir, quality=options.quality,
                            animate=options.animate)

    with st.status("Đang vẽ hình...", expanded=False) as status:
        if options.uses_ai:
            status.update(label="DeepSeek đang phân tích đề và viết mã Manim...")
            generated = generate_manim_code(problem, options.ai, options.animate,
                                            previous_code=previous_code)
            if not generated.ok:
                status.update(label="Không tạo được mã vẽ", state="error")
                return DrawingOutcome(False, generated.error)
            scene_path.write_text(generated.code, encoding="utf-8")
            summary = f"DeepSeek AI · {options.model}"
        else:
            scene_path, summary = parser_scene(problem, options.animate, scene_path)

        status.update(label="Manim đang render...")
        result = render()
        if not result.ok and options.uses_ai:
            for attempt in range(1, REPAIR_ATTEMPTS + 1):
                status.update(
                    label=f"Bản vẽ chưa đạt — DeepSeek đang tự cân chỉnh lần {attempt}/{REPAIR_ATTEMPTS}..."
                )
                repair_context = (
                    result.log[-4500:]
                    + "\n\nPrevious module to improve:\n"
                    + scene_path.read_text(encoding="utf-8")[-9000:]
                )
                repaired = generate_manim_code(problem, options.ai, options.animate,
                                               repair_log=repair_context)
                if not repaired.ok:
                    break
                scene_path.write_text(repaired.code, encoding="utf-8")
                result = render()
                if result.ok:
                    break

        if result.ok and result.image_path:
            status.update(label="Đã vẽ xong", state="complete")
            return DrawingOutcome(True, f"Đã vẽ xong · {summary}", scene_path,
                                  result.image_path, result.video_path, result.log)
        status.update(label="Render thất bại", state="error")
        return DrawingOutcome(False, "Manim render thất bại: " + render_error_summary(result.log),
                              scene_path, None, None, result.log)
