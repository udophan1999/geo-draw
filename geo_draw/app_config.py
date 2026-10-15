"""Settings an admin changes at runtime (for now, the tutor's system prompts).

Stored as key/value rows in the shared PostgreSQL database, or in SQLite under ``root``.
A missing key means "use the built-in default".
"""

from __future__ import annotations

import time
from pathlib import Path

from .db import Database, SqliteDatabase

_SCHEMA = ["""CREATE TABLE IF NOT EXISTS app_config (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL,
                  updated_at {FLOAT} NOT NULL,
                  updated_by TEXT NOT NULL DEFAULT ''
              )"""]


class ConfigStore:
    def __init__(self, root: Path, db: Database | None = None):
        self.db = db or SqliteDatabase(root / "config.sqlite3")

    def create_tables(self) -> None:
        self.db.ensure_schema("app_config", _SCHEMA)

    def _connect(self):
        self.create_tables()
        return self.db.connect()

    def all(self) -> dict[str, tuple[str, float, str]]:
        """key -> (value, updated_at, updated_by)."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT key, value, updated_at, updated_by FROM app_config").fetchall()
        return {key: (value, updated_at, by) for key, value, updated_at, by in rows}

    def values(self) -> dict[str, str]:
        return {key: value for key, (value, _, _) in self.all().items()}

    def set(self, key: str, value: str, updated_by: str = "") -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO app_config (key, value, updated_at, updated_by) VALUES (?, ?, ?, ?) "
                "ON CONFLICT (key) DO UPDATE SET value = excluded.value, "
                "updated_at = excluded.updated_at, updated_by = excluded.updated_by",
                (key, value, time.time(), updated_by))

    def delete(self, key: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM app_config WHERE key = ?", (key,))
