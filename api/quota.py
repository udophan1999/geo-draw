"""Daily limit on DeepSeek turns, since every AI turn is paid with the server's key."""

from __future__ import annotations

import time
from pathlib import Path

from geo_draw.db import Database, SqliteDatabase

_SCHEMA = ["""CREATE TABLE IF NOT EXISTS usage (
                  owner TEXT NOT NULL,
                  day TEXT NOT NULL,
                  count INTEGER NOT NULL DEFAULT 0,
                  PRIMARY KEY (owner, day)
              )"""]


def _today() -> str:
    return time.strftime("%Y-%m-%d")


class QuotaStore:
    """``db`` is the shared PostgreSQL database; without it, SQLite at ``db_path``."""

    def __init__(self, db_path: Path, db: Database | None = None):
        self.db = db or SqliteDatabase(db_path)

    def create_tables(self) -> None:
        self.db.ensure_schema("usage", _SCHEMA)

    def _connect(self):
        self.create_tables()
        return self.db.connect()

    def used(self, owner: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT count FROM usage WHERE owner = ? AND day = ?", (owner, _today())
            ).fetchone()
        return row[0] if row else 0

    def consume(self, owner: str, limit: int) -> bool:
        """Count one AI turn; return False (and count nothing) when the limit is reached."""
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO usage (owner, day, count) VALUES (?, ?, 0) ON CONFLICT DO NOTHING",
                (owner, _today()),
            )
            cursor = connection.execute(
                "UPDATE usage SET count = count + 1 WHERE owner = ? AND day = ? AND count < ?",
                (owner, _today(), limit),
            )
            return cursor.rowcount == 1
