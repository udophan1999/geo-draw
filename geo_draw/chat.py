"""One chat turn, shared by every UI: optional OCR, save the messages, redraw.

The first user message of a conversation is the problem; later ones are extra requests.
Every turn redraws ``compose_problem`` of all user messages and passes the previous
drawing's scene as ``previous_code`` so DeepSeek keeps the layout.
"""

from __future__ import annotations

import mimetypes
from collections.abc import Callable

from .ai_codegen import AiSettings, extract_problem_from_image
from .conversations import ASSISTANT, USER, ConversationStore, Message, compose_problem
from .pipeline import draw

OCR = "ocr"

# on_event("progress", {"stage": ..., "label": ...}) or on_event("message", Message)
EventCallback = Callable[[str, object], None]


def run_turn(store: ConversationStore, owner: str, conversation_id: str, *, text: str,
             image: bytes | None = None, image_type: str | None = None,
             ai: AiSettings | None, quality: str = "l", animate: bool = False,
             on_event: EventCallback | None = None) -> list[Message]:
    """Handle one user message in an existing conversation; return the new messages.

    ``ai=None`` draws with the local parser (and cannot read images).
    """
    emit = on_event or (lambda kind, payload: None)
    history = store.messages(conversation_id)
    text = (text or "").strip()

    user_message_id, user_dir = store.new_message_dir(owner, conversation_id)
    image_path = None
    if image:
        suffix = mimetypes.guess_extension(image_type or "") or ".png"
        image_path = user_dir / f"problem{suffix}"
        image_path.write_bytes(image)

    def add(role: str, body: str, **files) -> Message:
        message = store.add_message(conversation_id, role, body, **files)
        emit("message", message)
        return message

    request, reply_prefix = text, ""
    if image_path:
        recognized, error = _read_image(image, image_type, ai, emit)
        if error:
            return [add(USER, text, message_id=user_message_id, image_path=image_path),
                    add(ASSISTANT, error)]
        request = recognized + (f"\n\n{text}" if text else "")
        reply_prefix = f"**Đề đọc được từ ảnh:**\n\n{recognized}\n\n"
        if not history:
            store.rename(owner, conversation_id, recognized)
    user_message = add(USER, request, message_id=user_message_id, image_path=image_path)

    requests = [message.text for message in history if message.role == USER] + [request]
    drawings = [message for message in history if message.has_drawing]
    previous_code = (drawings[-1].scene_path.read_text(encoding="utf-8")
                     if drawings and drawings[-1].scene_path.is_file() else None)
    reply_id, reply_dir = store.new_message_dir(owner, conversation_id)
    outcome = draw(
        compose_problem(requests), reply_dir, ai=ai, quality=quality, animate=animate,
        previous_code=previous_code,
        on_progress=lambda stage, label: emit("progress", {"stage": stage, "label": label}),
    )
    reply = add(ASSISTANT, reply_prefix + outcome.message, message_id=reply_id,
                image_path=outcome.image_path,
                scene_path=outcome.scene_path if outcome.ok else None,
                video_path=outcome.video_path, log=outcome.log)
    return [user_message, reply]


def _read_image(image: bytes, image_type: str | None, ai: AiSettings | None,
                emit: EventCallback) -> tuple[str, str]:
    """Return ``(recognized_text, error_message)``."""
    if ai is None:
        return "", "Đọc đề từ ảnh cần chế độ **DeepSeek AI**. Hãy đổi trong **Cài đặt**."
    emit("progress", {"stage": OCR, "label": "DeepSeek đang đọc đề bài trong ảnh..."})
    try:
        return extract_problem_from_image(image, image_type or "", ai), ""
    except ValueError as exc:
        return "", str(exc)
