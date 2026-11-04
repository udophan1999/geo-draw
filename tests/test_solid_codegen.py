import unittest
from unittest.mock import patch

from geo_draw.ai_codegen import AiSettings
from geo_draw.solid_codegen import SOLID_PROMPT, generate_solid_code


SOLID_SCENE = '''from manim import *
import numpy as np
from geo_draw.geometry_primitives import apply_light_theme, fit_scene_to_frame

class GeoScene(Scene):
    def construct(self):
        apply_light_theme(self)
        A = np.array([-2.0, -1.0, 0.0])
        B = np.array([2.0, -1.0, 0.0])
        C = np.array([2.8, 0.2, 0.0])
        D = np.array([-1.2, 0.2, 0.0])
        S = np.array([0.4, 3.0, 0.0])
        self.add(Line(A, B), Line(B, C), DashedLine(C, D), DashedLine(D, A))
        self.add(Line(S, A), Line(S, B), Line(S, C), DashedLine(S, D))
        self.add(*[Dot(point) for point in (A, B, C, D, S)])
        self.add(Text("A").next_to(A, DOWN), Text("B").next_to(B, DOWN),
                 Text("C").next_to(C, RIGHT), Text("D").next_to(D, LEFT),
                 Text("S").next_to(S, UP))
        fit_scene_to_frame(self)
        self.wait(0.1)
'''


class SolidCodegenTests(unittest.TestCase):
    def test_prompt_uses_textbook_projection_and_hidden_edges(self):
        self.assertIn("2D textbook projection", SOLID_PROMPT)
        self.assertIn("gray dashed hidden edges", SOLID_PROMPT)
        self.assertIn("Do not use ThreeDScene", SOLID_PROMPT)

    @patch("geo_draw.solid_codegen._request_chat", return_value=SOLID_SCENE)
    def test_generates_a_safe_solid_projection(self, request_chat):
        result = generate_solid_code(
            "Cho hình chóp S.ABCD có đáy là hình vuông.",
            AiSettings(api_key="test-key"),
            animate=False,
        )
        self.assertTrue(result.ok, result.detail)
        self.assertIn("DashedLine", result.code)
        request_chat.assert_called_once()


if __name__ == "__main__":
    unittest.main()
