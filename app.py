import base64
import json
import mimetypes
import re
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from geo_draw.ai_codegen import (
    AiSettings,
    extract_problem_from_image,
    generate_manim_code,
    load_dotenv,
    missing_reference_figure_points,
    settings_from_env,
)
from geo_draw.engine import build_figure
from geo_draw.geometry_knowledge import GEOMETRY_HELP_VI
from geo_draw.parser import parse_problem
from geo_draw.renderer import render_scene
from geo_draw.scene_builder import write_scene

ROOT = Path(__file__).resolve().parent
GENERATED = ROOT / "generated"
LAST_RENDER_STATE = GENERATED / "last_render.json"
load_dotenv(ROOT / ".env")

EXAMPLES = {
    "Tam giác vuông": "Cho tam giác ABC vuông tại A, AB = 3, AC = 4.",
    "Tam giác + nhiều yêu cầu": (
        "Cho tam giác ABC vuông tại A, AB = 4, AC = 6. Gọi M là trung điểm BC. "
        "Kẻ đường cao AH. Qua M kẻ đường thẳng song song với AB, cắt AC tại N. "
        "Vẽ đường tròn tâm M đi qua B."
    ),
    "Đường tròn + tiếp tuyến": (
        "Cho đường tròn tâm O bán kính 3 và điểm A nằm ngoài đường tròn. "
        "Từ A kẻ hai tiếp tuyến AB, AC với đường tròn, B và C là các tiếp điểm. Vẽ OA, OB, OC."
    ),
    "Hình vuông": "Cho hình vuông ABCD cạnh 4. Vẽ hai đường chéo AC và BD, đánh dấu giao điểm O.",
    "Các đường đặc biệt và góc": (
        "Cho tam giác ABC có AB = 5, AC = 6 và góc BAC = 60°. Gọi M là trung điểm BC; "
        "vẽ trung tuyến AM. Kẻ đường cao AH, phân giác AD và đường trung trực của BC. "
        "Đánh dấu các góc bằng nhau và các góc vuông."
    ),
}


