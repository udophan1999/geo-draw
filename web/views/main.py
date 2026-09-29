"""Main page: problem input (text or image) → DeepSeek/parser → Manim render → result."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from geo_draw.ai_codegen import (
    extract_problem_from_image,
    generate_manim_code,
    missing_reference_figure_points,
    settings_from_env,
)
from geo_draw.renderer import render_scene
from web import auth, config, session
from web.components.clipboard_image import CLIPBOARD_IMAGE, decode_clipboard_image
from web.components.manual_editor import manual_editor
from web.components.sidebar import DrawOptions, account_section, options_section
from web.components.zoomable_image import zoomable_image
from web.rendering import parser_scene, render_error_summary


def main_page(user_id: str | None) -> None:
    session.restore_render_state()
    _header(user_id)
    with st.sidebar:
        if user_id:
            account_section(user_id)
            st.divider()
        options = options_section(settings_from_env())

    st.subheader("Đề bài")
    _image_to_text(options)
    text = st.text_area(
        "Nội dung đề bài",
        value=st.session_state.get("problem", config.EXAMPLES["Tam giác + nhiều yêu cầu"]),
        height=160,
        key="problem",
    )
    if st.button("Vẽ hình", type="primary"):
        _draw(text, options, user_id)
    elif not _show_saved_drawing():
        st.info("Chọn DeepSeek AI cho đề có nhiều điểm, giao tuyến, tiếp tuyến, đường phụ hoặc ký hiệu.")


def _header(user_id: str | None) -> None:
    st.title("geo-draw")
    st.caption("Nhập văn bản hoặc tải ảnh đề hình học — DeepSeek đọc đề, tạo mã Manim và vẽ hình.")
    if user_id is None:
        notice, action = st.columns([5, 1], vertical_alignment="center")
        notice.info("Đăng nhập để lưu lại lịch sử hỏi đáp", icon="🔐")
        action.button("Đăng nhập", type="primary", width="stretch", on_click=auth.go_to_login)


def _selected_problem_image() -> tuple[bytes, str] | None:
    clipboard_state = st.session_state.get("clipboard_problem_image", {})
    clipboard_result = CLIPBOARD_IMAGE(
        key="clipboard_problem_image",
        data={"image": clipboard_state.get("image")},
        default={"image": None},
        on_image_change=lambda: None,
    )
    image = decode_clipboard_image(getattr(clipboard_result, "image", None))

    with st.expander("Hoặc chọn tệp ảnh"):
        uploaded = st.file_uploader(
            "Chọn ảnh đề bài",
            type=["png", "jpg", "jpeg", "webp", "gif"],
            max_upload_size=20,
            help="Phương án dự phòng nếu trình duyệt không cho phép dán clipboard.",
            label_visibility="collapsed",
        )
    if image is None and uploaded is not None:
        image = (uploaded.getvalue(), uploaded.type)
        st.image(uploaded, caption="Ảnh đề bài đã chọn", width=520)
    return image


def _image_to_text(options: DrawOptions) -> None:
    """Optional OCR step: fills the problem text area from a pasted or uploaded image."""
    image = _selected_problem_image()
    st.caption("Dán ảnh → bấm Đọc đề từ ảnh → kiểm tra văn bản → bấm Vẽ hình.")
    if image is not None and st.button("Đọc đề từ ảnh", type="secondary"):
        if not options.uses_ai:
            st.error("Hãy chọn DeepSeek AI để đọc nội dung từ ảnh.")
        elif not options.ai.api_key:
            st.error("Cần DeepSeek API key để đọc đề từ ảnh.")
        else:
            try:
                with st.spinner("DeepSeek đang đọc đề bài trong ảnh..."):
                    recognized = extract_problem_from_image(image[0], image[1], options.ai)
            except ValueError as exc:
                st.error(str(exc))
            else:
                # Set before the text area exists in the next run.
                st.session_state["problem"] = recognized
                st.session_state["ocr_success"] = True
                st.rerun()
    if st.session_state.pop("ocr_success", False):
        st.success("Đã đọc đề từ ảnh. Bạn hãy kiểm tra nội dung bên dưới trước khi vẽ.")


def _draw(text: str, options: DrawOptions, user_id: str | None) -> None:
    if not text.strip():
        st.error("Chưa có đề bài.")
        return
    if options.uses_ai:
        missing_points = missing_reference_figure_points(text)
        if missing_points:
            st.error(
                "Đề nhắc đến hình minh họa nhưng chưa nêu vị trí các điểm "
                + ", ".join(missing_points)
                + ". Hãy dán ảnh có đầy đủ hình vẽ hoặc bổ sung các quan hệ "
                "của những điểm này vào đề trước khi vẽ."
            )
            return

    st.session_state["label_offsets"] = {}
    st.session_state["manual_edits"] = session.empty_manual_edits()
    workspace = session.workspace()
    workspace.mkdir(parents=True, exist_ok=True)
    scene_path = workspace / "scene.py"
    media_dir = workspace / "media"

    def render():
        return render_scene(
            scene_path, media_dir, quality=options.quality, animate=options.animate,
            label_offsets=st.session_state["label_offsets"],
            manual_edits=st.session_state["manual_edits"],
        )

    if options.uses_ai:
        with st.spinner("DeepSeek đang phân tích đề và viết mã Manim..."):
            generated = generate_manim_code(text, options.ai, options.animate)
        if not generated.ok:
            st.error(generated.error)
            return
        scene_path.write_text(generated.code, encoding="utf-8")
        summary = f"DeepSeek AI · {options.ai.model}"
    else:
        scene_path, summary = parser_scene(text, options.animate, scene_path)

    with st.spinner("Manim đang render..."):
        result = render()

    if not result.ok and options.uses_ai:
        for repair_attempt in range(1, 4):
            with st.spinner(
                f"Bản vẽ chưa đạt — DeepSeek đang tự cân chỉnh lần {repair_attempt}/3..."
            ):
                previous_code = scene_path.read_text(encoding="utf-8")
                repair_context = (
                    result.log[-4500:]
                    + "\n\nPrevious module to improve:\n"
                    + previous_code[-9000:]
                )
                repaired = generate_manim_code(
                    text, options.ai, options.animate, repair_log=repair_context,
                )
            if not repaired.ok:
                break
            scene_path.write_text(repaired.code, encoding="utf-8")
            result = render()
            if result.ok:
                break

    if result.ok and result.image_path:
        session.save_render_state(result, scene_path, summary, options.quality, options.animate,
                                  problem=text)
        if user_id:
            config.HISTORY.add(user_id, text, summary, scene_path, result.image_path)
            st.toast("Đã lưu hình vào lịch sử hỏi đáp.")
    else:
        st.error("Manim render thất bại: " + render_error_summary(result.log))
    _show_drawing(scene_path, result.image_path if result.ok else None, result.video_path,
                  result.log, options.quality, options.animate)


def _show_saved_drawing() -> bool:
    """Show the drawing kept in session state (or the newest one in the workspace)."""
    image_path = Path(st.session_state.get("last_image_path", ""))
    scene_path = Path(st.session_state.get("last_scene_path", ""))
    if not image_path.is_file() or not scene_path.is_file():
        workspace = session.workspace()
        scene_path = workspace / "scene.py"
        media_dir = workspace / "media"
        candidates = list(media_dir.rglob("*.png")) if media_dir.exists() else []
        image_path = max(candidates, key=lambda path: path.stat().st_mtime) if candidates else Path("")
        if image_path.is_file() and scene_path.is_file():
            st.session_state.setdefault("label_offsets", {})
            st.session_state.setdefault("manual_edits", session.empty_manual_edits())
            st.session_state["last_image_path"] = str(image_path)
            st.session_state["last_scene_path"] = str(scene_path)
            st.session_state["last_summary"] = "Bản vẽ gần nhất · chỉnh tại máy"
            st.session_state["last_quality"] = "l"
            st.session_state["last_animate"] = False
    if not image_path.is_file() or not scene_path.is_file():
        return False
    video_path = Path(st.session_state.get("last_video_path", ""))
    _show_drawing(
        scene_path, image_path, video_path if video_path.is_file() else None,
        st.session_state.get("last_render_log", ""),
        st.session_state.get("last_quality", "l"),
        st.session_state.get("last_animate", False),
    )
    return True


def _show_drawing(scene_path: Path, image_path: Path | None, video_path: Path | None,
                  log: str, quality: str, animate: bool) -> None:
    if image_path:
        manual_editor(scene_path, quality, animate)
        zoomable_image(image_path, "Khung hình Manim")
    if video_path and video_path.exists():
        st.video(str(video_path))
    with st.expander("Mã Manim đã sinh"):
        st.code(scene_path.read_text(encoding="utf-8"), language="python")
    with st.expander("Log render"):
        st.text(log[-8000:])
