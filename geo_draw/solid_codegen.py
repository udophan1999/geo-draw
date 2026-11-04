"""Generate readable 2D textbook projections for school solid-geometry problems."""

from __future__ import annotations

from .ai_codegen import AiResult, AiSettings, _ensure_light_theme, _request_chat, extract_python
from .graphing import validate_graph_code

SOLID_PROMPT = """You draw a Vietnamese middle/high-school solid-geometry figure as a clean 2D
textbook projection using Manim Community Edition.

Return ONLY a complete Python module, without markdown or explanation.

Rules:
- Import only `from manim import *`, `import numpy as np`, and
  `apply_light_theme, fit_scene_to_frame` from `geo_draw.geometry_primitives`.
- Define exactly `class GeoScene(Scene)` and `construct(self)`. Call apply_light_theme first and
  fit_scene_to_frame last. Use a white canvas, black visible edges and gray dashed hidden edges.
- Use an upright oblique or perspective projection appropriate to the named solid. Keep vertical
  edges vertical, the base balanced, and the complete solid centered with readable proportions.
- Draw every named vertex and every edge stated or structurally required by the solid. Define each
  named point as its own uppercase np.array variable, add a Dot, and label it with Text. Keep labels
  clear of edges. Never merge vertices because of projection.
- Solid vertex order and incidence are mathematical facts. Preserve bases, lateral edges, apex,
  centers, diagonals, sections, perpendiculars, midpoints and intersections exactly as stated.
- Hidden existing edges may be DashedLine; visible edges and all auxiliary constructions are solid.
  Do not dash an edge merely to reduce clutter.
- Do not draw a conclusion that the student must prove (perpendicularity, equality, coplanarity,
  special section shape, or a sphere) as if it were already given.
- Use Text for every label; never MathTex, Tex or LaTeX-dependent objects. Black/gray only.
- Do not use ThreeDScene or a moving camera: construct a stable 2D textbook projection that renders
  consistently as an image and remains easy to zoom.
"""

SOLID_INCOMPLETE = "MathMate chưa vẽ được hình không gian này. Hãy ghi rõ các đỉnh, đáy và cạnh bên."


def generate_solid_code(problem: str, settings: AiSettings, animate: bool, *,
                        previous_code: str | None = None,
                        repair_log: str | None = None) -> AiResult:
    mode = ("Use self.play animations and finish with self.wait(0.5)." if animate else
            "Do not use self.play; add objects directly and finish with self.wait(0.1).")
    user = f"Animation mode: {mode}\n\nSolid-geometry problem:\n{problem.strip()}"
    if previous_code:
        user += "\n\nUpdate this existing projection while preserving its layout:\n" + previous_code[-9000:]
    if repair_log:
        user += "\n\nThe previous render failed. Return a corrected full module:\n" + repair_log[-12000:]
    messages = [{"role": "system", "content": SOLID_PROMPT}, {"role": "user", "content": user}]
    first_raw = ""
    for attempt in range(4):
        try:
            raw = _request_chat(settings, messages)
            first_raw = first_raw or raw
            code = _ensure_light_theme(extract_python(raw))
            validate_graph_code(code)
            return AiResult(code=code, raw=raw, ok=True)
        except ValueError as error:
            if attempt == 3:
                return AiResult(code="", raw=first_raw, ok=False, error=SOLID_INCOMPLETE,
                                detail=str(error))
            messages.extend([
                {"role": "assistant", "content": (first_raw or "")[-12000:]},
                {"role": "user", "content": f"Validation failed: {error}. Return the full corrected module."},
            ])
    return AiResult(code="", raw=first_raw, ok=False, error=SOLID_INCOMPLETE)
