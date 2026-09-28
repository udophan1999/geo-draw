import unittest
from unittest.mock import patch

from geo_draw.ai_codegen import (
    AiSettings,
    SYSTEM_PROMPT,
    _drawing_facts_text,
    _ensure_light_theme,
    _ordinary_polygons,
    extract_problem_from_image,
    extract_python,
    generate_manim_code,
    missing_reference_figure_points,
    sanitize_code,
    validate_code,
)
from geo_draw.geometry_knowledge import DRAWING_ERROR_MEMORY, MIDDLE_SCHOOL_GEOMETRY_RULES


SAFE_CODE = """from manim import *
import numpy as np

class GeoScene(Scene):
    def construct(self):
        a = np.array([0, 0, 0])
        self.add(Dot(a), Text("A").next_to(a, UP))
"""


class AiCodegenTests(unittest.TestCase):
    def test_multiline_proof_goals_are_not_drawing_facts(self):
        problem = (
            "Trong Hình 12, cho biết ABCD là một hình vuông. Chứng minh rằng:\n"
            "a/ Tứ giác EFGH có ba góc vuông.\n"
            "b/ HE = HG.\n"
            "c/ Tứ giác EFGH là một hình vuông."
        )
        facts = _drawing_facts_text(problem)
        self.assertIn("ABCD", facts)
        self.assertNotIn("HE = HG", facts)
        self.assertNotIn("EFGH", facts)
        self.assertEqual(missing_reference_figure_points(problem), ["E", "F", "G", "H"])
        self.assertEqual(_ordinary_polygons(problem), [])

    @patch("geo_draw.ai_codegen._request_chat")
    def test_missing_referenced_figure_stops_before_ai_generation(self, request_chat):
        problem = (
            "Trong Hình 12, cho biết ABCD là một hình vuông. "
            "Chứng minh rằng: a/ Tứ giác EFGH có ba góc vuông. b/ HE = HG."
        )
        result = generate_manim_code(problem, AiSettings(api_key="test-key"), False)
        self.assertFalse(result.ok)
        self.assertIn("E, F, G, H", result.error)
        request_chat.assert_not_called()

    def test_visible_referenced_figure_description_supplies_points(self):
        problem = (
            "Trong Hình 12, ABCD là hình vuông. Chứng minh rằng EFGH là hình vuông.\n"
            "Theo hình vẽ: E thuộc AB, F thuộc BC, G thuộc CD, H thuộc DA."
        )
        self.assertEqual(missing_reference_figure_points(problem), [])
        self.assertIn("E thuộc AB", _drawing_facts_text(problem))

    def test_proof_only_equality_marks_are_rejected_before_render(self):
        problem = (
            "Trong Hình 12, cho biết ABCD là một hình vuông. "
            "Chứng minh rằng:\na/ EFGH có ba góc vuông.\nb/ HE = HG."
        )
        code = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import equal_segment_marks

class GeoScene(Scene):
    def construct(self):
        A = np.array([0, 0, 0])
        B = np.array([3, 0, 0])
        C = np.array([3, 3, 0])
        D = np.array([0, 3, 0])
        E = np.array([1, 0, 0])
        F = np.array([3, 1, 0])
        G = np.array([1, 3, 0])
        H = np.array([0, 1, 0])
        self.add(equal_segment_marks((H, E), (H, G)))
"""
        with self.assertRaisesRegex(ValueError, "Không tự đánh dấu cạnh bằng nhau"):
            validate_code(code, problem=problem)

    def test_rejects_oversized_raw_line_with_arithmetic_endpoints(self):
        code = SAFE_CODE.replace(
            "        self.add(Dot(a), Text(\"A\").next_to(a, UP))",
            "        direction = np.array([1.0, 0.0, 0.0])\n"
            "        self.add(Line(a - 12 * direction, a + 12 * direction))",
        )
        with self.assertRaisesRegex(ValueError, "Không kéo Line"):
            validate_code(code)

    def test_conditional_hypothesis_requires_equal_segment_marks(self):
        problem = (
            "Cho hình thang ABCD (AB // CD). Chứng minh rằng nếu EC = ED "
            "thì hình thang ABCD là hình thang cân."
        )
        with self.assertRaisesRegex(ValueError, "Đẳng thức hai đoạn thẳng"):
            validate_code(SAFE_CODE, problem=problem)

    @patch("geo_draw.ai_codegen._request_chat")
    def test_extract_problem_from_image_uses_vision_model(self, request_chat):
        request_chat.return_value = "Tam giác ABC có góc A bằng 30 độ."
        settings = AiSettings(api_key="test-key")

        result = extract_problem_from_image(b"fake-png", "image/png", settings)

        self.assertEqual(result, request_chat.return_value)
        _, messages = request_chat.call_args.args
        image_part = messages[0]["content"][1]
        self.assertTrue(image_part["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertEqual(
            request_chat.call_args.kwargs["model"],
            "deepseek-v4-flash-vision-exp",
        )

    def test_extract_problem_from_image_rejects_unsupported_files(self):
        with self.assertRaisesRegex(ValueError, "định dạng"):
            extract_problem_from_image(
                b"not-an-image",
                "application/pdf",
                AiSettings(api_key="test-key"),
            )

    def test_extracts_python_fence(self):
        wrapped = f"Đây là mã:\n```python\n{SAFE_CODE}```"
        self.assertEqual(extract_python(wrapped), SAFE_CODE.strip())

    def test_accepts_safe_scene(self):
        self.assertEqual(sanitize_code(SAFE_CODE, animate=False), SAFE_CODE)

    def test_ai_scene_gets_white_background_and_black_ink_setup(self):
        themed = _ensure_light_theme(SAFE_CODE)
        self.assertIn(
            "from geo_draw.geometry_primitives import apply_light_theme",
            themed,
        )
        self.assertIn("        apply_light_theme(self)", themed)
        validate_code(themed)

    def test_rejects_direct_background_override(self):
        unsafe = SAFE_CODE.replace(
            "        a = np.array([0, 0, 0])",
            "        self.camera.background_color = '#111111'\n"
            "        a = np.array([0, 0, 0])",
        )
        with self.assertRaisesRegex(ValueError, "apply_light_theme"):
            validate_code(unsafe)

    def test_rejects_file_access(self):
        unsafe = SAFE_CODE.replace("a = np.array([0, 0, 0])", "a = open('secret.txt')")
        with self.assertRaisesRegex(ValueError, "không an toàn"):
            validate_code(unsafe)

    def test_rejects_unapproved_import(self):
        with self.assertRaisesRegex(ValueError, "import"):
            validate_code("import os\n" + SAFE_CODE)

    def test_rejects_extra_class(self):
        with self.assertRaisesRegex(ValueError, "đúng một class"):
            validate_code(SAFE_CODE + "\nclass Surprise: pass\n")

    def test_accepts_safe_geometry_helper(self):
        helper = """from manim import *
