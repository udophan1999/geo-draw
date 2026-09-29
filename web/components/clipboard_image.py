"""Paste-an-image (Ctrl+V) input built as a Streamlit v2 component."""

from __future__ import annotations

import base64

import streamlit as st


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


def decode_clipboard_image(payload) -> tuple[bytes, str] | None:
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
