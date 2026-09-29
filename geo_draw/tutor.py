"""One tutor turn in the ``chat`` channel: hints level by level, or the worked solution.

The first message of a conversation sets its ``problem`` (typed, or read from a photo).
Later messages are the student's answers and questions. Replies stream piece by piece
through ``on_event("delta", {"text": ...})`` and are saved when complete.
"""

from __future__ import annotations

import mimetypes
import re
import unicodedata
from collections.abc import Callable
from typing import Literal

from .ai_codegen import AiSettings, extract_problem_from_image, stream_chat
from .conversations import (
    ASSISTANT, CHAT, HINT, SOLUTION, USER, ConversationStore, Message,
)
from .tutor_prompts import FIGURE_NONE, build_system_prompt, clamp_level

ASK = "ask"          # a normal message (the problem, or an answer to the tutor)
DEEPER = "deeper"    # "Gợi ý sâu hơn": one hint level up
SHOW_SOLUTION = "solution"  # switch to the worked solution
BACK_TO_HINTS = "hint"      # switch back to hints
ACTIONS = (ASK, DEEPER, SHOW_SOLUTION, BACK_TO_HINTS)
HISTORY_LIMIT = 16  # recent chat messages sent to the model, as in MathLovers

DEFAULT_TEXT = {
    DEEPER: "Em vẫn chưa nghĩ ra, mình gợi ý sâu hơn một chút được không?",
    SHOW_SOLUTION: "Cho em xem lời giải chi tiết nhé.",
    BACK_TO_HINTS: "Mình quay lại gợi ý từng bước để em tự làm nhé.",
}

# on_event("progress", {...}) | ("delta", {"text"}) | ("message", Message)
# | ("conversation", Conversation)
EventCallback = Callable[[str, object], None]


def run_tutor_turn(store: ConversationStore, owner: str, conversation_id: str, *,
                   text: str = "", image: bytes | None = None, image_type: str | None = None,
                   action: str = ASK, ai: AiSettings,
                   figure: Callable[[], str] = lambda: FIGURE_NONE,
                   on_event: EventCallback | None = None) -> list[Message]:
    """Handle one chat message; return the saved user message and tutor reply.

    ``figure()`` tells the prompt whether a figure is shown, being drawn, or missing. It is
    called after the user message is saved, since that may start the automatic drawing.
    """
    emit = on_event or (lambda kind, payload: None)
    if action not in ACTIONS:
        raise ValueError(f"Unknown tutor action: {action}")
    conversation = store.get(owner, conversation_id)
    if conversation is None:
        raise ValueError("Conversation not found")
    history = store.messages(conversation_id, CHAT)
    problem = store.problem_of(conversation)
    text = (text or "").strip() or DEFAULT_TEXT.get(action, "")

    mode, level = conversation.mode, conversation.hint_level
    if action == DEEPER:
        mode, level = HINT, clamp_level(level + 1)
    elif action == SHOW_SOLUTION:
        mode = SOLUTION
    elif action == BACK_TO_HINTS:
        mode = HINT

    user_message_id, user_dir = store.new_message_dir(owner, conversation_id)
    image_path = None
    request = text
    if image:
        suffix = mimetypes.guess_extension(image_type or "") or ".png"
        image_path = user_dir / f"problem{suffix}"
        image_path.write_bytes(image)
        emit("progress", {"stage": "ocr", "label": "Đang đọc đề bài trong ảnh..."})
        try:
            recognized = extract_problem_from_image(image, image_type or "", ai)
        except ValueError as exc:
            return _save_pair(store, conversation_id, emit, text, image_path, user_message_id,
                              str(exc), mode, level)
        request = recognized + (f"\n\n{text}" if text else "")

    if not problem:
        # The first message is the problem itself.
        problem = request
        store.update(owner, conversation_id, problem=problem)
        store.rename(owner, conversation_id, problem)
    elif not conversation.problem:
        store.update(owner, conversation_id, problem=problem)  # older drawing-only chats

    meta = {"mode": mode, "hint_level": level, "action": action}
    user_message = store.add_message(conversation_id, USER, request, message_id=user_message_id,
                                     image_path=image_path, channel=CHAT, meta=meta)
    emit("message", user_message)

    model_messages = [{"role": "system",
                       "content": build_system_prompt(problem, mode, level, figure())}]
    for message in history[-HISTORY_LIMIT:]:
        if message.text:
            model_messages.append({"role": message.role, "content": message.text})
    model_messages.append({"role": "user", "content": _framed(request, problem, history, mode)})

    emit("progress", {"stage": "thinking",
                      "label": "Đang soạn lời giải..." if mode == SOLUTION else "Đang suy nghĩ..."})
    reply_text, reply_meta = "", dict(meta)
    solved = conversation.solved
    hidden = _ProgressTagFilter()
    try:
        for piece in stream_chat(ai, model_messages, max_tokens=6000 if mode == SOLUTION else 1500):
            reply_text += piece
            shown = hidden.feed(piece)
            if shown:
                emit("delta", {"text": shown})
        reply_text, reported_level, done = read_progress(reply_text)
        if not reply_text.strip():
            raise ValueError("AI không trả về nội dung. Hãy thử lại.")
        if mode == HINT:
            level = max(level, clamp_level(reported_level or level))
            solved = solved or done
        reply_meta = {**meta, "hint_level": level, "solved": solved}
    except ValueError as exc:
        reply_text, reply_meta = str(exc), {**meta, "error": True}
    reply = store.add_message(conversation_id, ASSISTANT, reply_text, channel=CHAT,
                              meta=reply_meta)
    emit("message", reply)
    if not reply_meta.get("error"):
        store.update(owner, conversation_id, mode=mode, hint_level=level, solved=solved)
    emit("conversation", store.get(owner, conversation_id))
    return [user_message, reply]


