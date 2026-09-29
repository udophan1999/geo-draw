"""Per-browser-session state: signed-in user, workspace folder and the last drawing."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import streamlit as st

from geo_draw.history import HistoryEntry

from web import config


def empty_manual_edits() -> dict:
    return {
        "hidden_labels": [], "hidden_points": [], "hidden_segments": [],
        "added_segments": [], "segment_widths": {}, "constructions": [],
    }


def current_user_id() -> str | None:
    # The URL keeps a random session token (?session=...), so a page reload stays signed in
    # without putting the name itself in the URL, which would bypass the secret code.
    if "user_id" not in st.session_state:
        token = st.query_params.get("session", "")
        user_id = config.ACCOUNTS.session_user(token)
        st.session_state["user_id"] = user_id or ""
        st.session_state["session_token"] = token if user_id else ""
        if token and not user_id:
            st.query_params.pop("session", None)
    return st.session_state["user_id"] or None


def workspace() -> Path:
    """Logged-in users keep one folder across sessions; each anonymous session gets its own."""
    user_id = current_user_id()
    if user_id:
        return config.USERS_DIR / user_id
    session_id = st.session_state.setdefault("anonymous_session_id", uuid.uuid4().hex[:16])
    return config.SESSIONS_DIR / session_id


def save_render_state(result, scene_path: Path, summary: str,
                       quality: str, animate: bool, problem: str | None = None) -> None:
    st.session_state["last_scene_path"] = str(scene_path)
    st.session_state["last_image_path"] = str(result.image_path) if result.image_path else ""
    st.session_state["last_video_path"] = str(result.video_path) if result.video_path else ""
    st.session_state["last_render_log"] = result.log
    st.session_state["last_summary"] = summary
    st.session_state["last_quality"] = quality
    st.session_state["last_animate"] = animate
    # The text area owns session_state["problem"] once instantiated. Writing
    # that key during the same run raises StreamlitWidgetAlreadyInstantiatedError.
    # Persist the submitted value directly instead of mutating widget state.
    saved_problem = problem if problem is not None else st.session_state.get("problem", "")
    state_path = workspace() / "last_render.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({
        "problem": saved_problem,
        "scene_path": str(scene_path.resolve()),
        "image_path": str(result.image_path.resolve()) if result.image_path else "",
        "video_path": str(result.video_path.resolve()) if result.video_path else "",
        "summary": summary,
        "quality": quality,
        "animate": animate,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def restore_render_state() -> None:
    """Restore one coherent problem/scene/image bundle after a server restart."""
    if st.session_state.get("render_state_restored"):
        return
    st.session_state["render_state_restored"] = True
    try:
        saved = json.loads((workspace() / "last_render.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return
    scene_path = Path(str(saved.get("scene_path", "")))
    image_path = Path(str(saved.get("image_path", "")))
    if not scene_path.is_file() or not image_path.is_file():
        return
    st.session_state["problem"] = str(saved.get("problem", ""))
    st.session_state["last_scene_path"] = str(scene_path)
    st.session_state["last_image_path"] = str(image_path)
    st.session_state["last_video_path"] = str(saved.get("video_path", ""))
    st.session_state["last_summary"] = str(saved.get("summary", "Manim"))
    st.session_state["last_quality"] = str(saved.get("quality", "l"))
    st.session_state["last_animate"] = bool(saved.get("animate", False))


def open_history_entry(entry: HistoryEntry) -> None:
    # Runs as a button callback, i.e. before the problem text area exists in the next run.
    st.session_state["problem"] = entry.problem
    st.session_state["label_offsets"] = {}
    st.session_state["manual_edits"] = empty_manual_edits()
    st.session_state["last_scene_path"] = str(entry.scene_path)
    st.session_state["last_image_path"] = str(entry.image_path)
    st.session_state["last_video_path"] = ""
    st.session_state["last_render_log"] = ""
    st.session_state["last_summary"] = entry.summary
    st.session_state["last_quality"] = "l"
    st.session_state["last_animate"] = False