import numpy as np

def midpoint(a, b):
    return (a + b) / 2

class GeoScene(Scene):
    def construct(self):
        a = np.array([0, 0, 0])
        b = np.array([2, 0, 0])
        self.add(Dot(midpoint(a, b)))
"""
        validate_code(helper)

    def test_rejects_top_level_execution(self):
        unsafe = SAFE_CODE + "\nprint('ran at import')\n"
        with self.assertRaisesRegex(ValueError, "cấp module"):
            validate_code(unsafe)

    def test_rejects_ambiguous_angle_branch(self):
        unsafe = SAFE_CODE.replace(
            "self.add(Dot(a), Text(\"A\").next_to(a, UP))",
            "self.add(Angle(Line(a, RIGHT), Line(a, UP)))",
        )
        with self.assertRaisesRegex(ValueError, "other_angle"):
            validate_code(unsafe)

    def test_accepts_explicit_interior_angle_branch(self):
        safe = SAFE_CODE.replace(
            "self.add(Dot(a), Text(\"A\").next_to(a, UP))",
            "self.add(Angle(Line(a, RIGHT), Line(a, UP), other_angle=True))",
        )
        validate_code(safe)

    def test_rejects_raw_right_angle(self):
        unsafe = SAFE_CODE.replace(
            "self.add(Dot(a), Text(\"A\").next_to(a, UP))",
            "self.add(RightAngle(Line(a, RIGHT), Line(a, UP)))",
        )
        with self.assertRaisesRegex(ValueError, "Không tạo RightAngle trực tiếp"):
            validate_code(unsafe)

    def test_rhombus_diagonals_use_exactly_one_right_angle_marker(self):
        code = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import perpendicular_intersection_marker, safe_point_label, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([-3.0, 0.0, 0.0])
        B = np.array([0.0, 4.0, 0.0])
        C = np.array([3.0, 0.0, 0.0])
        D = np.array([0.0, -4.0, 0.0])
        O = np.array([0.0, 0.0, 0.0])
        self.add(Line(A, B), Line(B, C), Line(C, D), Line(D, A))
        self.add(Line(A, C), Line(B, D))
        self.add(perpendicular_intersection_marker((A, C), (B, D), O))
        self.add(*[Dot(point) for point in (A, B, C, D, O)])
        self.add(*[safe_point_label(point, name) for point, name in zip((A, B, C, D, O), "ABCDO")])
        fit_scene_to_frame(self)
"""
        problem = "Cho hình thoi ABCD, hai đường chéo AC và BD cắt nhau tại O."
        validate_code(code, problem=problem)

        duplicated = code.replace(
            "        self.add(perpendicular_intersection_marker((A, C), (B, D), O))",
            "        self.add(perpendicular_intersection_marker((A, C), (B, D), O))\n"
            "        self.add(perpendicular_intersection_marker((C, A), (D, B), O))",
        )
        with self.assertRaisesRegex(ValueError, "chỉ được ký hiệu một góc vuông"):
            validate_code(duplicated, problem=problem)

        missing = code.replace(
            "        self.add(perpendicular_intersection_marker((A, C), (B, D), O))\n",
            "",
        )
        with self.assertRaisesRegex(ValueError, "chỉ vẽ đúng một ký hiệu"):
            validate_code(missing, problem=problem)

    def test_middle_school_polygon_knowledge_is_in_prompt(self):
        for term in ("Isosceles trapezoid", "Parallelogram", "Rectangle", "Rhombus", "Square"):
            self.assertIn(term, MIDDLE_SCHOOL_GEOMETRY_RULES)
        self.assertIn("signed area", SYSTEM_PROMPT)
        self.assertIn("white canvas with black geometry", SYSTEM_PROMPT)
        self.assertIn(DRAWING_ERROR_MEMORY, SYSTEM_PROMPT)
        for remembered_rule in (
            "exactly one right-angle square",
            "Unequal angle measures",
            "All explicitly equal segments share one tick style",
            "Use only solid strokes",
            "Define, dot, label, and connect every named point",
        ):
            self.assertIn(remembered_rule, DRAWING_ERROR_MEMORY)

    def test_isosceles_trapezoid_requires_verified_markers(self):
        problem = "Vẽ hình thang cân ABCD, AB // CD, góc A bằng 120 độ"
        with self.assertRaisesRegex(ValueError, "[Gg]óc trong đa giác"):
            validate_code(SAFE_CODE, problem=problem)

        verified = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import interior_angle_marker, equal_segment_marks, parallel_segment_marks, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([-2, 1, 0])
        B = np.array([2, 1, 0])
        C = np.array([3, -1, 0])
        D = np.array([-3, -1, 0])
        vertices = [A, B, C, D]
        self.add(interior_angle_marker(vertices, 0, degrees=120))
        self.add(equal_segment_marks((A, D), (B, C)))
        self.add(parallel_segment_marks((A, B), (D, C)))
        self.add(*[Dot(point) for point in vertices])
        self.add(*[Text(name) for name in ("A", "B", "C", "D")])
        fit_scene_to_frame(self)
