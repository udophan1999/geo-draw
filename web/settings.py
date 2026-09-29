"""Drawing settings chosen in the "Cài đặt" dialog.

Kept in ``session_state["settings"]``. For signed-in users everything except the API key
is also saved to ``<workspace>/settings.json``; the key only lives in the session (or
comes from ``DEEPSEEK_API_KEY`` in ``.env``).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace

import streamlit as st

from geo_draw.ai_codegen import AiSettings, settings_from_env
from web import session

AI_MODE = "DeepSeek AI"
PARSER_MODE = "Parser nhanh (không dùng API)"
MODES = [AI_MODE, PARSER_MODE]
MODELS = ["deepseek-v4-flash", "deepseek-v4-pro"]
QUALITIES = ["l", "m", "h"]


@dataclass
class DrawOptions:
    mode: str
    api_key: str
    model: str
    animate: bool
    quality: str

    @property
    def uses_ai(self) -> bool:
        return self.mode == AI_MODE

    @property
    def ai(self) -> AiSettings:
        env = settings_from_env()
        return AiSettings(api_key=self.api_key.strip(), model=self.model,
                          base_url=env.base_url, vision_model=env.vision_model)


def _defaults() -> DrawOptions:
    env = settings_from_env()
    return DrawOptions(mode=AI_MODE, api_key=env.api_key,
                       model=env.model if env.model in MODELS else MODELS[0],
                       animate=False, quality="l")


def current() -> DrawOptions:
    if "settings" not in st.session_state:
        options = _defaults()
        saved = _load_saved()
        if saved:
            options = replace(options, **saved)
        st.session_state["settings"] = options
    return st.session_state["settings"]


def save(options: DrawOptions) -> None:
    st.session_state["settings"] = options
    if session.current_user_id():
        stored = asdict(options)
        stored.pop("api_key")  # never write the key to disk
        path = session.workspace() / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(stored, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_saved() -> dict:
    if not session.current_user_id():
        return {}
    try:
        data = json.loads((session.workspace() / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    allowed = {"mode": MODES, "model": MODELS, "quality": QUALITIES}
    saved = {key: value for key, value in data.items()
             if key in allowed and value in allowed[key]}
    if isinstance(data.get("animate"), bool):
        saved["animate"] = data["animate"]
    return saved
