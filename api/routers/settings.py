"""Drawing settings, saved to ``<workspace>/settings.json`` (no API key: the server's is used)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import ValidationError

from ..deps import Owner, get_owner
from ..schemas import Settings

router = APIRouter(prefix="/settings", tags=["settings"])
SETTINGS_FILE = "settings.json"
_LEGACY_MODES = {"DeepSeek AI": "ai", "Parser nhanh (không dùng API)": "parser"}


def load_settings(owner: Owner) -> Settings:
    try:
        data = json.loads((owner.workspace / SETTINGS_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Settings()
    if not isinstance(data, dict):
        return Settings()
    # Files written by the Streamlit app store the mode as its Vietnamese label.
    data["mode"] = _LEGACY_MODES.get(data.get("mode"), data.get("mode", "ai"))
    try:
        return Settings.model_validate({key: data[key] for key in Settings.model_fields
                                        if key in data})
    except ValidationError:
        return Settings()


@router.get("")
def read_settings(owner: Owner = Depends(get_owner)) -> Settings:
    return load_settings(owner)


@router.put("")
def write_settings(settings: Settings, owner: Owner = Depends(get_owner)) -> Settings:
    owner.workspace.mkdir(parents=True, exist_ok=True)
    (owner.workspace / SETTINGS_FILE).write_text(settings.model_dump_json(indent=2),
                                                 encoding="utf-8")
    return settings
