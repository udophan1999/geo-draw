"""Function graphs (hàm số, đồ thị, tích phân) drawn by DeepSeek with Manim ``Axes``.

The geometry pipeline (``ai_codegen``) only knows plane figures; asked to "draw" an integral it
invented a triangle. Problems are therefore routed by ``drawing_kind``: plane geometry goes to
the geometry prompt, functions and integrals to ``GRAPH_PROMPT`` here, anything else is not
drawn at all. Graph code gets the same safety checks as geometry code, but none of the
geometry completeness rules. No LaTeX is installed, so every label must be ``Text``.
"""

from __future__ import annotations

import ast
import re

from .ai_codegen import (
    ALLOWED_IMPORTS, BLOCKED_NAMES, BLOCKED_NODES, AiResult, AiSettings, _ensure_light_theme,
    _request_chat, extract_python,
)
from .branding import APP_NAME
from .tutor import _FIGURES, _RELATIONS, _SOLIDS, _mentions, _plain, is_geometry_problem

GEOMETRY = "geometry"
GRAPH = "graph"

NOT_DRAWABLE = ("Bài này không có hình hay đồ thị để vẽ. Khung hình dùng cho bài hình học và "
                "bài hàm số, đồ thị, tích phân.")
GRAPH_NEEDS_AI = f"Vẽ đồ thị cần chế độ {APP_NAME} AI (Cài đặt → Cách vẽ hình)."

_GRAPH_WORDS = [
    "ham so", "do thi", "tich phan", "nguyen ham", "parabol", "dao ham", "cuc tri", "tiem can",
    "dien tich hinh phang", "khao sat", "dong bien", "nghich bien", "gia tri lon nhat",
    "gia tri nho nhat", "logarit", "ham mu", "luong giac",
]
_SHAPE_WORDS = ["goc", "canh", "diem", "hinh", "duong thang", "tia", "cung"]
_GRAPH_SYMBOLS = re.compile(r"∫|\\int(?![A-Za-z])|\by\s*=|\bf\s*\(\s*x\s*\)")


def is_graph_problem(text: str) -> bool:
    """Whether a problem is about a function's graph or an integral (drawn on axes)."""
    return _mentions(_plain(text), _GRAPH_WORDS) or bool(_GRAPH_SYMBOLS.search(text))


def drawing_kind(text: str) -> str | None:
    """``"geometry"``, ``"graph"`` or ``None`` (nothing to draw: do not invent a figure)."""
    if is_geometry_problem(text):
        return GEOMETRY
    if is_graph_problem(text):
        return GRAPH
    # Anything else with geometry words ("góc xOy", "mảnh vườn hình chữ nhật", solids) is
    # still sketched when asked for; only problems without them are refused.
    if _mentions(_plain(text), _FIGURES + _SOLIDS + _RELATIONS + _SHAPE_WORDS):
        return GEOMETRY
    return None


GRAPH_PROMPT = """You draw the figure for a Vietnamese school math problem about functions, graphs,
or integrals, using Manim Community Edition.

Return ONLY a complete Python module, without markdown or explanation.

Rules:
- Imports: `from manim import *`, `import numpy as np`, and
  `from geo_draw.geometry_primitives import apply_light_theme, fit_scene_to_frame`. Nothing else.
- Define exactly one class `GeoScene(Scene)` with `construct(self)`. Its first statement is
  `apply_light_theme(self)` (white canvas, black ink); its last is `fit_scene_to_frame(self)`,
  called after every object has been added.
- NO LaTeX is installed. Never use MathTex, Tex, Title, DecimalNumber, Integer, Variable or
  Matrix. Never pass include_numbers=True and never call add_coordinates, get_axis_labels,
  get_graph_label, get_x_axis_label or get_y_axis_label. Write every label with Text(...);
  Unicode is fine: "y = x² + 1", "√x", "π", "∫".
- Draw Axes (tips=True, x_length about 9, y_length about 6) whose x_range and y_range cover
  what matters: roots, vertex, extrema, intersections, integration bounds, asymptotes.
- Label a few tick values with Text placed at axes.c2p(...) (below the x-axis, left of the
  y-axis), the axes with Text("x") / Text("y"), and the origin with Text("O").
- Plot every function with axes.plot(lambda x: ..., x_range=[...]) using numpy (np.sin,
  np.exp, np.log, np.sqrt). Keep each curve inside y_range by restricting its x_range, and split
  the range around vertical asymptotes or other discontinuities.
- For a definite integral or an area: shade it with axes.get_area(graph, x_range=(a, b),
  opacity=0.25) (use bounded_graph=... for the area between two curves), draw thin vertical
  lines at x = a and x = b, and label a and b under the x-axis.
- Mark key points (roots, vertex, intersections) with Dot and a Text coordinate label such as
  "(1; 2)". Label each curve with its equation in Text near the curve.
- Black and gray only; do not set other colors.
- Draw only what the problem states or clearly implies. Never add triangles, polygons, or points
  that the problem does not mention.
"""

