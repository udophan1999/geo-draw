import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from geo_draw.ai_codegen import AiResult, AiSettings
from geo_draw.pipeline import (
    GENERATING, RENDERING, REPAIRING, draw, render_error_summary,
)
from geo_draw.renderer import RenderResult
from geo_draw.scene_info import (
    empty_manual_edits, label_names, load_edits, save_edits, segment_names, suggest_point_name,
)

AI_SCENE = '''from manim import *
import numpy as np
from geo_draw.geometry_primitives import apply_light_theme, fit_scene_to_frame, safe_point_label

class GeoScene(Scene):
    def construct(self):
        apply_light_theme(self)
        A = np.array([0.0, 2.0, 0.0])
        B = np.array([-2.0, -1.0, 0.0])
        C = np.array([2.0, -1.0, 0.0])
        self.add(Line(A, B), Line(B, C), Dot(A))
        self.add(safe_point_label(A, "A", B, C), safe_point_label(B, "B", A, C))
        fit_scene_to_frame(self)
'''


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name) / "turn"

    def tearDown(self):
        self._tmp.cleanup()

    def test_parser_turn_renders_an_image(self):
        stages = []
        outcome = draw("Cho tam giác ABC vuông tại A, AB = 3, AC = 4.", self.folder, ai=None,
                       on_progress=lambda stage, label: stages.append(stage))
        self.assertTrue(outcome.ok, outcome.log[-500:])
        self.assertTrue(outcome.image_path.is_file())
        self.assertEqual(outcome.scene_path, self.folder / "scene.py")
        self.assertTrue(outcome.message.startswith("Đã vẽ xong · Parser"))
        self.assertEqual(stages, [RENDERING])

    def test_ai_needs_a_key(self):
        outcome = draw("Cho tam giác ABC.", self.folder, ai=AiSettings(api_key=""))
        self.assertFalse(outcome.ok)
        self.assertIn("API key", outcome.message)

    def test_ai_follow_up_passes_previous_code_then_repairs(self):
        ok = AiResult(code="class GeoScene: pass\n", raw="", ok=True)
        image = Path(self._tmp.name) / "figure.png"
        image.write_bytes(b"png")
        renders = [RenderResult(None, None, "ValueError: GEOMETRY_LAYOUT_CROWDED", False),
                   RenderResult(image, None, "ok", True)]
        stages = []
        with patch("geo_draw.pipeline.generate_manim_code", return_value=ok) as generate, \
                patch("geo_draw.pipeline.render_scene", side_effect=renders):
            outcome = draw("Cho tam giác ABC.", self.folder, ai=AiSettings(api_key="k"),
                           previous_code="OLD", on_progress=lambda s, label: stages.append(s))
        self.assertTrue(outcome.ok)
        self.assertEqual(stages, [GENERATING, RENDERING, REPAIRING])
        self.assertEqual(generate.call_args_list[0].kwargs["previous_code"], "OLD")
        self.assertIn("GEOMETRY_LAYOUT_CROWDED", generate.call_args_list[1].kwargs["repair_log"])
        self.assertEqual(outcome.message, "Đã vẽ xong · DeepSeek AI · deepseek-v4-flash")

    def test_failed_render_is_summarised(self):
        self.assertEqual(render_error_summary("x\nValueError: GEOMETRY_LAYOUT_CROWDED"),
                         "Các điểm và đối tượng phụ đang quá sát nhau; cần đổi tỷ lệ hình.")
        self.assertEqual(render_error_summary("a\nTypeError: bad\nexit"), "TypeError: bad")
        self.assertEqual(render_error_summary(""), "Không có thông tin lỗi từ Manim.")


class SceneInfoTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.scene = Path(self._tmp.name) / "scene.py"
        self.scene.write_text(AI_SCENE, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_names_come_from_the_scene_and_edits(self):
        self.assertEqual(label_names(self.scene), ["A", "B"])
        edits = {**empty_manual_edits(), "added_segments": ["CA"]}
        self.assertEqual(segment_names(self.scene, edits), ["AB", "AC", "BC"])
        self.assertEqual(label_names(self.scene.parent / "missing.py"), [])

    def test_suggested_names_skip_used_ones(self):
        edits = {**empty_manual_edits(), "constructions": [{"name": "H"}]}
        self.assertEqual(suggest_point_name(["A", "B", "M"], edits, "H"), "N")

    def test_edits_round_trip_and_default(self):
        self.assertEqual(load_edits(self.scene), ({}, empty_manual_edits()))
        edits = {**empty_manual_edits(), "hidden_labels": ["A"]}
        save_edits(self.scene, {"B": [0.1, 0.0]}, edits)
        self.assertEqual(load_edits(self.scene), ({"B": [0.1, 0.0]}, edits))


if __name__ == "__main__":
    unittest.main()