CLIPBOARD_IMAGE = st.components.v2.component(
    "geo_draw_clipboard_image",
    html="""
      <div id="paste-zone" tabindex="0" role="button" aria-label="Dán ảnh đề bài">
        <div id="empty-state">
          <strong>📋 Click vào đây rồi nhấn Ctrl+V</strong>
          <span>Dán ảnh chụp hoặc ảnh đã copy vào vùng này</span>
        </div>
        <div id="preview-state" hidden>
          <img id="preview" alt="Ảnh đề bài từ clipboard" />
          <div><strong>Đã nhận ảnh từ clipboard</strong><span>Nhấn Ctrl+V lần nữa để thay ảnh</span></div>
          <button id="clear-image" type="button">Xóa ảnh</button>
        </div>
        <div id="paste-error" hidden></div>
      </div>
    """,
    css="""
      #paste-zone {
        box-sizing: border-box; width: 100%; min-height: 132px; padding: 18px;
        border: 2px dashed var(--st-border-color); border-radius: 12px;
        background: var(--st-secondary-background-color); cursor: pointer;
        display: flex; align-items: center; justify-content: center; outline: none;
      }
      #paste-zone:focus, #paste-zone:hover { border-color: var(--st-primary-color); }
      #empty-state { display: flex; flex-direction: column; gap: 6px; text-align: center; }
      #empty-state span, #preview-state span { color: color-mix(in srgb, var(--st-text-color) 65%, transparent); }
      #preview-state { width: 100%; align-items: center; gap: 14px; }
      #preview-state:not([hidden]) { display: flex; }
      #preview-state div { display: flex; flex: 1; flex-direction: column; gap: 4px; }
      #preview { width: 108px; height: 88px; border-radius: 8px; object-fit: contain; background: white; }
      #clear-image { padding: 7px 12px; border: 1px solid var(--st-border-color); border-radius: 8px; cursor: pointer; }
      #paste-error { margin-top: 8px; color: var(--st-red-text-color); }
    """,
    js="""
      export default function(component) {
        const { data, setStateValue, parentElement } = component;
        const zone = parentElement.querySelector('#paste-zone');
        const empty = parentElement.querySelector('#empty-state');
        const previewState = parentElement.querySelector('#preview-state');
        const preview = parentElement.querySelector('#preview');
        const clear = parentElement.querySelector('#clear-image');
        const error = parentElement.querySelector('#paste-error');
        const current = data?.image;

        if (current?.data_url) {
          preview.src = current.data_url;
          empty.hidden = true;
          previewState.hidden = false;
        } else {
          preview.removeAttribute('src');
          empty.hidden = false;
          previewState.hidden = true;
        }

        const showError = (message) => {
          error.textContent = message;
          error.hidden = false;
        };
        const handlePaste = (event) => {
          const items = Array.from(event.clipboardData?.items || []);
          const imageItem = items.find(item => item.type.startsWith('image/'));
          if (!imageItem) {
            showError('Clipboard chưa có ảnh. Hãy copy ảnh rồi thử Ctrl+V lại.');
            return;
          }
          event.preventDefault();
          const file = imageItem.getAsFile();
          if (!file) return;
          if (file.size > 20 * 1024 * 1024) {
            showError('Ảnh lớn hơn 20 MB. Hãy cắt gọn ảnh rồi thử lại.');
            return;
          }
          const reader = new FileReader();
          reader.onload = () => setStateValue('image', {
            data_url: reader.result,
            mime_type: file.type || 'image/png',
            name: file.name || 'clipboard-image.png',
            nonce: Date.now(),
          });
          reader.onerror = () => showError('Không đọc được ảnh trong clipboard.');
          reader.readAsDataURL(file);
        };
        zone.addEventListener('paste', handlePaste);
        zone.onclick = (event) => {
          if (event.target !== clear) zone.focus();
        };
        clear.onclick = (event) => {
          event.stopPropagation();
          setStateValue('image', null);
        };
        return () => zone.removeEventListener('paste', handlePaste);
      }
    """,
)


def _decode_clipboard_image(payload) -> tuple[bytes, str] | None:
    if not isinstance(payload, dict):
        return None
    data_url = payload.get("data_url", "")
    mime_type = payload.get("mime_type", "")
    if not isinstance(data_url, str) or not data_url.startswith("data:image/"):
        return None
    try:
        header, encoded = data_url.split(",", 1)
        image_bytes = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        return None
    if not mime_type and ";base64" in header:
        mime_type = header[5:].split(";", 1)[0]
    return image_bytes, mime_type


def _parser_scene(text: str, animate: bool) -> tuple[Path, str]:
    problem = parse_problem(text)
    figure = build_figure(problem)
    path = write_scene(figure, GENERATED / "scene.py", animate=animate)
    summary = f"Parser · hình {problem.figure} · điểm: {', '.join(sorted(figure.points))}"
    return path, summary