_NO_LATEX_NAMES = {"MathTex", "Tex", "Title", "DecimalNumber", "Integer", "Variable", "Matrix",
                   "SingleStringMathTex", "BulletedList"}
_NO_LATEX_METHODS = {"add_coordinates", "get_axis_labels", "get_graph_label",
                     "get_x_axis_label", "get_y_axis_label"}


def validate_graph_code(code: str) -> None:
    """Safety checks (as for geometry code) plus the no-LaTeX rules for graphs."""
    if len(code) > 60_000:
        raise ValueError("Mã AI quá dài.")
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ValueError(f"Mã AI sai cú pháp ở dòng {exc.lineno}: {exc.msg}") from exc
    allowed_top_level = (ast.Import, ast.ImportFrom, ast.ClassDef, ast.FunctionDef, ast.Assign,
                         ast.AnnAssign)
    if any(not isinstance(node, allowed_top_level) for node in tree.body):
        raise ValueError("Mã AI chứa lệnh thực thi ở cấp module.")
    for node in ast.walk(tree):
        if isinstance(node, BLOCKED_NODES):
            raise ValueError(f"Mã AI chứa cấu trúc không được phép: {type(node).__name__}")
        if isinstance(node, ast.Import) and any(
                alias.name.split(".")[0] not in ALLOWED_IMPORTS for alias in node.names):
            raise ValueError("Mã AI import thư viện không được phép.")
        if isinstance(node, ast.ImportFrom) and (
                node.level or (node.module or "").split(".")[0] not in ALLOWED_IMPORTS):
            raise ValueError("Mã AI import thư viện không được phép.")
        if isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            raise ValueError(f"Mã AI dùng tên không an toàn: {node.id}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("Mã AI truy cập thuộc tính đặc biệt không an toàn.")
        if isinstance(node, ast.Name) and node.id in _NO_LATEX_NAMES:
            raise ValueError(f"Không dùng {node.id} (cần LaTeX); hãy viết nhãn bằng Text.")
        if isinstance(node, ast.Attribute) and node.attr in _NO_LATEX_METHODS:
            raise ValueError(f"Không gọi {node.attr} (cần LaTeX); hãy viết nhãn bằng Text.")
        if (isinstance(node, ast.keyword) and node.arg == "include_numbers"
                and not (isinstance(node.value, ast.Constant) and node.value.value is False)):
            raise ValueError("Không bật include_numbers (cần LaTeX); ghi số trên trục bằng Text.")
        if (isinstance(node, ast.Dict) and any(
                isinstance(key, ast.Constant) and key.value == "include_numbers"
                and not (isinstance(value, ast.Constant) and value.value is False)
                for key, value in zip(node.keys, node.values))):
            raise ValueError("Không bật include_numbers (cần LaTeX); ghi số trên trục bằng Text.")
    scenes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    if len(scenes) != 1 or scenes[0].name != "GeoScene":
        raise ValueError("Mã AI phải có đúng một class GeoScene(Scene).")
    if "fit_scene_to_frame(self)" not in code:
        raise ValueError("Hãy gọi fit_scene_to_frame(self) sau khi thêm mọi đối tượng.")


def generate_graph_code(problem: str, settings: AiSettings, animate: bool, *,
                        previous_code: str | None = None,
                        repair_log: str | None = None) -> AiResult:
    """Ask DeepSeek for a graph scene; retry up to 3 times when validation fails."""
    mode = ("Use self.play animations and finish with self.wait(0.5)." if animate else
            "Do not use self.play. Add all mobjects with self.add(...) and finish with "
            "self.wait(0.1).")
    user = f"Animation mode: {mode}\n\nMath problem:\n{problem.strip()}"
    if previous_code:
        user += ("\n\nThe current drawing was made for an earlier version of this problem. Return "
                 "a complete updated module that also satisfies every numbered 'Yêu cầu bổ sung'. "
                 "Current module:\n" + previous_code[-9000:])
    if repair_log:
        user += ("\n\nA previous render failed. Return a complete corrected module. Fix this "
                 "error:\n" + repair_log[-12000:])
    messages = [{"role": "system", "content": GRAPH_PROMPT}, {"role": "user", "content": user}]
    try:
        raw = _request_chat(settings, messages)
    except ValueError as exc:
        return AiResult(code="", raw="", ok=False, error=str(exc))
    first_raw = raw
    for attempt in range(4):
        try:
            code = _ensure_light_theme(extract_python(raw))
            validate_graph_code(code)
            return AiResult(code=code, raw=raw, ok=True)
        except ValueError as error:
            if attempt == 3:
                return AiResult(code="", raw=first_raw, ok=False, error=str(error))
            messages += [
                {"role": "assistant", "content": raw[-12000:]},
                {"role": "user", "content": f"Your module failed validation: {error}. Return the "
                                            "full corrected module, following every rule."},
            ]
            try:
                raw = _request_chat(settings, messages)
            except ValueError as exc:
                return AiResult(code="", raw=first_raw, ok=False, error=str(exc))
    return AiResult(code="", raw=first_raw, ok=False, error="Không tạo được đồ thị.")
