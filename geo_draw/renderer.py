"""Render the generated Manim scene to PNG (and optional MP4)."""

from __future__ import annotations

import os
import json
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RenderResult:
    image_path: Path | None
    video_path: Path | None
    log: str
    ok: bool


def _newest(folder: Path, pattern: str) -> Path | None:
    if not folder.exists():
        return None
    files = list(folder.rglob(pattern))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def render_scene(scene_file: Path, media_dir: Path, quality: str = "l", animate: bool = True,
                 label_offsets: dict[str, list[float]] | None = None,
                 manual_edits: dict | None = None) -> RenderResult:
    # A path already displayed by Streamlit can stay locked on Windows. Give
    # every render its own output directory instead of overwriting preview files.
    run_media_dir = media_dir / f"run-{uuid.uuid4().hex[:12]}"
    run_media_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "manim",
        "render",
        str(scene_file),
        "GeoScene",
        f"-q{quality}",
        "--media_dir",
        str(run_media_dir),
        "--disable_caching",
    ]
    if not animate:
        cmd.append("-s")

    render_env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    render_env["GEO_DRAW_LABEL_OFFSETS"] = json.dumps(label_offsets or {})
    render_env["GEO_DRAW_MANUAL_EDITS"] = json.dumps(manual_edits or {})
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=render_env,
    )
    log = (proc.stdout or "") + "\n" + (proc.stderr or "")
    image = _newest(run_media_dir, "*.png")
    video = _newest(run_media_dir, "*.mp4")
    expected_output = video if animate else image

    return RenderResult(
        image_path=image,
        video_path=video if animate else None,
        log=log,
        ok=proc.returncode == 0 and expected_output is not None,
    )
