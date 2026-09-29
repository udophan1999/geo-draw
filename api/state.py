"""Server-wide configuration and stores, built once per app in ``create_app``."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from geo_draw.accounts import AccountStore
from geo_draw.ai_codegen import AiSettings, settings_from_env
from geo_draw.conversations import ConversationStore
from geo_draw.db import database_from_url
from geo_draw.history import HistoryStore, import_into_conversations

from .jobs import JobManager
from .quota import QuotaStore

ROOT = Path(__file__).resolve().parent.parent


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass
class AppState:
    """Everything the routers share. ``data_dir`` is ``generated/`` unless overridden."""

    data_dir: Path
    ai: AiSettings = field(default_factory=settings_from_env)
    daily_limit_user: int = field(default_factory=lambda: _int_env("GEO_DRAW_DAILY_LIMIT_USER", 100))
    daily_limit_guest: int = field(default_factory=lambda: _int_env("GEO_DRAW_DAILY_LIMIT_GUEST", 10))
    cookie_secure: bool = field(default_factory=lambda: os.environ.get("GEO_DRAW_COOKIE_SECURE") == "1")
    # PostgreSQL for accounts, conversations and usage; None keeps SQLite files in data_dir.
    # Files (photos, drawings) always stay in data_dir.
    database_url: str | None = field(default_factory=lambda: os.environ.get("DATABASE_URL") or None)
    workers: int = 2

    def __post_init__(self) -> None:
        self.users_dir = self.data_dir / "users"
        self.sessions_dir = self.data_dir / "sessions"
        self.db = database_from_url(self.database_url)
        self.accounts = AccountStore(self.users_dir, self.db)
        # Signed-in users share one store; each guest keeps files in their own folder.
        self.conversations = ConversationStore(self.users_dir, self.db)
        self.quota = QuotaStore(self.data_dir / "usage.sqlite3", self.db)
        self.jobs = JobManager(self.workers)
        # conversation id -> marker of the figure job drawing it right now
        self.figure_jobs: dict[str, str] = {}
        self._history = HistoryStore(self.users_dir)
        self._history_imported: set[str] = set()

    def import_history(self, user_id: str) -> None:
        """Bring a user's pre-chat drawings into their conversations, once per process."""
        if user_id not in self._history_imported:
            import_into_conversations(self._history, self.conversations, user_id)
            self._history_imported.add(user_id)

    @property
    def ai_available(self) -> bool:
        return bool(self.ai.api_key)

    def guest_store(self, guest_id: str) -> ConversationStore:
        return ConversationStore(self.sessions_dir / guest_id, self.db)

    def guest_owner(self, guest_id: str) -> str:
        """The owner column for a guest's conversations.

        With SQLite every guest has a database file of their own, so "guest" is enough. The
        PostgreSQL tables are shared, so there the owner must tell guests apart.
        """
        return f"guest-{guest_id}" if self.db else "guest"

    def close(self) -> None:
        self.jobs.shutdown()
        if self.db:
            self.db.close()
