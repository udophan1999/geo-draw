"""One drawing turn: problem text → DeepSeek or parser → Manim render (with AI repairs).

UI-independent: progress is reported through ``on_progress(stage, label)`` so the
Streamlit app, the FastAPI server and later the mobile backend can all show it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .ai_codegen import AiSettings, generate_manim_code, missing_reference_figure_points
from .engine import build_figure
from .graphing import GRAPH, GRAPH_NEEDS_AI, NOT_DRAWABLE, drawing_kind, generate_graph_code
from .parser import parse_problem
from .renderer import render_scene
from .scene_builder import write_scene

REPAIR_ATTEMPTS = 3

# Progress stages passed to on_progress.
GENERATING = "generating"
RENDERING = "rendering"
REPAIRING = "repairing"

ProgressCallback = Callable[[str, str], None]


@dataclass
class DrawingOutcome:
    ok: bool
    message: str
    scene_path: Path | None = None
    image_path: Path | None = None
    video_path: Path | None = None
    log: str = ""


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


def draw(problem: str, folder: Path, *, ai: AiSettings | None, quality: str = "l",
         animate: bool = False, previous_code: str | None = None,
         on_progress: ProgressCallback | None = None) -> DrawingOutcome:
    """Draw ``problem`` into ``folder`` (``scene.py`` + ``media/``).

    ``ai=None`` uses the local parser. ``previous_code`` is the scene of the drawing being
    extended by a chat follow-up; DeepSeek is asked to keep its layout.
    """
    report = on_progress or (lambda stage, label: None)
    kind = drawing_kind(problem)
    if kind is None:
        return DrawingOutcome(False, NOT_DRAWABLE)
    if kind == GRAPH and ai is None:
        return DrawingOutcome(False, GRAPH_NEEDS_AI)
    # Functions and integrals get axes and curves; the geometry prompt would invent a triangle.
    generate = generate_graph_code if kind == GRAPH else generate_manim_code
    if ai is not None:
        if not ai.api_key:
            return DrawingOutcome(False, "Chưa có DeepSeek API key.")
        missing_points = [] if kind == GRAPH else missing_reference_figure_points(problem)
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
        return render_scene(scene_path, media_dir, quality=quality, animate=animate)

    if ai is not None:
        report(GENERATING, "DeepSeek đang vẽ đồ thị..." if kind == GRAPH else
               "DeepSeek đang phân tích đề và viết mã Manim...")
        generated = generate(problem, ai, animate, previous_code=previous_code)
        if not generated.ok:
            return DrawingOutcome(False, generated.error)
        scene_path.write_text(generated.code, encoding="utf-8")
        summary = f"DeepSeek AI · {ai.model}"
    else:
        scene_path, summary = parser_scene(problem, animate, scene_path)

    report(RENDERING, "Manim đang render...")
    result = render()
    if not result.ok and ai is not None:
        for attempt in range(1, REPAIR_ATTEMPTS + 1):
            report(REPAIRING,
                   f"Bản vẽ chưa đạt — DeepSeek đang tự cân chỉnh lần {attempt}/{REPAIR_ATTEMPTS}...")
            repair_context = (
                result.log[-4500:]
                + "\n\nPrevious module to improve:\n"
                + scene_path.read_text(encoding="utf-8")[-9000:]
            )
            repaired = generate(problem, ai, animate, repair_log=repair_context)
            if not repaired.ok:
                break
            scene_path.write_text(repaired.code, encoding="utf-8")
            result = render()
            if result.ok:
                break

    if result.ok and result.image_path:
        return DrawingOutcome(True, f"Đã vẽ xong · {summary}", scene_path,
                              result.image_path, result.video_path, result.log)
    return DrawingOutcome(False, "Manim render thất bại: " + render_error_summary(result.log),
                          scene_path, None, None, result.log)
