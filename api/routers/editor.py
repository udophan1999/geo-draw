"""Manual editor: read a drawing's names and saved edits, re-render it locally (no DeepSeek)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from geo_draw.conversations import Message
from geo_draw.pipeline import render_error_summary
from geo_draw.renderer import render_scene
from geo_draw.scene_info import (
    empty_manual_edits, label_names, load_edits, save_edits, segment_names,
)

from ..deps import Owner, get_owner, owned_message
from ..schemas import ManualEdits, message_json
from .settings import load_settings

router = APIRouter(prefix="/messages/{message_id}", tags=["editor"])


def _drawing(owner: Owner, message_id: str) -> Message:
    message = owned_message(owner, message_id)
    if not message.has_drawing or not message.scene_path.is_file():
        raise HTTPException(404, "Tin nhắn này không có hình để chỉnh.")
    return message


@router.get("/editor")
def editor_state(message_id: str, owner: Owner = Depends(get_owner)) -> dict:
    """Names the editor offers. ``labels`` is empty for parser scenes (nothing to edit)."""
    scene = _drawing(owner, message_id).scene_path
    offsets, edits = load_edits(scene)
    return {
        "labels": label_names(scene),
        "segments": segment_names(scene, edits),
        "label_offsets": offsets,
        "manual_edits": edits,
    }


@router.post("/render")
def rerender(message_id: str, body: ManualEdits, owner: Owner = Depends(get_owner)) -> dict:
    """Re-render with the given edits; on success they are saved and the image replaced."""
    message = _drawing(owner, message_id)
    edits = {**empty_manual_edits(), **body.manual_edits}
    settings = load_settings(owner)
    result = render_scene(message.scene_path, message.scene_path.parent / "media",
                          quality=settings.quality, animate=settings.animate,
                          label_offsets=body.label_offsets, manual_edits=edits)
    if not (result.ok and result.image_path):
        raise HTTPException(422, "Không thể cập nhật hình: " + render_error_summary(result.log))
    save_edits(message.scene_path, body.label_offsets, edits)
    owner.store.update_drawing(message.id, result.image_path, result.video_path)
    return message_json(owner.store.get_message(message.id))
