"""Write a Manim scene from a Figure."""

from __future__ import annotations

from pathlib import Path

from .engine import Figure


def write_scene(figure: Figure, dest: Path, animate: bool = True) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "from manim import *",
        "import numpy as np",
        "",
        "",
        "class GeoScene(Scene):",
        "    def construct(self):",
        "        self.camera.background_color = WHITE",
    ]

    for name, (x, y) in sorted(figure.points.items()):
        lines.append(f"        {name} = np.array([{x:.5f}, {y:.5f}, 0.0])")

    lines.append("        dots = VGroup()")
    lines.append("        labels = VGroup()")
    for name in sorted(figure.points):
        lines.append(f"        dot_{name} = Dot({name}, radius=0.07, color=BLACK)")
        lines.append(
            f"        lab_{name} = Text('{name}', font_size=32, color=BLACK).next_to(dot_{name}, UR, buff=0.12)"
        )
        lines.append(f"        dots.add(dot_{name})")
        lines.append(f"        labels.add(lab_{name})")

    lines.append("        segs = VGroup()")
    for i, (u, v) in enumerate(figure.segments):
        lines.append(f"        seg_{i} = Line({u}, {v}, color=BLACK, stroke_width=4)")
        lines.append(f"        segs.add(seg_{i})")

    lines.append("        circs = VGroup()")
    for i, (center, r) in enumerate(figure.circles):
        lines.append(
            f"        circ_{i} = Circle(radius={r:.5f}, color=BLACK).move_to({center})"
        )
        lines.append(f"        circs.add(circ_{i})")

    lines.append("        marks = VGroup()")
    for i, (v, a, b) in enumerate(figure.right_marks):
        lines.append(
            f"        mark_{i} = RightAngle(Line({v}, {a}), Line({v}, {b}), length=0.22, color=BLACK)"
        )
        lines.append(f"        marks.add(mark_{i})")

    if animate:
        lines.extend(
            [
                "        if len(circs) > 0:",
                "            self.play(Create(circs), run_time=1.2)",
                "        if len(segs) > 0:",
                "            self.play(Create(segs), run_time=1.4)",
                "        if len(marks) > 0:",
                "            self.play(Create(marks), run_time=0.6)",
                "        self.play(FadeIn(dots, labels), run_time=0.8)",
                "        self.wait(0.6)",
            ]
        )
    else:
        lines.extend(
            [
                "        self.add(circs, segs, marks, dots, labels)",
                "        self.wait(0.1)",
            ]
        )

    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest
