"""Send a chat message (text and/or a problem image) and follow its drawing job over SSE."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from geo_draw.ai_codegen import AiSettings
from geo_draw.chat import run_turn
from geo_draw.conversations import Message

from ..deps import Owner, app_state, get_owner, owned_conversation
from ..schemas import conversation_json, message_json
from .settings import load_settings

router = APIRouter(tags=["messages"])

IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
KEEPALIVE_SECONDS = 15


@router.post("/messages", status_code=202)
async def send_message(
    request: Request,
    text: str = Form(""),
    conversation_id: str | None = Form(None),
    image: UploadFile | None = File(None),
    owner: Owner = Depends(get_owner),
) -> dict:
    """Start one chat turn. Returns at once with the job to follow at ``/api/jobs/{id}/events``."""
    state = app_state(request)
    text = text.strip()
    image_bytes, image_type = None, None
    if image is not None and image.filename:
        image_type = (image.content_type or "").lower()
        if image_type not in IMAGE_TYPES:
            raise HTTPException(415, "Ảnh phải có định dạng PNG, JPG, WEBP hoặc GIF.")
        image_bytes = await image.read()
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "Ảnh lớn hơn 20 MB; hãy cắt gọn vùng chứa đề bài.")
    if not text and not image_bytes:
        raise HTTPException(422, "Hãy nhập đề bài hoặc đính kèm ảnh.")
    # Check ownership before counting quota, so a bad id never costs a turn.
    conversation = owned_conversation(owner, conversation_id) if conversation_id else None

    settings = load_settings(owner)
    ai: AiSettings | None = None
    if settings.mode == "ai":
        if not state.ai_available:
            raise HTTPException(503, "Máy chủ chưa cấu hình DeepSeek API key. "
                                     "Hãy dùng chế độ Parser trong Cài đặt.")
        limit = state.daily_limit_guest if owner.is_guest else state.daily_limit_user
        if not state.quota.consume(owner.identity, limit):
            hint = " Đăng nhập để có thêm lượt." if owner.is_guest else ""
            raise HTTPException(429, f"Bạn đã dùng hết {limit} lượt vẽ bằng AI hôm nay.{hint}")
        ai = AiSettings(api_key=state.ai.api_key, model=settings.model,
                        base_url=state.ai.base_url, vision_model=state.ai.vision_model)

    if conversation is None:
        conversation = owner.store.create(owner.store_owner, text or "Đề từ ảnh")

    def work(push) -> None:
        def on_event(kind: str, payload: object) -> None:
            push(kind, message_json(payload) if isinstance(payload, Message) else payload)

        run_turn(owner.store, owner.store_owner, conversation.id, text=text, image=image_bytes,
                 image_type=image_type, ai=ai, quality=settings.quality,
                 animate=settings.animate, on_event=on_event)

    job = state.jobs.submit(owner.identity, work)
    return {"conversation": conversation_json(conversation), "job_id": job.id}


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str, request: Request, owner: Owner = Depends(get_owner)):
    """Server-sent events: ``progress``, ``message`` (saved message JSON), then ``done`` or ``error``."""
    job = app_state(request).jobs.get(job_id, owner.identity)
    if job is None:
        raise HTTPException(404, "Không tìm thấy lượt vẽ.")

    async def stream():
        sent = 0
        while True:
            events, finished = await asyncio.to_thread(job.wait, sent, KEEPALIVE_SECONDS)
            if not events and not finished:
                yield ": keepalive\n\n"
                continue
            for kind, data in events:
                yield f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            sent += len(events)
            if finished and sent >= len(job.events):
                return
            if await request.is_disconnected():
                return  # the job keeps running and still saves its result

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
