"""Place plane-geometry figures in 2D coordinates."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .parser import Problem

Point = tuple[float, float]


@dataclass
class Figure:
    points: dict[str, Point] = field(default_factory=dict)
    segments: list[tuple[str, str]] = field(default_factory=list)
    circles: list[tuple[str, float]] = field(default_factory=list)  # center name, radius
    right_marks: list[tuple[str, str, str]] = field(default_factory=list)  # vertex, from, to
    labels: dict[str, Point] = field(default_factory=dict)
    title: str = ""


def _sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])


def _add(a: Point, b: Point) -> Point:
    return (a[0] + b[0], a[1] + b[1])


def _mul(a: Point, k: float) -> Point:
    return (a[0] * k, a[1] * k)


def _dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _len(a: Point) -> float:
    return math.hypot(a[0], a[1])


def _unit(a: Point) -> Point:
    n = _len(a)
    if n < 1e-12:
        return (1.0, 0.0)
    return (a[0] / n, a[1] / n)


def _perp(a: Point) -> Point:
    return (-a[1], a[0])


def _mid(a: Point, b: Point) -> Point:
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def _rotate(v: Point, deg: float) -> Point:
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


def _side(problem: Problem, a: str, b: str, default: float) -> float:
    key = (a, b) if a < b else (b, a)
    return problem.sides.get(key, default)


def _project_on_segment(p: Point, a: Point, b: Point) -> Point:
    ab = _sub(b, a)
    t = _dot(_sub(p, a), ab) / max(_dot(ab, ab), 1e-12)
    t = min(1.0, max(0.0, t))
    return _add(a, _mul(ab, t))


def _fit(points: dict[str, Point]) -> dict[str, Point]:
    if not points:
        return points
    xs = [p[0] for p in points.values()]
    ys = [p[1] for p in points.values()]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    w = max(max(xs) - min(xs), 1e-6)
    h = max(max(ys) - min(ys), 1e-6)
    scale = 5.4 / max(w, h)
    out: dict[str, Point] = {}
    for name, (x, y) in points.items():
        out[name] = ((x - cx) * scale, (y - cy) * scale)
    return out


def _ring_segments(verts: list[str]) -> list[tuple[str, str]]:
    return [(verts[i], verts[(i + 1) % len(verts)]) for i in range(len(verts))]


def build_figure(problem: Problem) -> Figure:
    fig = Figure(title=problem.raw_text.strip().split("\n")[0][:80])
    pts: dict[str, Point] = {}

    if problem.figure == "square":
        a, b, c, d = problem.vertices
        side = _side(problem, a, b, 4.0)
        pts[a] = (0.0, 0.0)
        pts[b] = (side, 0.0)
        pts[c] = (side, side)
        pts[d] = (0.0, side)
        fig.segments = _ring_segments([a, b, c, d])
        fig.right_marks = [(a, d, b), (b, a, c), (c, b, d), (d, c, a)]
    elif problem.figure == "rectangle":
        a, b, c, d = problem.vertices
        ab = _side(problem, a, b, 6.0)
        ad = _side(problem, a, d, 3.5)
        pts[a] = (0.0, 0.0)
        pts[b] = (ab, 0.0)
        pts[c] = (ab, ad)
        pts[d] = (0.0, ad)
        fig.segments = _ring_segments([a, b, c, d])
        fig.right_marks = [(a, d, b), (b, a, c), (c, b, d), (d, c, a)]
    elif problem.figure == "rhombus":
        a, b, c, d = problem.vertices
        side = _side(problem, a, b, 4.0)
        pts[a] = (0.0, 0.0)
        pts[b] = (side, 0.0)
        pts[d] = _rotate((side, 0.0), 60)
        pts[c] = _add(pts[b], pts[d])
        fig.segments = _ring_segments([a, b, c, d])
    elif problem.figure == "parallelogram":
        a, b, c, d = problem.vertices
        ab = _side(problem, a, b, 6.0)
        ad = _side(problem, a, d, 3.5)
        pts[a] = (0.0, 0.0)
        pts[b] = (ab, 0.0)
        pts[d] = (ad * 0.45, ad * 0.9)
        pts[c] = _add(pts[b], pts[d])
        fig.segments = _ring_segments([a, b, c, d])
    elif problem.figure == "trapezoid":
        a, b, c, d = problem.vertices
        ab = _side(problem, a, b, 7.0)
        pts[a] = (0.0, 0.0)
        pts[b] = (ab, 0.0)
        pts[c] = (ab * 0.78, 3.2)
        pts[d] = (ab * 0.22, 3.2)
        fig.segments = _ring_segments([a, b, c, d])
    elif problem.figure == "circle":
        o = problem.circle_center or "O"
        r = problem.circle_radius or 3.0
        pts[o] = (0.0, 0.0)
        fig.circles.append((o, r))
        if problem.diameter:
            p, q = problem.diameter
            pts[p] = (-r, 0.0)
            pts[q] = (r, 0.0)
            fig.segments.append((p, q))
    else:
        a, b, c = (problem.vertices + ["A", "B", "C"])[:3]
        if problem.equilateral:
            s = _side(problem, a, b, 4.0)
            pts[a] = (0.0, 0.0)
            pts[b] = (s, 0.0)
            h = s * math.sqrt(3) / 2
            pts[c] = (s / 2, h)
        elif problem.right_at:
            right = problem.right_at
            others = [v for v in [a, b, c] if v != right]
            p1, p2 = others[0], others[1]
            l1 = _side(problem, right, p1, 3.0)
            l2 = _side(problem, right, p2, 4.0)
            pts[right] = (0.0, 0.0)
            pts[p1] = (l1, 0.0)
            pts[p2] = (0.0, l2)
            fig.right_marks.append((right, p1, p2))
        elif problem.isosceles_apex:
            apex = problem.isosceles_apex
            base = [v for v in [a, b, c] if v != apex]
            p1, p2 = base[0], base[1]
            base_len = _side(problem, p1, p2, 4.0)
            leg = _side(problem, apex, p1, 5.0)
            pts[p1] = (0.0, 0.0)
            pts[p2] = (base_len, 0.0)
            x = base_len / 2
            y = math.sqrt(max(leg * leg - x * x, 0.25))
            pts[apex] = (x, y)
        else:
            ab = _side(problem, a, b, 5.0)
            ac = _side(problem, a, c, 4.5)
            bc = _side(problem, b, c, 4.0)
            pts[a] = (0.0, 0.0)
            pts[b] = (ab, 0.0)
            # SSS: place C via two circles
            cos_a = (ab * ab + ac * ac - bc * bc) / max(2 * ab * ac, 1e-9)
            cos_a = min(1.0, max(-1.0, cos_a))
            ang = math.acos(cos_a)
            pts[c] = (ac * math.cos(ang), ac * math.sin(ang))
        fig.segments = _ring_segments([a, b, c])

    for m, p, q in problem.midpoints:
        if p in pts and q in pts:
            pts[m] = _mid(pts[p], pts[q])
            fig.segments.append((p, q))

    for a, h, bc in problem.altitudes:
        if len(bc) < 2 or a not in pts:
            continue
        b, c = bc[0], bc[1]
        if b not in pts or c not in pts:
            continue
        foot = _project_on_segment(pts[a], pts[b], pts[c])
        pts[h] = foot
        fig.segments.append((a, h))
        fig.right_marks.append((h, a, c if _len(_sub(pts[c], foot)) > 1e-6 else b))

    for name, p, q in problem.extra_points_on:
        if p in pts and q in pts:
            pts[name] = _mid(pts[p], pts[q])

    pts = _fit(pts)
    # rescale circle radii after fit
    if fig.circles:
        o, r = fig.circles[0]
        if problem.diameter and problem.diameter[0] in pts and problem.diameter[1] in pts:
            r = _len(_sub(pts[problem.diameter[0]], pts[problem.diameter[1]])) / 2
        else:
            # radius scaled similarly: original r vs fitted origin-only -> keep relative
            r = 2.7 if r else 2.7
            if problem.circle_radius:
                # after fit a lone center has no scale; use a readable default mapped from r
                r = min(3.2, max(1.6, problem.circle_radius * 0.7))
        fig.circles = [(o, r)]

    fig.points = pts
    fig.labels = dict(pts)
    # unique segments
    seen = set()
    uniq = []
    for u, v in fig.segments:
        key = (u, v) if u < v else (v, u)
        if key in seen or u not in fig.points or v not in fig.points:
            continue
        seen.add(key)
        uniq.append((u, v))
    fig.segments = uniq
    return fig
