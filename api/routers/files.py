"""Files of a message (problem image, drawing, video, scene code, render log), owner-checked."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from ..deps import Owner, get_owner, owned_message

router = APIRouter(prefix="/messages/{message_id}", tags=["files"])
# The URL carries ?v=<version>, so a given URL always means the same file.
CACHE = {"Cache-Control": "private, max-age=31536000, immutable"}


def _file(path) -> FileResponse:
    if path is None or not path.is_file():
        raise HTTPException(404, "Không tìm thấy tệp.")
    return FileResponse(path, headers=CACHE)


@router.get("/image")
def image(message_id: str, owner: Owner = Depends(get_owner)) -> FileResponse:
    return _file(owned_message(owner, message_id).image_path)


@router.get("/video")
def video(message_id: str, owner: Owner = Depends(get_owner)) -> FileResponse:
    return _file(owned_message(owner, message_id).video_path)


@router.get("/scene", response_class=PlainTextResponse)
def scene(message_id: str, owner: Owner = Depends(get_owner)) -> str:
    path = owned_message(owner, message_id).scene_path
    if path is None or not path.is_file():
        raise HTTPException(404, "Tin nhắn này không có mã Manim.")
    return path.read_text(encoding="utf-8")


@router.get("/log", response_class=PlainTextResponse)
def log(message_id: str, owner: Owner = Depends(get_owner)) -> str:
    return owned_message(owner, message_id).log[-8000:]