_PROGRESS_TAG = re.compile(r"\[\[\s*(?:bac\s*:\s*(\d+)|(xong))\s*\]\]", re.IGNORECASE)


def read_progress(text: str) -> tuple[str, int | None, bool]:
    """Split the tutor's progress tag off a reply: (text, reported level, solved)."""
    level, done = None, False
    for match in _PROGRESS_TAG.finditer(text):
        if match.group(1):
            level = int(match.group(1))
        else:
            done = True
    return _PROGRESS_TAG.sub("", text).rstrip(), level, done


class _ProgressTagFilter:
    """Hide the trailing progress tag from the streamed text (the tag comes last)."""

    def __init__(self) -> None:
        self._held = ""
        self._stopped = False

    def feed(self, piece: str) -> str:
        if self._stopped:
            return ""
        text = self._held + piece
        start = text.find("[[")
        if start >= 0:
            self._stopped = True
            return text[:start].rstrip()
        # A lone "[" at the end may be the start of a tag: hold it until the next piece.
        self._held = "[" if text.endswith("[") else ""
        return text[:-1] if self._held else text


def record_canned_reply(store: ConversationStore, conversation_id: str, text: str,
                        reply: str, on_event: EventCallback | None = None) -> list[Message]:
    """Save a chat exchange answered by the app itself (no AI call), e.g. "vẽ giúp mình"."""
    emit = on_event or (lambda kind, payload: None)
    meta = {"canned": True}
    user_message = store.add_message(conversation_id, USER, text, channel=CHAT, meta=meta)
    emit("message", user_message)
    answer = store.add_message(conversation_id, ASSISTANT, reply, channel=CHAT, meta=meta)
    emit("message", answer)
    return [user_message, answer]


def _framed(request: str, problem: str, history: list[Message], mode: str) -> str:
    """The first message restates the problem the way a student would ask for help."""
    if history or request != problem:
        return request
    ask = ("Cho em xem lời giải chi tiết nhé." if mode == SOLUTION
           else "Em chưa biết bắt đầu từ đâu, mình gợi ý giúp em nhé.")
    return f"Đề bài của em:\n{problem}\n\n{ask}"


def _save_pair(store, conversation_id, emit, text, image_path, user_message_id, error,
               mode, level) -> list[Message]:
    meta = {"mode": mode, "hint_level": level}
    user_message = store.add_message(conversation_id, USER, text, message_id=user_message_id,
                                     image_path=image_path, channel=CHAT, meta=meta)
    emit("message", user_message)
    reply = store.add_message(conversation_id, ASSISTANT, error, channel=CHAT,
                              meta={**meta, "error": True})
    emit("message", reply)
    return [user_message, reply]


# Geometry detection (decides whether a figure is drawn automatically) -----------------

