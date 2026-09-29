"""Image viewer with wheel/button zoom and drag-to-pan."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


def zoomable_image(path: Path, caption: str) -> None:
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
