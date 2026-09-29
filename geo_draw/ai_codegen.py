"""Generate and validate a Manim scene with the DeepSeek API."""

from __future__ import annotations

import ast
import base64
import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .geometry_knowledge import DRAWING_ERROR_MEMORY, MIDDLE_SCHOOL_GEOMETRY_RULES


SYSTEM_PROMPT = """You convert plane-geometry problems (usually Vietnamese) into Manim Community Edition code.

Return ONLY a complete Python module, without markdown or explanation.

Rules:
- Import `from manim import *`, `import numpy as np`, and the verified helpers you use from
  `geo_draw.geometry_primitives`. Do not import anything else.
- Define exactly one class: `class GeoScene(Scene)` with `construct(self)`.
- Import `apply_light_theme` and make `apply_light_theme(self)` the first statement in `construct`.
  It guarantees a white canvas with black geometry, dots, labels, and construction marks. Never set
  `self.camera.background_color` directly and never override this black-and-white theme.
- Never use MathTex, Tex, LaTeX, file/network/process access, dynamic imports, eval, or exec.
- Use real 2D coordinates. Draw every stated point, segment, circle, right angle, midpoint,
  altitude, median, angle bisector, parallel/perpendicular line, tangent, and requested construction.
- Define every named geometry point as its own uppercase variable inside `construct`, for example
  `A = np.array(...)`, `E = ...`, and `I = ...`. Do not hide named points only inside a list,
  dictionary, loop, lowercase alias, helper function, or anonymous coordinate expression. Add an
  explicit Dot and `safe_point_label` for every named point.
- Preserve every condition when adding later constructions: auxiliary points, opposite rays, and
  extra lines must never remove or replace previously requested angles, marks, labels, or sides.
- Show every explicitly stated numerical length exactly once with a compact Text label beside its
  segment (for example `Text("4 cm", font_size=24)` below AC). Do not replace the segment with text
  and do not invent labels for unstated lengths.
- Optimize for a middle-school student's visual reading, not merely mathematical validity. Spread
  important auxiliary points, perpendicular feet, intersections, and midpoints so labels and marks
  have clear negative space. Avoid skinny, excessively wide, or excessively tall shapes and
  near-coincident construction points. Aim for a main-figure bounding-box aspect ratio between
  about 1.2 and 1.8 (never above 2.0), normally 7-9 Manim units wide and 4.5-6.5 units high.
- When three or more important auxiliary points form the focus of the exercise, call
  `layout_spacing_check(E, I, F, all_points=(A, B, C, D), maximum_aspect_ratio=2.0)` after
  computing them. For a symmetric
  configuration such as perpendicular feet E,F around diagonal intersection I, make EI and IF each
  at least about 12% of the main diagonal and make EF visually substantial before this check.
  For the common pattern "parallelogram ABCD; AE and CF perpendicular to BD; AC meets BD at I",
  a reliable balanced template is A=(-3.5,2), B=(2.5,2), C=(3.5,-2), D=(-2.5,-2), followed by
  exact projections for E,F and I=(A+C)/2. Rotate or scale uniformly if useful. Never weaken,
  bypass, catch, or remove `layout_spacing_check` to make a crowded scene pass.
- After every object has been added, call `fit_scene_to_frame(self)` once so the complete drawing,
  including labels and exterior points, stays inside the camera frame.
- Use a white background and black Dot + Text labels, solid Line, Circle, Arc, Angle, and RightAngle.
- Never use `DashedLine`. In plane geometry, every line, ray, segment, altitude, perpendicular
  bisector, extension, and auxiliary construction must be drawn with a continuous solid stroke.
- Place every point name with `safe_point_label`, not a guessed Text offset. Positional arguments
  after the name must be only points directly joined to that point by a drawn side, diagonal, or
  auxiliary line; never pass every point in the scene. Pass other nearby points via `avoid_points`
  and drawn segments via `avoid_segments`, so vertex names stay outside the polygon and labels near
  feet/midpoints do not touch sides, diagonals, or right-angle marks. Example:
  `safe_point_label(H, "H", A, B, D, I, avoid_points=(C, K),`
  `avoid_segments=((A, B), (B, D), (C, D)))`.
- Follow the requested animation mode exactly.

Exact construction requirements:
- First solve coordinates from the stated constraints; never place a requested point by eye.
- Midpoint M of BC: use `M = (B + C) / 2` and verify it with `midpoint_marker`.
- For grouped statements such as "E, F lần lượt là trung điểm của AB và AC", call
  `midpoint_marker(E, A, B, count=...)` and `midpoint_marker(F, A, C, count=...)` separately.
  If AB=AC is given (for example, ABC is isosceles at A), these two midpoint groups use the same
  count. A separate statement "E là trung điểm của OM" additionally requires
  `midpoint_marker(E, O, M, count=...)` with a different count unless equality is established.
  Never place another equality marker over either half of a midpoint-marked segment.
  Pass every other named point using `other_points=(...)`, for example
  `midpoint_marker(M, B, C, other_points=(A, H, N))`. If H lies inside CM, the helper keeps the
  midpoint verification but hides both ticks, so the drawing cannot be misread as CH=MB.
- Median AM: compute M as the midpoint of BC, then draw the segment from A to M.
- Altitude AH to BC: use orthogonal projection
  `H = B + dot(A-B, C-B) / dot(C-B, C-B) * (C-B)`, draw AH and a RightAngle at H.
- Internal angle bisector from A: normalize vectors AB and AC, sum the unit vectors for the
  direction, then intersect that ray with BC. Equivalently use the angle-bisector theorem
  `BD/DC = AB/AC`. `angle_bisector_segment` draws the bisector and matching arcs on both halves.
  A phrase such as "BD là tia phân giác của góc B" is not a numerical angle request: do not add
  `interior_angle_marker` for the whole angle unless its degree measure is explicitly stated.
  The two small half-angle arcs are already produced by `angle_bisector_segment`; never add raw
  Angle/Arc objects or duplicate the bisector with another Line. Keep the vertex label outside
  the polygon, away from these interior arcs.
- `angle_bisector_segment` automatically numbers the two sub-angles 1 and 2. Whenever several
  angle bisectors are drawn in a polygon, pass every possible non-incident boundary side through
  `boundary_segments=...`; the helper extends the solid bisector ray past its named intersections
  to the first polygon side it meets. Do not draw a disconnected short replacement segment.
- For named interior intersections such as E, F, G, H, keep labels close to their dots with
  `distance=0.32` to `0.42` in `safe_point_label`, while still listing all incident/nearby segments
  for collision avoidance. Vertex labels may retain the normal larger distance.
- Perpendicular bisector of BC: pass through `(B+C)/2` in direction
  `[-(C-B)[1], (C-B)[0], 0]`; extend it visibly on both sides and add a right-angle mark.
- For every auxiliary line through M perpendicular to AH, use
  `self.add(perpendicular_through_point(M, A, H, N))` when it also reaches a named point N.
  This helper draws the solid auxiliary line and places a right-angle square at its actual
  intersection with AH. Each separate perpendicular relation needs its own helper and marker.
- For explicit relations such as `AH vuông góc với BD tại H` and
  `CK vuông góc với BD tại K`, add `altitude_segment(A, H, B, D)` and
  `altitude_segment(C, K, B, D)` separately. Never let one right-angle square satisfy two clauses.
  This helper automatically places each square between the altitude ray toward its apex and the
  ray toward the actual reference segment. Never add or reposition a raw RightAngle yourself.
- When two full lines or diagonals are perpendicular at one intersection O, draw exactly one square
  with `self.add(perpendicular_intersection_marker((A, C), (B, D), O))`. One square represents the
  entire perpendicular relation; never draw the other three right-angle sectors at O.
- A point E on the ray from B opposite to BC must be computed with
  `E = opposite_ray_point(B, C, distance=...)`; if EB=BC, omit distance or use `np.linalg.norm(C-B)`.
- A specified angle must determine the ray coordinates with sine/cosine (or an equivalent
  exact construction). For polygon angles, use only `interior_angle_marker`; it already creates
  both the interior arc and the degree label.
- When a triangle is determined by two stated angles, construct the two inward ray directions and
  set the remaining vertex with `ray_intersection(A, dirA, C, dirC)`. Never hand-code the
  determinant signs. The helper rejects an intersection behind either ray, which prevents a
  requested angle such as 30 degrees from becoming its supplementary 150-degree angle.
- Use stable line/ray intersection math. Guard only genuinely degenerate denominators.
- When a newly constructed line intersects the line containing AB at an exterior point E, draw the
  carrier with `self.add(line_through_intersection(A, B, E))`. This replaces a short `Line(A, B)`
  and extends the solid line through E. Do not demand an extension for an ordinary internal
  intersection of two already drawn segments or diagonals, such as "AC cắt BD tại I"; draw both
  AC and BD through I normally.
- Add conventional geometry marks only for construction data stated in the problem: equal-length
  ticks, equal-angle arcs, and right-angle squares. All main and auxiliary lines remain solid.
- A shape name constrains coordinates but does not by itself request equality ticks. For a
  parallelogram, rectangle, square, or rhombus, never mark equal sides unless the problem explicitly
  states a segment equality or explicitly asks for those marks. In particular, do not infer and
  mark AB=CD or AD=BC merely from the word "parallelogram". Draw auxiliary objects normally and
  add only their explicitly required markers, such as right-angle squares and midpoint ticks.
- Construct named parallelograms and trapezoids with genuinely parallel coordinates. The invisible
  `parallel_segment_marks` verifier is mandatory for an explicit relation such as AB//CD or
  "song song", but its absence alone must not prevent rendering when only the standard shape name
  is given.
- A plain "tam giác ABC" must look scalene and non-right; a plain "tứ giác ABCD" must not
  accidentally look like a trapezoid, parallelogram, rectangle, or kite. Avoid near-equalities,
  near-right angles, and near-parallel opposite sides unless the givens require them. The app
  automatically checks the original named polygon with `ordinary_polygon_check` before render.
  If GEOMETRY_ACCIDENTAL_SPECIAL occurs, change the original vertex coordinates and recompute all
  dependent points. Do not change or delete a stated condition. A special auxiliary polygon that
  the problem asks students to prove (for example AHCE is a rectangle) must still be constructed
  accurately; the ordinary-shape check applies only to the original ABC/ABCD.
- For every stated equilateral triangle ABC, construct three genuinely equal side lengths and call
  `equilateral_triangle_check(A, B, C)` before rendering. This is an invisible numerical check;
  do not add side ticks unless the problem explicitly requests equality marks.
- Treat text after "chứng minh"/"prove" as a proof goal, not as given construction data. Draw the
  named segments needed by the goal, but never add equality ticks, equal-angle arcs, or right-angle
  squares for a conclusion such as "Chứng minh IB = ID" or "Chứng minh EFGH là hình chữ nhật".
- Resolve explicitly given segment equalities transitively before drawing ticks. Put every segment
  in one stated equality class into one `equal_segment_marks(...)` call with one shared count.
  Never mark the same segment in two calls, never mix unrelated segments in a call, and give
  different equality classes different counts. Example: if AB=CD and EF=GH are separately stated,
  use count=1 for `(A,B),(C,D)` and count=2 for `(E,F),(G,H)`.
- For all mathematical markers and special lines, use the verified helpers from
  `geo_draw.geometry_primitives`: apply_light_theme, interior_angle_marker, equal_segment_marks,
  parallel_segment_marks, midpoint_marker, median_segment, altitude_segment,
  equilateral_triangle_check,
  perpendicular_intersection_marker,
  angle_bisector_segment, perpendicular_bisector, perpendicular_through_point,
  opposite_ray_point, ray_intersection, ray, infinite_line,
  line_through_intersection, layout_spacing_check, safe_point_label, and fit_scene_to_frame.
- Do not manually construct angle arcs, equality ticks, parallel arrows, medians, altitudes,
  angle bisectors, or perpendicular bisectors with raw Line/Arc/Angle objects.
- Every finite segment must remain a plain Line without arrowheads. Arrowheads are reserved for
  rays/vectors. `parallel_segment_marks` verifies parallelism but intentionally draws nothing.
- A raw `Line` must connect named points directly. Never create oversized carrier lines with
  arithmetic endpoints such as `Line(C - 12*n, C + 12*n)`: they shrink the actual figure and
  create large empty margins. Use `line_through_intersection` for a required extension.
- Call `interior_angle_marker` exactly once for each angle explicitly stated in the problem.
  Never add a separate `Text("50°")`, Arc, or Angle for an angle already handled by this helper.
- Give unequal stated angles different arc counts with `mark_count=1`, `2`, or `3`; give equal
  angles the same mark_count. For example, 50° may use one arc and 130° two arcs.
- Call helpers with these exact signatures:
  `apply_light_theme(self)` as the first statement in `construct`;
  `parallel_segment_marks((A, B), (C, D), count=1)`;
  `equal_segment_marks((A, D), (B, C), count=1)`;
  `interior_angle_marker([A, B, C, D], vertex_index, degrees=120, mark_count=1)`;
  `midpoint_marker(M, B, C)`; `median_segment(A, M, B, C)`;
  `altitude_segment(A, H, B, C)`;
  `angle_bisector_segment(A, E, B, D, boundary_segments=((B, C), (C, D)))`;
  `perpendicular_intersection_marker((A, C), (B, D), O)`;
  `perpendicular_bisector(B, C)`; `perpendicular_through_point(M, A, H, N)`;
  `B = ray_intersection(A, dirA, C, dirC)`;
  `E = opposite_ray_point(B, C)`;
  `line_through_intersection(A, B, E)`;
  `layout_spacing_check(E, I, F, all_points=(A, B, C, D), maximum_aspect_ratio=2.0)`;
  `safe_point_label(E, "E", B, avoid_points=(A, C, D),`
  `avoid_segments=((A, B), (B, C)))`; `fit_scene_to_frame(self)`.
  Never pass a Manim Line object to these helpers.
- Every visible helper result must be passed directly to `self.add(...)`, or assigned and then
  added later. A standalone call such as `interior_angle_marker(...)` does not draw anything and
  is forbidden. `altitude_segment` already includes its right-angle square.
- Before returning code, audit the finished scene against the original problem sentence by sentence.
  Every named point must be defined, dotted, labeled, and connected as requested; every numerical
  angle and every equality/perpendicular/parallel/opposite-ray relation must remain visible or be
  verified by its helper. Never satisfy a later clause by deleting an earlier clause.
- Draw a measurement/relationship marker only when the problem states or logically requires it.
  In particular, do not draw angle arcs when the problem does not ask for an angle.
- Never call `np.cross` in generated code. For a 2D determinant use
  `u[0] * v[1] - u[1] * v[0]`, or rely on the verified helper.
""" + MIDDLE_SCHOOL_GEOMETRY_RULES + DRAWING_ERROR_MEMORY

