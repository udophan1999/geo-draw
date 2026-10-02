"""Server-wide configuration and stores, built once per app in ``create_app``."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from geo_draw.accounts import AccountStore
from geo_draw.app_config import ConfigStore
from geo_draw.ai_codegen import AiSettings, settings_from_env
from geo_draw.conversations import ConversationStore
from geo_draw.db import database_from_url
from geo_draw.history import HistoryStore, import_into_conversations

from .jobs import JobManager
from .quota import QuotaStore

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger("mathmate")


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
    # Guests are only a cookie, and a script can drop it to get a fresh quota every time, so
    # guests also share a daily limit per IP address (a school network shares one IP: keep it
    # well above one guest's limit). Accounts are capped by the sign-ups per IP instead.
    daily_limit_guest_ip: int = field(default_factory=lambda: _int_env("GEO_DRAW_DAILY_LIMIT_GUEST_IP", 60))
    registrations_per_ip: int = field(default_factory=lambda: _int_env("GEO_DRAW_REGISTER_LIMIT_IP", 20))
    # Every AI turn on the server together, per day: the last guard on the API bill.
    # 0 turns the cap off.
    daily_limit_total: int = field(default_factory=lambda: _int_env("GEO_DRAW_DAILY_LIMIT_TOTAL", 2000))
    cookie_secure: bool = field(default_factory=lambda: os.environ.get("GEO_DRAW_COOKIE_SECURE") == "1")
    # PostgreSQL for accounts, conversations and usage; None keeps SQLite files in data_dir.
    # Files (photos, drawings) always stay in data_dir.
    database_url: str | None = field(default_factory=lambda: os.environ.get("DATABASE_URL") or None)
    # The first admin, created at startup when no admin exists yet (see ensure_admin).
    admin_username: str | None = field(default_factory=lambda: os.environ.get("ADMIN_USERNAME") or None)
    admin_password: str | None = field(default_factory=lambda: os.environ.get("ADMIN_PASSWORD") or None)
    workers: int = 2

    def __post_init__(self) -> None:
        self.users_dir = self.data_dir / "users"
        self.sessions_dir = self.data_dir / "sessions"
        self.db = database_from_url(self.database_url)
        self.accounts = AccountStore(self.users_dir, self.db)
        # Signed-in users share one store; each guest keeps files in their own folder.
        self.conversations = ConversationStore(self.users_dir, self.db)
        self.quota = QuotaStore(self.data_dir / "usage.sqlite3", self.db)
        self.config = ConfigStore(self.data_dir, self.db)
        self.jobs = JobManager(self.workers)
        # conversation id -> marker of the figure job drawing it right now
        self.figure_jobs: dict[str, str] = {}
        self._history = HistoryStore(self.users_dir)
        self._history_imported: set[str] = set()

    def startup(self) -> None:
        """Run when the server starts (not when the app object is built)."""
        self.create_first_admin()

    def create_first_admin(self) -> None:
        if not (self.admin_username and self.admin_password):
            if not self.accounts.admin_count():
                log.warning("Chưa có tài khoản quản trị: đặt ADMIN_USERNAME và ADMIN_PASSWORD "
                            "trong .env rồi khởi động lại.")
            return
        try:
            done = self.accounts.ensure_admin(self.admin_username, self.admin_password)
        except ValueError as exc:  # e.g. a password that is too short
            log.error("Không tạo được tài khoản quản trị: %s", exc)
            return
        if done:
            log.warning(done)

    def daily_limit(self, is_guest: bool, own_limit: int | None = None) -> int:
        """A user's own limit (set by an admin) wins over the server default."""
        if is_guest:
            return self.daily_limit_guest
        return self.daily_limit_user if own_limit is None else own_limit

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