"""
        validate_code(verified, problem=problem)

    def test_triangle_with_two_angles_requires_forward_ray_intersection(self):
        code = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import apply_light_theme, interior_angle_marker, safe_point_label, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        apply_light_theme(self)
        A = np.array([-3.0, 0.0, 0.0])
        B = np.array([2.0, 2.0, 0.0])
        C = np.array([3.0, 0.0, 0.0])
        self.add(Line(A, B), Line(B, C), Line(C, A))
        self.add(Dot(A), Dot(B), Dot(C))
        self.add(safe_point_label(A, "A", B, C))
        self.add(safe_point_label(B, "B", A, C))
        self.add(safe_point_label(C, "C", A, B))
        self.add(interior_angle_marker([A, B, C], 0, degrees=30, mark_count=1))
        self.add(interior_angle_marker([A, B, C], 2, degrees=75, mark_count=2))
        fit_scene_to_frame(self)
"""
        with self.assertRaisesRegex(ValueError, "ray_intersection"):
            validate_code(
                code,
                problem="Tam giác ABC có góc A bằng 30 độ, góc C bằng 75 độ.",
            )

    def test_rejects_visible_helper_result_not_added_to_scene(self):
        missing = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import interior_angle_marker, parallel_segment_marks, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([0, 0, 0])
        B = np.array([3, 0, 0])
        C = np.array([4, 2, 0])
        D = np.array([1, 2, 0])
        interior_angle_marker([A, B, C, D], 0, degrees=45)
        parallel_segment_marks((A, B), (D, C))
        fit_scene_to_frame(self)
"""
        with self.assertRaisesRegex(ValueError, "chưa được thêm vào hình"):
            validate_code(missing, problem="Vẽ hình bình hành ABCD, góc A bằng 45 độ")

    def test_rejects_wrong_parallel_helper_signature(self):
        wrong = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import parallel_segment_marks

class GeoScene(Scene):
    def construct(self):
        A = np.array([0, 0, 0])
        B = np.array([1, 0, 0])
        line = Line(A, B)
        self.add(parallel_segment_marks(A, B, line))
"""
        with self.assertRaisesRegex(ValueError, "Sai cách gọi parallel_segment_marks"):
            validate_code(wrong)

    def test_plain_trapezoid_requires_parallel_marker(self):
        with self.assertRaisesRegex(ValueError, "parallel_segment_marks"):
            validate_code(SAFE_CODE, problem="Vẽ hình thang ABCD, AB // CD")

    def test_sanitizer_adds_omitted_explicit_parallel_verifier(self):
        missing = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import apply_light_theme, safe_point_label, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        apply_light_theme(self)
        A = np.array([-2, 1, 0])
        B = np.array([2, 1, 0])
        C = np.array([3, -1, 0])
        D = np.array([-3, -1, 0])
        self.add(Line(A, B), Line(B, C), Line(C, D), Line(D, A))
        self.add(Dot(A), Dot(B), Dot(C), Dot(D))
        self.add(safe_point_label(A, "A", B, D))
        self.add(safe_point_label(B, "B", A, C))
        self.add(safe_point_label(C, "C", B, D))
        self.add(safe_point_label(D, "D", A, C))
        fit_scene_to_frame(self)
        self.wait(0.1)
