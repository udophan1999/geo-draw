"""Parse Vietnamese (and simple English) plane-geometry problem text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Problem:
    figure: str = "triangle"  # triangle, square, rectangle, rhombus, parallelogram, trapezoid, circle
    vertices: list[str] = field(default_factory=lambda: ["A", "B", "C"])
    right_at: Optional[str] = None
    isosceles_apex: Optional[str] = None
    equilateral: bool = False
    sides: dict[tuple[str, str], float] = field(default_factory=dict)
    angles_deg: dict[str, float] = field(default_factory=dict)
    circle_center: Optional[str] = None
    circle_radius: Optional[float] = None
    diameter: Optional[tuple[str, str]] = None
    midpoints: list[tuple[str, str, str]] = field(default_factory=list)  # M of PQ
    altitudes: list[tuple[str, str, str]] = field(default_factory=list)  # H from A to BC
    medians: list[tuple[str, str, str]] = field(default_factory=list)  # M from A to BC
    extra_points_on: list[tuple[str, str, str]] = field(default_factory=list)  # D on BC
    raw_text: str = ""


_NUM = r"(?:\d+(?:[.,]\d+)?)"


def _norm(text: str) -> str:
    t = text.replace("\u00a0", " ").strip()
    t = re.sub(r"[ \t]+", " ", t)
    return t


def _f(num: str) -> float:
    return float(num.replace(",", "."))


def _edge_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def parse_problem(text: str) -> Problem:
    original = text
    text = _norm(text)
    p = Problem(raw_text=original)

    m = re.search(
        r"hình\s+vuông\s+([A-Z]{4})",
        text,
        re.I,
    ) or re.search(r"\bsquare\s+([A-Z]{4})\b", text, re.I)
    if m:
        p.figure = "square"
        p.vertices = list(m.group(1).upper())
    else:
        m = re.search(r"hình\s+chữ\s+nhật\s+([A-Z]{4})", text, re.I) or re.search(
            r"\brectangle\s+([A-Z]{4})\b", text, re.I
        )
        if m:
            p.figure = "rectangle"
            p.vertices = list(m.group(1).upper())
        else:
            m = re.search(r"hình\s+thoi\s+([A-Z]{4})", text, re.I)
            if m:
                p.figure = "rhombus"
                p.vertices = list(m.group(1).upper())
            else:
                m = re.search(r"hình\s+bình\s+hành\s+([A-Z]{4})", text, re.I)
                if m:
                    p.figure = "parallelogram"
                    p.vertices = list(m.group(1).upper())
                else:
                    m = re.search(r"hình\s+thang\s+([A-Z]{4})", text, re.I)
                    if m:
                        p.figure = "trapezoid"
                        p.vertices = list(m.group(1).upper())
                    else:
                        m = re.search(
                            r"(?:đường\s+)?tròn\s+tâm\s+([A-Z])(?:\s+bán\s+kính\s+("
                            + _NUM
                            + r"))?",
                            text,
                            re.I,
                        )
                        if m:
                            p.figure = "circle"
                            p.circle_center = m.group(1).upper()
                            p.vertices = [p.circle_center]
                            if m.group(2):
                                p.circle_radius = _f(m.group(2))
                        else:
                            m = re.search(r"tam\s+giác\s+([A-Z]{3})", text, re.I) or re.search(
                                r"\btriangle\s+([A-Z]{3})\b", text, re.I
                            )
                            if m:
                                p.figure = "triangle"
                                p.vertices = list(m.group(1).upper())

    if re.search(r"\bđều\b|\bequilateral\b", text, re.I):
        p.equilateral = True

    m = re.search(r"vuông\s+tại\s+([A-Z])", text, re.I) or re.search(
        r"right(?:[- ]angled)?\s+at\s+([A-Z])", text, re.I
    )
    if m:
        p.right_at = m.group(1).upper()

    m = re.search(r"cân\s+(?:tại|đỉnh)\s+([A-Z])", text, re.I)
    if m:
        p.isosceles_apex = m.group(1).upper()

    m = re.search(r"cạnh\s+(" + _NUM + r")", text, re.I)
    if m and (p.figure in {"square", "rhombus"} or p.equilateral):
        side = _f(m.group(1))
        verts = p.vertices
        if p.figure == "triangle" and len(verts) == 3:
            a, b, c = verts
            p.sides[_edge_key(a, b)] = side
            p.sides[_edge_key(b, c)] = side
            p.sides[_edge_key(c, a)] = side
        elif len(verts) >= 2:
            for i in range(len(verts)):
                p.sides[_edge_key(verts[i], verts[(i + 1) % len(verts)])] = side

    for m in re.finditer(r"\b([A-Z]{2})\s*=\s*(" + _NUM + r")", text):
        a, b = m.group(1)[0], m.group(1)[1]
        p.sides[_edge_key(a, b)] = _f(m.group(2))

    for m in re.finditer(
        r"(?:góc\s+)?([A-Z](?:[A-Z]{2})?)\s*=\s*(" + _NUM + r")\s*°?",
        text,
        re.I,
    ):
        name = m.group(1).upper()
        if len(name) == 1 or len(name) == 3:
            p.angles_deg[name] = _f(m.group(2))

    if p.figure == "circle":
        m = re.search(r"bán\s+kính\s+(" + _NUM + r")", text, re.I) or re.search(
            r"\bradius\s+(" + _NUM + r")", text, re.I
        )
        if m:
            p.circle_radius = _f(m.group(1))
        m = re.search(r"đường\s+kính\s+([A-Z]{2})", text, re.I)
        if m:
            p.diameter = (m.group(1)[0], m.group(1)[1])
            p.vertices = [p.circle_center or "O", m.group(1)[0], m.group(1)[1]]

    for m in re.finditer(
        r"([A-Z])\s+(?:là\s+)?trung\s+điểm\s+(?:của\s+)?(?:cạnh\s+)?([A-Z]{2})",
        text,
        re.I,
    ):
        p.midpoints.append((m.group(1).upper(), m.group(2)[0], m.group(2)[1]))

    for m in re.finditer(
        r"trung\s+điểm\s+([A-Z])\s+(?:của\s+)?(?:cạnh\s+)?([A-Z]{2})",
        text,
        re.I,
    ):
        p.midpoints.append((m.group(1).upper(), m.group(2)[0], m.group(2)[1]))

    m = re.search(
        r"đường\s+cao\s+([A-Z]{2})(?:\s+(?:kẻ\s+)?(?:từ\s+[A-Z]\s+)?(?:xuống|đến)\s+([A-Z]{2}))?",
        text,
        re.I,
    )
    if m:
        foot_seg = m.group(2)
        ah = m.group(1).upper()
        a, h = ah[0], ah[1]
        if foot_seg:
            p.altitudes.append((a, h, foot_seg.upper()))
        else:
            others = [v for v in p.vertices if v != a]
            if len(others) == 2:
                p.altitudes.append((a, h, "".join(others)))

    m = re.search(r"trung\s+tuyến\s+([A-Z]{2})", text, re.I)
    if m:
        am = m.group(1).upper()
        a, mid = am[0], am[1]
        others = [v for v in p.vertices if v != a]
        if len(others) == 2:
            p.medians.append((a, mid, "".join(others)))
            p.midpoints.append((mid, others[0], others[1]))

    for m in re.finditer(r"điểm\s+([A-Z])\s+trên\s+([A-Z]{2})", text, re.I):
        p.extra_points_on.append((m.group(1).upper(), m.group(2)[0], m.group(2)[1]))

    if p.figure == "triangle" and not p.vertices:
        p.vertices = ["A", "B", "C"]

    return p
