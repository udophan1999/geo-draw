"""The "Chỉnh hình thủ công" panel: local re-renders without calling DeepSeek."""

from __future__ import annotations

import streamlit as st

from geo_draw.conversations import Message
from geo_draw.pipeline import render_error_summary
from geo_draw.renderer import render_scene
from geo_draw.scene_info import (
    empty_manual_edits, label_names, load_edits, save_edits, segment_names, suggest_point_name,
)

from streamlit_app import session


def manual_editor(message: Message, quality: str, animate: bool) -> None:
    """Edit the drawing of ``message``; a successful re-render replaces its image."""
    scene_path = message.scene_path
    names = label_names(scene_path)
    if not names:
        return
    # Edits are saved next to the scene so they survive reloads and keep accumulating.
    if st.session_state.get("edits_for") != message.id:
        offsets, edits = load_edits(scene_path)
        st.session_state["label_offsets"] = offsets
        st.session_state["manual_edits"] = edits
        st.session_state["edits_for"] = message.id
    offsets = st.session_state["label_offsets"]
    edits = st.session_state["manual_edits"]

    def rerender() -> None:
        with st.spinner("Đang cập nhật hình tại máy, không gọi DeepSeek..."):
            result = render_scene(
                scene_path, scene_path.parent / "media", quality=quality, animate=animate,
                label_offsets=offsets, manual_edits=edits,
            )
        if result.ok and result.image_path:
            save_edits(scene_path, offsets, edits)
            session.conversations().update_drawing(message.id, result.image_path,
                                                   result.video_path)
            st.rerun()
        st.error("Không thể cập nhật hình: " + render_error_summary(result.log))

    with st.expander("🛠️ Chỉnh hình thủ công", expanded=False):
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
            segments = segment_names(scene_path, edits)
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
                    default_name = suggest_point_name(names, edits, "H")
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
                    default_name = suggest_point_name(names, edits, "M")
                    name = st.text_input("Tên trung điểm", value=default_name, max_chars=1)
                    spec = {"type": "perpendicular_bisector", "segment": segment,
                            "name": name.upper()}
                else:
                    col1, col2 = st.columns(2)
                    apex = col1.selectbox("Đỉnh", names, key="median_apex")
                    opposite = col2.selectbox("Cạnh đối diện", segments, key="median_side")
                    default_name = suggest_point_name(names, edits, "M")
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
            edits.update(empty_manual_edits())
            rerender()