"""
        sanitized = sanitize_code(
            missing,
            animate=False,
            problem="Cho hình thang ABCD (AB // CD).",
        )
        self.assertIn(
            "parallel_segment_marks((A, B), (C, D), count=1)",
            sanitized,
        )
        self.assertIn(
            "from geo_draw.geometry_primitives import parallel_segment_marks",
            sanitized,
        )

    def test_plain_triangle_is_checked_without_restricting_auxiliary_rectangle(self):
        problem = (
            "Cho tam giác ABC có đường cao AH. Gọi I là trung điểm của AC, E là điểm đối xứng "
            "với H qua I. Gọi M, N lần lượt là trung điểm của HC, CE. Các đường thẳng AM, AN "
            "cắt HE tại G và K. Chứng minh tứ giác AHCE là hình chữ nhật."
        )
        self.assertEqual(_ordinary_polygons(problem), ["ABC"])
        code = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([0, 4, 0])
        B = np.array([-3, 0, 0])
        C = np.array([3, 0, 0])
        self.add(Line(A, B), Line(B, C), Line(C, A))
        fit_scene_to_frame(self)
"""
        sanitized = sanitize_code(code, animate=False, problem="Cho tam giác ABC.")
        self.assertIn("ordinary_polygon_check((A, B, C), names='ABC'", sanitized)
        self.assertEqual(sanitized.count("ordinary_polygon_check((A, B, C)"), 1)

    def test_explicit_special_polygon_does_not_get_ordinary_check(self):
        self.assertEqual(_ordinary_polygons("Cho tam giác cân ABC tại A."), [])
        self.assertEqual(_ordinary_polygons("Cho tam giác ABC vuông tại B."), [])
        self.assertEqual(_ordinary_polygons("Cho hình chữ nhật ABCD."), [])
        self.assertEqual(
            _ordinary_polygons("Cho tứ giác ABCD. Chứng minh tứ giác ABCD là hình chữ nhật."),
            [],
        )

    def test_rejects_unrequested_angle_markers(self):
        marked = SAFE_CODE.replace(
            "self.add(Dot(a), Text(\"A\").next_to(a, UP))",
            "self.add(Angle(Line(a, RIGHT), Line(a, UP), other_angle=False))",
        )
        with self.assertRaisesRegex(ValueError, "không yêu cầu góc"):
            validate_code(marked, problem="Vẽ hình thang ABCD, AB // CD")

    def test_rejects_duplicate_degree_text_for_verified_angle(self):
        duplicated = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import interior_angle_marker, parallel_segment_marks

class GeoScene(Scene):
    def construct(self):
        A = np.array([0, 0, 0])
        B = np.array([3, 0, 0])
        C = np.array([4, 2, 0])
        D = np.array([1, 2, 0])
        self.add(interior_angle_marker([A, B, C, D], 0, degrees=45))
        self.add(Text("45°"))
        self.add(parallel_segment_marks((A, B), (D, C)))
"""
        with self.assertRaisesRegex(ValueError, "nhãn số đo"):
            validate_code(duplicated, problem="Vẽ hình bình hành ABCD, góc A bằng 45 độ")

    def test_rejects_more_angle_markers_than_requested_angles(self):
        duplicated = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import interior_angle_marker, parallel_segment_marks

class GeoScene(Scene):
    def construct(self):
        A = np.array([0, 0, 0])
        B = np.array([3, 0, 0])
        C = np.array([4, 2, 0])
        D = np.array([1, 2, 0])
        self.add(interior_angle_marker([A, B, C, D], 0, degrees=45))
        self.add(interior_angle_marker([A, B, C, D], 0, degrees=45))
        self.add(parallel_segment_marks((A, B), (D, C)))
"""
        with self.assertRaisesRegex(ValueError, "chỉ được ký hiệu một lần"):
            validate_code(duplicated, problem="Vẽ hình bình hành ABCD, góc A bằng 45 độ")

    def test_unequal_angles_require_different_arc_counts(self):
        same_style = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import interior_angle_marker, parallel_segment_marks

class GeoScene(Scene):
    def construct(self):
        A = np.array([0, 0, 0])
        B = np.array([3, 0, 0])
        C = np.array([4, 2, 0])
        D = np.array([1, 2, 0])
        self.add(interior_angle_marker([A, B, C, D], 0, degrees=45, mark_count=1))
        self.add(interior_angle_marker([A, B, C, D], 1, degrees=135, mark_count=1))
        self.add(parallel_segment_marks((A, B), (D, C)))
"""
        with self.assertRaisesRegex(ValueError, "góc khác nhau"):
            validate_code(
                same_style,
                problem="Vẽ hình bình hành ABCD, góc A bằng 45 độ, góc B bằng 135 độ",
            )

    def test_accepts_complete_scene_with_opposite_ray_and_frame_fit(self):
        complete = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import interior_angle_marker, equal_segment_marks, parallel_segment_marks, altitude_segment, opposite_ray_point, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([-2.0, -1.0, 0.0])
        B = np.array([2.0, -1.0, 0.0])
        D = A + 2 * np.array([0.5, np.sqrt(3) / 2, 0.0])
        C = B + (D - A)
        H = np.array([D[0], A[1], 0.0])
        E = opposite_ray_point(B, C)
        self.add(Line(A, B), Line(B, C), Line(C, D), Line(D, A), Line(E, B))
        self.add(altitude_segment(D, H, A, B))
        self.add(interior_angle_marker([A, B, C, D], 0, degrees=60, mark_count=1))
        self.add(interior_angle_marker([A, B, C, D], 1, degrees=120, mark_count=2))
        self.add(equal_segment_marks((E, B), (B, C)))
        parallel_segment_marks((A, B), (D, C))
        parallel_segment_marks((A, D), (B, C))
        self.add(*[Dot(point) for point in (A, B, C, D, E, H)])
        self.add(*[Text(name) for name in ("A", "B", "C", "D", "E", "H")])
        fit_scene_to_frame(self)
"""
        validate_code(
            complete,
            problem=(
                "Vẽ hình bình hành ABCD, góc A bằng 60 độ, góc B bằng 120 độ, "
                "kẻ DH vuông góc với AB. Trên tia đối của BC lấy E sao cho EB = BC."
            ),
        )

    def test_rejects_overlapping_segment_equality_groups(self):
        overlapping = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import equal_segment_marks, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([0, 0, 0])
        B = np.array([1, 0, 0])
        C = np.array([2, 0, 0])
        D = np.array([3, 0, 0])
        self.add(equal_segment_marks((A, B), (B, C), count=1))
        self.add(equal_segment_marks((B, C), (C, D), count=2))
        self.add(*[Dot(point) for point in (A, B, C, D)])
        self.add(*[Text(name) for name in ("A", "B", "C", "D")])
        fit_scene_to_frame(self)
"""
        with self.assertRaisesRegex(ValueError, "gộp cùng một lần gọi"):
            validate_code(overlapping, problem="Cho AB = BC và BC = CD")

    def test_grouped_and_repeated_midpoint_facts_keep_correct_tick_groups(self):
        complete = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import midpoint_marker, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([0.0, 2.0, 0.0])
        B = np.array([-2.0, 0.0, 0.0])
        C = np.array([2.0, 0.0, 0.0])
        E = (A + B) / 2
        F = (A + C) / 2
        M = np.array([0.0, 0.0, 0.0])
        O = 2 * E - M
        self.add(Line(A, B), Line(A, C), Line(O, M))
        self.add(midpoint_marker(E, A, B, other_points=(C, F, M, O), count=1))
        self.add(midpoint_marker(F, A, C, other_points=(B, E, M, O), count=1))
        self.add(midpoint_marker(E, O, M, other_points=(A, B, C, F), count=2))
        self.add(*[Dot(point) for point in ()])
        self.add(*[Dot(point) for point in (A, B, C, E, F, M, O)])
        self.add(*[Text(name) for name in ("A", "B", "C", "E", "F", "M", "O")])
        fit_scene_to_frame(self)
"""
        problem = (
            "Cho tam giác ABC cân tại A. Gọi E, F lần lượt là trung điểm của AB và AC, "
            "lấy O sao cho E là trung điểm của OM."
        )
        validate_code(complete, problem=problem)

        missing_om = complete.replace(
            "        self.add(midpoint_marker(E, O, M, other_points=(A, B, C, F), count=2))\n",
            "",
        )
        with self.assertRaisesRegex(ValueError, "E là trung điểm"):
            validate_code(missing_om, problem=problem)

        mismatched_equal_parents = complete.replace(
            "midpoint_marker(F, A, C, other_points=(B, E, M, O), count=1)",
            "midpoint_marker(F, A, C, other_points=(B, E, M, O), count=3)",
        )
        with self.assertRaisesRegex(ValueError, "hai đoạn bằng nhau"):
            validate_code(mismatched_equal_parents, problem=problem)

        reused_unrelated_style = complete.replace(
            "midpoint_marker(E, O, M, other_points=(A, B, C, F), count=2)",
            "midpoint_marker(E, O, M, other_points=(A, B, C, F), count=1)",
        )
        with self.assertRaisesRegex(ValueError, "chưa được chứng minh bằng nhau"):
            validate_code(reused_unrelated_style, problem=problem)

    def test_rejects_equality_marks_overlaid_on_midpoint_halves(self):
        overlaid = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import midpoint_marker, equal_segment_marks, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([0.0, 0.0, 0.0])
        E = np.array([1.0, 0.0, 0.0])
        B = np.array([2.0, 0.0, 0.0])
        self.add(midpoint_marker(E, A, B, count=1))
        self.add(equal_segment_marks((A, E), (E, B), count=2))
        self.add(*[Dot(point) for point in (A, E, B)])
        self.add(*[Text(name) for name in ("A", "E", "B")])
        fit_scene_to_frame(self)
"""
        with self.assertRaisesRegex(ValueError, "Không được chồng thêm ký hiệu"):
            validate_code(overlaid, problem="E là trung điểm của AB.")

    def test_rejects_same_tick_count_for_distinct_equality_groups(self):
        ambiguous = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import equal_segment_marks, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([0, 0, 0])
        B = np.array([1, 0, 0])
        C = np.array([0, 2, 0])
        D = np.array([1, 2, 0])
        self.add(equal_segment_marks((A, B), (C, D), count=1))
        self.add(equal_segment_marks((A, C), (B, D), count=1))
        self.add(*[Dot(point) for point in (A, B, C, D)])
        self.add(*[Text(name) for name in ("A", "B", "C", "D")])
        fit_scene_to_frame(self)
"""
        with self.assertRaisesRegex(ValueError, "số vạch khác nhau"):
            validate_code(ambiguous, problem="Cho AB = CD và AC = BD")

    def test_rejects_numpy_cross(self):
        wrong = SAFE_CODE.replace(
            "a = np.array([0, 0, 0])",
            "a = np.cross(np.array([1, 0]), np.array([0, 1]))",
        )
        with self.assertRaisesRegex(ValueError, "np.cross"):
            validate_code(wrong)

    def test_rejects_dashed_geometry_lines(self):
        wrong = SAFE_CODE.replace(
            'self.add(Dot(a), Text("A").next_to(a, UP))',
            "self.add(DashedLine(a, RIGHT))",
        )
        with self.assertRaisesRegex(ValueError, "nét liền"):
            validate_code(wrong)

    def test_intersection_outside_segment_requires_visible_line_extension(self):
        missing_extension = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import parallel_segment_marks, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([0, 0, 0])
        B = np.array([2, 0, 0])
        C = np.array([0, 1, 0])
        D = np.array([1, 0, 0])
        E = np.array([4, 0, 0])
        self.add(Line(A, B), Line(C, E))
        parallel_segment_marks((C, E), (B, D))
        self.add(*[Dot(point) for point in (A, B, C, D, E)])
        self.add(*[Text(name) for name in ("A", "B", "C", "D", "E")])
        fit_scene_to_frame(self)
"""
        problem = "Vẽ đường thẳng đi qua C, song song với BD và cắt AB tại E."
        with self.assertRaisesRegex(ValueError, "kéo dài tới giao điểm E"):
            validate_code(missing_extension, problem=problem)

        complete = missing_extension.replace(
            "from geo_draw.geometry_primitives import parallel_segment_marks, fit_scene_to_frame",
            "from geo_draw.geometry_primitives import parallel_segment_marks, fit_scene_to_frame, line_through_intersection",
        ).replace(
            "self.add(Line(A, B), Line(C, E))",
            "self.add(line_through_intersection(A, B, E), Line(C, E))",
        )
        validate_code(complete, problem=problem)

    def test_angle_bisector_does_not_require_whole_angle_marker(self):
        bisected = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import angle_bisector_segment, equal_segment_marks, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        B = np.array([0.0, 0.0, 0.0])
        A = np.array([np.sqrt(2), np.sqrt(2), 0.0])
        C = np.array([np.sqrt(2), -np.sqrt(2), 0.0])
        D = np.array([2 * np.sqrt(2), 0.0, 0.0])
        self.add(Line(A, B), Line(B, C), Line(C, D), Line(D, A))
        self.add(angle_bisector_segment(B, D, A, C))
        self.add(equal_segment_marks((A, B), (A, D), count=1))
        self.add(*[Dot(point) for point in (A, B, C, D)])
        self.add(*[Text(name) for name in ("A", "B", "C", "D")])
        fit_scene_to_frame(self)
"""
        validate_code(
            bisected,
            problem="Cho tứ giác ABCD có AB = AD, BD là tia phân giác của góc B.",
        )

    def test_equilateral_triangle_requires_runtime_geometry_check(self):
        unchecked = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([0.0, 1.0, 0.0])
        B = np.array([-1.0, 0.0, 0.0])
        C = np.array([2.0, 0.0, 0.0])
        self.add(Line(A, B), Line(B, C), Line(C, A))
        self.add(*[Dot(point) for point in (A, B, C)])
        self.add(*[Text(name) for name in ("A", "B", "C")])
        fit_scene_to_frame(self)
"""
        problem = r"Cho M nằm trong tam giác đều \(ABC\)."
        with self.assertRaisesRegex(ValueError, "Tam giác đều ABC"):
            validate_code(unchecked, problem=problem)

        checked = unchecked.replace(
            "from geo_draw.geometry_primitives import fit_scene_to_frame",
            "from geo_draw.geometry_primitives import equilateral_triangle_check, fit_scene_to_frame",
        ).replace(
            "        self.add(Line(A, B), Line(B, C), Line(C, A))",
            "        equilateral_triangle_check(A, B, C)\n"
            "        self.add(Line(A, B), Line(B, C), Line(C, A))",
        )
        validate_code(checked, problem=problem)

    def test_multiple_bisectors_reach_boundary_and_use_compact_intersection_labels(self):
        complete = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import angle_bisector_segment, safe_point_label, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([-2.0, 1.0, 0.0])
        B = np.array([2.0, 1.0, 0.0])
        C = np.array([2.5, -1.0, 0.0])
        D = np.array([-1.5, -1.0, 0.0])
        E = np.array([0.0, 0.0, 0.0])
        F = np.array([0.5, 0.0, 0.0])
        self.add(Line(A, B), Line(B, C), Line(C, D), Line(D, A))
        self.add(angle_bisector_segment(A, E, B, D, boundary_segments=((B, C), (C, D))))
        self.add(angle_bisector_segment(B, F, A, C, boundary_segments=((C, D), (D, A))))
        self.add(*[Dot(point) for point in (A, B, C, D, E, F)])
        self.add(*[Text(name) for name in ("A", "B", "C", "D")])
        self.add(safe_point_label(E, "E", A, B, distance=0.35))
        self.add(safe_point_label(F, "F", B, C, distance=0.35))
        fit_scene_to_frame(self)
"""
        problem = "Cho tứ giác ABCD. Các tia phân giác cắt nhau tại các điểm E, F."
        validate_code(complete, problem=problem)

        short_ray = complete.replace(
            ", boundary_segments=((B, C), (C, D))", "", 1,
        )
        with self.assertRaisesRegex(ValueError, "kéo dài liên tục"):
            validate_code(short_ray, problem=problem)

        far_label = complete.replace(
            'safe_point_label(E, "E", A, B, distance=0.35)',
            'safe_point_label(E, "E", A, B, distance=0.60)',
        )
        with self.assertRaisesRegex(ValueError, "Nhãn điểm trong E"):
            validate_code(far_label, problem=problem)

        unnumbered = complete.replace(
            "boundary_segments=((B, C), (C, D))",
            "boundary_segments=((B, C), (C, D)), numbered=False",
            1,
        )
        with self.assertRaisesRegex(ValueError, "không được tắt đánh số"):
            validate_code(unnumbered, problem=problem)

    def test_each_auxiliary_perpendicular_requires_its_own_marker(self):
        missing_marker = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import line_through_intersection, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([0.0, 2.0, 0.0])
        H = np.array([0.0, -2.0, 0.0])
        M = np.array([2.0, 1.0, 0.0])
        B = np.array([-1.0, 1.0, 0.0])
        N = np.array([-1.0, 1.0, 0.0])
        self.add(line_through_intersection(A, B, N))
        self.add(Line(M, N))
        self.add(*[Dot(point) for point in (A, B, H, M, N)])
        self.add(*[Text(name) for name in ("A", "B", "H", "M", "N")])
        fit_scene_to_frame(self)
