"""What the manual editor needs from a generated scene, and its saved edits.

The editor re-renders the same ``scene.py`` with ``GEO_DRAW_LABEL_OFFSETS`` and
``GEO_DRAW_MANUAL_EDITS`` (see ``renderer.render_scene``); the edits are kept in
``edits.json`` next to the scene so they accumulate across sessions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

EDITS_FILE = "edits.json"


def empty_manual_edits() -> dict:
    return {
        "hidden_labels": [], "hidden_points": [], "hidden_segments": [],
        "added_segments": [], "segment_widths": {}, "constructions": [],
    }


def label_names(scene_path: Path) -> list[str]:
    """Point names placed with ``safe_point_label`` (AI scenes; parser scenes have none)."""
    if not scene_path.exists():
        return []
    code = scene_path.read_text(encoding="utf-8")
    return sorted(set(re.findall(r'safe_point_label\([^,]+,\s*["\']([A-Z])["\']', code)))


def segment_names(scene_path: Path, edits: dict | None = None) -> list[str]:
    if not scene_path.exists():
        return []
    code = scene_path.read_text(encoding="utf-8")
    found = {
        "".join(sorted(match))
        for match in re.findall(r"\bLine\(\s*([A-Z])\s*,\s*([A-Z])", code)
    }
    found.update(
        "".join(sorted(value))
        for value in (edits or {}).get("added_segments", ())
        if isinstance(value, str) and len(value) == 2
    )
    return sorted(found)


def suggest_point_name(names: list[str], edits: dict, preferred: str) -> str:
    occupied = set(names)
    occupied.update(
        str(item.get("name", ""))
        for item in edits.get("constructions", ())
        if isinstance(item, dict)
    )
    choices = preferred + "MNPKQRESTUVXYZ"
    return next((name for name in choices if name not in occupied), "")


def load_edits(scene_path: Path) -> tuple[dict, dict]:
    """Return ``(label_offsets, manual_edits)`` saved next to ``scene_path``."""
    try:
        saved = json.loads((scene_path.parent / EDITS_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    offsets = saved.get("label_offsets", {})
    edits = {**empty_manual_edits(), **saved.get("manual_edits", {})}
    return (offsets if isinstance(offsets, dict) else {}), edits


def save_edits(scene_path: Path, label_offsets: dict, manual_edits: dict) -> None:
    (scene_path.parent / EDITS_FILE).write_text(
        json.dumps({"label_offsets": label_offsets, "manual_edits": manual_edits},
                   ensure_ascii=False),
        encoding="utf-8",
    )