ALLOWED_IMPORTS = {"manim", "numpy", "geo_draw"}
BLOCKED_NAMES = {
    "open", "exec", "eval", "compile", "input", "breakpoint", "help",
    "globals", "locals", "vars", "getattr", "setattr", "delattr", "__import__",
    "exit", "quit", "os", "sys", "subprocess", "socket", "pathlib", "shutil",
    "requests", "urllib", "http", "ctypes", "pickle", "importlib", "builtins",
}
BLOCKED_NODES = (
    ast.AsyncFunctionDef, ast.Await, ast.Global, ast.Nonlocal, ast.Try, ast.With,
    ast.AsyncWith, ast.While, ast.Delete,
)


@dataclass
class AiSettings:
    api_key: str
    model: str = "deepseek-v4-flash"
    base_url: str = "https://api.deepseek.com"
    vision_model: str = "deepseek-v4-flash-vision-exp"


@dataclass
class AiResult:
    code: str
    raw: str
    ok: bool
    error: str = ""


def load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE entries without overriding the process environment."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def settings_from_env() -> AiSettings:
    return AiSettings(
        api_key=os.environ.get("DEEPSEEK_API_KEY", "").strip(),
        model=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash").strip()
        or "deepseek-v4-flash",
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        .strip().rstrip("/"),
        vision_model=os.environ.get(
            "DEEPSEEK_VISION_MODEL", "deepseek-v4-flash-vision-exp"
        ).strip() or "deepseek-v4-flash-vision-exp",
    )


def extract_python(text: str) -> str:
    fences = re.findall(r"```(?:python)?\s*\n(.*?)```", text, re.S | re.I)
    if fences:
        return max(fences, key=len).strip()
    if "class GeoScene" in text:
        start = text.find("from manim")
        if start < 0:
            start = text.find("class GeoScene")
        return text[start:].strip()
    raise ValueError("DeepSeek không trả về class GeoScene.")


def _drawing_facts_text(problem: str) -> str:
    """Return givens and constructions while excluding proof conclusions."""
    facts = []
    in_proof = False
    in_figure_description = False
    for clause in re.split(r"[.;\n]+", problem):
        clause = clause.strip()
        if not clause:
            continue
        parts = re.split(
            r"\b(?:chứng\s+minh|prove|show\s+that)\b",
            clause,
            maxsplit=1,
            flags=re.I,
        )
        if len(parts) == 2:
            given = parts[0].strip()
            if not in_proof and given:
                facts.append(given)
            in_proof = True
        elif not in_proof:
            facts.append(clause)
        elif re.match(r"^theo\s+hình\s+vẽ\s*:", clause, re.I):
            # OCR may append an explicit description of the referenced figure
            # after all proof goals. This is source evidence, not a conclusion.
            facts.append(clause)
            in_figure_description = True
        elif in_figure_description:
            facts.append(clause)
        elif re.match(r"^[a-z]\s*[)/]|^\d+\s*[)/]", clause, re.I) and re.search(
            r"\b(?:kẻ|vẽ|dựng|gọi|lấy|cho\s+điểm)\b", clause, re.I,
        ):
            # A later exercise part can introduce a new construction.
            facts.append(clause)
            in_proof = False
        # A theorem of the form "chứng minh rằng nếu X thì Y" uses X as an
        # additional hypothesis.  Keep that antecedent for the diagram while
        # still excluding the conclusion Y.
        if len(parts) == 2:
            conditional = re.search(
                r"\b(?:rằng\s+)?nếu\s+(.+?)\s+thì\b",
                parts[1],
                flags=re.I,
            )
            if conditional:
                facts.append(conditional.group(1).strip(" ,:"))
    return ". ".join(facts)


def missing_reference_figure_points(problem: str) -> list[str]:
    """Find proof-only points whose placement depends on an unseen numbered figure."""
    if not re.search(r"\b(?:trong|theo|xem)\s+hình\s*\d+\b", problem, re.I):
        return []
    proof = re.search(r"\b(?:chứng\s+minh|prove|show\s+that)\b", problem, re.I)
    if not proof:
        return []
    givens = _drawing_facts_text(problem)
    given_tokens = re.findall(r"(?<![A-Z])([A-Z]{2,6})(?![A-Z])", givens)
    goal_tokens = re.findall(r"(?<![A-Z])([A-Z]{2,6})(?![A-Z])", problem[proof.end():])
    given_points = {point for token in given_tokens for point in token}
    given_points.update(re.findall(r"\b[A-Z]\b", givens))
    goal_points = {point for token in goal_tokens for point in token}
    return sorted(goal_points - given_points)