"""
        problem = "Từ M kẻ đường thẳng vuông góc với AH và cắt AB tại N."
        with self.assertRaisesRegex(ValueError, "ký hiệu góc vuông riêng"):
            validate_code(missing_marker, problem=problem)

        complete = missing_marker.replace(
            "from geo_draw.geometry_primitives import line_through_intersection, fit_scene_to_frame",
            "from geo_draw.geometry_primitives import line_through_intersection, perpendicular_through_point, fit_scene_to_frame",
        ).replace(
            "self.add(Line(M, N))",
            "self.add(perpendicular_through_point(M, A, H, N))",
        )
        validate_code(complete, problem=problem)

    def test_point_dictionary_is_a_valid_point_definition(self):
        mapped = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import safe_point_label, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        points = {
            "A": np.array([0.0, 1.0, 0.0]),
            "B": np.array([-1.0, 0.0, 0.0]),
            "C": np.array([0.0, -1.0, 0.0]),
            "D": np.array([1.0, 0.0, 0.0]),
        }
        self.add(Line(points["A"], points["B"]), Line(points["B"], points["C"]))
        self.add(Line(points["C"], points["D"]), Line(points["D"], points["A"]))
        self.add(Dot(points["A"]), safe_point_label(points["A"], "A", points["B"], points["D"]))
        self.add(Dot(points["B"]), safe_point_label(points["B"], "B", points["A"], points["C"]))
        self.add(Dot(points["C"]), safe_point_label(points["C"], "C", points["B"], points["D"]))
        self.add(Dot(points["D"]), safe_point_label(points["D"], "D", points["A"], points["C"]))
        fit_scene_to_frame(self)
"""
        validate_code(mapped, problem="Cho tứ giác ABCD.")

    def test_containerized_points_with_compact_label_string_are_recognized(self):
        containerized = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        points = np.array([
            [-1.0, 1.0, 0.0], [1.0, 1.0, 0.0],
            [1.0, -1.0, 0.0], [-1.0, -1.0, 0.0],
        ])
        labels = "ABCD"
        self.add(Line(points[0], points[1]), Line(points[1], points[2]))
        self.add(Line(points[2], points[3]), Line(points[3], points[0]))
        for point, label in zip(points, labels):
            self.add(Dot(point), Text(label).next_to(point, UP))
        fit_scene_to_frame(self)
"""
        validate_code(containerized, problem="Cho tứ giác ABCD.")

    def test_multiple_explicit_perpendiculars_need_separate_markers(self):
        one_marker = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import altitude_segment, layout_spacing_check, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([-2.0, 2.0, 0.0])
        B = np.array([-3.0, 0.0, 0.0])
        C = np.array([2.0, 2.0, 0.0])
        D = np.array([3.0, 0.0, 0.0])
        H = np.array([-1.0, 0.0, 0.0])
        K = np.array([1.0, 0.0, 0.0])
        self.add(altitude_segment(A, H, B, D))
        self.add(*[Dot(point) for point in (A, B, C, D, H, K)])
        self.add(*[Text(name) for name in ("A", "B", "C", "D", "H", "K")])
        fit_scene_to_frame(self)
"""
        problem = "Kẻ AH vuông góc với BD tại H và CK vuông góc với BD tại K."
        with self.assertRaisesRegex(ValueError, "Thiếu đường CK"):
            validate_code(one_marker, problem=problem)

        complete = one_marker.replace(
            "self.add(altitude_segment(A, H, B, D))",
            "self.add(altitude_segment(A, H, B, D))\n        self.add(altitude_segment(C, K, B, D))",
        )
        validate_code(complete, problem=problem)

    def test_default_parallelogram_rejects_unrequested_equal_side_marks(self):
        over_marked = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import equal_segment_marks, parallel_segment_marks, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([-2.0, 1.0, 0.0])
        B = np.array([2.0, 1.0, 0.0])
        C = np.array([3.0, -1.0, 0.0])
        D = np.array([-1.0, -1.0, 0.0])
        self.add(Line(A, B), Line(B, C), Line(C, D), Line(D, A))
        self.add(equal_segment_marks((A, B), (C, D), count=1))
        self.add(parallel_segment_marks((A, B), (C, D), count=1))
        self.add(parallel_segment_marks((A, D), (B, C), count=2))
        self.add(*[Dot(point) for point in (A, B, C, D)])
        self.add(*[Text(name) for name in ("A", "B", "C", "D")])
        fit_scene_to_frame(self)