def _render_error_summary(log: str) -> str:
    known_errors = {
        "GEOMETRY_INVALID_SEGMENT": "Ký hiệu hình học nhận sai dữ liệu đoạn thẳng.",
        "GEOMETRY_PARALLEL_NO_SEGMENT": "Chưa truyền đoạn thẳng cần đánh dấu song song.",
        "GEOMETRY_LAYOUT_CROWDED": "Các điểm và đối tượng phụ đang quá sát nhau; cần đổi tỷ lệ hình.",
    }
    for code, message in known_errors.items():
        if code in log:
            return message
    lines = [line.strip() for line in log.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith(("ValueError:", "TypeError:", "ImportError:", "NameError:")):
            return line
    return lines[-1] if lines else "Không có thông tin lỗi từ Manim."


def _zoomable_image(path: Path, caption: str) -> None:
    """Show a contained image with wheel/button zoom and drag-to-pan."""
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    components.html(
        f"""
        <div class="viewport" id="viewport">
          <img id="drawing" alt="{caption}" src="data:{mime};base64,{payload}">
          <div class="controls">
            <button id="minus" title="Thu nhỏ">−</button>
            <button id="reset" title="Vừa khung">100%</button>
            <button id="plus" title="Phóng to">+</button>
          </div>
        </div>
        <style>
          html, body {{ margin: 0; background: transparent; overflow: hidden; }}
          .viewport {{
            position: relative; width: 100%; height: 560px; overflow: hidden;
            border-radius: 14px; background: #17172a; cursor: grab; user-select: none;
          }}
          .viewport.dragging {{ cursor: grabbing; }}
          #drawing {{
            position: absolute; inset: 0; margin: auto; max-width: 100%; max-height: 100%;
            width: auto; height: auto; object-fit: contain; transform-origin: center;
            pointer-events: none; will-change: transform;
          }}
          .controls {{ position: absolute; right: 12px; top: 12px; display: flex; gap: 6px; }}
          button {{
            min-width: 38px; height: 36px; padding: 0 10px; border: 0; border-radius: 9px;
            background: rgba(255,255,255,.92); color: #20202a; font: 600 15px sans-serif;
            cursor: pointer; box-shadow: 0 2px 10px rgba(0,0,0,.24);
          }}
        </style>
        <script>
          const viewport = document.getElementById('viewport');
          const image = document.getElementById('drawing');
          const reset = document.getElementById('reset');
          let scale = 1, x = 0, y = 0, dragging = false, lastX = 0, lastY = 0;
          const apply = () => {{
            image.style.transform = `translate(${{x}}px, ${{y}}px) scale(${{scale}})`;
            reset.textContent = `${{Math.round(scale * 100)}}%`;
          }};
          const zoom = delta => {{ scale = Math.min(5, Math.max(0.5, scale + delta)); apply(); }};
          document.getElementById('plus').onclick = () => zoom(0.25);
          document.getElementById('minus').onclick = () => zoom(-0.25);
          reset.onclick = () => {{ scale = 1; x = 0; y = 0; apply(); }};
          viewport.addEventListener('wheel', event => {{
            event.preventDefault(); zoom(event.deltaY < 0 ? 0.15 : -0.15);
          }}, {{ passive: false }});
          viewport.addEventListener('pointerdown', event => {{
            dragging = true; lastX = event.clientX; lastY = event.clientY;
            viewport.classList.add('dragging'); viewport.setPointerCapture(event.pointerId);
          }});
          viewport.addEventListener('pointermove', event => {{
            if (!dragging || scale <= 1) return;
            x += event.clientX - lastX; y += event.clientY - lastY;
            lastX = event.clientX; lastY = event.clientY; apply();
          }});
          viewport.addEventListener('pointerup', () => {{
            dragging = false; viewport.classList.remove('dragging');
          }});
        </script>
        """,
        height=570,
        scrolling=False,
    )
    st.caption(caption + " · Cuộn chuột hoặc dùng nút +/− để zoom; kéo ảnh để di chuyển.")


def _scene_label_names(scene_path: Path) -> list[str]:
    if not scene_path.exists():
        return []
    code = scene_path.read_text(encoding="utf-8")
    return sorted(set(re.findall(r'safe_point_label\([^,]+,\s*["\']([A-Z])["\']', code)))


def _scene_segment_names(scene_path: Path, edits: dict | None = None) -> list[str]:
    if not scene_path.exists():
        return []
    code = scene_path.read_text(encoding="utf-8")
    found = {
        "".join(sorted(match))
        for match in re.findall(r"\bLine\(\s*([A-Z])\s*,\s*([A-Z])", code)
    }
    found.update(
        "".join(sorted(value))
        for value in (edits or {}).get("added_segments", ())
        if isinstance(value, str) and len(value) == 2
    )
    return sorted(found)


def _suggest_point_name(names: list[str], edits: dict, preferred: str) -> str:
    occupied = set(names)
    occupied.update(
        str(item.get("name", ""))
        for item in edits.get("constructions", ())
        if isinstance(item, dict)
    )
    choices = preferred + "MNPKQRESTUVXYZ"
    return next((name for name in choices if name not in occupied), "")


def _save_render_state(result, scene_path: Path, summary: str,
                       quality: str, animate: bool, problem: str | None = None) -> None:
    st.session_state["last_scene_path"] = str(scene_path)
    st.session_state["last_image_path"] = str(result.image_path) if result.image_path else ""
    st.session_state["last_video_path"] = str(result.video_path) if result.video_path else ""
    st.session_state["last_render_log"] = result.log
    st.session_state["last_summary"] = summary
    st.session_state["last_quality"] = quality
    st.session_state["last_animate"] = animate
    # The text area owns session_state["problem"] once instantiated. Writing
    # that key during the same run raises StreamlitWidgetAlreadyInstantiatedError.
    # Persist the submitted value directly instead of mutating widget state.
    saved_problem = problem if problem is not None else st.session_state.get("problem", "")
    GENERATED.mkdir(parents=True, exist_ok=True)
    LAST_RENDER_STATE.write_text(json.dumps({
        "problem": saved_problem,
        "scene_path": str(scene_path.resolve()),
        "image_path": str(result.image_path.resolve()) if result.image_path else "",
        "video_path": str(result.video_path.resolve()) if result.video_path else "",
        "summary": summary,
        "quality": quality,
        "animate": animate,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def _restore_render_state() -> None:
    """Restore one coherent problem/scene/image bundle after a server restart."""
    if st.session_state.get("render_state_restored"):
        return
    st.session_state["render_state_restored"] = True
    try:
        saved = json.loads(LAST_RENDER_STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return
    scene_path = Path(str(saved.get("scene_path", "")))
    image_path = Path(str(saved.get("image_path", "")))
    if not scene_path.is_file() or not image_path.is_file():
        return
    st.session_state["problem"] = str(saved.get("problem", ""))
    st.session_state["last_scene_path"] = str(scene_path)
    st.session_state["last_image_path"] = str(image_path)
    st.session_state["last_video_path"] = str(saved.get("video_path", ""))
    st.session_state["last_summary"] = str(saved.get("summary", "Manim"))
    st.session_state["last_quality"] = str(saved.get("quality", "l"))
    st.session_state["last_animate"] = bool(saved.get("animate", False))


def _manual_editor(scene_path: Path, quality: str, animate: bool) -> None:
    names = _scene_label_names(scene_path)
    if not names:
        return
    offsets = st.session_state.setdefault("label_offsets", {})
    edits = st.session_state.setdefault("manual_edits", {
        "hidden_labels": [], "hidden_points": [], "hidden_segments": [],
        "added_segments": [], "segment_widths": {}, "constructions": [],
    })

    def rerender() -> None:
        with st.spinner("Đang cập nhật hình tại máy, không gọi DeepSeek..."):
            result = render_scene(
                scene_path, GENERATED / "media", quality=quality, animate=animate,
                label_offsets=offsets, manual_edits=edits,
            )
        if result.ok and result.image_path:
            _save_render_state(
                result, scene_path, st.session_state.get("last_summary", "Manim"),
                quality, animate,
            )
            st.rerun()
        st.error("Không thể cập nhật hình: " + _render_error_summary(result.log))

    with st.expander("🛠️ Chỉnh hình thủ công", expanded=True):
        st.caption(
            "Các thao tác ở đây chỉ render lại trên máy, không gửi yêu cầu mới tới DeepSeek. "
            "Tọa độ hình học gốc được giữ nguyên để không làm sai dữ kiện."
        )
        label_tab, point_tab, segment_tab, construct_tab = st.tabs(
            ["Tên điểm", "Điểm", "Đoạn thẳng", "Dựng hình"]
        )

        with label_tab:
            selected = st.selectbox("Tên điểm cần chỉnh", names, key="layout_selected_label")
            step = st.select_slider(
                "Bước dịch", options=[0.08, 0.12, 0.18, 0.25], value=0.12,
                format_func=lambda value: {
                    0.08: "Nhỏ", 0.12: "Vừa", 0.18: "Lớn", 0.25: "Rất lớn"
                }[value],
            )
            left, up, down, right, visibility, reset_one = st.columns(6)
            action = None
            if left.button("←", key="label_left", help="Dịch tên sang trái"):
                action = (-step, 0.0)
            if up.button("↑", key="label_up", help="Dịch tên lên trên"):
                action = (0.0, step)
            if down.button("↓", key="label_down", help="Dịch tên xuống dưới"):
                action = (0.0, -step)
            if right.button("→", key="label_right", help="Dịch tên sang phải"):
                action = (step, 0.0)
            hidden_labels = edits["hidden_labels"]
            toggle_label = visibility.button(
                "Hiện tên" if selected in hidden_labels else "Ẩn tên", key="label_visibility"
            )
            reset_selected = reset_one.button("Đặt lại", key="label_reset_one")
            if action:
                current = offsets.get(selected, [0.0, 0.0])
                offsets[selected] = [current[0] + action[0], current[1] + action[1]]
                rerender()
            if toggle_label:
                if selected in hidden_labels:
                    hidden_labels.remove(selected)
                else:
                    hidden_labels.append(selected)
                rerender()
            if reset_selected:
                offsets.pop(selected, None)
                if selected in hidden_labels:
                    hidden_labels.remove(selected)
                rerender()

        with point_tab:
            selected_point = st.selectbox("Điểm cần ẩn/hiện", names, key="manual_point")
            hidden_points = edits["hidden_points"]
            if st.button(
                "Hiện chấm điểm" if selected_point in hidden_points else "Ẩn chấm điểm",
                key="point_visibility",
            ):
                if selected_point in hidden_points:
                    hidden_points.remove(selected_point)
                else:
                    hidden_points.append(selected_point)
                rerender()
            st.caption("Ẩn chấm điểm không xóa các đường đang đi qua điểm đó.")

        with segment_tab:
            first_col, second_col = st.columns(2)
            first = first_col.selectbox("Điểm đầu", names, key="segment_first")
            second_options = [name for name in names if name != first]
            second = second_col.selectbox("Điểm cuối", second_options, key="segment_second")
            segment = "".join(sorted((first, second)))
            width = st.slider(
                "Độ đậm nét", min_value=1.0, max_value=6.0,
                value=float(edits["segment_widths"].get(segment, 2.0)), step=0.5,
                key=f"segment_width_{segment}",
            )
            add_col, hide_col, show_col, width_col = st.columns(4)
            if add_col.button("Thêm đoạn", key="segment_add"):
                if segment not in edits["added_segments"]:
                    edits["added_segments"].append(segment)
                if segment in edits["hidden_segments"]:
                    edits["hidden_segments"].remove(segment)
                edits["segment_widths"][segment] = width
                rerender()
            if hide_col.button("Ẩn đoạn", key="segment_hide"):
                if segment not in edits["hidden_segments"]:
                    edits["hidden_segments"].append(segment)
                rerender()
            if show_col.button("Hiện đoạn", key="segment_show"):
                if segment in edits["hidden_segments"]:
                    edits["hidden_segments"].remove(segment)
                rerender()
            if width_col.button("Áp dụng nét", key="segment_width_apply"):
                edits["segment_widths"][segment] = width
                rerender()

        with construct_tab:
            segments = _scene_segment_names(scene_path, edits)
            constructions = edits.setdefault("constructions", [])
            if not segments:
                st.info("Hình hiện tại chưa có đoạn thẳng để dùng làm cạnh tham chiếu.")
            else:
                tool = st.selectbox(
                    "Công cụ",
                    ["Hạ đường vuông góc", "Tia phân giác", "Đường trung trực", "Đường trung tuyến"],
                    key="construction_tool",
                )
                spec = None
                if tool == "Hạ đường vuông góc":
                    col1, col2 = st.columns(2)
                    point = col1.selectbox("Điểm đi qua", names, key="perp_point")
                    reference = col2.selectbox("Đường thẳng/cạnh", segments, key="perp_line")
                    default_name = _suggest_point_name(names, edits, "H")
                    name = st.text_input("Tên chân đường vuông góc", value=default_name, max_chars=1)
                    spec = {"type": "perpendicular", "point": point, "segment": reference,
                            "name": name.upper()}
                elif tool == "Tia phân giác":
                    col1, col2 = st.columns(2)
                    first_side = col1.selectbox("Cạnh thứ nhất", segments, key="bisector_side_1")
                    other_options = [value for value in segments if value != first_side]
                    second_side = col2.selectbox("Cạnh thứ hai", other_options, key="bisector_side_2")
                    spec = {"type": "angle_bisector", "side1": first_side, "side2": second_side}
                    if len(set(first_side) & set(second_side)) != 1:
                        st.warning("Hai cạnh được chọn phải có chung đúng một đỉnh của góc.")
                        spec = None
                elif tool == "Đường trung trực":
                    segment = st.selectbox("Đoạn thẳng", segments, key="bisector_segment")
                    default_name = _suggest_point_name(names, edits, "M")
                    name = st.text_input("Tên trung điểm", value=default_name, max_chars=1)
                    spec = {"type": "perpendicular_bisector", "segment": segment,
                            "name": name.upper()}
                else:
                    col1, col2 = st.columns(2)
                    apex = col1.selectbox("Đỉnh", names, key="median_apex")
                    opposite = col2.selectbox("Cạnh đối diện", segments, key="median_side")
                    default_name = _suggest_point_name(names, edits, "M")
                    name = st.text_input("Tên trung điểm cạnh", value=default_name, max_chars=1)
                    spec = {"type": "median", "point": apex, "segment": opposite,
                            "name": name.upper()}
                    if apex in opposite:
                        st.warning("Cạnh đối diện không được chứa đỉnh đã chọn.")
                        spec = None

                add_col, undo_col = st.columns(2)
                if add_col.button("Dựng đối tượng", type="primary", key="construction_add"):
                    new_name = (spec or {}).get("name", "")
                    used_names = set(names) | {
                        item.get("name", "") for item in constructions if isinstance(item, dict)
                    }
                    if spec is None:
                        st.error("Lựa chọn chưa tạo thành một phép dựng hợp lệ.")
                    elif new_name and (len(new_name) != 1 or not new_name.isalpha()):
                        st.error("Tên điểm mới phải là một chữ cái.")
                    elif new_name and new_name in used_names:
                        st.error(f"Tên điểm {new_name} đã được sử dụng.")
                    elif spec not in constructions:
                        constructions.append(spec)
                        rerender()
                if undo_col.button("Xóa thao tác cuối", key="construction_undo",
                                   disabled=not constructions):
                    constructions.pop()
                    rerender()
                if constructions:
                    st.caption(f"Đã thêm {len(constructions)} phép dựng thủ công.")

        if st.button("Khôi phục toàn bộ chỉnh sửa", key="manual_reset_all"):
            offsets.clear()
            edits.clear()
            edits.update({
                "hidden_labels": [], "hidden_points": [], "hidden_segments": [],
                "added_segments": [], "segment_widths": {}, "constructions": [],
            })
            rerender()


def _display_saved_render() -> bool:
    image_path = Path(st.session_state.get("last_image_path", ""))
    scene_path = Path(st.session_state.get("last_scene_path", ""))
    if not image_path.is_file() or not scene_path.is_file():
        scene_path = GENERATED / "scene.py"
        candidates = list((GENERATED / "media").rglob("*.png")) if (GENERATED / "media").exists() else []
        image_path = max(candidates, key=lambda path: path.stat().st_mtime) if candidates else Path("")
        if image_path.is_file() and scene_path.is_file():
            st.session_state.setdefault("label_offsets", {})
            st.session_state.setdefault("manual_edits", {
                "hidden_labels": [], "hidden_points": [], "hidden_segments": [],
                "added_segments": [], "segment_widths": {}, "constructions": [],
            })
            st.session_state["last_image_path"] = str(image_path)
            st.session_state["last_scene_path"] = str(scene_path)
            st.session_state["last_summary"] = "Bản vẽ gần nhất · chỉnh tại máy"
            st.session_state["last_quality"] = "l"
            st.session_state["last_animate"] = False
    if not image_path.is_file() or not scene_path.is_file():
        return False
    _manual_editor(
        scene_path,
        st.session_state.get("last_quality", "l"),
        st.session_state.get("last_animate", False),
    )
    _zoomable_image(image_path, "Khung hình Manim")
    video_path = Path(st.session_state.get("last_video_path", ""))
    if video_path.is_file():
        st.video(str(video_path))
    with st.expander("Mã Manim đã sinh"):
        st.code(scene_path.read_text(encoding="utf-8"), language="python")
    with st.expander("Log render"):
        st.text(st.session_state.get("last_render_log", "")[-8000:])
    return True


def main() -> None:
    st.set_page_config(page_title="geo-draw", layout="wide")
    _restore_render_state()
    st.title("geo-draw")
    st.caption("Nhập văn bản hoặc tải ảnh đề hình học — DeepSeek đọc đề, tạo mã Manim và vẽ hình.")

    env = settings_from_env()
    with st.sidebar:
        st.header("Tùy chọn")
        mode = st.radio(
            "Cách dựng hình",
            ["DeepSeek AI", "Parser nhanh (không dùng API)"],
            help="AI phù hợp đề phức tạp; parser nhanh chỉ hiểu các mẫu cơ bản.",
        )
        api_key = ""
        model = env.model
        if mode == "DeepSeek AI":
            api_key = st.text_input(
                "DeepSeek API key",
                value=env.api_key,
                type="password",
                help="Key chỉ dùng cho yêu cầu hiện tại và không được ghi vào mã hoặc log.",
            )
            model = st.selectbox(
                "Mô hình DeepSeek",
                ["deepseek-v4-flash", "deepseek-v4-pro"],
                index=1 if env.model == "deepseek-v4-pro" else 0,
            )
        example = st.selectbox("Đề mẫu", list(EXAMPLES))
        if st.button("Dùng đề mẫu"):
            st.session_state["problem"] = EXAMPLES[example]
        animate = st.checkbox("Xuất video hoạt hình", value=False)
        quality = st.selectbox("Chất lượng Manim", ["l", "m", "h"], index=0)
        st.caption("Chất lượng l nhanh nhất. Video cần FFmpeg; ảnh tĩnh chỉ cần Manim.")
        with st.expander("Quy ước hình học THCS"):
            st.markdown(GEOMETRY_HELP_VI)

    st.subheader("Đề bài")
    clipboard_state = st.session_state.get("clipboard_problem_image", {})
    clipboard_result = CLIPBOARD_IMAGE(
        key="clipboard_problem_image",
        data={"image": clipboard_state.get("image")},
        default={"image": None},
        on_image_change=lambda: None,
    )
    clipboard_image = _decode_clipboard_image(getattr(clipboard_result, "image", None))

    uploaded_problem = None
    with st.expander("Hoặc chọn tệp ảnh"):
        uploaded_problem = st.file_uploader(
            "Chọn ảnh đề bài",
            type=["png", "jpg", "jpeg", "webp", "gif"],
            max_upload_size=20,
            help="Phương án dự phòng nếu trình duyệt không cho phép dán clipboard.",
            label_visibility="collapsed",
        )

    selected_image = clipboard_image
    if selected_image is None and uploaded_problem is not None:
        selected_image = (uploaded_problem.getvalue(), uploaded_problem.type)
        st.image(uploaded_problem, caption="Ảnh đề bài đã chọn", width=520)

    st.caption("Dán ảnh → bấm Đọc đề từ ảnh → kiểm tra văn bản → bấm Vẽ hình.")
    if selected_image is not None:
        if st.button("Đọc đề từ ảnh", type="secondary"):
            if mode != "DeepSeek AI":
                st.error("Hãy chọn DeepSeek AI để đọc nội dung từ ảnh.")
            elif not api_key.strip():
                st.error("Cần DeepSeek API key để đọc đề từ ảnh.")
            else:
                vision_settings = AiSettings(
                    api_key=api_key.strip(),
                    model=model,
                    base_url=env.base_url,
                    vision_model=env.vision_model,
                )
                try:
                    with st.spinner("DeepSeek đang đọc đề bài trong ảnh..."):
                        recognized = extract_problem_from_image(
                            selected_image[0],
                            selected_image[1],
                            vision_settings,
                        )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state["problem"] = recognized
                    st.session_state["ocr_success"] = True
                    st.rerun()

    if st.session_state.pop("ocr_success", False):
        st.success("Đã đọc đề từ ảnh. Bạn hãy kiểm tra nội dung bên dưới trước khi vẽ.")

    text = st.text_area(
        "Nội dung đề bài",
        value=st.session_state.get("problem", EXAMPLES["Tam giác + nhiều yêu cầu"]),
        height=160,
        key="problem",
    )
    draw = st.button("Vẽ hình", type="primary")

    if not draw:
        if not _display_saved_render():
            st.info("Chọn DeepSeek AI cho đề có nhiều điểm, giao tuyến, tiếp tuyến, đường phụ hoặc ký hiệu.")
        return
    if not text.strip():
        st.error("Chưa có đề bài.")
        return
    if mode == "DeepSeek AI":
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
    st.session_state["manual_edits"] = {
        "hidden_labels": [], "hidden_points": [], "hidden_segments": [],
        "added_segments": [], "segment_widths": {}, "constructions": [],
    }

    scene_path: Path
    summary: str
    if mode == "DeepSeek AI":
        settings = AiSettings(
            api_key=api_key.strip(), model=model, base_url=env.base_url,
            vision_model=env.vision_model,
        )
        with st.spinner("DeepSeek đang phân tích đề và viết mã Manim..."):
            generated = generate_manim_code(text, settings, animate)
        if not generated.ok:
            st.error(generated.error)
            return
        GENERATED.mkdir(parents=True, exist_ok=True)
        scene_path = GENERATED / "scene.py"
        scene_path.write_text(generated.code, encoding="utf-8")
        summary = f"DeepSeek AI · {model}"
    else:
        scene_path, summary = _parser_scene(text, animate)

    with st.spinner("Manim đang render..."):
        result = render_scene(
            scene_path, GENERATED / "media", quality=quality, animate=animate,
            label_offsets=st.session_state["label_offsets"],
            manual_edits=st.session_state["manual_edits"],
        )

    if not result.ok and mode == "DeepSeek AI":
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
                    text, settings, animate, repair_log=repair_context,
                )
            if not repaired.ok:
                break
            scene_path.write_text(repaired.code, encoding="utf-8")
            result = render_scene(
                scene_path, GENERATED / "media", quality=quality, animate=animate,
                label_offsets=st.session_state["label_offsets"],
                manual_edits=st.session_state["manual_edits"],
            )
            if result.ok:
                break

    if result.ok and result.image_path:
        _save_render_state(result, scene_path, summary, quality, animate, problem=text)
        _manual_editor(scene_path, quality, animate)
        _zoomable_image(result.image_path, "Khung hình Manim")
    else:
        st.error("Manim render thất bại: " + _render_error_summary(result.log))

    if result.video_path and result.video_path.exists():
        st.video(str(result.video_path))
    with st.expander("Mã Manim đã sinh"):
        st.code(scene_path.read_text(encoding="utf-8"), language="python")
    with st.expander("Log render"):
        st.text(result.log[-8000:])


if __name__ == "__main__":
    main()