def validate_code(code: str, problem: str | None = None) -> None:
    if len(code) > 60_000:
        raise ValueError("Mã AI quá dài.")
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ValueError(f"Mã AI sai cú pháp ở dòng {exc.lineno}: {exc.msg}") from exc

    allowed_top_level = (ast.Import, ast.ImportFrom, ast.ClassDef, ast.FunctionDef, ast.Assign, ast.AnnAssign)
    if any(not isinstance(node, allowed_top_level) for node in tree.body):
        raise ValueError("Mã AI chứa lệnh thực thi ở cấp module.")

    scene_classes = []
    functions = []
    called_names = set()
    direct_angle_calls = 0
    direct_arc_calls = 0
    interior_angle_calls = 0
    interior_angle_nodes = []
    degree_text_calls = 0
    parallel_marker_calls = 0
    parallel_segment_calls = []
    equal_segment_calls = []
    midpoint_calls = []
    angle_bisector_calls = []
    perpendicular_intersection_calls = []
    equilateral_triangle_calls = []
    for node in ast.walk(tree):
        if isinstance(node, BLOCKED_NODES):
            raise ValueError(f"Mã AI chứa cấu trúc không được phép: {type(node).__name__}")
        if isinstance(node, ast.Import):
            if any(alias.name.split(".")[0] not in ALLOWED_IMPORTS for alias in node.names):
                raise ValueError("Mã AI import thư viện không được phép.")
        if isinstance(node, ast.ImportFrom):
            if node.level or (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                raise ValueError("Mã AI import thư viện không được phép.")
        if isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            raise ValueError(f"Mã AI dùng tên không an toàn: {node.id}")
        if isinstance(node, ast.Name) and node.id == "DashedLine":
            raise ValueError("Không dùng DashedLine; mọi đường hình học phải là nét liền.")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("Mã AI truy cập thuộc tính đặc biệt không an toàn.")
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            assignment_targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(
                isinstance(target, ast.Attribute) and target.attr == "background_color"
                for target in assignment_targets
            ):
                raise ValueError(
                    "Không đặt background_color trực tiếp; hãy dùng apply_light_theme(self) "
                    "để có nền trắng và nét đen."
                )
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "np" and node.func.attr == "cross"):
            raise ValueError("Không dùng np.cross; hãy dùng hàm hình học đã kiểm chứng.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Angle":
            direct_angle_calls += 1
            if not any(keyword.arg == "other_angle" for keyword in node.keywords):
                raise ValueError(
                    "Ký hiệu Angle của đa giác phải chỉ định other_angle để nằm phía trong."
                )
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "RightAngle"):
            raise ValueError(
                "Không tạo RightAngle trực tiếp; mỗi cặp đường vuông góc tại một giao điểm "
                "chỉ dùng một perpendicular_intersection_marker hoặc helper đường phụ phù hợp."
            )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "Arc":
                direct_arc_calls += 1
            elif node.func.id == "interior_angle_marker":
                interior_angle_calls += 1
                interior_angle_nodes.append(node)
            elif node.func.id == "parallel_segment_marks":
                parallel_marker_calls += 1
                parallel_segment_calls.append(node)
            elif node.func.id == "Text" and node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                    if "°" in first_arg.value or re.search(r"\bdegrees?\b", first_arg.value, re.I):
                        degree_text_calls += 1
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called_names.add(node.func.id)
            helper_name = node.func.id
            if helper_name == "Line" and any(
                isinstance(child, ast.BinOp)
                for argument in node.args[:2]
                for child in ast.walk(argument)
            ):
                raise ValueError(
                    "Không kéo Line bằng tọa độ cộng/trừ tùy ý; hãy nối trực tiếp các điểm "
                    "đã đặt tên hoặc dùng line_through_intersection."
                )
            if helper_name == "equal_segment_marks":
                equal_segment_calls.append(node)
            if helper_name == "midpoint_marker":
                midpoint_calls.append(node)
            if helper_name == "angle_bisector_segment":
                angle_bisector_calls.append(node)
            if helper_name == "perpendicular_intersection_marker":
                perpendicular_intersection_calls.append(node)
            if helper_name == "equilateral_triangle_check":
                equilateral_triangle_calls.append(node)
            if helper_name in {"equal_segment_marks", "parallel_segment_marks"}:
                valid_pairs = (
                    len(node.args) >= 2
                    and all(isinstance(arg, (ast.Tuple, ast.List)) and len(arg.elts) == 2
                            for arg in node.args)
                )
                if not valid_pairs:
                    raise ValueError(
                        f"Sai cách gọi {helper_name}: dùng {helper_name}((A, B), (C, D))."
                    )
            if helper_name == "perpendicular_intersection_marker":
                valid_perpendicular_marker = (
                    len(node.args) >= 3
                    and all(
                        isinstance(argument, (ast.Tuple, ast.List))
                        and len(argument.elts) == 2
                        for argument in node.args[:2]
                    )
                    and isinstance(node.args[2], ast.Name)
                )
                if not valid_perpendicular_marker:
                    raise ValueError(
                        "Sai cách gọi perpendicular_intersection_marker: dùng "
                        "perpendicular_intersection_marker((A, C), (B, D), O)."
                    )
            minimum_args = {
                "interior_angle_marker": 2,
                "midpoint_marker": 3,
                "median_segment": 4,
                "altitude_segment": 4,
                "angle_bisector_segment": 4,
                "perpendicular_bisector": 2,
                "perpendicular_through_point": 3,
                "perpendicular_intersection_marker": 3,
                "equilateral_triangle_check": 3,
                "opposite_ray_point": 2,
                "ray": 2,
                "infinite_line": 2,
                "line_through_intersection": 3,
                "layout_spacing_check": 2,
                "safe_point_label": 2,
                "fit_scene_to_frame": 1,
            }
            if helper_name in minimum_args and len(node.args) < minimum_args[helper_name]:
                raise ValueError(
                    f"Sai cách gọi {helper_name}: cần ít nhất {minimum_args[helper_name]} đối số."
                )
            if helper_name == "layout_spacing_check":
                numeric_keywords = {
                    keyword.arg: keyword.value.value
                    for keyword in node.keywords
                    if keyword.arg in {
                        "minimum_ratio", "minimum_distance", "maximum_aspect_ratio"
                    }
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, (int, float))
                }
                if numeric_keywords.get("minimum_ratio", 0.09) < 0.09:
                    raise ValueError("Không được giảm chuẩn khoảng cách tương đối của bố cục.")
                if numeric_keywords.get("minimum_distance", 0.65) < 0.65:
                    raise ValueError("Không được giảm khoảng cách tối thiểu giữa các điểm phụ.")
                if numeric_keywords.get("maximum_aspect_ratio", 2.0) > 2.0:
                    raise ValueError("Không được nới tỷ lệ rộng/cao tối đa của bố cục quá 2.0.")
        if isinstance(node, ast.ClassDef):
            scene_classes.append(node)
        if isinstance(node, ast.Lambda):
            raise ValueError("Mã AI không được dùng lambda.")
        if isinstance(node, ast.FunctionDef):
            functions.append(node)
            if node.name.startswith("__") or node.decorator_list:
                raise ValueError("Hàm hình học phụ không hợp lệ.")

    if len(functions) > 12:
        raise ValueError("Mã AI định nghĩa quá nhiều hàm phụ.")

    equality_groups = []
    seen_equal_segments = set()
    for call in equal_segment_calls:
        count_node = next((kw.value for kw in call.keywords if kw.arg == "count"), None)
        count_value = 1 if count_node is None else (
            count_node.value if isinstance(count_node, ast.Constant) else None
        )
        if not isinstance(count_value, int) or not 1 <= count_value <= 3:
            raise ValueError("Mỗi nhóm đoạn bằng nhau phải dùng count từ 1 đến 3.")
        segment_keys = set()
        for argument in call.args:
            if (isinstance(argument, (ast.Tuple, ast.List)) and len(argument.elts) == 2
                    and all(isinstance(point, ast.Name) for point in argument.elts)):
                segment_keys.add(tuple(sorted(point.id for point in argument.elts)))
        overlap = segment_keys & seen_equal_segments
        if overlap:
            repeated = ", ".join("".join(segment) for segment in sorted(overlap))
            raise ValueError(
                "Một đoạn không được nhận hai bộ ký hiệu bằng nhau; hãy gộp cùng một lần gọi: "
                + repeated
            )
        seen_equal_segments.update(segment_keys)
        equality_groups.append((segment_keys, count_value))
    used_counts = {}
    for segment_keys, count_value in equality_groups:
        if segment_keys and count_value in used_counts:
            raise ValueError(
                "Các nhóm đoạn bằng nhau khác nhau phải dùng số vạch khác nhau; "
                "hãy đổi count hoặc gộp nhóm nếu chúng có quan hệ bắc cầu."
            )
        if segment_keys:
            used_counts[count_value] = segment_keys

    midpoint_call_info = []
    for call in midpoint_calls:
        if not all(isinstance(argument, ast.Name) for argument in call.args[:3]):
            raise ValueError("midpoint_marker phải nhận ba tên điểm: midpoint_marker(M, A, B).")
        midpoint, start, end = (argument.id for argument in call.args[:3])
        count_node = next((kw.value for kw in call.keywords if kw.arg == "count"), None)
        count_value = 1 if count_node is None else (
            count_node.value if isinstance(count_node, ast.Constant) else None
        )
        if not isinstance(count_value, int) or not 1 <= count_value <= 3:
            raise ValueError("Ký hiệu trung điểm phải dùng count từ 1 đến 3.")
        half_segments = {
            tuple(sorted((start, midpoint))),
            tuple(sorted((midpoint, end))),
        }
        overlap = half_segments & seen_equal_segments
        if overlap:
            repeated = ", ".join("".join(segment) for segment in sorted(overlap))
            raise ValueError(
                "Không được chồng thêm ký hiệu khác lên hai nửa của một đoạn có trung điểm: "
                + repeated
            )
        seen_equal_segments.update(half_segments)
        midpoint_call_info.append({
            "midpoint": midpoint,
            "parent": tuple(sorted((start, end))),
            "halves": half_segments,
            "count": count_value,
            "other_points": {
                element.id
                for keyword in call.keywords if keyword.arg == "other_points"
                for element in (
                    keyword.value.elts
                    if isinstance(keyword.value, (ast.Tuple, ast.List)) else []
                )
                if isinstance(element, ast.Name)
            },
        })

    perpendicular_marker_keys = set()
    for call in perpendicular_intersection_calls:
        first, second, intersection = call.args[:3]
        if not all(
            isinstance(point, ast.Name)
            for segment in (first, second)
            for point in segment.elts
        ):
            raise ValueError(
                "Hai đường của perpendicular_intersection_marker phải được ghi bằng tên điểm."
            )
        first_key = tuple(sorted(point.id for point in first.elts))
        second_key = tuple(sorted(point.id for point in second.elts))
        key = (tuple(sorted((first_key, second_key))), intersection.id)
        if key in perpendicular_marker_keys:
            raise ValueError(
                "Mỗi cặp đường vuông góc tại một giao điểm chỉ được ký hiệu một góc vuông."
            )
        perpendicular_marker_keys.add(key)

    if len(scene_classes) != 1 or scene_classes[0].name != "GeoScene":
        raise ValueError("Mã AI phải có đúng một class GeoScene(Scene).")
    bases = scene_classes[0].bases
    if len(bases) != 1 or not isinstance(bases[0], ast.Name) or bases[0].id != "Scene":
        raise ValueError("GeoScene phải kế thừa trực tiếp từ Scene.")
    methods = [n for n in scene_classes[0].body if isinstance(n, ast.FunctionDef)]
    if sum(method.name == "construct" for method in methods) != 1:
        raise ValueError("GeoScene phải có đúng một phương thức construct.")

    if problem:
        request = problem.casefold()
        drawing_facts = _drawing_facts_text(problem)
        drawing_request = drawing_facts.casefold()
        point_tokens = re.findall(r"(?<![A-Z])([A-Z]{2,6})(?![A-Z])", problem)
        point_tokens += re.findall(
            r"(?:góc|điểm|tâm|tại|gọi|lấy)\s+([A-Z])\b", problem, re.I
        )
        expected_points = {letter for token in point_tokens for letter in token.upper()}

        stated_equilateral_triangles = [
            match.group(1).upper()
            for pattern in (
                r"tam\s+giác\s+đều\s+(?:\\?\(\s*)?([A-Z]{3})(?:\s*\\?\))?",
                r"equilateral\s+triangle\s+(?:\\?\(\s*)?([A-Z]{3})(?:\s*\\?\))?",
            )
            for match in re.finditer(pattern, drawing_facts, re.I)
        ]
        for vertices in stated_equilateral_triangles:
            verified = any(
                len(call.args) >= 3
                and all(isinstance(argument, ast.Name) for argument in call.args[:3])
                and tuple(argument.id for argument in call.args[:3]) == tuple(vertices)
                for call in equilateral_triangle_calls
            )
            if not verified:
                raise ValueError(
                    f"Tam giác đều {vertices} phải được dựng với ba cạnh bằng nhau và kiểm tra "
                    f"bằng equilateral_triangle_check({', '.join(vertices)})."
                )

        if perpendicular_intersection_calls:
            directly_stated_perpendicular = any(
                phrase in drawing_request
                for phrase in (
                    "vuông góc", "góc vuông", "tam giác vuông", "hình chữ nhật",
                    "hình vuông", "đường cao", "trung trực",
                )
            )
            stated_perpendicular_diagonals = (
                any(shape in drawing_request for shape in ("hình thoi", "hình vuông"))
                and "đường chéo" in drawing_request
                and ("cắt" in drawing_request or "giao" in drawing_request)
            )
            if not (directly_stated_perpendicular or stated_perpendicular_diagonals):
                raise ValueError(
                    "Không tự ký hiệu góc vuông từ kết luận cần chứng minh; chỉ vẽ ô vuông "
                    "khi quan hệ vuông góc thuộc dữ kiện của đề."
                )

        required_midpoints = []
        for match in re.finditer(
            r"\b([A-Z])\s*,\s*([A-Z])\s+lần\s+lượt\s+là\s+trung\s+điểm\s+"
            r"(?:của\s+)?([A-Z]{2})\s+và\s+([A-Z]{2})\b",
            drawing_facts,
            re.I,
        ):
            first_midpoint, second_midpoint, first_parent, second_parent = (
                value.upper() for value in match.groups()
            )
            required_midpoints.extend((
                (first_midpoint, tuple(sorted(first_parent))),
                (second_midpoint, tuple(sorted(second_parent))),
            ))
        for match in re.finditer(
            r"\b([A-Z])\s+là\s+trung\s+điểm\s+(?:của\s+)?([A-Z]{2})\b",
            drawing_facts,
            re.I,
        ):
            relation = (match.group(1).upper(), tuple(sorted(match.group(2).upper())))
            if relation not in required_midpoints:
                required_midpoints.append(relation)

        midpoint_call_by_relation = {
            (info["midpoint"], info["parent"]): info for info in midpoint_call_info
        }
        for midpoint_relation in required_midpoints:
            if midpoint_relation not in midpoint_call_by_relation:
                midpoint, parent = midpoint_relation
                raise ValueError(
                    f"{midpoint} là trung điểm của {''.join(parent)} nên phải dùng "
                    f"midpoint_marker({midpoint}, {parent[0]}, {parent[1]})."
                )
            midpoint, parent = midpoint_relation
            other_named_points = expected_points - {midpoint, *parent}
            supplied_points = midpoint_call_by_relation[midpoint_relation]["other_points"]
            if other_named_points and not other_named_points <= supplied_points:
                raise ValueError(
                    f"midpoint_marker({midpoint}, {parent[0]}, {parent[1]}) phải nhận tất cả "
                    "điểm còn lại qua other_points để tự ẩn ký hiệu dễ gây hiểu lầm."
                )

        stated_equalities = [
            (tuple(sorted(match.group(1).upper())), tuple(sorted(match.group(2).upper())))
            for match in re.finditer(
                r"\b([A-Z]{2})\s*=\s*([A-Z]{2})\b",
                drawing_facts,
                re.I,
            )
        ]
        given_equal_pairs = list(stated_equalities)
        parent_equalities = {frozenset((left, right)) for left, right in stated_equalities}
        for match in re.finditer(
            r"tam\s+giác\s+([A-Z]{3})\s+cân\s+tại\s+([A-Z])",
            drawing_facts,
            re.I,
        ):
            vertices, apex = match.group(1).upper(), match.group(2).upper()
            others = [vertex for vertex in vertices if vertex != apex]
            if len(others) == 2:
                isosceles_pair = (
                    tuple(sorted((apex, others[0]))),
                    tuple(sorted((apex, others[1]))),
                )
                parent_equalities.add(frozenset(isosceles_pair))
                given_equal_pairs.append(isosceles_pair)

        for match in re.finditer(r"hình\s+thang\s+cân\s+([A-Z]{4})", drawing_facts, re.I):
            first, second, third, fourth = match.group(1).upper()
            given_equal_pairs.append((
                tuple(sorted((first, fourth))),
                tuple(sorted((second, third))),
            ))

        required_midpoint_info = [
            midpoint_call_by_relation[relation]
            for relation in required_midpoints
            if relation in midpoint_call_by_relation
        ]
        for index, first in enumerate(required_midpoint_info):
            for second in required_midpoint_info[index + 1:]:
                parents_equal = (
                    first["parent"] == second["parent"]
                    or frozenset((first["parent"], second["parent"])) in parent_equalities
                )
                if parents_equal and first["count"] != second["count"]:
                    raise ValueError(
                        "Các trung điểm của hai đoạn bằng nhau phải dùng cùng kiểu vạch."
                    )
                if not parents_equal and first["count"] == second["count"]:
                    raise ValueError(
                        "Các nhóm trung điểm chưa được chứng minh bằng nhau phải dùng số vạch khác nhau."
                    )

        allowed_equality_components = []
        for left, right in given_equal_pairs:
            touching = [
                component for component in allowed_equality_components
                if left in component or right in component
            ]
            merged = {left, right}
            for component in touching:
                merged.update(component)
                allowed_equality_components.remove(component)
            allowed_equality_components.append(merged)
        for midpoint, parent in required_midpoints:
            halves = {
                tuple(sorted((parent[0], midpoint))),
                tuple(sorted((midpoint, parent[1]))),
            }
            allowed_equality_components.append(halves)
        for segment_keys, _count in equality_groups:
            if segment_keys and not any(
                segment_keys <= component for component in allowed_equality_components
            ):
                raise ValueError(
                    "Không tự đánh dấu cạnh bằng nhau hoặc quan hệ chỉ xuất hiện trong phần "
                    "chứng minh; chỉ đánh dấu đẳng thức được nêu trong dữ kiện."
                )
        visible_helpers = {
            "interior_angle_marker", "equal_segment_marks", "midpoint_marker",
            "median_segment", "altitude_segment", "angle_bisector_segment",
            "perpendicular_bisector", "perpendicular_through_point", "ray", "infinite_line",
            "perpendicular_intersection_marker", "line_through_intersection", "safe_point_label",
        }
        assigned_visible_helpers = {}
        added_names = set()
        added_call_ids = set()
        construct = next(method for method in methods if method.name == "construct")
        defined_points = {
            node.id for node in ast.walk(construct)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
            and len(node.id) == 1 and node.id.isupper()
        }
        defined_points.update(
            key.value.upper()
            for node in ast.walk(construct)
            if isinstance(node, ast.Dict)
            for key in node.keys
            if (isinstance(key, ast.Constant) and isinstance(key.value, str)
                and len(key.value) == 1 and key.value.isupper())
        )
        for node in ast.walk(construct):
            if not isinstance(node, (ast.Tuple, ast.List)):
                continue
            labels_in_pair = {
                element.value.upper() for element in node.elts
                if (isinstance(element, ast.Constant) and isinstance(element.value, str)
                    and len(element.value) == 1 and element.value.isupper())
            }
            if labels_in_pair and any(isinstance(element, (ast.Name, ast.Subscript))
                                      for element in node.elts):
                defined_points.update(labels_in_pair)
        literal_labels = set()
        for node in ast.walk(construct):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            value = node.value.strip()
            if re.fullmatch(r"[A-Z]{1,12}", value):
                literal_labels.update(value)
        for node in ast.walk(construct):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "safe_point_label"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
                and len(node.args[1].value) == 1
                and node.args[1].value.isupper()
            ):
                continue
            defined_points.add(node.args[1].value)
            literal_labels.add(node.args[1].value)
        has_dot = any(
            isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "Dot"
            for node in ast.walk(construct)
        )
        has_label_drawing = any(
            isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in {"Text", "safe_point_label"}
            for node in ast.walk(construct)
        )
        if has_dot and has_label_drawing and expected_points <= literal_labels:
            defined_points.update(expected_points)
        missing_points = sorted(expected_points - defined_points)
        missing_labels = sorted(expected_points - literal_labels)
        for node in ast.walk(construct):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = node.value
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                        and value.func.id in visible_helpers):
                    for target in targets:
                        if isinstance(target, ast.Name):
                            assigned_visible_helpers[id(value)] = target.id
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "self" and node.func.attr == "add"):
                for argument in node.args:
                    for child in ast.walk(argument):
                        if isinstance(child, ast.Name):
                            added_names.add(child.id)
                        if (isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
                                and child.func.id in visible_helpers):
                            added_call_ids.add(id(child))
        for node in ast.walk(construct):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in visible_helpers and id(node) not in added_call_ids):
                assigned_name = assigned_visible_helpers.get(id(node))
                if assigned_name not in added_names:
                    raise ValueError(
                        f"Kết quả {node.func.id} chưa được thêm vào hình bằng self.add(...)."
                    )
        polygon_words = ("tam giác", "tứ giác", "hình thang", "hình bình hành", "hình chữ nhật",
                         "hình thoi", "hình vuông", "hình diều", "đa giác")
        explicit_angles = {
            match.group(1).upper()
            for match in re.finditer(
                r"góc\s+([A-Z](?:[A-Z]{2})?)\s*(?:bằng|=)\s*\d+(?:[.,]\d+)?\s*(?:độ|°)?",
                problem,
                re.I,
            )
        }
        if explicit_angles and any(word in request for word in polygon_words):
            if (
                "tam giác" in request
                and len(explicit_angles) >= 2
                and "ray_intersection" not in called_names
            ):
                raise ValueError(
                    "Tam giác có từ hai góc đã biết phải dựng đỉnh bằng ray_intersection "
                    "để chọn đúng giao điểm phía trước của hai tia."
                )
            if "interior_angle_marker" not in called_names:
                raise ValueError("Góc trong đa giác phải dùng interior_angle_marker tại đúng đỉnh.")
            if direct_angle_calls:
                raise ValueError("Không dùng Angle trực tiếp cho góc đa giác; hãy dùng bộ kiểm tra góc trong.")
            if direct_arc_calls:
                raise ValueError("Không dùng Arc trực tiếp cho góc đa giác; mỗi góc chỉ dùng một interior_angle_marker.")
            if degree_text_calls:
                raise ValueError(
                    "interior_angle_marker đã có nhãn số đo; không được thêm Text số đo góc lần hai."
                )
            if explicit_angles and interior_angle_calls != len(explicit_angles):
                raise ValueError(
                    f"Mỗi góc chỉ được ký hiệu một lần: đề có {len(explicit_angles)} góc "
                    f"nhưng mã tạo {interior_angle_calls} ký hiệu."
                )
            if len(explicit_angles) > 1:
                styles_by_degrees = {}
                for call in interior_angle_nodes:
                    degrees_node = next(
                        (kw.value for kw in call.keywords if kw.arg == "degrees"),
                        call.args[2] if len(call.args) > 2 else None,
                    )
                    count_node = next(
                        (kw.value for kw in call.keywords if kw.arg == "mark_count"), None
                    )
                    if not (isinstance(degrees_node, ast.Constant)
                            and isinstance(degrees_node.value, (int, float))
                            and isinstance(count_node, ast.Constant)
                            and isinstance(count_node.value, int)):
                        raise ValueError(
                            "Khi đề có nhiều góc, mỗi ký hiệu phải ghi rõ degrees và mark_count."
                        )
                    degree_value = float(degrees_node.value)
                    count_value = count_node.value
                    previous_count = styles_by_degrees.setdefault(degree_value, count_value)
                    if previous_count != count_value:
                        raise ValueError("Các góc bằng nhau phải dùng cùng số cung ký hiệu.")
                if len(set(styles_by_degrees.values())) != len(styles_by_degrees):
                    raise ValueError("Hai góc khác nhau phải dùng số cung ký hiệu khác nhau.")
        elif ("phân giác" in request or "bisector" in request) and not explicit_angles:
            if direct_angle_calls or direct_arc_calls or "interior_angle_marker" in called_names:
                raise ValueError(
                    "Tia phân giác dùng hai cung bằng nhau từ angle_bisector_segment; "
                    "không ký hiệu thêm toàn bộ góc khi đề không cho số đo."
                )
        elif "góc" not in request and "angle" not in request:
            if direct_angle_calls or direct_arc_calls or "interior_angle_marker" in called_names:
                raise ValueError("Đề không yêu cầu góc nên không được tự thêm ký hiệu góc.")
        required_helpers = (
            (("hình thang cân", "isosceles trapezoid"),
             ("equal_segment_marks", "parallel_segment_marks")),
            (("trung điểm", "midpoint"), ("midpoint_marker",)),
            (("trung tuyến", "median"), ("median_segment",)),
            (("đường cao", "altitude"), ("altitude_segment",)),
            (("phân giác", "bisector"), ("angle_bisector_segment",)),
            (("trung trực", "perpendicular bisector"), ("perpendicular_bisector",)),
        )
        for phrases, helpers in required_helpers:
            if any(phrase in drawing_request for phrase in phrases):
                missing = [helper for helper in helpers if helper not in called_names]
                if missing:
                    raise ValueError("Thiếu phép dựng đã kiểm chứng: " + ", ".join(missing))
        if len(angle_bisector_calls) > 1:
            for call in angle_bisector_calls:
                boundary_node = next(
                    (keyword.value for keyword in call.keywords
                     if keyword.arg == "boundary_segments"),
                    None,
                )
                numbered_node = next(
                    (keyword.value for keyword in call.keywords if keyword.arg == "numbered"),
                    None,
                )
                if not isinstance(boundary_node, (ast.Tuple, ast.List)) or not boundary_node.elts:
                    raise ValueError(
                        "Bài có nhiều tia phân giác: mỗi tia phải dùng boundary_segments để "
                        "kéo dài liên tục tới cạnh của hình."
                    )
                if isinstance(numbered_node, ast.Constant) and numbered_node.value is False:
                    raise ValueError(
                        "Bài có nhiều góc con tại đỉnh nên không được tắt đánh số góc 1, 2."
                    )

        compact_intersection_points = set()
        for match in re.finditer(
            r"(?:cắt|Cắt)\s+nhau\s+tại\s+các\s+điểm\s+((?:[A-Z]\s*,\s*)+[A-Z])",
            problem,
        ):
            compact_intersection_points.update(re.findall(r"[A-Z]", match.group(1).upper()))
        for point_name in compact_intersection_points:
            label_calls = [
                node for node in ast.walk(construct)
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "safe_point_label" and len(node.args) >= 2
                    and isinstance(node.args[0], ast.Name) and node.args[0].id == point_name
                    and isinstance(node.args[1], ast.Constant)
                    and node.args[1].value == point_name)
            ]
            compact_distance = None
            if label_calls:
                compact_distance = next(
                    (keyword.value.value for keyword in label_calls[0].keywords
                     if keyword.arg == "distance"
                     and isinstance(keyword.value, ast.Constant)
                     and isinstance(keyword.value.value, (int, float))),
                    None,
                )
            if compact_distance is None or not 0.28 <= float(compact_distance) <= 0.42:
                raise ValueError(
                    f"Nhãn điểm trong {point_name} phải bám gần điểm bằng "
                    "safe_point_label(..., distance=0.32 đến 0.42)."
                )
        perpendicular_clauses = list(re.finditer(
            r"(?:qua|từ)\s+([A-Z])\b[^.]{0,100}?vuông\s+góc\s+với\s+([A-Z]{2})\b",
            drawing_facts,
            re.I,
        ))
        for relation in perpendicular_clauses:
            through = relation.group(1).upper()
            reference = relation.group(2).upper()
            clause_end = drawing_facts.find(".", relation.end())
            if clause_end < 0:
                clause_end = len(drawing_facts)
            clause = drawing_facts[relation.start():clause_end]
            named_end_match = re.search(
                r"cắt\s+(?:đường\s+thẳng\s+)?[A-Z]{2}\s+tại\s+([A-Z])\b",
                clause,
                re.I,
            )
            named_end = named_end_match.group(1).upper() if named_end_match else None
            verified = False
            for node in ast.walk(construct):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "perpendicular_through_point"
                        and len(node.args) >= 3
                        and all(isinstance(argument, ast.Name) for argument in node.args[:3])):
                    continue
                same_relation = (
                    node.args[0].id == through
                    and {node.args[1].id, node.args[2].id} == set(reference)
                )
                includes_named_end = (
                    named_end is None
                    or (len(node.args) >= 4 and isinstance(node.args[3], ast.Name)
                        and node.args[3].id == named_end)
                )
                if same_relation and includes_named_end:
                    verified = True
                    break
            if not verified:
                detail = f" và đi qua {named_end}" if named_end else ""
                raise ValueError(
                    f"Đường phụ qua {through} vuông góc với {reference}{detail} phải dùng "
                    "perpendicular_through_point để vẽ ký hiệu góc vuông riêng."
                )
        explicit_perpendiculars = re.finditer(
            r"\b([A-Z])([A-Z])\s+vuông\s+góc\s+với\s+([A-Z]{2})\s+tại\s+([A-Z])\b",
            drawing_facts,
            re.I,
        )
        for relation in explicit_perpendiculars:
            first_start, first_end, reference, intersection = (
                value.upper() for value in relation.groups()
            )
            apex = first_start if first_end == intersection else first_end
            verified = False
            for node in ast.walk(construct):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id in {"altitude_segment", "perpendicular_through_point"}
                        and len(node.args) >= 4
                        and all(isinstance(argument, ast.Name) for argument in node.args[:4])):
                    continue
                if node.func.id == "altitude_segment":
                    matches = (
                        node.args[0].id == apex
                        and node.args[1].id == intersection
                        and {node.args[2].id, node.args[3].id} == set(reference)
                    )
                else:
                    matches = (
                        node.args[0].id == apex
                        and {node.args[1].id, node.args[2].id} == set(reference)
                        and node.args[3].id == intersection
                    )
                if matches:
                    verified = True
                    break
            if not verified:
                raise ValueError(
                    f"Thiếu đường {first_start}{first_end} và ký hiệu vuông góc riêng tại "
                    f"{intersection} với {reference}."
                )
        grouped_perpendiculars = re.finditer(
            r"\b([A-Z]{2})(?:\s+và\s+([A-Z]{2}))\s+vuông\s+góc\s+với\s+([A-Z]{2})\b",
            drawing_facts,
            re.I,
        )
        for relation in grouped_perpendiculars:
            first, second, reference = (value.upper() for value in relation.groups())
            for segment in (first, second):
                apex, intersection = segment
                verified = any(
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "altitude_segment"
                    and len(node.args) >= 4
                    and all(isinstance(argument, ast.Name) for argument in node.args[:4])
                    and node.args[0].id == apex
                    and node.args[1].id == intersection
                    and {node.args[2].id, node.args[3].id} == set(reference)
                    for node in ast.walk(construct)
                )
                if not verified:
                    raise ValueError(
                        f"Thiếu đường {segment} và ký hiệu vuông góc riêng tại "
                        f"{intersection} với {reference}."
                    )
        grouped_feet = {
            segment[1]
            for relation in re.finditer(
                r"\b([A-Z]{2})(?:\s+và\s+([A-Z]{2}))\s+vuông\s+góc\s+với\s+([A-Z]{2})\b",
                drawing_facts,
                re.I,
            )
            for segment in (relation.group(1).upper(), relation.group(2).upper())
        }
        stated_equalities = [
            (tuple(sorted(match.group(1).upper())), tuple(sorted(match.group(2).upper())))
            for match in re.finditer(
                r"\b([A-Z]{2})\s*=\s*([A-Z]{2})\b",
                drawing_facts,
                re.I,
            )
        ]
        if stated_equalities:
            if "equal_segment_marks" not in called_names:
                raise ValueError("Đẳng thức hai đoạn thẳng phải có ký hiệu bằng nhau.")
        standard_shapes = ("hình bình hành", "hình chữ nhật", "hình vuông", "hình thoi")
        explicit_mark_request = any(
            phrase in drawing_request
            for phrase in (
                "đánh dấu cạnh", "đánh dấu các cạnh", "ký hiệu cạnh", "kí hiệu cạnh",
                "đánh dấu đoạn", "ký hiệu đoạn", "kí hiệu đoạn",
            )
        )
        if any(shape in drawing_request for shape in standard_shapes) and not explicit_mark_request:
            equality_components = []
            for left, right in stated_equalities:
                touching = [
                    component for component in equality_components
                    if left in component or right in component
                ]
                merged = {left, right}
                for component in touching:
                    merged.update(component)
                    equality_components.remove(component)
                equality_components.append(merged)
            for segment_keys, _count in equality_groups:
                if segment_keys and not any(
                    segment_keys <= component for component in equality_components
                ):
                    raise ValueError(
                        "Không tự đánh dấu cạnh bằng nhau của hình bình hành, hình chữ nhật, "
                        "hình vuông hoặc hình thoi khi đề không cho đẳng thức đó."
                    )
        if ("//" in drawing_request or "song song" in drawing_request
                or "parallel" in drawing_request) and "parallel_segment_marks" not in called_names:
            raise ValueError(
                "Thiếu kiểm tra quan hệ song song được nêu trực tiếp trong đề bằng "
                "parallel_segment_marks((A, B), (C, D))."
            )
        if any(phrase in request for phrase in ("tia đối", "opposite ray")):
            if "opposite_ray_point" not in called_names:
                raise ValueError("Điểm trên tia đối phải được dựng bằng opposite_ray_point.")
        paired_intersection_matches = re.findall(
            r"\b([A-Z]{2})\s+cắt\s+([A-Z]{2})\s+tại\s+([A-Z])\b",
            problem,
            re.I,
        )
        paired_intersection_matches += re.findall(
            r"\b([A-Z]{2})\s+và\s+([A-Z]{2})\s+cắt\s+nhau\s+tại\s+([A-Z])\b",
            problem,
            re.I,
        )
        paired_intersections = list(dict.fromkeys(
            (left.upper(), right.upper(), intersection.upper())
            for left, right, intersection in paired_intersection_matches
        ))
        if any(shape in drawing_request for shape in ("hình thoi", "hình vuông")):
            for left, right, intersection in paired_intersections:
                marker_key = (
                    tuple(sorted((tuple(sorted(left)), tuple(sorted(right))))),
                    intersection,
                )
                if marker_key not in perpendicular_marker_keys:
                    raise ValueError(
                        f"Hai đường chéo {left} và {right} của hình thoi hoặc hình vuông "
                        f"vuông góc tại {intersection}; chỉ vẽ đúng một ký hiệu bằng "
                        "perpendicular_intersection_marker."
                    )
        focus_intersections = {intersection for _left, _right, intersection in paired_intersections}
        required_focus = grouped_feet | focus_intersections
        if len(required_focus) >= 3:
            spacing_calls = [
                node for node in ast.walk(construct)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "layout_spacing_check"
            ]
            covers_focus = any(
                required_focus <= {
                    argument.id for argument in call.args if isinstance(argument, ast.Name)
                }
                for call in spacing_calls
            )
            if not covers_focus:
                raise ValueError(
                    "Các điểm phụ " + ", ".join(sorted(required_focus))
                    + " phải được kiểm tra độ thoáng bằng layout_spacing_check."
                )

        def carrier_is_drawn(carrier: str, intersection: str) -> bool:
            for assignment in ast.walk(construct):
                if not isinstance(assignment, ast.Assign):
                    continue
                if not (
                    isinstance(assignment.value, ast.Call)
                    and isinstance(assignment.value.func, ast.Name)
                    and assignment.value.func.id in {"Line", "line_through_intersection"}
                    and len(assignment.value.args) >= 2
                    and all(isinstance(value, ast.Name) for value in assignment.value.args[:2])
                    and {assignment.value.args[0].id, assignment.value.args[1].id} == set(carrier)
                ):
                    continue
                assigned_names = {
                    target.id for target in assignment.targets if isinstance(target, ast.Name)
                }
                if not assigned_names & added_names:
                    continue
                if assignment.value.func.id == "Line":
                    return True
                if (len(assignment.value.args) >= 3
                        and isinstance(assignment.value.args[2], ast.Name)
                        and assignment.value.args[2].id == intersection):
                    return True
            for add_call in ast.walk(construct):
                if not (
                    isinstance(add_call, ast.Call)
                    and isinstance(add_call.func, ast.Attribute)
                    and isinstance(add_call.func.value, ast.Name)
                    and add_call.func.value.id == "self"
                    and add_call.func.attr == "add"
                ):
                    continue
                for argument in add_call.args:
                    for child in ast.walk(argument):
                        if not (
                            isinstance(child, ast.Call)
                            and isinstance(child.func, ast.Name)
                            and child.func.id in {"Line", "line_through_intersection"}
                            and len(child.args) >= 2
                            and all(isinstance(value, ast.Name) for value in child.args[:2])
                            and {child.args[0].id, child.args[1].id} == set(carrier)
                        ):
                            continue
                        if child.func.id == "Line":
                            return True
                        if (len(child.args) >= 3 and isinstance(child.args[2], ast.Name)
                                and child.args[2].id == intersection):
                            return True
            return False

        for left, right, intersection in paired_intersections:
            for carrier in (left, right):
                if not carrier_is_drawn(carrier, intersection):
                    raise ValueError(
                        f"Hai đoạn {left} và {right} cắt nhau tại {intersection} nên phải vẽ "
                        f"đầy đủ đoạn {carrier} đi qua giao điểm."
                    )

        paired_right_sides = {
            (right, intersection) for _left, right, intersection in paired_intersections
        }
        intersections = re.findall(
            r"cắt\s+(?:đường\s+thẳng\s+)?([A-Z]{2})\s+tại\s+([A-Z])\b",
            problem,
            re.I,
        )
        for carrier_name, intersection_name in intersections:
            carrier = carrier_name.upper()
            intersection = intersection_name.upper()
            if (carrier, intersection) in paired_right_sides:
                continue
            has_extension = any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "line_through_intersection"
                and len(node.args) >= 3
                and all(isinstance(argument, ast.Name) for argument in node.args[:3])
                and {node.args[0].id, node.args[1].id} == set(carrier)
                and node.args[2].id == intersection
                for node in ast.walk(construct)
            )
            if not has_extension:
                raise ValueError(
                    f"Đường thẳng {carrier} phải được kéo dài tới giao điểm {intersection} "
                    "bằng line_through_intersection."
                )
        through_parallel = re.search(
            r"qua\s+([A-Z])\s*,?\s*song\s+song\s+với\s+([A-Z]{2}).*?"
            r"cắt\s+(?:đường\s+thẳng\s+)?[A-Z]{2}\s+tại\s+([A-Z])\b",
            problem,
            re.I | re.S,
        )
        if through_parallel:
            through, reference, intersection = (value.upper() for value in through_parallel.groups())
            required_segments = {
                tuple(sorted((through, intersection))),
                tuple(sorted(reference)),
            }
            verified = False
            for call in parallel_segment_calls:
                segments = {
                    tuple(sorted(point.id for point in argument.elts))
                    for argument in call.args
                    if (isinstance(argument, (ast.Tuple, ast.List))
                        and len(argument.elts) == 2
                        and all(isinstance(point, ast.Name) for point in argument.elts))
                }
                if required_segments <= segments:
                    verified = True
                    break
            if not verified:
                raise ValueError(
                    f"Phải kiểm tra trực tiếp {through}{intersection} song song với {reference} "
                    "trong cùng một lần gọi parallel_segment_marks."
                )
        if "fit_scene_to_frame" not in called_names:
            raise ValueError("Thiếu fit_scene_to_frame(self) để giữ toàn bộ hình trong khung.")
        if missing_points:
            raise ValueError(
                "Thiếu điểm được nêu trong đề: " + ", ".join(missing_points)
                + ". Hãy khai báo từng điểm bằng biến chữ hoa riêng và gắn Dot + nhãn rõ ràng."
            )
        if missing_labels:
            raise ValueError("Thiếu nhãn điểm trên hình: " + ", ".join(missing_labels))