"""
        with self.assertRaisesRegex(ValueError, "Không tự đánh dấu cạnh bằng nhau"):
            validate_code(over_marked, problem="Cho hình bình hành ABCD.")

    def test_proof_conclusion_is_not_treated_as_given_equality(self):
        complete = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import altitude_segment, midpoint_marker, parallel_segment_marks, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([-2.0, 2.0, 0.0])
        B = np.array([-3.0, 0.0, 0.0])
        C = np.array([2.0, 2.0, 0.0])
        D = np.array([3.0, 0.0, 0.0])
        H = np.array([-1.0, 0.0, 0.0])
        K = np.array([1.0, 0.0, 0.0])
        I = (H + K) / 2
        self.add(Line(A, B), Line(B, C), Line(C, D), Line(D, A), Line(B, D))
        self.add(Line(I, B), Line(I, D))
        self.add(altitude_segment(A, H, B, D))
        self.add(altitude_segment(C, K, B, D))
        self.add(midpoint_marker(I, H, K, other_points=(A, B, C, D)))
        self.add(parallel_segment_marks((A, B), (C, D), count=1))
        self.add(parallel_segment_marks((A, D), (B, C), count=2))
        self.add(*[Dot(point) for point in (A, B, C, D, H, I, K)])
        self.add(*[Text(name) for name in ("A", "B", "C", "D", "H", "I", "K")])
        fit_scene_to_frame(self)
"""
        validate_code(
            complete,
            problem=(
                "Cho hình bình hành ABCD, kẻ AH vuông góc với BD tại H và CK vuông góc "
                "với BD tại K. Gọi I là trung điểm của HK. Chứng minh IB = ID."
            ),
        )

    def test_proof_conclusion_is_not_treated_as_given_right_angle(self):
        over_marked = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import perpendicular_intersection_marker, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([-2.0, 1.0, 0.0])
        B = np.array([2.0, 1.0, 0.0])
        C = np.array([2.5, -1.0, 0.0])
        D = np.array([-1.5, -1.0, 0.0])
        E = np.array([-0.5, 0.3, 0.0])
        F = np.array([0.5, 0.3, 0.0])
        G = np.array([0.5, -0.3, 0.0])
        H = np.array([-0.5, -0.3, 0.0])
        self.add(Line(A, B), Line(B, C), Line(C, D), Line(D, A))
        self.add(Line(E, F), Line(F, G), Line(G, H), Line(H, E))
        self.add(perpendicular_intersection_marker((E, F), (F, G), F))
        self.add(*[Dot(point) for point in (A, B, C, D, E, F, G, H)])
        self.add(*[Text(name) for name in ("A", "B", "C", "D", "E", "F", "G", "H")])
        fit_scene_to_frame(self)
"""
        with self.assertRaisesRegex(ValueError, "Không tự ký hiệu góc vuông"):
            validate_code(
                over_marked,
                problem=(
                    "Cho hình bình hành ABCD. Các tia phân giác cắt nhau tại E, F, G, H. "
                    "Chứng minh rằng EFGH là một hình chữ nhật."
                ),
            )

    def test_parallelogram_name_does_not_require_invisible_parallel_verifier(self):
        code = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([-2.0, 1.0, 0.0])
        B = np.array([2.0, 1.0, 0.0])
        D = np.array([-1.0, -1.0, 0.0])
        C = B + D - A
        self.add(Line(A, B), Line(B, C), Line(C, D), Line(D, A))
        self.add(*[Dot(point) for point in (A, B, C, D)])
        self.add(*[Text(name) for name in ("A", "B", "C", "D")])
        fit_scene_to_frame(self)
"""
        validate_code(code, problem="Cho hình bình hành ABCD.")

    def test_grouped_perpendiculars_need_two_right_angle_markers(self):
        complete = """from manim import *
import numpy as np
from geo_draw.geometry_primitives import altitude_segment, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        A = np.array([-2.0, 1.0, 0.0])
        B = np.array([2.0, 1.0, 0.0])
        D = np.array([-1.0, -1.0, 0.0])
        C = B + D - A
        E = np.array([0.0, 0.0, 0.0])
        F = np.array([1.0, 0.0, 0.0])
        I = np.array([0.5, 0.0, 0.0])
        self.add(Line(A, B), Line(B, C), Line(C, D), Line(D, A), Line(A, C))
        self.add(Line(B, D))
        self.add(altitude_segment(A, E, B, D))
        self.add(altitude_segment(C, F, B, D))
        layout_spacing_check(E, I, F, all_points=(A, B, C, D))
        self.add(*[Dot(point) for point in (A, B, C, D, E, F, I)])
        self.add(*[Text(name) for name in ("A", "B", "C", "D", "E", "F", "I")])
        fit_scene_to_frame(self)
"""
        problem = (
            "Cho hình bình hành ABCD, kẻ AE và CF vuông góc với BD, AC cắt BD tại I. "
            "a) Chứng minh I là trung điểm EF. b) Chứng minh AFCE là hình bình hành."
        )
        validate_code(complete, problem=problem)
        assigned_diagonals = complete.replace(
            "        self.add(Line(A, B), Line(B, C), Line(C, D), Line(D, A), Line(A, C))\n"
            "        self.add(Line(B, D))",
            "        AC = Line(A, C)\n"
            "        BD = Line(B, D)\n"
            "        self.add(Line(A, B), Line(B, C), Line(C, D), Line(D, A), AC, BD)",
        )
        validate_code(assigned_diagonals, problem=problem)
        missing_cf = complete.replace(
            "        self.add(altitude_segment(C, F, B, D))\n",
            "",
        )
        with self.assertRaisesRegex(ValueError, "Thiếu đường CF"):
            validate_code(missing_cf, problem=problem)

        missing_ac = complete.replace(", Line(A, C)", "")
        with self.assertRaisesRegex(ValueError, "đầy đủ đoạn AC"):
            validate_code(missing_ac, problem=problem)

        missing_spacing = complete.replace(
            "        layout_spacing_check(E, I, F, all_points=(A, B, C, D))\n",
            "",
        )
        with self.assertRaisesRegex(ValueError, "kiểm tra độ thoáng"):
            validate_code(missing_spacing, problem=problem)


if __name__ == "__main__":
    unittest.main()
