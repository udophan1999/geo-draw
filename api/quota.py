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


# Counters that are not a user or a guest start with "~" (the admin charts skip them).
TOTAL = "~total"


def client_counter(kind: str, ip: str) -> str:
    """A per-IP counter, e.g. ``~ai:203.0.113.5`` or ``~register:203.0.113.5``."""
    return f"~{kind}:{ip}"


class _Full(Exception):
    def __init__(self, owner: str):
        self.owner = owner


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

    def used_today(self) -> dict[str, int]:
        """Today's count for every owner that used the AI."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT owner, count FROM usage WHERE day = ?", (_today(),)
            ).fetchall()
        return dict(rows)

    def daily_since(self, first_day: str) -> list[tuple[str, str, int]]:
        """(owner, day, count) rows from ``first_day`` (YYYY-MM-DD) on."""
        with self._connect() as connection:
            return connection.execute(
                "SELECT owner, day, count FROM usage WHERE day >= ?", (first_day,)
            ).fetchall()

    def owner_days(self, owner: str) -> list[tuple[str, int]]:
        """(day, count) of every day ``owner`` used the AI."""
        with self._connect() as connection:
            return connection.execute(
                "SELECT day, count FROM usage WHERE owner = ? ORDER BY day", (owner,)
            ).fetchall()

    def consume(self, owner: str, limit: int) -> bool:
        """Count one AI turn; return False (and count nothing) when the limit is reached."""
        return self.consume_all([(owner, limit)]) is None

    def consume_all(self, counters: list[tuple[str, int]]) -> str | None:
        """Count one use on every ``(owner, limit)`` counter, all or nothing.

        Returns None when all were counted, else the first full counter's owner; then the
        transaction rolls back, so a full counter never uses up the others.
        """
        day = _today()
        try:
            with self._connect() as connection:
                for owner, limit in counters:
                    connection.execute(
                        "INSERT INTO usage (owner, day, count) VALUES (?, ?, 0) ON CONFLICT DO NOTHING",
                        (owner, day),
                    )
                    cursor = connection.execute(
                        "UPDATE usage SET count = count + 1 WHERE owner = ? AND day = ? AND count < ?",
                        (owner, day, limit),
                    )
                    if cursor.rowcount != 1:
                        raise _Full(owner)
        except _Full as full:
            return full.owner
        return None
