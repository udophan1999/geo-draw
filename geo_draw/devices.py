"""Phones that receive push notifications (APNs device tokens from the iOS app).

A device belongs to one owner at a time: the API's ``Owner.identity``, so a user id or
``guest:<guest id>``. Signing in on a phone registers its token again, which moves it to the
new owner. ``environment`` is ``sandbox`` for builds run from Xcode and ``production`` for
TestFlight and the App Store; APNs has a separate server for each.

Stored in the shared PostgreSQL database, or in SQLite under ``root``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from .db import Database, SqliteDatabase

IOS = "ios"
PLATFORMS = (IOS,)
SANDBOX, PRODUCTION = "sandbox", "production"
ENVIRONMENTS = (SANDBOX, PRODUCTION)

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS devices (
           token TEXT PRIMARY KEY,
           owner TEXT NOT NULL,
           platform TEXT NOT NULL,
           environment TEXT NOT NULL,
           updated_at {FLOAT} NOT NULL
       )""",
    "CREATE INDEX IF NOT EXISTS devices_owner ON devices (owner)",
]


@dataclass(frozen=True)
class Device:
    token: str
    owner: str
    platform: str
    environment: str


class DeviceStore:
    def __init__(self, root: Path, db: Database | None = None):
        self.db = db or SqliteDatabase(root / "devices.sqlite3")

    def create_tables(self) -> None:
        self.db.ensure_schema("devices", _SCHEMA)

    def _connect(self):
        self.create_tables()
        return self.db.connect()

    def register(self, owner: str, token: str, platform: str = IOS,
                 environment: str = PRODUCTION) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO devices (token, owner, platform, environment, updated_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (token) DO UPDATE SET owner = excluded.owner, "
                "platform = excluded.platform, environment = excluded.environment, "
                "updated_at = excluded.updated_at",
                (token, owner, platform, environment, time.time()))

    def remove(self, token: str, owner: str | None = None) -> None:
        """Forget a token; with ``owner``, only when it still belongs to that owner."""
        with self._connect() as connection:
            if owner is None:
                connection.execute("DELETE FROM devices WHERE token = ?", (token,))
            else:
                connection.execute("DELETE FROM devices WHERE token = ? AND owner = ?",
                                   (token, owner))

    def for_owner(self, owner: str) -> list[Device]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT token, owner, platform, environment FROM devices WHERE owner = ?",
                (owner,)).fetchall()
        return [Device(*row) for row in rows]

    def delete_owner(self, owner: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM devices WHERE owner = ?", (owner,))
