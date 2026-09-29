"""Dashboard (/dashboard): chat on the left, the latest drawing on the right.

The first user message of a conversation is the problem; later messages are extra
requests. Each turn redraws from ``compose_problem`` of all user messages, passing the
previous drawing's code so DeepSeek keeps the layout.
"""

from __future__ import annotations

import mimetypes

import streamlit as st

from geo_draw.ai_codegen import extract_problem_from_image
from geo_draw.conversations import ASSISTANT, USER, Conversation, Message, compose_problem
from web import config, session, settings, styles
from web.components.manual_editor import manual_editor
from web.components.sidebar import sidebar
from web.components.zoomable_image import zoomable_image
from web.drawing import draw

IMAGE_TYPES = ["png", "jpg", "jpeg", "webp", "gif"]
ASSISTANT_AVATAR = "📐"


def dashboard_page(user_id: str | None) -> None:
    styles.dashboard()
    sidebar(user_id)
    store = session.conversations()
    conversation_id = session.current_conversation_id()
    conversation = store.get(session.owner(), conversation_id) if conversation_id else None
    messages = store.messages(conversation.id) if conversation else []
    drawings = [message for message in messages
                if message.has_drawing and message.image_path.is_file()]
    wanted = st.session_state.get("viewing_message_id")
    shown = next((d for d in drawings if d.id == wanted), drawings[-1] if drawings else None)

    chat_column, drawing_column = st.columns([1, 1.2], gap="large")
    with chat_column:
        _chat(conversation, messages, shown)
    with drawing_column:
        _drawing_panel(drawings, shown)


# Chat ----------------------------------------------------------------------------------

def _chat(conversation: Conversation | None, messages: list[Message],
          shown: Message | None) -> None:
    history = st.container(height=640, border=False, key="chat_history")
    with history:
        if not messages:
            _welcome()
        for message in messages:
            _show_message(message, shown)

    submitted = st.chat_input(
        "Yêu cầu chỉnh hình, vd: vẽ thêm đường cao AH"
        if messages else "Nhập đề bài hoặc đính kèm ảnh đề…",
        key="chat_input", accept_file=True, file_type=IMAGE_TYPES, max_upload_size=20,
    )
    pending = st.session_state.pop("pending_prompt", None)
    if submitted is not None:
        text = (submitted.text or "").strip()
        image = submitted.files[0] if submitted.files else None
    elif pending:
        text, image = pending, None
    else:
        return
    if not text and image is None:
        return
    with history:
        _run_turn(conversation, messages, text, image)
    st.rerun()


def _welcome() -> None:
    st.markdown("#### Chào bạn! 👋")
    st.markdown(
        "Gửi một đề hình học phẳng — gõ trực tiếp hoặc bấm 📎 để đính kèm ảnh chụp đề. "
        "Sau khi có hình, bạn có thể nhắn thêm yêu cầu như *“vẽ thêm đường tròn ngoại tiếp”* "
        "để chỉnh tiếp."
    )
    st.caption("Thử một đề mẫu:")
    for name, problem in config.EXAMPLES.items():
        st.button(f"💡 {name}", key=f"example_{name}", width="stretch",
                  on_click=_queue_prompt, args=(problem,))


def _queue_prompt(text: str) -> None:
    st.session_state["pending_prompt"] = text


def _show_message(message: Message, shown: Message | None) -> None:
    if message.role == USER:
        with st.chat_message("user"):
            if message.image_path and message.image_path.is_file():
                st.image(str(message.image_path), width=260)
            if message.text:
                st.markdown(message.text)
        return
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        st.markdown(message.text)
        if message.has_drawing and message.image_path.is_file():
            st.image(str(message.image_path), width=220)
            if shown is None or message.id != shown.id:
                st.button("Xem hình này", key=f"view_{message.id}", type="tertiary",
                          on_click=session.view_message, args=(message.id,))