def _explicit_parallel_relations(problem: str | None) -> list[tuple[str, str]]:
    """Return segment pairs that the givens explicitly state are parallel."""
    if not problem:
        return []
    facts = _drawing_facts_text(problem)
    patterns = (
        r"\b([A-Z]{2})\s*(?://|∥|\\parallel)\s*([A-Z]{2})\b",
        r"\b([A-Z]{2})\s+song\s+song(?:\s+với)?\s+([A-Z]{2})\b",
    )
    relations: list[tuple[str, str]] = []
    for pattern in patterns:
        for match in re.finditer(pattern, facts, re.I):
            relation = (match.group(1).upper(), match.group(2).upper())
            if relation not in relations and relation[::-1] not in relations:
                relations.append(relation)
    return relations


def _ensure_explicit_parallel_verifiers(code: str, problem: str | None) -> str:
    """Deterministically add omitted invisible checks for stated parallel sides.

    DeepSeek occasionally constructs genuinely parallel coordinates but forgets the
    required verifier call.  That omission should not consume several API retries or
    prevent an otherwise complete diagram from rendering.
    """
    relations = _explicit_parallel_relations(problem)
    if not relations:
        return code
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code
    scene_class = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "GeoScene"),
        None,
    )
    construct = next(
        (
            node for node in (scene_class.body if scene_class else [])
            if isinstance(node, ast.FunctionDef) and node.name == "construct"
        ),
        None,
    )
    if construct is None:
        return code

    defined_points = {
        target.id
        for node in ast.walk(construct)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(target, ast.Name) and re.fullmatch(r"[A-Z]", target.id)
    }

    def relation_key(left: str, right: str) -> frozenset[tuple[str, str]]:
        return frozenset((tuple(sorted(left)), tuple(sorted(right))))

    verified = set()
    for node in ast.walk(construct):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "parallel_segment_marks"
        ):
            continue
        segments = []
        for argument in node.args:
            if (
                isinstance(argument, (ast.Tuple, ast.List))
                and len(argument.elts) == 2
                and all(isinstance(point, ast.Name) for point in argument.elts)
            ):
                segments.append(tuple(sorted(point.id for point in argument.elts)))
        for index, first in enumerate(segments):
            for second in segments[index + 1:]:
                verified.add(frozenset((first, second)))

    missing = [
        (left, right) for left, right in relations
        if relation_key(left, right) not in verified
        and set(left + right) <= defined_points
    ]
    if not missing:
        return code

    fit_call = next(
        (
            node for node in ast.walk(construct)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "fit_scene_to_frame"
        ),
        None,
    )
    if fit_call is None:
        return code

    lines = code.rstrip().splitlines()
    insertion_index = fit_call.lineno - 1
    indent = re.match(r"\s*", lines[insertion_index]).group(0)
    verifier_lines = [
        f"{indent}self.add(parallel_segment_marks(({left[0]}, {left[1]}), "
        f"({right[0]}, {right[1]}), count=1))"
        for left, right in missing
    ]
    lines[insertion_index:insertion_index] = verifier_lines

    imports_helper = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "geo_draw.geometry_primitives"
        and any(alias.name in {"parallel_segment_marks", "*"} for alias in node.names)
        for node in tree.body
    )
    if not imports_helper:
        import_nodes = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
        import_index = max((node.end_lineno or node.lineno) for node in import_nodes)
        lines.insert(
            import_index,
            "from geo_draw.geometry_primitives import parallel_segment_marks",
        )
    return "\n".join(lines) + "\n"


