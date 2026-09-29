"""Daily limit on DeepSeek turns, since every AI turn is paid with the server's key."""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


def _today() -> str:
    return time.strftime("%Y-%m-%d")


class QuotaStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    @contextmanager
    def _connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.execute(
            """CREATE TABLE IF NOT EXISTS usage (
                   owner TEXT NOT NULL,
                   day TEXT NOT NULL,
                   count INTEGER NOT NULL DEFAULT 0,
                   PRIMARY KEY (owner, day)
               )"""
        )
        try:
            with connection:
                yield connection
        finally:
            connection.close()

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
                "INSERT OR IGNORE INTO usage (owner, day, count) VALUES (?, ?, 0)",
                (owner, _today()),
            )
            cursor = connection.execute(
                "UPDATE usage SET count = count + 1 WHERE owner = ? AND day = ? AND count < ?",
                (owner, _today(), limit),
            )
            return cursor.rowcount == 1
