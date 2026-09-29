"""Helpers shared by the drawing flow and the manual editor."""

from __future__ import annotations

from pathlib import Path

from geo_draw.engine import build_figure
from geo_draw.parser import parse_problem
from geo_draw.scene_builder import write_scene


def parser_scene(text: str, animate: bool, scene_path: Path) -> tuple[Path, str]:
    problem = parse_problem(text)
    figure = build_figure(problem)
    path = write_scene(figure, scene_path, animate=animate)
    summary = f"Parser · hình {problem.figure} · điểm: {', '.join(sorted(figure.points))}"
    return path, summary


def render_error_summary(log: str) -> str:
    known_errors = {
        "GEOMETRY_INVALID_SEGMENT": "Ký hiệu hình học nhận sai dữ liệu đoạn thẳng.",
        "GEOMETRY_PARALLEL_NO_SEGMENT": "Chưa truyền đoạn thẳng cần đánh dấu song song.",
        "GEOMETRY_LAYOUT_CROWDED": "Các điểm và đối tượng phụ đang quá sát nhau; cần đổi tỷ lệ hình.",
    }
    for code, message in known_errors.items():
        if code in log:
            return message
    lines = [line.strip() for line in log.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith(("ValueError:", "TypeError:", "ImportError:", "NameError:")):
            return line
    return lines[-1] if lines else "Không có thông tin lỗi từ Manim."