def _ordinary_polygons(problem: str | None) -> list[str]:
    """Find original polygons described without a special type in the givens."""
    if not problem:
        return []
    facts = _drawing_facts_text(problem)
    found = []
    for kind, size in (("tam\\s+giác", 3), ("tứ\\s+giác", 4)):
        pattern = rf"\b{kind}\s+(?:\\?\(\s*)?([A-Z]{{{size}}})(?![A-Z])"
        for match in re.finditer(pattern, facts, re.I):
            names = match.group(1).upper()
            if len(set(names)) != size or names in found:
                continue
            if size == 3:
                special = (
                    rf"tam\s+giác\s+(?:cân|đều|vuông)\s+{names}\b",
                    rf"tam\s+giác\s+{names}\s+(?:là\s+)?(?:cân|đều|vuông)\b",
                )
            else:
                special = (
                    rf"(?:tứ\s+giác\s+)?{names}\s+là\s+hình\s+"
                    r"(?:thang|bình\s+hành|chữ\s+nhật|vuông|thoi|diều)\b",
                )
            if not any(re.search(special_pattern, problem, re.I) for special_pattern in special):
                found.append(names)
    return found


def _ensure_ordinary_polygon_checks(code: str, problem: str | None) -> str:
    """Insert trusted numerical checks for ordinary base polygons, not proof goals."""
    polygons = _ordinary_polygons(problem)
    if not polygons:
        return code
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code
    scene_class = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "GeoScene"),
        None,
    )
    construct = next(
        (node for node in (scene_class.body if scene_class else [])
         if isinstance(node, ast.FunctionDef) and node.name == "construct"),
        None,
    )
    if construct is None:
        return code
    defined = {
        target.id
        for node in ast.walk(construct)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(target, ast.Name) and re.fullmatch(r"[A-Z]", target.id)
    }
    fit_call = next(
        (node for node in ast.walk(construct)
         if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
         and node.func.id == "fit_scene_to_frame"),
        None,
    )
    if fit_call is None:
        return code

    facts = _drawing_facts_text(problem or "")
    equality_pairs = [
        (match.group(1).upper(), match.group(2).upper())
        for match in re.finditer(
            r"\b([A-Z]{2})\s*(?:=|bằng)\s*([A-Z]{2})\b", facts, re.I,
        )
    ]
    measured = [
        (match.group(1).upper(), float(match.group(2).replace(",", ".")))
        for match in re.finditer(
            r"\b([A-Z]{2})\s*(?:=|bằng)\s*(\d+(?:[.,]\d+)?)", facts, re.I,
        )
    ]
    for index, (first, value) in enumerate(measured):
        for second, other_value in measured[index + 1:]:
            if abs(value - other_value) < 1e-9:
                equality_pairs.append((first, second))
    right_vertices = {
        match.group(1).upper()
        for match in re.finditer(r"\bvuông\s+tại\s+([A-Z])\b", facts, re.I)
    }
    right_vertices.update(
        match.group(1).upper()
        for match in re.finditer(
            r"\bgóc\s+([A-Z])\s*(?:=|bằng)\s*90\s*(?:°|độ)?", facts, re.I,
        )
    )
    for match in re.finditer(
        r"\b([A-Z]{2})\s*(?:vuông\s+góc\s+với|⊥|\\perp)\s*([A-Z]{2})\b",
        facts, re.I,
    ):
        shared = set(match.group(1).upper()) & set(match.group(2).upper())
        if len(shared) == 1:
            right_vertices.update(shared)
    parallel_pairs = _explicit_parallel_relations(problem)
    already_checked = {
        keyword.value.value
        for node in ast.walk(construct)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "ordinary_polygon_check"
        for keyword in node.keywords
        if keyword.arg == "names" and isinstance(keyword.value, ast.Constant)
        and isinstance(keyword.value.value, str)
    }

    checks = []
    for names in polygons:
        if not set(names) <= defined or names in already_checked:
            continue
        edges = {
            "".join(sorted((names[i], names[(i + 1) % len(names)])))
            for i in range(len(names))
        }
        allowed_equals = [
            pair for pair in equality_pairs
            if all("".join(sorted(edge)) in edges for edge in pair)
        ]
        allowed_parallels = [
            pair for pair in parallel_pairs
            if all("".join(sorted(edge)) in edges for edge in pair)
        ]
        allowed_rights = tuple(name for name in names if name in right_vertices)
        vertices = ", ".join(names)
        checks.append(
            f"ordinary_polygon_check(({vertices}), names={names!r}, "
            f"allowed_equal_pairs={tuple(allowed_equals)!r}, "
            f"allowed_right_vertices={allowed_rights!r}, "
            f"allowed_parallel_pairs={tuple(allowed_parallels)!r})"
        )
    if not checks:
        return code

    lines = code.rstrip().splitlines()
    insertion_index = fit_call.lineno - 1
    indent = re.match(r"\s*", lines[insertion_index]).group(0)
    lines[insertion_index:insertion_index] = [f"{indent}{check}" for check in checks]
    imports_helper = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "geo_draw.geometry_primitives"
        and any(alias.name in {"ordinary_polygon_check", "*"} for alias in node.names)
        for node in tree.body
    )
    if not imports_helper:
        import_nodes = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
        import_index = max(node.end_lineno or node.lineno for node in import_nodes)
        lines.insert(
            import_index,
            "from geo_draw.geometry_primitives import ordinary_polygon_check",
        )
    return "\n".join(lines) + "\n"


