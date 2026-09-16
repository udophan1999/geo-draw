import unittest
from unittest.mock import patch

import numpy as np
from manim import BLACK, WHITE, Dot, Line, Scene

from geo_draw.geometry_primitives import (
    _NAMED_POINTS,
    _apply_manual_constructions,
    apply_light_theme,
    altitude_segment,
    angle_bisector_segment,
    equal_segment_marks,
    interior_angle_marker,
    line_through_intersection,
    layout_spacing_check,
    midpoint_marker,
    parallel_segment_marks,
    perpendicular_bisector,
    perpendicular_intersection_marker,
    equilateral_triangle_check,
    fit_scene_to_frame,
    perpendicular_through_point,
    polygon_signed_area,
    ray_intersection,
    safe_point_label,
)


class GeometryPrimitiveTests(unittest.TestCase):
    def _manual_triangle_scene(self):
        scene = Scene()
        apply_light_theme(scene)
        A = np.array([0.0, 3.0, 0.0])
        B = np.array([-3.0, 0.0, 0.0])
        C = np.array([4.0, 0.0, 0.0])
        scene.add(Line(A, B), Line(B, C), Line(C, A))
        scene.add(safe_point_label(A, "A"), safe_point_label(B, "B"), safe_point_label(C, "C"))
        return scene, A, B, C

    def test_manual_perpendicular_constructs_exact_foot(self):
        scene, A, B, C = self._manual_triangle_scene()
        _apply_manual_constructions(scene, {"constructions": [{
            "type": "perpendicular", "point": "A", "segment": "BC", "name": "H",
        }]}, {"AB", "AC", "BC"})
        self.assertTrue(np.allclose(_NAMED_POINTS["H"], np.array([0.0, 0.0, 0.0])))

    def test_manual_angle_bisector_is_bounded_by_figure(self):
        scene, A, B, C = self._manual_triangle_scene()
        before = len(scene.mobjects)
        _apply_manual_constructions(scene, {"constructions": [{
            "type": "angle_bisector", "side1": "AB", "side2": "AC",
        }]}, {"AB", "AC", "BC"})
        added = scene.mobjects[before:]
        self.assertEqual(len(added), 1)
        bisector_group = added[0]
        self.assertLessEqual(bisector_group[0].get_end()[1], A[1])
        self.assertGreaterEqual(bisector_group[0].get_end()[1], B[1] - 0.01)
        self.assertEqual(len(bisector_group), 3)

    def test_manual_perpendicular_bisector_marks_midpoint(self):
        scene, A, B, C = self._manual_triangle_scene()
        _apply_manual_constructions(scene, {"constructions": [{
            "type": "perpendicular_bisector", "segment": "BC", "name": "M",
        }]}, {"AB", "AC", "BC"})
        self.assertTrue(np.allclose(_NAMED_POINTS["M"], (B + C) / 2))

    def test_manual_median_uses_opposite_side_midpoint(self):
        scene, A, B, C = self._manual_triangle_scene()
        _apply_manual_constructions(scene, {"constructions": [{
            "type": "median", "point": "A", "segment": "BC", "name": "M",
        }]}, {"AB", "AC", "BC"})
        self.assertTrue(np.allclose(_NAMED_POINTS["M"], (B + C) / 2))

    def test_ray_intersection_uses_the_forward_branches(self):
        first = np.array([0.0, 0.0, 0.0])
        second = np.array([4.0, 0.0, 0.0])
        direction_first = np.array([np.cos(np.pi / 6), np.sin(np.pi / 6), 0.0])
        direction_second = np.array([np.cos(7 * np.pi / 12), np.sin(7 * np.pi / 12), 0.0])
        result = ray_intersection(first, direction_first, second, direction_second)
        self.assertGreater(result[0], 0.0)
        self.assertGreater(result[1], 0.0)

    def test_ray_intersection_rejects_a_backward_intersection(self):
        with self.assertRaisesRegex(ValueError, "phía sau gốc"):
            ray_intersection(
                np.array([0.0, 0.0, 0.0]),
                np.array([-1.0, 0.0, 0.0]),
                np.array([1.0, -1.0, 0.0]),
                np.array([0.0, 1.0, 0.0]),
            )

    def test_equilateral_triangle_check_rejects_unequal_sides(self):
        equilateral_triangle_check(
            np.array([0.0, np.sqrt(3), 0.0]),
            np.array([-1.0, 0.0, 0.0]),
            np.array([1.0, 0.0, 0.0]),
        )
        with self.assertRaisesRegex(ValueError, "ba cạnh không bằng nhau"):
            equilateral_triangle_check(
                np.array([0.0, 1.0, 0.0]),
                np.array([-1.0, 0.0, 0.0]),
                np.array([2.0, 0.0, 0.0]),
            )

    def setUp(self):
        self.a = np.array([-2.0, 1.0, 0.0])
        self.b = np.array([2.0, 1.0, 0.0])
        leg = 2.5
        self.c = self.b + leg * np.array([0.5, -np.sqrt(3) / 2, 0.0])
        self.d = self.a + leg * np.array([-0.5, -np.sqrt(3) / 2, 0.0])
        self.vertices = [self.a, self.b, self.c, self.d]

    def test_isosceles_trapezoid_angle_and_marks(self):
        self.assertLess(polygon_signed_area(self.vertices), 0)
        interior_angle_marker(self.vertices, 0, degrees=120)
        equal_segment_marks((self.a, self.d), (self.b, self.c))
        parallel_segment_marks((self.a, self.b), (self.d, self.c))

    def test_light_theme_forces_white_canvas_and_black_objects(self):
        scene = Scene()
        apply_light_theme(scene)
        dot = Dot(color=WHITE)
        scene.add(dot)
        self.assertEqual(scene.camera.background_color.to_hex(), WHITE.to_hex())
        self.assertEqual(dot.get_color().to_hex(), BLACK.to_hex())

    def test_angle_marker_supports_distinct_arc_counts(self):
        one_arc = interior_angle_marker(self.vertices, 0, degrees=120, mark_count=1)
        two_arcs = interior_angle_marker(self.vertices, 1, degrees=120, mark_count=2)
        self.assertEqual(len(one_arc[0]), 1)
        self.assertEqual(len(two_arcs[0]), 2)

    def test_rejects_marking_unequal_bases_as_equal(self):
        with self.assertRaisesRegex(ValueError, "độ dài khác nhau"):
            equal_segment_marks((self.a, self.b), (self.d, self.c))

    def test_parallel_verification_draws_no_arrow_on_segment(self):
        mark = parallel_segment_marks(Line(self.a, self.b))
        self.assertEqual(len(mark), 0)

    def test_midpoint_is_verified(self):
        midpoint_marker((self.a + self.b) / 2, self.a, self.b)
        with self.assertRaisesRegex(ValueError, "trung điểm"):
            midpoint_marker(self.a, self.a, self.b)

    def test_midpoint_ticks_are_hidden_when_named_point_splits_a_half(self):
        start = np.array([0.0, 0.0, 0.0])
        midpoint = np.array([2.0, 0.0, 0.0])
        end = np.array([4.0, 0.0, 0.0])
        blocker = np.array([3.0, 0.0, 0.0])
        visible = midpoint_marker(midpoint, start, end)
        hidden = midpoint_marker(midpoint, start, end, other_points=(blocker,))
        self.assertGreater(len(visible), 0)
        self.assertEqual(len(hidden), 0)

    def test_altitude_is_verified(self):
        altitude = altitude_segment(
            np.array([0.0, 2.0, 0.0]), np.array([0.0, 0.0, 0.0]),
            np.array([-2.0, 0.0, 0.0]), np.array([2.0, 0.0, 0.0]),
        )
        self.assertIs(type(altitude[0]), Line)
        with self.assertRaisesRegex(ValueError, "vuông góc"):
            altitude_segment(np.array([1.0, 2.0, 0.0]), np.array([0.0, 0.0, 0.0]),
                             np.array([-2.0, 0.0, 0.0]), np.array([2.0, 0.0, 0.0]))

    def test_right_angle_square_points_toward_segment_from_both_extensions(self):
        side_start = np.array([0.0, 0.0, 0.0])
        side_end = np.array([2.0, 0.0, 0.0])
        cases = (
            (np.array([-1.0, 1.0, 0.0]), np.array([-1.0, 0.0, 0.0]), side_start),
            (np.array([3.0, 1.0, 0.0]), np.array([3.0, 0.0, 0.0]), side_end),
        )
        for apex, foot, nearest_endpoint in cases:
            marker = altitude_segment(apex, foot, side_start, side_end)[1]
            offset = marker.get_center() - foot
            toward_segment = nearest_endpoint - foot
            toward_apex = apex - foot
            self.assertGreater(float(np.dot(offset[:2], toward_segment[:2])), 0.0)
            self.assertGreater(float(np.dot(offset[:2], toward_apex[:2])), 0.0)

    def test_perpendicular_bisector_is_solid_even_with_legacy_flag(self):
        bisector = perpendicular_bisector(self.a, self.b, dashed=True)
        self.assertIs(type(bisector), Line)

    def test_auxiliary_perpendicular_includes_line_and_right_angle(self):
        reference_start = np.array([0.0, 2.0, 0.0])
        reference_end = np.array([0.0, -2.0, 0.0])
        point = np.array([2.0, 1.0, 0.0])
        named_end = np.array([-1.0, 1.0, 0.0])
        construction = perpendicular_through_point(
            point, reference_start, reference_end, named_end,
        )
        self.assertEqual(len(construction), 2)
        self.assertIs(type(construction[0]), Line)
        endpoints = [construction[0].get_start(), construction[0].get_end()]
        self.assertTrue(any(np.allclose(endpoint, point) for endpoint in endpoints))
        self.assertTrue(any(np.allclose(endpoint, named_end) for endpoint in endpoints))

    def test_perpendicular_intersection_uses_one_verified_square(self):
        A = np.array([-3.0, 0.0, 0.0])
        C = np.array([3.0, 0.0, 0.0])
        B = np.array([0.0, 4.0, 0.0])
        D = np.array([0.0, -4.0, 0.0])
        O = np.zeros(3)
        marker = perpendicular_intersection_marker((A, C), (B, D), O)
        self.assertEqual(marker.__class__.__name__, "RightAngle")
        with self.assertRaisesRegex(ValueError, "không vuông góc"):
            perpendicular_intersection_marker((A, C), (A, B), O)

    def test_line_extends_through_external_intersection(self):
        start = np.array([0.0, 0.0, 0.0])
        end = np.array([2.0, 0.0, 0.0])
        intersection = np.array([5.0, 0.0, 0.0])
        extended = line_through_intersection(start, end, intersection)
        np.testing.assert_allclose(extended.get_start(), start)
        np.testing.assert_allclose(extended.get_end(), intersection)

    def test_point_label_chooses_clear_sector_between_lines(self):
        point = np.zeros(3)
        connected = (
            np.array([2.0, 0.0, 0.0]),
            np.array([2.0, 2.0, 0.0]),
            np.array([2.0, -2.0, 0.0]),
        )
        label = safe_point_label(point, "E", *connected)
        direction = label.get_center() - point
        direction = direction / np.linalg.norm(direction[:2])
        for other in connected:
            axis = other / np.linalg.norm(other[:2])
            clearance = abs(direction[0] * axis[1] - direction[1] * axis[0])
            self.assertGreater(clearance, 0.35)

    def test_point_label_avoids_nearby_non_incident_segment(self):
        point = np.zeros(3)
        label = safe_point_label(
            point,
            "H",
            np.array([-1.0, -1.0, 0.0]),
            np.array([1.0, 1.0, 0.0]),
            avoid_points=(np.array([-0.4, 0.45, 0.0]),),
            avoid_segments=((
                np.array([-2.0, 0.45, 0.0]),
                np.array([2.0, 0.45, 0.0]),
            ),),
        )
        self.assertLess(float(label.get_center()[1]), 0.0)

    def test_central_point_label_never_sits_on_crossing_lines(self):
        point = np.zeros(3)
        connected = (
            np.array([-3.0, 0.0, 0.0]),
            np.array([3.0, 0.0, 0.0]),
            np.array([0.0, 4.0, 0.0]),
            np.array([0.0, -4.0, 0.0]),
            np.array([-2.0, 2.0, 0.0]),
            np.array([2.0, 2.0, 0.0]),
        )
        label = safe_point_label(point, "M", *connected)
        offset = label.get_center() - point
        self.assertGreaterEqual(float(np.linalg.norm(offset[:2])), 0.50)
        for other in connected:
            direction = other / np.linalg.norm(other[:2])
            distance_from_line = abs(offset[0] * direction[1] - offset[1] * direction[0])
            self.assertGreater(distance_from_line, 0.12)

    def test_point_label_accepts_local_manual_offset(self):
        point = np.zeros(3)
        with patch.dict("os.environ", {"GEO_DRAW_LABEL_OFFSETS": '{"M": [0.4, -0.2]}' }):
            base = safe_point_label(point, "N")
            moved = safe_point_label(point, "M")
        np.testing.assert_allclose(
            moved.get_center() - base.get_center(),
            np.array([0.4, -0.2, 0.0]),
            atol=1e-6,
        )

    def test_manual_editor_can_hide_and_add_segments_without_moving_points(self):
        scene = Scene()
        apply_light_theme(scene)
        A = np.array([-1.0, 0.0, 0.0])
        B = np.array([1.0, 0.0, 0.0])
        C = np.array([0.0, 1.0, 0.0])
        scene.add(Line(A, B), Dot(A), Dot(B), Dot(C))
        scene.add(safe_point_label(A, "A"), safe_point_label(B, "B"), safe_point_label(C, "C"))
        edits = '{"hidden_points":["A"],"hidden_segments":["AB"],"added_segments":["AC"]}'
        with patch.dict("os.environ", {"GEO_DRAW_MANUAL_EDITS": edits}):
            fit_scene_to_frame(scene)
        direct_lines = [mobject for mobject in scene.mobjects if isinstance(mobject, Line)]
        dots = [mobject for mobject in scene.mobjects if isinstance(mobject, Dot)]
        self.assertEqual(len(direct_lines), 1)
        self.assertEqual(len(dots), 2)

    def test_layout_spacing_rejects_crowded_auxiliary_points(self):
        with self.assertRaisesRegex(ValueError, "GEOMETRY_LAYOUT_CROWDED"):
            layout_spacing_check(
                np.array([-0.2, 0.0, 0.0]),
                np.array([0.0, 0.0, 0.0]),
                np.array([0.2, 0.0, 0.0]),
                all_points=(self.a, self.b, self.c, self.d),
            )
        layout_spacing_check(
            np.array([-1.2, 0.0, 0.0]),
            np.array([0.0, 0.0, 0.0]),
            np.array([1.2, 0.0, 0.0]),
            all_points=(self.a, self.b, self.c, self.d),
            maximum_aspect_ratio=4.0,
        )

    def test_layout_spacing_rejects_excessively_wide_shape(self):
        with self.assertRaisesRegex(ValueError, "quá rộng hoặc quá cao"):
            layout_spacing_check(
                np.array([-1.0, 0.0, 0.0]),
                np.array([0.0, 0.0, 0.0]),
                np.array([1.0, 0.0, 0.0]),
                all_points=(
                    np.array([-5.0, -1.0, 0.0]),
                    np.array([5.0, -1.0, 0.0]),
                    np.array([5.0, 1.0, 0.0]),
                    np.array([-5.0, 1.0, 0.0]),
                ),
            )

    def test_angle_bisector_is_verified(self):
        origin = np.zeros(3)
        marked = angle_bisector_segment(
            origin, np.array([1.0, 1.0, 0.0]),
            np.array([2.0, 0.0, 0.0]), np.array([0.0, 2.0, 0.0]),
        )
        self.assertEqual(len(marked), 5)  # line, two matching arcs, and sub-angle numbers 1,2
        for arc in marked[1:3]:
            self.assertGreaterEqual(float(arc.get_all_points()[:, 0].min()), -1e-7)
        self.assertEqual(marked[3].text, "1")
        self.assertEqual(marked[4].text, "2")
        extended = angle_bisector_segment(
            origin, np.array([1.0, 1.0, 0.0]),
            np.array([4.0, 0.0, 0.0]), np.array([0.0, 4.0, 0.0]),
            boundary_segments=((np.array([6.0, 0.0, 0.0]),
                                np.array([0.0, 6.0, 0.0])),),
        )
        np.testing.assert_allclose(extended[0].get_end(), np.array([3.0, 3.0, 0.0]))
        with self.assertRaisesRegex(ValueError, "phân giác"):
            angle_bisector_segment(origin, np.array([2.0, 0.5, 0.0]),
                                   np.array([2.0, 0.0, 0.0]), np.array([0.0, 2.0, 0.0]))


if __name__ == "__main__":
    unittest.main()
