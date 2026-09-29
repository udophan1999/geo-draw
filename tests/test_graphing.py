import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from geo_draw.ai_codegen import AiResult, AiSettings
from geo_draw.graphing import (
    GEOMETRY, GRAPH, drawing_kind, generate_graph_code, validate_graph_code,
)
from geo_draw.pipeline import draw

GRAPH_SCENE = '''from manim import *
import numpy as np
from geo_draw.geometry_primitives import apply_light_theme, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        apply_light_theme(self)
        axes = Axes(x_range=[-1, 11, 1], y_range=[0, 110, 10], x_length=9, y_length=6,
                    tips=True, axis_config={"include_numbers": False})
        graph = axes.plot(lambda x: x ** 2 + 1, x_range=[-1, 10.3], color=BLACK)
        area = axes.get_area(graph, x_range=(1, 10), opacity=0.25)
        a = Text("1", font_size=24).next_to(axes.c2p(1, 0), DOWN)
        b = Text("10", font_size=24).next_to(axes.c2p(10, 0), DOWN)
        label = Text("y = x² + 1", font_size=28).next_to(axes.c2p(8, 70), LEFT)
        self.add(axes, area, graph, a, b, label)
        fit_scene_to_frame(self)
        self.wait(0.1)
'''

AI = AiSettings(api_key="test-key", model="deepseek-test", base_url="http://localhost:9")


class DrawingKindTests(unittest.TestCase):
    def test_integrals_and_functions_are_graphs(self):
        for text in [r"Tính $\int_1^{10} x^2+1\,dx$", "Tính tích phân ∫₁¹⁰ (x²+1) dx",
                     "Cho hàm số y = x² - 4x + 3. Vẽ đồ thị hàm số.",
                     "Cho parabol (P): y = x² và đường thẳng (d): y = 2x + 3.",
                     "Tính diện tích hình phẳng giới hạn bởi y = x² và y = x."]:
            self.assertEqual(drawing_kind(text), GRAPH, text)

    def test_geometry_stays_geometry(self):
        for text in ["Cho tam giác ABC vuông tại A, đường cao AH.",
                     "Cho góc xOy, vẽ tia phân giác Oz.",
                     "Một mảnh vườn hình chữ nhật có chu vi 40 m.",
                     "Cho đường tròn (O) và điểm M nằm ngoài đường tròn, kẻ tiếp tuyến MA."]:
            self.assertEqual(drawing_kind(text), GEOMETRY, text)

    def test_problems_without_a_figure_are_not_drawn(self):
        for text in ["Giải phương trình x² - 5x + 6 = 0", "Tính 15% của 200",
                     "Rút gọn biểu thức (a + b)² - 2ab"]:
            self.assertIsNone(drawing_kind(text), text)


class ValidateGraphCodeTests(unittest.TestCase):
    def test_accepts_a_plain_graph(self):
        validate_graph_code(GRAPH_SCENE)

    def test_rejects_latex_and_unsafe_code(self):
        cases = {
            'MathTex("x^2")': "MathTex",
            "axes.add_coordinates()": "add_coordinates",
            "axes.get_axis_labels()": "get_axis_labels",
            'Axes(axis_config={"include_numbers": True})': "include_numbers",
            "Axes(include_numbers=True)": "include_numbers",
            'open("x")': "open",
        }
        for statement, word in cases.items():
            code = GRAPH_SCENE.replace("        self.wait(0.1)", f"        {statement}")
            with self.assertRaises(ValueError, msg=statement) as caught:
                validate_graph_code(code)
            self.assertIn(word, str(caught.exception))

    def test_rejects_other_imports(self):
        with self.assertRaises(ValueError):
            validate_graph_code("import os\n" + GRAPH_SCENE)


class GenerateGraphCodeTests(unittest.TestCase):
    def test_sends_the_graph_prompt_and_retries_invalid_code(self):
        bad = GRAPH_SCENE.replace("self.wait(0.1)", 'MathTex("x")')
        with patch("geo_draw.graphing._request_chat", side_effect=[bad, GRAPH_SCENE]) as chat:
            result = generate_graph_code("Tính tích phân ∫₁¹⁰ (x²+1) dx", AI, animate=False)
        self.assertTrue(result.ok, result.error)
        self.assertEqual(chat.call_count, 2)
        first_messages = chat.call_args_list[0].args[1]
        self.assertIn("Axes", first_messages[0]["content"])
        self.assertNotIn("safe_point_label", first_messages[0]["content"])
        self.assertIn("MathTex", chat.call_args_list[1].args[1][-1]["content"])


class GraphPipelineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name) / "turn"

    def tearDown(self):
        self._tmp.cleanup()

    def test_integral_uses_the_graph_generator_and_renders(self):
        with patch("geo_draw.pipeline.generate_graph_code",
                   return_value=AiResult(code=GRAPH_SCENE, raw=GRAPH_SCENE, ok=True)) as graph, \
                patch("geo_draw.pipeline.generate_manim_code") as geometry:
            outcome = draw("Tính tích phân ∫₁¹⁰ (x²+1) dx", self.folder, ai=AI)
        self.assertTrue(outcome.ok, outcome.log[-2000:])
        self.assertTrue(outcome.image_path.exists())
        graph.assert_called_once()
        geometry.assert_not_called()

    def test_nothing_to_draw_is_refused_without_calling_the_ai(self):
        with patch("geo_draw.pipeline.generate_manim_code") as geometry, \
                patch("geo_draw.pipeline.generate_graph_code") as graph:
            outcome = draw("Giải phương trình x² - 5x + 6 = 0", self.folder, ai=AI)
        self.assertFalse(outcome.ok)
        self.assertIn("không có hình", outcome.message)
        geometry.assert_not_called()
        graph.assert_not_called()

    def test_graph_needs_the_ai(self):
        outcome = draw("Cho hàm số y = 2x + 1. Vẽ đồ thị.", self.folder, ai=None)
        self.assertFalse(outcome.ok)
        self.assertIn("DeepSeek", outcome.message)


if __name__ == "__main__":
    unittest.main()