def sanitize_code(code: str, animate: bool, problem: str | None = None) -> str:
    del animate
    code = code.strip() + "\n"
    code = _ensure_explicit_parallel_verifiers(code, problem)
    code = _ensure_ordinary_polygon_checks(code, problem)
    validate_code(code, problem=problem)
    return code


def _ensure_light_theme(code: str) -> str:
    """Inject the trusted light-theme setup into an AI module when it omitted it."""
    code = code.strip() + "\n"
    if not re.search(r"\bapply_light_theme\s*\(\s*self\s*\)", code):
        try:
            parsed = ast.parse(code)
        except SyntaxError as exc:
            raise ValueError(f"Mã AI sai cú pháp ở dòng {exc.lineno}: {exc.msg}") from exc
        import_nodes = [node for node in parsed.body if isinstance(node, (ast.Import, ast.ImportFrom))]
        if not import_nodes:
            raise ValueError("Mã AI thiếu phần import cần thiết cho giao diện hình học.")
        lines = code.splitlines()
        insertion_line = max(node.end_lineno or node.lineno for node in import_nodes)
        lines.insert(insertion_line, "from geo_draw.geometry_primitives import apply_light_theme")
        code = "\n".join(lines) + "\n"
        code, replacements = re.subn(
            r"(^\s{4}def\s+construct\s*\(\s*self\s*\)\s*:\s*$)",
            r"\1\n        apply_light_theme(self)",
            code,
            count=1,
            flags=re.M,
        )
        if replacements != 1:
            raise ValueError("Không tìm thấy construct(self) để áp dụng nền trắng, nét đen.")
    return code


