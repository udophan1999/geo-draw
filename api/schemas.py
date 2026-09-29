"""Request bodies and JSON shapes shared by the routers (and the web/mobile clients)."""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, Field

from geo_draw.conversations import Conversation, Message

MODELS = ("deepseek-v4-flash", "deepseek-v4-pro")


class Credentials(BaseModel):
    username: str = Field(max_length=40)
    password: str = Field(max_length=64)


class Settings(BaseModel):
    mode: Literal["ai", "parser"] = "ai"
    model: Literal["deepseek-v4-flash", "deepseek-v4-pro"] = "deepseek-v4-flash"
    quality: Literal["l", "m", "h"] = "l"
    animate: bool = False


class TitleUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class ManualEdits(BaseModel):
    label_offsets: dict[str, list[float]] = {}
    manual_edits: dict = {}


def _version(path) -> str:
    # Re-renders write a new file, so the path doubles as a cache-busting version.
    return hashlib.sha1(str(path).encode()).hexdigest()[:10]


def message_json(message: Message) -> dict:
    image = message.image_path if message.image_path and message.image_path.is_file() else None
    video = message.video_path if message.video_path and message.video_path.is_file() else None
    base = f"/api/messages/{message.id}"
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "text": message.text,
        "created_at": message.created_at,
        "image_url": f"{base}/image?v={_version(image)}" if image else None,
        "video_url": f"{base}/video?v={_version(video)}" if video else None,
        "has_drawing": message.has_drawing and image is not None,
        "has_log": bool(message.log),
    }


def conversation_json(conversation: Conversation) -> dict:
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }
