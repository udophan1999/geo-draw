"""Chat turns (the math tutor) and figure turns (drawing), both followed over SSE.

- ``POST /api/messages``: a message to the tutor (the problem, an answer, or an action such
  as "Gợi ý sâu hơn"). The first message of a plane-geometry problem also starts a figure
  job, announced on the tutor's event stream as ``figure_job``.
- ``POST /api/conversations/{id}/figure``: draw the figure, or refine it with a request.
- ``GET /api/jobs/{id}/events``: ``progress``, ``delta`` (tutor text as it arrives),
  ``message`` (saved message JSON), ``conversation``, ``figure_job``, then ``done`` or
  ``failed`` (not ``error``, which EventSource reserves for connection problems).
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from geo_draw.ai_codegen import AiSettings
from geo_draw.chat import run_figure_turn
from geo_draw.conversations import CHAT, USER, Conversation, Message
from geo_draw.tutor import ACTIONS, ASK, is_geometry_problem, run_tutor_turn

from ..deps import Owner, app_state, get_owner, owned_conversation
from ..jobs import Job
from ..schemas import FigureRequest, conversation_json, message_json
from ..state import AppState
from .settings import load_settings

router = APIRouter(tags=["messages"])

IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
KEEPALIVE_SECONDS = 15


def _ai(state: AppState, model: str) -> AiSettings:
    return AiSettings(api_key=state.ai.api_key, model=model, base_url=state.ai.base_url,
                      vision_model=state.ai.vision_model)


def _consume_ai_turn(state: AppState, owner: Owner) -> None:
    limit = state.daily_limit_guest if owner.is_guest else state.daily_limit_user
    if not state.quota.consume(owner.identity, limit):
        hint = " Đăng nhập để có thêm lượt." if owner.is_guest else ""
        raise HTTPException(429, f"Bạn đã dùng hết {limit} lượt dùng AI hôm nay.{hint}")


def _event_payload(owner: Owner):
    """Turn core objects into the JSON the clients receive."""
    def convert(payload: object) -> object:
        if isinstance(payload, Message):
            return message_json(payload)
        if isinstance(payload, Conversation):
            return conversation_json(payload, owner.store.problem_of(payload))
        return payload
    return convert


def start_figure_job(state: AppState, owner: Owner, conversation: Conversation,
                     text: str = "") -> Job:
    """Start a drawing turn. Raises HTTPException when it cannot run (no problem, quota…)."""
    if not text and not owner.store.problem_of(conversation):
        raise HTTPException(422, "Chưa có đề bài để vẽ hình.")
    settings = load_settings(owner)
    ai = None
    if settings.mode == "ai":
        if not state.ai_available:
            raise HTTPException(503, "Máy chủ chưa cấu hình DeepSeek API key. "
                                     "Hãy dùng chế độ Parser trong Cài đặt.")
        _consume_ai_turn(state, owner)
        ai = _ai(state, settings.model)
    convert = _event_payload(owner)

    def work(push) -> None:
        run_figure_turn(owner.store, owner.store_owner, conversation.id, text=text, ai=ai,
                        quality=settings.quality, animate=settings.animate,
                        on_event=lambda kind, payload: push(kind, convert(payload)))

    return state.jobs.submit(owner.identity, work)


@router.post("/messages", status_code=202)
async def send_message(
    request: Request,
    text: str = Form(""),
    conversation_id: str | None = Form(None),
    action: str = Form(ASK),
    image: UploadFile | None = File(None),
    owner: Owner = Depends(get_owner),
) -> dict:
    """Start one tutor turn. Returns at once with the job to follow at ``/api/jobs/{id}/events``."""
    state = app_state(request)
    text = text.strip()
    if action not in ACTIONS:
        raise HTTPException(422, "Thao tác không hợp lệ.")
    image_bytes, image_type = None, None
    if image is not None and image.filename:
        image_type = (image.content_type or "").lower()
        if image_type not in IMAGE_TYPES:
            raise HTTPException(415, "Ảnh phải có định dạng PNG, JPG, WEBP hoặc GIF.")
        image_bytes = await image.read()
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "Ảnh lớn hơn 20 MB; hãy cắt gọn vùng chứa đề bài.")
    if action == ASK and not text and not image_bytes:
        raise HTTPException(422, "Hãy nhập đề bài hoặc đính kèm ảnh.")
    # Check ownership before counting quota, so a bad id never costs a turn.
    conversation = owned_conversation(owner, conversation_id) if conversation_id else None
    if conversation is None and action != ASK:
        raise HTTPException(422, "Hãy gửi đề bài trước.")
    if not state.ai_available:
        raise HTTPException(503, "Máy chủ chưa cấu hình DeepSeek API key nên chưa giải toán được.")
    _consume_ai_turn(state, owner)
    if conversation is None:
        conversation = owner.store.create(owner.store_owner, text or "Đề từ ảnh")
    first_turn = not owner.store.messages(conversation.id, CHAT)
    ai = _ai(state, load_settings(owner).model)
    convert = _event_payload(owner)

    def work(push) -> None:
        def on_event(kind: str, payload: object) -> None:
            push(kind, convert(payload))
            # Once the problem is known (typed or read from a photo), draw plane geometry.
            if (first_turn and kind == "message" and payload.role == USER
                    and is_geometry_problem(payload.text)):
                try:
                    figure = start_figure_job(state, owner, conversation)
                except HTTPException as exc:
                    push("figure_skipped", {"detail": exc.detail})
                else:
                    push("figure_job", {"job_id": figure.id})

        run_tutor_turn(owner.store, owner.store_owner, conversation.id, text=text,
                       image=image_bytes, image_type=image_type, action=action, ai=ai,
                       on_event=on_event)

    job = state.jobs.submit(owner.identity, work)
    return {"conversation": conversation_json(conversation), "job_id": job.id}


@router.post("/conversations/{conversation_id}/figure", status_code=202)
def draw_figure(conversation_id: str, body: FigureRequest, request: Request,
                owner: Owner = Depends(get_owner)) -> dict:
    """Draw the conversation's figure (empty ``text``) or refine it with a request."""
    conversation = owned_conversation(owner, conversation_id)
    job = start_figure_job(app_state(request), owner, conversation, body.text.strip())
    return {"job_id": job.id}


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str, request: Request, owner: Owner = Depends(get_owner)):
    """Server-sent events of a tutor or figure job (see the module docstring)."""
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