def _open_chat(settings: AiSettings, payload: dict, timeout: int):
    """POST a chat completion request; HTTP and network errors become Vietnamese ValueErrors."""
    if not settings.api_key:
        raise ValueError("Chưa có API key DeepSeek. Dán key ở sidebar hoặc đặt DEEPSEEK_API_KEY.")
    request = urllib.request.Request(
        settings.base_url + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.api_key}"},
        method="POST",
    )
    try:
        return urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(detail).get("error", {}).get("message", detail)
        except json.JSONDecodeError:
            pass
        raise ValueError(f"DeepSeek trả về lỗi HTTP {exc.code}: {str(detail)[:500]}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"Không kết nối được DeepSeek: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ValueError("DeepSeek phản hồi quá thời gian chờ.") from exc


def _request_chat(
    settings: AiSettings,
    messages: list[dict],
    timeout: int = 120,
    model: str | None = None,
    max_tokens: int = 6000,
) -> str:
    payload = {"model": model or settings.model, "messages": messages, "stream": False,
               "max_tokens": max_tokens, "thinking": {"type": "disabled"}}
    try:
        with _open_chat(settings, payload, timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except TimeoutError as exc:
        raise ValueError("DeepSeek phản hồi quá thời gian chờ.") from exc
    try:
        content = body["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise TypeError
        return content
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Phản hồi DeepSeek không có nội dung mã hợp lệ.") from exc


def stream_chat(
    settings: AiSettings,
    messages: list[dict],
    timeout: int = 120,
    model: str | None = None,
    max_tokens: int = 4000,
) -> Iterator[str]:
    """Yield a chat reply piece by piece (OpenAI-style ``stream: true`` server-sent events)."""
    payload = {"model": model or settings.model, "messages": messages, "stream": True,
               "max_tokens": max_tokens, "thinking": {"type": "disabled"}}
    try:
        with _open_chat(settings, payload, timeout) as response:
            for raw in response:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue  # blank separators and ": keep-alive" comments
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    return
                try:
                    choice = json.loads(data)["choices"][0]
                except (ValueError, KeyError, IndexError, TypeError):
                    continue
                piece = (choice.get("delta") or {}).get("content")
                if piece:
                    yield piece
    except (TimeoutError, urllib.error.URLError) as exc:
        raise ValueError("Mất kết nối với DeepSeek khi đang trả lời. Hãy thử lại.") from exc


def extract_problem_from_image(
    image_bytes: bytes,
    mime_type: str,
    settings: AiSettings,
) -> str:
    """Read one Vietnamese geometry exercise image with DeepSeek Vision."""
    supported = {"image/png", "image/jpeg", "image/webp", "image/gif"}
    mime_type = (mime_type or "").casefold()
    if mime_type not in supported:
        raise ValueError("Ảnh phải có định dạng PNG, JPG, JPEG, WEBP hoặc GIF.")
    if not image_bytes:
        raise ValueError("Tệp ảnh đang trống.")
    if len(image_bytes) > 20 * 1024 * 1024:
        raise ValueError("Ảnh lớn hơn 20 MB; hãy cắt gọn vùng chứa đề bài rồi thử lại.")

    encoded = base64.b64encode(image_bytes).decode("ascii")
    messages = [{
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": (
                    "Đọc chính xác đề bài hình học trong ảnh. Chỉ trả về nguyên văn đề bài, "
                    "không giải, không nhận xét, không thêm Markdown. Giữ nguyên tên điểm, số đo, "
                    "đơn vị, ký hiệu bằng nhau, song song, vuông góc và thứ tự các ý a), b), c). "
                    "Chuẩn hóa lỗi xuống dòng nhưng không tự bổ sung dữ kiện không nhìn thấy. "
                    "Nếu đề nhắc đến một Hình đánh số và hình đó cũng hiện rõ trong ảnh, "
                    "sau nguyên văn đề bài thêm một dòng bắt đầu bằng 'Theo hình vẽ:' "
                    "mô tả vị trí các điểm, đoạn và quan hệ nhìn thấy được. "
                    "Không suy đoán quan hệ bị khuất hoặc hình không có trong ảnh."
                ),
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{encoded}",
                    "detail": "original",
                },
            },
        ],
    }]
    text = _request_chat(
        settings,
        messages,
        model=settings.vision_model,
        max_tokens=2500,
    ).strip()
    text = re.sub(r"^```(?:text)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    if len(text) < 5:
        raise ValueError("Không đọc được đề bài rõ ràng từ ảnh; hãy dùng ảnh nét và cắt sát phần đề.")
    return text


def generate_manim_code(problem: str, settings: AiSettings, animate: bool,
                        repair_log: str | None = None,
                        previous_code: str | None = None) -> AiResult:
    missing_points = missing_reference_figure_points(problem)
    if missing_points:
        return AiResult(
            code="", raw="", ok=False,
            error=(
                "Đề nhắc đến hình minh họa nhưng chưa nêu vị trí các điểm "
                + ", ".join(missing_points)
                + ". Hãy cung cấp hình vẽ đầy đủ hoặc mô tả vị trí các điểm trước khi vẽ."
            ),
        )
    mode = ("Use self.play animations and finish with self.wait(0.5)." if animate else
            "Do not use self.play. Add all mobjects with self.add(...) and finish with self.wait(0.1).")
    user = f"Animation mode: {mode}\n\nGeometry problem:\n{problem.strip()}"
    if previous_code:
        # Chat follow-ups: the problem now ends with "Yêu cầu bổ sung"; update the last drawing.
        user += ("\n\nThe current drawing was made for an earlier version of this problem. "
                 "Return a complete updated module that satisfies the whole problem above, "
                 "including every numbered 'Yêu cầu bổ sung'. Keep the existing coordinates, "
                 "labels and objects unless a request changes them. Current module:\n"
                 + previous_code[-9000:])
    if repair_log:
        user += ("\n\nA previous render failed. Return a complete corrected module for the same problem. "
                 "If GEOMETRY_LAYOUT_CROWDED or GEOMETRY_ACCIDENTAL_SPECIAL appears, "
                 "change the main figure coordinates and "
                 "recompute every dependent point; never weaken or remove the layout check. "
                 "Fix this error and improve the previous module:\n" + repair_log[-12000:])
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
    try:
        raw = _request_chat(settings, messages)
    except ValueError as exc:
        return AiResult(code="", raw="", ok=False, error=str(exc))

    first_raw = raw
    for repair_attempt in range(4):
        try:
            themed_code = _ensure_light_theme(extract_python(raw))
            code = sanitize_code(themed_code, animate=animate, problem=problem)
            return AiResult(code=code, raw=raw, ok=True)
        except ValueError as validation_error:
            if repair_attempt == 3:
                return AiResult(code="", raw=first_raw, ok=False, error=str(validation_error))
            messages.extend([
                {"role": "assistant", "content": raw[-12000:]},
                {
                    "role": "user",
                    "content": (
                        "Your module failed the app's geometry, completeness, or safety validation: "
                        f"{validation_error}. Return a full corrected module. Re-audit every clause "
                        "of the original problem and keep all earlier objects while fixing this error. "
                        "Use the exact verified-helper signatures in the system instructions. Pass each "
                        "named point as its own uppercase variable (A, B, C, ...), never only inside "
                        "a container or lowercase alias. Add an explicit Dot and safe_point_label for it. "
                        "Pass each "
                        "segment as a two-point tuple; for example "
                        "parallel_segment_marks((A, B), (C, D)) in one call. Every visible helper "
                        "result must be included in self.add(...), and fit_scene_to_frame(self) must "
                        "run after all visible objects have been added."
                    ),
                },
            ])
            try:
                raw = _request_chat(settings, messages)
            except ValueError as exc:
                return AiResult(code="", raw=first_raw, ok=False, error=str(exc))
    return AiResult(code="", raw=first_raw, ok=False, error="Không tạo được hình nguyên vẹn.")
