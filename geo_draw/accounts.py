"""Username + password accounts and browser sessions, stored in SQLite."""

from __future__ import annotations

import hashlib
import hmac
import math
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .history import user_id_for

MAX_FAILED_ATTEMPTS = 5
LOCK_SECONDS = 300
MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 64


def normalize_name(value: str) -> str:
    return " ".join(str(value).split())[:40]


def valid_password(password: str) -> bool:
    return MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)


class AccountStore:
    def __init__(self, root: Path):
        self.root = root
        self.db_path = root / "accounts.sqlite3"

    @contextmanager
    def _connect(self):
        self.root.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.executescript(
            """CREATE TABLE IF NOT EXISTS users (
                   user_id TEXT PRIMARY KEY,
                   name TEXT NOT NULL,
                   code_hash BLOB NOT NULL,  -- password hash; name kept for existing DBs
                   salt BLOB NOT NULL,
                   failed_attempts INTEGER NOT NULL DEFAULT 0,
                   locked_until REAL NOT NULL DEFAULT 0,
                   created_at REAL NOT NULL
               );
               CREATE TABLE IF NOT EXISTS sessions (
                   token TEXT PRIMARY KEY,
                   user_id TEXT NOT NULL,
                   created_at REAL NOT NULL
               );"""
        )
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _user_id(name: str) -> str:
        # Names are unique ignoring case and extra spaces.
        return user_id_for(normalize_name(name).casefold())

    def name_exists(self, name: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM users WHERE user_id = ?", (self._user_id(name),)
            ).fetchone()
        return row is not None

    def suggest_names(self, name: str, count: int = 3) -> list[str]:
        base = normalize_name(name)[:36]
        suggestions = []
        number = 2
        while len(suggestions) < count:
            candidate = f"{base} {number}"
            if not self.name_exists(candidate):
                suggestions.append(candidate)
            number += 1
        return suggestions

    def create(self, name: str, password: str) -> str:
        name = normalize_name(name)
        if not name:
            raise ValueError("Tên không được để trống.")
        if not valid_password(password):
            raise ValueError(
                f"Mật khẩu phải có từ {MIN_PASSWORD_LENGTH} đến {MAX_PASSWORD_LENGTH} ký tự."
            )
        user_id = self._user_id(name)
        salt = secrets.token_bytes(16)
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO users (user_id, name, code_hash, salt, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (user_id, name, _hash_password(password, salt), salt, time.time()),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Tên đăng nhập «{name}» đã có người dùng.") from exc
        return user_id

    def locked_seconds(self, name: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT locked_until FROM users WHERE user_id = ?", (self._user_id(name),)
            ).fetchone()
        return math.ceil(row[0] - time.time()) if row and row[0] > time.time() else 0

    def verify(self, name: str, password: str) -> str | None:
        """Return the user id when the password matches; lock the name after repeated failures."""
        user_id = self._user_id(name)
        now = time.time()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT code_hash, salt, failed_attempts, locked_until FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                return None
            code_hash, salt, failed_attempts, locked_until = row
            if locked_until > now:
                return None
            if hmac.compare_digest(_hash_password(password, salt), code_hash):
                connection.execute(
                    "UPDATE users SET failed_attempts = 0, locked_until = 0 WHERE user_id = ?",
                    (user_id,),
                )
                return user_id
            failed_attempts += 1
            if failed_attempts >= MAX_FAILED_ATTEMPTS:
                connection.execute(
                    "UPDATE users SET failed_attempts = 0, locked_until = ? WHERE user_id = ?",
                    (now + LOCK_SECONDS, user_id),
                )
            else:
                connection.execute(
                    "UPDATE users SET failed_attempts = ? WHERE user_id = ?",
                    (failed_attempts, user_id),
                )
        return None

    def display_name(self, user_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT name FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
        return row[0] if row else None

    def start_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(24)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO sessions VALUES (?, ?, ?)", (token, user_id, time.time())
            )
        return token

    def session_user(self, token: str) -> str | None:
        if not token:
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT user_id FROM sessions WHERE token = ?", (token,)
            ).fetchone()
        return row[0] if row else None

    def end_session(self, token: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
