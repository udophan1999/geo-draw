"""Paths, shared stores and constants for the Streamlit app."""

from __future__ import annotations

import os
from pathlib import Path

from geo_draw.accounts import AccountStore
from geo_draw.ai_codegen import load_dotenv
from geo_draw.conversations import ConversationStore
from geo_draw.history import HistoryStore


# Repository root: web/config.py -> web/ -> repo.
ROOT = Path(__file__).resolve().parent.parent
# GEO_DRAW_DATA_DIR lets test runs use a temporary folder instead of the real data.
GENERATED = Path(os.environ.get("GEO_DRAW_DATA_DIR") or ROOT / "generated")
USERS_DIR = GENERATED / "users"
SESSIONS_DIR = GENERATED / "sessions"
HISTORY = HistoryStore(USERS_DIR)
ACCOUNTS = AccountStore(USERS_DIR)
# Signed-in users' chats; a guest's chats use a store in their session folder.
CONVERSATIONS = ConversationStore(USERS_DIR)
load_dotenv(ROOT / ".env")