def _run_turn(conversation: Conversation | None, messages: list[Message],
              text: str, image) -> None:
    """Handle one submitted message: optional OCR, then a full redraw."""
    store, owner, options = session.conversations(), session.owner(), settings.current()
    if conversation is None:
        conversation = store.create(owner, text or "Đề từ ảnh")
        session.open_conversation(conversation.id)

    user_message_id, user_dir = store.new_message_dir(owner, conversation.id)
    image_path = None
    if image is not None:
        suffix = mimetypes.guess_extension(image.type or "") or ".png"
        image_path = user_dir / f"problem{suffix}"
        image_path.write_bytes(image.getvalue())

    with st.chat_message("user"):
        if image_path:
            st.image(str(image_path), width=260)
        if text:
            st.markdown(text)

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        request, reply_prefix = text, ""
        if image_path:
            recognized, error = _read_problem_image(image, options)
            if error:
                store.add_message(conversation.id, USER, text, message_id=user_message_id,
                                  image_path=image_path)
                store.add_message(conversation.id, ASSISTANT, error)
                return
            request = recognized + (f"\n\n{text}" if text else "")
            reply_prefix = f"**Đề đọc được từ ảnh:**\n\n{recognized}\n\n"
            st.markdown(reply_prefix)
            if not messages:
                store.rename(owner, conversation.id, recognized)
        store.add_message(conversation.id, USER, request, message_id=user_message_id,
                          image_path=image_path)

        requests = [message.text for message in messages if message.role == USER] + [request]
        drawings = [message for message in messages if message.has_drawing]
        previous_code = (drawings[-1].scene_path.read_text(encoding="utf-8")
                         if drawings and drawings[-1].scene_path.is_file() else None)
        reply_id, reply_dir = store.new_message_dir(owner, conversation.id)
        outcome = draw(compose_problem(requests), options, reply_dir, previous_code)
        store.add_message(
            conversation.id, ASSISTANT, reply_prefix + outcome.message, message_id=reply_id,
            image_path=outcome.image_path, scene_path=outcome.scene_path if outcome.ok else None,
            video_path=outcome.video_path, log=outcome.log,
        )
    st.session_state.pop("viewing_message_id", None)  # show the newest drawing
    session.reset_manual_edits()


def _read_problem_image(image, options: settings.DrawOptions) -> tuple[str, str]:
    """Return ``(recognized_text, error_message)``."""
    if not options.uses_ai:
        return "", "Đọc đề từ ảnh cần chế độ **DeepSeek AI**. Hãy đổi trong **Cài đặt**."
    if not options.ai.api_key:
        return "", "Cần DeepSeek API key để đọc đề từ ảnh. Mở **Cài đặt** ở cuối thanh bên để nhập key."
    try:
        with st.spinner("DeepSeek đang đọc đề bài trong ảnh..."):
            return extract_problem_from_image(image.getvalue(), image.type, options.ai), ""
    except ValueError as exc:
        return "", str(exc)


# Drawing panel ------------------------------------------------------------------------

def _drawing_panel(drawings: list[Message], shown: Message | None) -> None:
    if shown is None:
        with st.container(border=True, height=640, vertical_alignment="center",
                          horizontal_alignment="center"):
            st.markdown("<div style='text-align:center;opacity:0.6'>"
                        "<div style='font-size:3rem'>📐</div>"
                        "Hình vẽ sẽ hiện ở đây</div>", unsafe_allow_html=True)
        return

    number = drawings.index(shown) + 1
    label = "mới nhất" if shown is drawings[-1] else f"{number}/{len(drawings)}"
    zoomable_image(shown.image_path, f"Hình vẽ · phiên bản {label}")
    if shown is not drawings[-1]:
        st.button("↩ Về hình mới nhất", key="view_latest", type="tertiary",
                  on_click=session.view_message, args=(drawings[-1].id,))
    if shown.video_path and shown.video_path.is_file():
        st.video(str(shown.video_path))
    options = settings.current()
    manual_editor(shown, options.quality, options.animate)
    with st.expander("Mã Manim đã sinh"):
        st.code(shown.scene_path.read_text(encoding="utf-8"), language="python")
    if shown.log:
        with st.expander("Log render"):
            st.text(shown.log[-8000:])
