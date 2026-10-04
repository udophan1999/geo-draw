"""One drawing turn in the ``figure`` channel of a conversation.

The figure is drawn from the conversation's problem plus every drawing request made so far
("vẽ thêm đường cao AH"…), composed by ``compose_problem``. The previous drawing's scene is
passed as ``previous_code`` so DeepSeek keeps the layout. Conversations from before the
tutor existed have no ``problem``: there the first figure request is the problem.
"""

from __future__ import annotations

from collections.abc import Callable

from .ai_codegen import AiSettings
from .conversations import ASSISTANT, FIGURE, USER, ConversationStore, Message, compose_problem
from .pipeline import draw

# on_event("progress", {"stage": ..., "label": ...}) or on_event("message", Message)
EventCallback = Callable[[str, object], None]


def run_figure_turn(store: ConversationStore, owner: str, conversation_id: str, *,
                    text: str = "", ai: AiSettings | None, quality: str = "l",
                    animate: bool = False,
                    on_event: EventCallback | None = None) -> list[Message]:
    """Draw (``text`` empty) or refine (``text`` = request) the figure; return new messages.

    ``ai=None`` draws with the local parser.
    """
    emit = on_event or (lambda kind, payload: None)
    conversation = store.get(owner, conversation_id)
    if conversation is None:
        raise ValueError("Conversation not found")
    history = store.messages(conversation_id, FIGURE)
    text = (text or "").strip()

    new_messages = []
    if text:
        request = store.add_message(conversation_id, USER, text, channel=FIGURE)
        emit("message", request)
        new_messages.append(request)

    requests = [message.text for message in history if message.role == USER] + (
        [text] if text else [])
    if conversation.problem:
        requests = [conversation.problem, *requests]
    drawings = [message for message in history if message.has_drawing]
    previous_code = (drawings[-1].scene_path.read_text(encoding="utf-8")
                     if drawings and drawings[-1].scene_path.is_file() else None)

    reply_id, reply_dir = store.new_message_dir(owner, conversation_id)
    outcome = draw(
        compose_problem(requests), reply_dir, ai=ai, quality=quality, animate=animate,
        previous_code=previous_code,
        on_progress=lambda stage, label: emit("progress", {"stage": stage, "label": label}),
    )
    reply = store.add_message(conversation_id, ASSISTANT, outcome.message, message_id=reply_id,
                              image_path=outcome.image_path,
                              scene_path=outcome.scene_path if outcome.ok else None,
                              video_path=outcome.video_path, log=outcome.log, channel=FIGURE)
    emit("message", reply)
    return [*new_messages, reply]