# Named plane figures: a problem mentioning one is geometry.
_FIGURES = [
    "tam giac", "tu giac", "ngu giac", "luc giac", "da giac", "hinh vuong", "hinh chu nhat",
    "hinh thoi", "hinh binh hanh", "hinh thang", "duong tron", "nua duong tron",
]
# Geometric relations: geometry too, unless the problem is about functions or equations
# ("đồ thị song song với đường thẳng…").
_RELATIONS = [
    "tiep tuyen", "day cung", "duong kinh", "trung diem", "trung tuyen", "duong cao",
    "phan giac", "trung truc", "vuong goc", "song song", "doan thang", "noi tiep",
    "ngoai tiep", "tia",
]  # not "kẻ": without accents it is also "kể" (to list); it comes with other words anyway
_ALGEBRA = ["ham so", "do thi", "phuong trinh", "bat phuong trinh", "dao ham", "tich phan",
            "parabol", "he truc toa do", "oxy"]
# The figure pipeline draws plane figures; solids are left to the "Vẽ hình" button.
_SOLIDS = ["hinh chop", "lang tru", "hinh hop", "tu dien", "hinh non", "hinh tru", "mat cau",
           "khoi"]


def _plain(text: str) -> str:
    """Lowercase ASCII-ish Vietnamese ("Đường tròn" -> "duong tron") for keyword matching."""
    text = unicodedata.normalize("NFD", text.lower()).replace("đ", "d")
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def _mentions(plain: str, words: list[str]) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", plain) for word in words)


# A figure to draw names its points: "ABC", "AH", "tâm O", "điểm M".
_NAMED_POINTS = re.compile(r"\b[A-Z]{2,4}\b|\b(?:điểm|tâm|đỉnh|tại)\s+[A-Z]\b")


def is_geometry_problem(text: str) -> bool:
    """Whether a problem is plane geometry, so its figure should be drawn automatically.

    Word problems about a "mảnh vườn hình chữ nhật" mention a figure but name no points,
    so they are not drawn.
    """
    plain = _plain(text)
    if _mentions(plain, _SOLIDS) or not _NAMED_POINTS.search(text):
        return False
    if _mentions(plain, _FIGURES):
        return True
    return _mentions(plain, _RELATIONS) and not _mentions(plain, _ALGEBRA)


# Drawing requests typed in the chat ------------------------------------------------------

# The app's own replies to "vẽ giúp mình" (no AI call).
REPLY_DRAWING = ("Mình đang vẽ hình ở khung bên cạnh nhé (trên điện thoại, chọn mục **Hình vẽ** ở "
                 "trên). Trong lúc chờ, em thử nghĩ tiếp câu hỏi lúc nãy của mình xem sao?")
REPLY_SHOWN = ("Hình vẽ của bài đang ở khung bên cạnh (trên điện thoại, chọn mục **Hình vẽ** ở trên). "
               "Muốn thêm chi tiết thì em nhắn cụ thể, ví dụ “vẽ thêm đường cao AH”.")
REPLY_NOT_DRAWN = "Mình chưa vẽ được hình: {detail}"

GENERIC = "generic"    # "vẽ giúp mình", "nên vẽ hình trước": draw the figure, no tutor reply
SPECIFIC = "specific"  # "kẻ thêm đường cao AH": refine the figure and let the tutor answer

# Matched on accented lowercase text: without accents "vẽ" would also match "về".
_DRAW_VERB = re.compile(r"(?<!\w)(vẽ|kẻ|dựng)(?!\w)")
_GENERIC_ASK = re.compile(
    r"(?<!\w)vẽ\s+(?:giúp|hộ|dùm|giùm|cho|ra|đi|lại hình|hình|thử|được không)(?!\w)"
)
_OBJECTS = [
    "đường cao", "trung điểm", "trung tuyến", "phân giác", "trung trực", "đường tròn",
    "tiếp tuyến", "đường thẳng", "đoạn", "tia", "góc", "hình chiếu", "giao điểm",
    "song song", "vuông góc", "đường chéo", "bán kính", "đường kính",
]


def drawing_request(text: str) -> Literal["generic", "specific"] | None:
    """Whether a chat message asks the app to draw, and how specifically."""
    lower = unicodedata.normalize("NFC", text.lower())
    if not _DRAW_VERB.search(lower):
        return None
    if _NAMED_POINTS.search(text) or any(word in lower for word in _OBJECTS):
        return SPECIFIC
    return GENERIC if _GENERIC_ASK.search(lower) else None
