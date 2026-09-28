"""Verified Manim primitives for Vietnamese middle-school plane geometry."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence

import numpy as np
from manim import Angle, BLACK, Dot, Line, ORIGIN, RightAngle, Text, VGroup, WHITE, config


EPS = 1e-7
_NAMED_POINTS: dict[str, np.ndarray] = {}


def _manual_edits() -> dict:
    try:
        value = json.loads(os.environ.get("GEO_DRAW_MANUAL_EDITS", "{}"))
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def apply_light_theme(scene):
    """Use a white canvas and make every subsequently added object black."""
    scene.camera.background_color = WHITE
    _NAMED_POINTS.clear()
    original_add = scene.add

    def add_with_black_ink(*mobjects):
        for mobject in mobjects:
            mobject.set_color(BLACK)
        return original_add(*mobjects)

    scene.add = add_with_black_ink
    return scene


def _point(value) -> np.ndarray:
    point = np.asarray(value, dtype=float)
    if point.shape == (2,):
        point = np.append(point, 0.0)
    if point.shape != (3,):
        raise ValueError("Điểm phải có hai hoặc ba tọa độ.")
    return point


def _unit(vector) -> np.ndarray:
    vector = _point(vector)
    length = np.linalg.norm(vector[:2])
    if length < EPS:
        raise ValueError("Không thể dựng từ hai điểm trùng nhau.")
    return vector / length


def _cross2(first, second) -> float:
    return float(first[0] * second[1] - first[1] * second[0])


def ray_intersection(
    first,
    first_direction,
    second,
    second_direction,
    require_forward: bool = True,
    tolerance: float = 1e-7,
) -> np.ndarray:
    """Return the intersection of two directed rays with sign-safe 2D math."""
    first = _point(first)
    second = _point(second)
    first_direction = _unit(first_direction)
    second_direction = _unit(second_direction)
    determinant = _cross2(first_direction, second_direction)
    if abs(determinant) <= tolerance:
        raise ValueError("Hai tia song song hoặc trùng nhau nên không có giao điểm duy nhất.")

    delta = second - first
    first_parameter = _cross2(delta, second_direction) / determinant
    second_parameter = _cross2(delta, first_direction) / determinant
    if require_forward and (
        first_parameter < -tolerance or second_parameter < -tolerance
    ):
        raise ValueError(
            "Giao điểm nằm phía sau gốc của ít nhất một tia; hãy kiểm tra lại hướng tia."
        )
    return first + first_parameter * first_direction


def _segment(value) -> tuple[np.ndarray, np.ndarray]:
    """Accept a point pair or a Manim Line-like object."""
    if hasattr(value, "get_start") and hasattr(value, "get_end"):
        return _point(value.get_start()), _point(value.get_end())
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return _point(value[0]), _point(value[1])
    raise ValueError("GEOMETRY_INVALID_SEGMENT: expected (start, end) or a Manim Line")


def _angle_degrees(first, second) -> float:
    cosine = float(np.clip(np.dot(_unit(first)[:2], _unit(second)[:2]), -1.0, 1.0))
    return float(np.degrees(np.arccos(cosine)))


def _assert_close(actual: float, expected: float, tolerance: float, message: str) -> None:
    if abs(actual - expected) > tolerance:
        raise ValueError(f"{message}: nhận được {actual:.2f}, cần {expected:.2f}.")


def polygon_signed_area(vertices: Sequence) -> float:
    points = [_point(value) for value in vertices]
    if len(points) < 3:
        raise ValueError("Đa giác phải có ít nhất ba đỉnh.")
    area2 = sum(_cross2(points[i], points[(i + 1) % len(points)]) for i in range(len(points)))
    if abs(area2) < EPS:
        raise ValueError("Đa giác bị suy biến hoặc các đỉnh không theo thứ tự biên.")
    return area2 / 2


def interior_angle_marker(
    vertices: Sequence,
    vertex_index: int,
    degrees: float | None = None,
    radius: float = 0.48,
    mark_count: int = 1,
    color=BLACK,
    font_size: int = 26,
    tolerance: float = 0.75,
):
    """Return distinct concentric interior arcs and one optional degree label."""
    points = [_point(value) for value in vertices]
    count = len(points)
    vertex_index %= count
    previous = points[(vertex_index - 1) % count]
    vertex = points[vertex_index]
    following = points[(vertex_index + 1) % count]
    area = polygon_signed_area(points)
    before = previous - vertex
    after = following - vertex
    small_angle = _angle_degrees(before, after)
    convex = _cross2(before, after) * area < 0
    actual_angle = small_angle if convex else 360.0 - small_angle
    if degrees is not None:
        _assert_close(actual_angle, float(degrees), tolerance, "Số đo góc trong không đúng")

    if not isinstance(mark_count, int) or not 1 <= mark_count <= 3:
        raise ValueError("Số cung ký hiệu góc phải từ 1 đến 3.")
    arcs = VGroup(*(
        Angle(
            Line(vertex, previous),
            Line(vertex, following),
            radius=radius + index * 0.10,
            color=color,
            other_angle=(area > 0),
        )
        for index in range(mark_count)
    ))
    if degrees is None:
        return arcs

    bisector = _unit(before) + _unit(after)
    if np.linalg.norm(bisector[:2]) < EPS:
        bisector = np.array([-before[1], before[0], 0.0])
    bisector = _unit(bisector)
    if not convex:
        bisector = -bisector
    label = Text(f"{float(degrees):g}°", font_size=font_size, color=color)
    label.move_to(vertex + (radius + (mark_count - 1) * 0.10 + 0.34) * bisector)
    return VGroup(arcs, label)


def equal_segment_marks(*segments, count: int = 1, size: float = 0.18, color=BLACK,
                        tolerance: float = 0.01):
    """Mark segments as equal, rejecting a geometrically false equality."""
    if len(segments) < 2:
        raise ValueError("Cần ít nhất hai đoạn thẳng để đánh dấu bằng nhau.")
    normalized = [_segment(segment) for segment in segments]
    lengths = [float(np.linalg.norm(end - start)) for start, end in normalized]
    scale = max(max(lengths), 1.0)
    if max(lengths) - min(lengths) > tolerance * scale:
        raise ValueError("Không thể đặt cùng ký hiệu lên các đoạn có độ dài khác nhau.")
    marks = VGroup()
    for start, end in normalized:
        direction = _unit(end - start)
        normal = np.array([-direction[1], direction[0], 0.0])
        middle = (start + end) / 2
        for offset_index in range(count):
            offset = (offset_index - (count - 1) / 2) * size * 0.8
            center = middle + offset * direction
            marks.add(Line(center - size * normal / 2, center + size * normal / 2, color=color))
    return marks


def parallel_segment_marks(*segments, count: int = 1, size: float = 0.22, color=BLACK,
                           tolerance: float = 0.01):
    """Verify that segments are parallel without drawing arrows on them.

    In this application an arrowhead is reserved for a ray/vector.  A finite
    segment must therefore remain a plain line, even when its parallel
    relationship is part of the problem.
    """
    if not segments:
        raise ValueError("GEOMETRY_PARALLEL_NO_SEGMENT")
    # One Line is accepted for compatibility with older generated scenes. New
    # scenes are statically required to pass all related segments in one call.
    normalized = [_segment(segment) for segment in segments]
    directions = [_unit(end - start) for start, end in normalized]
    if any(abs(_cross2(directions[0], direction)) > tolerance for direction in directions[1:]):
        raise ValueError("Không thể đặt ký hiệu song song lên các đoạn không song song.")
    # Keep the legacy style arguments for API compatibility.  The returned
    # empty group can safely be passed to self.add while the relation has still
    # been checked numerically above.
    del count, size, color
    return VGroup()


def equilateral_triangle_check(first, second, third, tolerance: float = 0.01):
    """Verify that three named vertices form a non-degenerate equilateral triangle."""
    first, second, third = _point(first), _point(second), _point(third)
    lengths = [
        float(np.linalg.norm(second - first)),
        float(np.linalg.norm(third - second)),
        float(np.linalg.norm(first - third)),
    ]
    scale = max(lengths)
    if scale < EPS or abs(_cross2(second - first, third - first)) < EPS * scale * scale:
        raise ValueError("Tam giác đều bị suy biến.")
    if max(lengths) - min(lengths) > tolerance * scale:
        raise ValueError(
            "Tam giác được nêu là tam giác đều nhưng ba cạnh không bằng nhau."
        )
    return True


def ordinary_polygon_check(vertices, names: str, allowed_equal_pairs=(),
                           allowed_right_vertices=(), allowed_parallel_pairs=(),
                           side_gap: float = 0.06, right_gap_degrees: float = 7.0,
                           parallel_sine_gap: float = 0.08):
    """Reject an unstated special case in a named ordinary triangle/quadrilateral.

    This checks only the original polygon, not auxiliary polygons that the
    exercise asks the student to prove special. Explicitly stated relations can
    be exempted without weakening checks on unrelated sides or vertices.
    """
    points = [_point(vertex) for vertex in vertices]
    if len(points) not in (3, 4) or len(names) != len(points):
        raise ValueError("ordinary_polygon_check cần ba hoặc bốn đỉnh có tên.")
    if len(set(names)) != len(names):
        raise ValueError("Các đỉnh của đa giác phải khác nhau.")

    n = len(points)
    sides = [points[(i + 1) % n] - points[i] for i in range(n)]
    lengths = [float(np.linalg.norm(side[:2])) for side in sides]
    scale = max(lengths)
    if min(lengths) < EPS or abs(_cross2(points[1] - points[0], points[2] - points[0])) < EPS * scale * scale:
        raise ValueError("Đa giác ban đầu bị suy biến.")

    edge_names = [names[i] + names[(i + 1) % n] for i in range(n)]

    def edge_key(name: str) -> str:
        return "".join(sorted(name.upper()))

    allowed_equals = {
        frozenset((edge_key(left), edge_key(right)))
        for left, right in allowed_equal_pairs
    }

    def equal_unstated(i: int, j: int) -> bool:
        if abs(lengths[i] - lengths[j]) > side_gap * scale:
            return False
        return frozenset((edge_key(edge_names[i]), edge_key(edge_names[j]))) not in allowed_equals

    def sides_nearly_equal(i: int, j: int) -> bool:
        return abs(lengths[i] - lengths[j]) <= side_gap * scale

    if n == 3:
        if any(equal_unstated(i, j) for i in range(3) for j in range(i + 1, 3)):
            raise ValueError(
                f"GEOMETRY_ACCIDENTAL_SPECIAL: Tam giác {names} gần cân/đều dù đề không cho; "
                "hãy đổi tọa độ tam giác gốc rồi tính lại các điểm phụ."
            )
    else:
        # An ordinary quadrilateral may have one equal-side pair by chance.
        # Two matching pairs, however, suggest a kite or parallelogram.
        special_equal_patterns = (((0, 1), (2, 3)), ((0, 3), (1, 2)), ((0, 2), (1, 3)))
        if any(all(sides_nearly_equal(i, j) for i, j in pattern)
               and any(equal_unstated(i, j) for i, j in pattern)
               for pattern in special_equal_patterns):
            raise ValueError(
                f"GEOMETRY_ACCIDENTAL_SPECIAL: Tứ giác {names} gần hình diều/hình bình hành "
                "dù đề không cho; hãy đổi tọa độ tứ giác gốc."
            )

    allowed_rights = {name.upper() for name in allowed_right_vertices}
    right_limit = float(np.sin(np.deg2rad(right_gap_degrees)))
    for i, vertex in enumerate(points):
        before = points[(i - 1) % n] - vertex
        after = points[(i + 1) % n] - vertex
        cosine = float(np.dot(before[:2], after[:2])) / (
            float(np.linalg.norm(before[:2])) * float(np.linalg.norm(after[:2]))
        )
        if abs(cosine) < right_limit and names[i] not in allowed_rights:
            raise ValueError(
                f"GEOMETRY_ACCIDENTAL_SPECIAL: Góc {names[i]} của đa giác {names} gần vuông "
                "dù đề không cho; hãy đổi tọa độ các đỉnh gốc."
            )

    if n == 4:
        allowed_parallels = {
            frozenset((edge_key(left), edge_key(right)))
            for left, right in allowed_parallel_pairs
        }
        for i, j in ((0, 2), (1, 3)):
            sine = abs(_cross2(sides[i], sides[j])) / (lengths[i] * lengths[j])
            relation = frozenset((edge_key(edge_names[i]), edge_key(edge_names[j])))
            if sine < parallel_sine_gap and relation not in allowed_parallels:
                raise ValueError(
                    f"GEOMETRY_ACCIDENTAL_SPECIAL: Tứ giác {names} có hai cạnh đối gần "
                    "song song dù đề không cho; hãy đổi tọa độ các đỉnh gốc."
                )
    return True


def midpoint_marker(midpoint, start, end, other_points=(), **mark_style):
    """Verify a midpoint and omit ambiguous ticks when another named point splits a half."""
    midpoint, start, end = _point(midpoint), _point(start), _point(end)
    error = float(np.linalg.norm(midpoint - (start + end) / 2))
    if error > 0.01 * max(float(np.linalg.norm(end - start)), 1.0):
        raise ValueError("Điểm được ghi là trung điểm nhưng không chia đoạn thành hai phần bằng nhau.")
    parent = end - start
    parent_length = float(np.linalg.norm(parent[:2]))
    direction = _unit(parent)
    for other in other_points:
        other = _point(other)
        if min(
            float(np.linalg.norm((other - start)[:2])),
            float(np.linalg.norm((other - midpoint)[:2])),
            float(np.linalg.norm((other - end)[:2])),
        ) < 0.01 * max(parent_length, 1.0):
            continue
        distance_from_line = abs(_cross2(other - start, direction))
        projection = float(np.dot((other - start)[:2], direction[:2]))
        if distance_from_line <= 0.01 * max(parent_length, 1.0) and 0 < projection < parent_length:
            return VGroup()
    return equal_segment_marks((start, midpoint), (midpoint, end), **mark_style)


def median_segment(apex, midpoint, side_start, side_end, color=BLACK):
    midpoint_marker(midpoint, side_start, side_end)
    return Line(_point(apex), _point(midpoint), color=color)


def altitude_segment(apex, foot, side_start, side_end, color=BLACK, dashed: bool = False,
                     tolerance: float = 0.01):
    apex, foot = _point(apex), _point(foot)
    side_start, side_end = _point(side_start), _point(side_end)
    side = side_end - side_start
    altitude = apex - foot
    scale = max(float(np.linalg.norm(side) * np.linalg.norm(altitude)), 1.0)
    if abs(float(np.dot(side[:2], altitude[:2]))) > tolerance * scale:
        raise ValueError("Đường cao không vuông góc với đường thẳng chứa cạnh đối diện.")
    if abs(_cross2(foot - side_start, side)) > tolerance * max(float(np.linalg.norm(side)), 1.0):
        raise ValueError("Chân đường cao không nằm trên đường thẳng chứa cạnh đối diện.")
    del dashed  # Kept only for compatibility; all plane-geometry lines are solid.
    altitude_line = Line(apex, foot, color=color)
    side_rays = [side_start - foot, side_end - foot]
    side_rays = [ray for ray in side_rays if np.linalg.norm(ray[:2]) >= EPS]
    if not side_rays:
        raise ValueError("Không xác định được phía đặt ký hiệu góc vuông trên cạnh đối diện.")
    # Point the reference ray toward the actual side segment. Together with foot->apex,
    # quadrant=(1, 1) keeps the square in the bounded construction instead of its extension.
    side_ray = min(side_rays, key=lambda ray: float(np.linalg.norm(ray[:2])))
    side_line = Line(foot, foot + _unit(side_ray), color=color)
    square = RightAngle(
        side_line,
        Line(foot, apex),
        length=0.20,
        quadrant=(1, 1),
        color=BLACK,
    )
    return VGroup(altitude_line, square)


def perpendicular_intersection_marker(first_segment, second_segment, intersection,
                                      length: float = 0.20, color=BLACK,
                                      tolerance: float = 0.01):
    """Draw exactly one right-angle square for two perpendicular intersecting lines."""
    if len(first_segment) != 2 or len(second_segment) != 2:
        raise ValueError("Mỗi đường vuông góc phải được truyền bằng đúng hai điểm.")
    first_start, first_end = (_point(point) for point in first_segment)
    second_start, second_end = (_point(point) for point in second_segment)
    intersection = _point(intersection)
    first_direction = first_end - first_start
    second_direction = second_end - second_start
    scale = max(
        float(np.linalg.norm(first_direction) * np.linalg.norm(second_direction)),
        1.0,
    )
    if abs(float(np.dot(first_direction[:2], second_direction[:2]))) > tolerance * scale:
        raise ValueError("Hai đường được ký hiệu nhưng không vuông góc.")
    for start, end, direction in (
        (first_start, first_end, first_direction),
        (second_start, second_end, second_direction),
    ):
        if abs(_cross2(intersection - start, direction)) > tolerance * max(
            float(np.linalg.norm(direction)), 1.0,
        ):
            raise ValueError("Giao điểm ký hiệu góc vuông không nằm trên cả hai đường.")

    def inward_ray(start, end):
        rays = [start - intersection, end - intersection]
        rays = [ray for ray in rays if np.linalg.norm(ray[:2]) >= EPS]
        if not rays:
            raise ValueError("Không xác định được tia để đặt ký hiệu góc vuông.")
        return min(rays, key=lambda ray: float(np.linalg.norm(ray[:2])))

    first_ray = inward_ray(first_start, first_end)
    second_ray = inward_ray(second_start, second_end)
    return RightAngle(
        Line(intersection, intersection + _unit(first_ray)),
        Line(intersection, intersection + _unit(second_ray)),
        length=float(length),
        quadrant=(1, 1),
        color=color,
    )


def angle_bisector_segment(vertex, point, first_ray_point, second_ray_point, color=BLACK,
                           tolerance_degrees: float = 0.75, radius: float = 0.42,
                           mark_count: int = 1, boundary_segments=(), numbered: bool = True):
    vertex, point = _point(vertex), _point(point)
    first_ray_point, second_ray_point = _point(first_ray_point), _point(second_ray_point)
    first = _angle_degrees(first_ray_point - vertex, point - vertex)
    second = _angle_degrees(point - vertex, second_ray_point - vertex)
    _assert_close(first, second, tolerance_degrees, "Tia được ghi là phân giác nhưng hai góc không bằng nhau")
    if not isinstance(mark_count, int) or not 1 <= mark_count <= 3:
        raise ValueError("Số cung ký hiệu phân giác phải từ 1 đến 3.")
    bisector_end = point
    if boundary_segments:
        direction = _unit(point - vertex)
        point_distance = float(np.linalg.norm((point - vertex)[:2]))
        candidates = []
        for segment in boundary_segments:
            if len(segment) != 2:
                raise ValueError("Mỗi cạnh biên phải gồm đúng hai điểm.")
            side_start, side_end = _point(segment[0]), _point(segment[1])
            side = side_end - side_start
            denominator = _cross2(direction, side)
            if abs(denominator) < EPS:
                continue
            offset = side_start - vertex
            distance_on_ray = _cross2(offset, side) / denominator
            position_on_side = _cross2(offset, direction) / denominator
            if (distance_on_ray > EPS and -0.01 <= position_on_side <= 1.01
                    and distance_on_ray + 0.01 >= point_distance):
                candidates.append((distance_on_ray, vertex + distance_on_ray * direction))
        if not candidates:
            raise ValueError(
                "Tia phân giác không gặp cạnh biên nào sau điểm đã nêu; hãy kiểm tra lại hình."
            )
        bisector_end = min(candidates, key=lambda item: item[0])[1]
    bisector = Line(vertex, bisector_end, color=color)
    marks = VGroup(bisector)
    first_vector = first_ray_point - vertex
    bisector_vector = point - vertex
    second_vector = second_ray_point - vertex
    for index in range(mark_count):
        arc_radius = radius + 0.10 * index
        marks.add(Angle(
            Line(vertex, first_ray_point), Line(vertex, point),
            radius=arc_radius, color=BLACK,
            other_angle=(_cross2(first_vector, bisector_vector) < 0),
        ))
        marks.add(Angle(
            Line(vertex, point), Line(vertex, second_ray_point),
            radius=arc_radius, color=BLACK,
            other_angle=(_cross2(bisector_vector, second_vector) < 0),
        ))
    if numbered:
        first_unit = _unit(first_vector)
        bisector_unit = _unit(bisector_vector)
        second_unit = _unit(second_vector)
        label_radius = radius + (mark_count - 1) * 0.10 + 0.25
        first_label_direction = _unit(first_unit + bisector_unit)
        second_label_direction = _unit(bisector_unit + second_unit)
        first_label = Text("1", font_size=18, color=color)
        second_label = Text("2", font_size=18, color=color)
        first_label.move_to(vertex + label_radius * first_label_direction)
        second_label.move_to(vertex + label_radius * second_label_direction)
        marks.add(first_label, second_label)
    return marks


def perpendicular_bisector(start, end, half_length: float = 3.0, color=BLACK, dashed: bool = False):
    start, end = _point(start), _point(end)
    middle = (start + end) / 2
    direction = _unit(end - start)
    perpendicular = np.array([-direction[1], direction[0], 0.0])
    del dashed  # Kept only for compatibility; all plane-geometry lines are solid.
    return Line(middle - half_length * perpendicular, middle + half_length * perpendicular,
                color=color)


def perpendicular_through_point(point, reference_start, reference_end, line_end=None,
                                color=BLACK, tolerance: float = 0.01,
                                minimum_half_length: float = 1.0):
    """Draw a solid auxiliary line and its right-angle square at the reference line.

    The perpendicular passes through ``point``. When ``line_end`` is supplied,
    the visible line includes that point too (for example the named intersection
    N with another carrier line).
    """
    point = _point(point)
    reference_start, reference_end = _point(reference_start), _point(reference_end)
    reference = reference_end - reference_start
    reference_unit = _unit(reference)
    foot = reference_start + float(
        np.dot((point - reference_start)[:2], reference_unit[:2])
    ) * reference_unit
    perpendicular = np.array([-reference_unit[1], reference_unit[0], 0.0])
    if np.dot((point - foot)[:2], perpendicular[:2]) < 0:
        perpendicular = -perpendicular

    candidates = [foot, point]
    if line_end is not None:
        line_end = _point(line_end)
        distance = abs(_cross2(line_end - point, perpendicular))
        if distance > tolerance * max(float(np.linalg.norm(line_end - point)), 1.0):
            raise ValueError("Điểm cuối không nằm trên đường phụ vuông góc đã dựng.")
        candidates.append(line_end)

    projections = [float(np.dot((candidate - foot)[:2], perpendicular[:2]))
                   for candidate in candidates]
    low, high = min(projections), max(projections)
    if high - low < minimum_half_length:
        low = min(low, -minimum_half_length)
        high = max(high, minimum_half_length)
    auxiliary = Line(foot + low * perpendicular, foot + high * perpendicular, color=color)
    reference_rays = [reference_start - foot, reference_end - foot]
    reference_rays = [ray for ray in reference_rays if np.linalg.norm(ray[:2]) >= EPS]
    reference_ray = min(
        reference_rays,
        key=lambda ray: float(np.linalg.norm(ray[:2])),
        default=reference_unit,
    )
    auxiliary_ray = point - foot
    if np.linalg.norm(auxiliary_ray[:2]) < EPS and line_end is not None:
        auxiliary_ray = line_end - foot
    if np.linalg.norm(auxiliary_ray[:2]) < EPS:
        auxiliary_ray = perpendicular
    square = RightAngle(
        Line(foot, foot + _unit(reference_ray)),
        Line(foot, foot + _unit(auxiliary_ray)),
        length=0.20,
        quadrant=(1, 1),
        color=BLACK,
    )
    return VGroup(auxiliary, square)


def ray(start, through, length: float = 6.0, color=BLACK):
    start, through = _point(start), _point(through)
    return Line(start, start + length * _unit(through - start), color=color)


def opposite_ray_point(origin, through, distance: float | None = None) -> np.ndarray:
    """Construct a point on the ray opposite to origin->through."""
    origin, through = _point(origin), _point(through)
    base_length = float(np.linalg.norm(through - origin))
    if distance is None:
        distance = base_length
    if float(distance) <= 0:
        raise ValueError("Khoảng cách trên tia đối phải dương.")
    return origin - float(distance) * _unit(through - origin)


def _manual_segment_points(name: str) -> tuple[np.ndarray, np.ndarray]:
    if not isinstance(name, str) or len(name) != 2 or name[0] == name[1]:
        raise ValueError("Đoạn thẳng được chọn không hợp lệ.")
    first = _NAMED_POINTS.get(name[0])
    second = _NAMED_POINTS.get(name[1])
    if first is None or second is None:
        raise ValueError(f"Không tìm thấy hai đầu mút của đoạn {name}.")
    return first, second


def _convex_boundary_segments(points: Sequence[np.ndarray]):
    unique = {}
    for point in points:
        point = _point(point)
        unique[(round(float(point[0]), 8), round(float(point[1]), 8))] = point
    ordered = sorted(unique.items())
    if len(ordered) < 3:
        return []

    def turn(first, second, third):
        return _cross2(second[1] - first[1], third[1] - second[1])

    lower = []
    for item in ordered:
        while len(lower) >= 2 and turn(lower[-2], lower[-1], item) <= EPS:
            lower.pop()
        lower.append(item)
    upper = []
    for item in reversed(ordered):
        while len(upper) >= 2 and turn(upper[-2], upper[-1], item) <= EPS:
            upper.pop()
        upper.append(item)
    hull = [item[1] for item in lower[:-1] + upper[:-1]]
    return [(hull[index], hull[(index + 1) % len(hull)]) for index in range(len(hull))]


def _bounded_bisector_endpoint(vertex, direction, all_points) -> np.ndarray:
    vertex = _point(vertex)
    direction = _unit(direction)
    candidates = []
    for start, end in _convex_boundary_segments(all_points):
        if np.linalg.norm(start - vertex) < 0.01 or np.linalg.norm(end - vertex) < 0.01:
            continue
        side = end - start
        denominator = _cross2(direction, side)
        if abs(denominator) < EPS:
            continue
        offset = start - vertex
        distance = _cross2(offset, side) / denominator
        position = _cross2(offset, direction) / denominator
        if distance > EPS and -0.01 <= position <= 1.01:
            candidates.append((distance, vertex + distance * direction))
    if candidates:
        return min(candidates, key=lambda item: item[0])[1]
    span = max(
        (float(np.linalg.norm(_point(point) - vertex)) for point in all_points),
        default=2.0,
    )
    return vertex + max(1.0, 0.65 * span) * direction


def _add_manual_point(scene, name: str, point, *connected_points) -> None:
    if not name:
        return
    point = _point(point)
    existing = _NAMED_POINTS.get(name)
    if existing is not None and np.linalg.norm(existing - point) > 0.02:
        raise ValueError(f"Tên điểm {name} đã thuộc một vị trí khác.")
    _NAMED_POINTS[name] = point.copy()
    scene.add(Dot(point, color=BLACK))
    scene.add(safe_point_label(
        point, name, *connected_points, distance=0.38,
        avoid_points=tuple(
            value for key, value in _NAMED_POINTS.items() if key != name
        ),
    ))


def _apply_manual_constructions(scene, edits: dict, segment_names: set[str]) -> None:
    """Apply coordinate-verified GeoGebra-like construction toolbar actions."""
    constructions = edits.get("constructions", ())
    if not isinstance(constructions, (list, tuple)):
        return
    original_points = list(_NAMED_POINTS.values())
    if not original_points:
        return
    cloud = np.array([point[:2] for point in original_points])
    span = max(float(np.ptp(cloud[:, 0])), float(np.ptp(cloud[:, 1])), 3.0)

    for index, spec in enumerate(constructions):
        if not isinstance(spec, dict):
            continue
        kind = spec.get("type")
        mark_count = index % 3 + 1
        if kind == "perpendicular":
            point_name = str(spec.get("point", ""))
            point = _NAMED_POINTS.get(point_name)
            if point is None:
                raise ValueError(f"Không tìm thấy điểm {point_name} để hạ vuông góc.")
            start, end = _manual_segment_points(str(spec.get("segment", "")))
            direction = end - start
            foot = start + float(
                np.dot((point - start)[:2], direction[:2])
                / np.dot(direction[:2], direction[:2])
            ) * direction
            if np.linalg.norm(point - foot) < 0.02:
                raise ValueError("Điểm đã nằm trên đường tham chiếu nên không tạo được đường chiếu.")
            scene.add(altitude_segment(point, foot, start, end))
            projection = float(np.dot((foot - start)[:2], direction[:2])
                               / np.dot(direction[:2], direction[:2]))
            if projection < 0.0 or projection > 1.0:
                scene.add(line_through_intersection(start, end, foot))
            _add_manual_point(scene, str(spec.get("name", "")), foot, point, start, end)

        elif kind == "angle_bisector":
            first_name = str(spec.get("side1", ""))
            second_name = str(spec.get("side2", ""))
            shared = set(first_name) & set(second_name)
            if len(shared) != 1:
                raise ValueError("Hai cạnh của góc phải có chung đúng một đỉnh.")
            vertex_name = next(iter(shared))
            vertex = _NAMED_POINTS[vertex_name]
            first_other = _NAMED_POINTS[next(name for name in first_name if name != vertex_name)]
            second_other = _NAMED_POINTS[next(name for name in second_name if name != vertex_name)]
            direction = _unit(first_other - vertex) + _unit(second_other - vertex)
            if np.linalg.norm(direction[:2]) < EPS:
                raise ValueError("Hai cạnh đối nhau không tạo thành một góc có tia phân giác duy nhất.")
            endpoint = _bounded_bisector_endpoint(vertex, direction, original_points)
            scene.add(angle_bisector_segment(
                vertex, endpoint, first_other, second_other,
                mark_count=mark_count, numbered=False,
            ))

        elif kind == "perpendicular_bisector":
            start, end = _manual_segment_points(str(spec.get("segment", "")))
            middle = (start + end) / 2
            bisector = perpendicular_bisector(start, end, half_length=0.72 * span)
            scene.add(bisector)
            scene.add(midpoint_marker(middle, start, end, count=mark_count,
                                      other_points=tuple(original_points)))
            scene.add(perpendicular_intersection_marker(
                (start, end), (bisector.get_start(), bisector.get_end()), middle,
            ))
            _add_manual_point(scene, str(spec.get("name", "")), middle, start, end)

        elif kind == "median":
            point_name = str(spec.get("point", ""))
            apex = _NAMED_POINTS.get(point_name)
            start, end = _manual_segment_points(str(spec.get("segment", "")))
            if apex is None:
                raise ValueError(f"Không tìm thấy đỉnh {point_name} của đường trung tuyến.")
            if np.linalg.norm(apex - start) < 0.02 or np.linalg.norm(apex - end) < 0.02:
                raise ValueError("Cạnh đối diện không được chứa đỉnh của đường trung tuyến.")
            middle = (start + end) / 2
            scene.add(Line(apex, middle, color=BLACK))
            scene.add(midpoint_marker(middle, start, end, count=mark_count,
                                      other_points=tuple(original_points)))
            _add_manual_point(scene, str(spec.get("name", "")), middle, apex, start, end)


def fit_scene_to_frame(scene, padding: float = 0.45):
    """Scale down and center all current mobjects so none are clipped by the camera."""
    edits = _manual_edits()
    hidden_points = set(edits.get("hidden_points", ()))
    hidden_segments = {"".join(sorted(value)) for value in edits.get("hidden_segments", ())}
    segment_widths = edits.get("segment_widths", {})

    for name in hidden_points:
        point = _NAMED_POINTS.get(name)
        if point is None:
            continue
        for mobject in list(scene.mobjects):
            if isinstance(mobject, Dot) and np.linalg.norm(mobject.get_center() - point) < 0.02:
                scene.remove(mobject)

    def segment_name(mobject) -> str | None:
        if not isinstance(mobject, Line):
            return None
        for first_name, first in _NAMED_POINTS.items():
            for second_name, second in _NAMED_POINTS.items():
                if first_name >= second_name:
                    continue
                direct = (
                    np.linalg.norm(mobject.get_start() - first) < 0.02
                    and np.linalg.norm(mobject.get_end() - second) < 0.02
                )
                reverse = (
                    np.linalg.norm(mobject.get_start() - second) < 0.02
                    and np.linalg.norm(mobject.get_end() - first) < 0.02
                )
                if direct or reverse:
                    return first_name + second_name
        return None

    existing_segments = set()
    for mobject in list(scene.mobjects):
        name = segment_name(mobject)
        if not name:
            continue
        existing_segments.add(name)
        if name in hidden_segments:
            scene.remove(mobject)
        elif name in segment_widths:
            mobject.set_stroke(width=float(segment_widths[name]))

    for value in edits.get("added_segments", ()):
        name = "".join(sorted(value))
        if len(name) != 2 or name in hidden_segments or name in existing_segments:
            continue
        first, second = (_NAMED_POINTS.get(letter) for letter in name)
        if first is not None and second is not None:
            scene.add(Line(first, second, color=BLACK,
                           stroke_width=float(segment_widths.get(name, 2.0))))

    _apply_manual_constructions(scene, edits, existing_segments)

    if not scene.mobjects:
        return
    group = VGroup(*scene.mobjects)
    available_width = float(config.frame_width) - 2 * padding
    available_height = float(config.frame_height) - 2 * padding
    if group.width < EPS or group.height < EPS:
        return
    scale = min(available_width / group.width, available_height / group.height, 1.0)
    if scale < 1.0:
        group.scale(scale)
    group.move_to(ORIGIN)


def layout_spacing_check(*focus_points, all_points=(), minimum_ratio: float = 0.09,
                         minimum_distance: float = 0.65,
                         maximum_aspect_ratio: float = 2.0):
    """Reject auxiliary layouts that are cramped or excessively wide/tall."""
    focus = [_point(point) for point in focus_points]
    if len(focus) < 2:
        raise ValueError("GEOMETRY_LAYOUT_CROWDED: cần ít nhất hai điểm phụ để kiểm tra bố cục.")
    cloud = focus + [_point(point) for point in all_points]
    coordinates = np.array([point[:2] for point in cloud])
    extents = np.ptp(coordinates, axis=0)
    span = float(np.linalg.norm(extents))
    narrow_extent = max(float(min(extents)), EPS)
    aspect_ratio = float(max(extents)) / narrow_extent
    if aspect_ratio > float(maximum_aspect_ratio):
        raise ValueError(
            "GEOMETRY_LAYOUT_CROWDED: hình đang quá rộng hoặc quá cao "
            f"(tỷ lệ {aspect_ratio:.2f} > {float(maximum_aspect_ratio):.2f}). "
            "Hãy chọn lại tọa độ để hình cân đối theo cả chiều ngang và chiều dọc."
        )
    required_gap = max(float(minimum_distance), float(minimum_ratio) * max(span, 1.0))
    closest = min(
        float(np.linalg.norm((focus[index] - focus[other])[:2]))
        for index in range(len(focus))
        for other in range(index + 1, len(focus))
    )
    if closest < required_gap:
        raise ValueError(
            "GEOMETRY_LAYOUT_CROWDED: các điểm phụ đang quá sát nhau "
            f"({closest:.2f} < {required_gap:.2f}). Hãy đổi tỷ lệ/tọa độ hình chính để "
            "các chân đường, giao điểm và nhãn tách rõ, rồi dựng lại toàn bộ hình."
        )


def _distance_to_segment(point, start, end) -> float:
    """Return the 2D distance from a point to a finite segment."""
    point, start, end = _point(point), _point(start), _point(end)
    segment = end - start
    squared_length = float(np.dot(segment[:2], segment[:2]))
    if squared_length < EPS:
        return float(np.linalg.norm((point - start)[:2]))
    ratio = float(np.dot((point - start)[:2], segment[:2]) / squared_length)
    ratio = min(1.0, max(0.0, ratio))
    projection = start + ratio * segment
    return float(np.linalg.norm((point - projection)[:2]))


def safe_point_label(point, name: str, *connected_points, distance: float = 0.52,
                     font_size: int = 28, color=BLACK, avoid_points=(),
                     avoid_segments=()):
    """Place a point name away from incident lines, nearby points, and drawn segments."""
    point = _point(point)
    _NAMED_POINTS[str(name)] = point.copy()
    if str(name) in set(_manual_edits().get("hidden_labels", ())):
        return VGroup()
    axes = []
    incident_segments = []
    for connected in connected_points:
        connected = _point(connected)
        vector = connected - point
        if np.linalg.norm(vector[:2]) >= EPS:
            axes.append(_unit(vector))
            incident_segments.append((point, connected))

    if axes:
        candidates = [
            np.array([np.cos(angle), np.sin(angle), 0.0])
            for angle in np.linspace(0.0, 2 * np.pi, 64, endpoint=False)
        ]
        nearby_points = [_point(other) for other in (*connected_points, *avoid_points)]
        obstacle_segments = incident_segments + [
            (_point(segment[0]), _point(segment[1]))
            for segment in avoid_segments
            if len(segment) == 2
        ]
        centroid = np.mean(nearby_points, axis=0) if nearby_points else point
        outward = point - centroid
        outward_length = float(np.linalg.norm(outward[:2]))
        outward = _unit(outward) if outward_length >= EPS else np.zeros(3)

        def clearance(direction) -> tuple[float, float, float, float]:
            center = point + float(distance) * direction
            line_clearance = min(abs(_cross2(direction, axis)) for axis in axes)
            segment_clearance = min(
                (_distance_to_segment(center, start, end) for start, end in obstacle_segments),
                default=float(distance),
            )
            point_clearance = min(
                (float(np.linalg.norm((center - other)[:2])) for other in nearby_points),
                default=float(distance),
            )
            normalized_segment = min(segment_clearance / max(float(distance), EPS), 2.0)
            normalized_point = min(point_clearance / max(float(distance), EPS), 2.0)
            outward_preference = float(np.dot(direction[:2], outward[:2]))
            score = (
                2.0 * normalized_segment
                + 0.9 * line_clearance
                + 0.45 * normalized_point
                + 0.55 * outward_preference
            )
            # Clearance from strokes is a hard priority. This prevents an outward preference
            # from placing a label directly on the extension of an incident line.
            stroke_safety = min(2.0 * line_clearance, normalized_segment)
            return stroke_safety, score, outward_preference, float(direction[1])

        direction = max(candidates, key=clearance)
    else:
        direction = np.array([0.0, 1.0, 0.0])

    label = Text(str(name), font_size=font_size, color=color)
    manual_offset = np.zeros(3)
    try:
        saved_offsets = json.loads(os.environ.get("GEO_DRAW_LABEL_OFFSETS", "{}"))
        offset = saved_offsets.get(str(name), (0.0, 0.0))
        if isinstance(offset, (list, tuple)) and len(offset) == 2:
            manual_offset = np.array([float(offset[0]), float(offset[1]), 0.0])
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    label.move_to(point + float(distance) * direction + manual_offset)
    return label


def infinite_line(first, second, half_length: float = 7.0, color=BLACK):
    first, second = _point(first), _point(second)
    middle = (first + second) / 2
    direction = _unit(second - first)
    return Line(middle - half_length * direction, middle + half_length * direction, color=color)


def line_through_intersection(start, end, intersection, color=BLACK,
                              tolerance: float = 0.01):
    """Draw the solid portion of a line containing a segment and a named intersection.

    If the intersection lies outside the original segment, the returned line is
    extended exactly far enough to include it. If it lies inside, the original
    segment is preserved.
    """
    start, end, intersection = _point(start), _point(end), _point(intersection)
    direction = _unit(end - start)
    line_length = float(np.linalg.norm(end - start))
    distance_from_line = abs(_cross2(intersection - start, direction))
    if distance_from_line > tolerance * max(line_length, 1.0):
        raise ValueError("Giao điểm không nằm trên đường thẳng cần kéo dài.")
    projection = float(np.dot((intersection - start)[:2], direction[:2]))
    low = min(0.0, line_length, projection)
    high = max(0.0, line_length, projection)
    return Line(start + low * direction, start + high * direction, color=color)
