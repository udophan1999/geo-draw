"""Username + password accounts and browser sessions (PostgreSQL, or SQLite locally)."""

from __future__ import annotations

import hashlib
import hmac
import math
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

from .db import Database, SqliteDatabase
from .history import user_id_for

MAX_FAILED_ATTEMPTS = 5
LOCK_SECONDS = 300
MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 64
USER = "user"
ADMIN = "admin"
ROLES = (USER, ADMIN)


def normalize_name(value: str) -> str:
    return " ".join(str(value).split())[:40]


def valid_password(password: str) -> bool:
    return MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)


_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
           user_id TEXT PRIMARY KEY,
           name TEXT NOT NULL,
           code_hash {BLOB} NOT NULL,  -- password hash; name kept for existing DBs
           salt {BLOB} NOT NULL,
           failed_attempts INTEGER NOT NULL DEFAULT 0,
           locked_until {FLOAT} NOT NULL DEFAULT 0,
           created_at {FLOAT} NOT NULL
       )""",
    """CREATE TABLE IF NOT EXISTS sessions (
           token TEXT PRIMARY KEY,
           user_id TEXT NOT NULL,
           created_at {FLOAT} NOT NULL
       )""",
]


# Columns added after the first release; older databases get them on open.
_ADDED_COLUMNS = {
    "users": [("role", f"TEXT NOT NULL DEFAULT '{USER}'"),
              ("disabled", "INTEGER NOT NULL DEFAULT 0"),
              ("daily_limit", "INTEGER"),  # NULL: the server's default limit
              ("last_login", "{FLOAT} NOT NULL DEFAULT 0")],
}
_USER_COLUMNS = "user_id, name, role, disabled, daily_limit, created_at, last_login"


@dataclass
class UserInfo:
    user_id: str
    name: str
    role: str
    disabled: bool
    daily_limit: int | None
    created_at: float
    last_login: float

    def __post_init__(self) -> None:
        self.disabled = bool(self.disabled)  # SQLite stores 0/1

    @property
    def is_admin(self) -> bool:
        return self.role == ADMIN


class AccountStore:
    """``db`` is the shared PostgreSQL database; without it, SQLite under ``root``."""

    def __init__(self, root: Path, db: Database | None = None):
        self.root = root
        self.db = db or SqliteDatabase(root / "accounts.sqlite3")

    def create_tables(self) -> None:
        self.db.ensure_schema("accounts", _SCHEMA, _ADDED_COLUMNS)

    def _connect(self):
        self.create_tables()
        return self.db.connect()

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
        except self.db.IntegrityError as exc:
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
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                (token, user_id, now),
            )
            connection.execute("UPDATE users SET last_login = ? WHERE user_id = ?", (now, user_id))
        return token

    def session_user(self, token: str) -> str | None:
        """The signed-in user of a session; a locked or deleted account has none."""
        if not token:
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT s.user_id FROM sessions s JOIN users u ON u.user_id = s.user_id "
                "WHERE s.token = ? AND u.disabled = 0", (token,)
            ).fetchone()
        return row[0] if row else None

    def end_session(self, token: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token = ?", (token,))

    # Administration ---------------------------------------------------------------------

    def get_user(self, user_id: str) -> UserInfo | None:
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT {_USER_COLUMNS} FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
        return UserInfo(*row) if row else None

    def list_users(self) -> list[UserInfo]:
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT {_USER_COLUMNS} FROM users ORDER BY created_at"
            ).fetchall()
        return [UserInfo(*row) for row in rows]

    def admin_count(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM users WHERE role = ? AND disabled = 0", (ADMIN,)
            ).fetchone()
        return row[0]

    def set_role(self, user_id: str, role: str) -> None:
        if role not in ROLES:
            raise ValueError(f"Vai trò không hợp lệ: {role}")
        self._update(user_id, "role = ?", role)

    def set_disabled(self, user_id: str, disabled: bool) -> None:
        """Lock or unlock an account; locking signs it out everywhere."""
        with self._connect() as connection:
            connection.execute("UPDATE users SET disabled = ? WHERE user_id = ?",
                               (int(disabled), user_id))
            if disabled:
                connection.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def set_daily_limit(self, user_id: str, limit: int | None) -> None:
        """A daily AI limit for this user; None goes back to the server default."""
        if limit is not None and limit < 0:
            raise ValueError("Hạn mức không được âm.")
        self._update(user_id, "daily_limit = ?", limit)

    def set_password(self, user_id: str, password: str) -> None:
        """Set a new password (an admin reset) and sign the user out everywhere."""
        if not valid_password(password):
            raise ValueError(
                f"Mật khẩu phải có từ {MIN_PASSWORD_LENGTH} đến {MAX_PASSWORD_LENGTH} ký tự."
            )
        salt = secrets.token_bytes(16)
        with self._connect() as connection:
            connection.execute(
                "UPDATE users SET code_hash = ?, salt = ?, failed_attempts = 0, locked_until = 0 "
                "WHERE user_id = ?", (_hash_password(password, salt), salt, user_id))
            connection.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def delete_user(self, user_id: str) -> None:
        """Remove the account and its sessions (its conversations are the caller's job)."""
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            connection.execute("DELETE FROM users WHERE user_id = ?", (user_id,))

    def ensure_admin(self, name: str, password: str) -> str | None:
        """Create the first admin (from ADMIN_USERNAME/ADMIN_PASSWORD) when there is none.

        An existing account with that name is promoted and keeps its password. Returns what
        was done, or None when an admin already exists.
        """
        if self.admin_count():
            return None
        name = normalize_name(name)
        user_id = self._user_id(name)
        if self.get_user(user_id) is None:
            user_id = self.create(name, password)
            done = f"Đã tạo tài khoản quản trị «{name}»."
        else:
            done = f"Đã cấp quyền quản trị cho tài khoản có sẵn «{name}» (giữ mật khẩu cũ)."
        self.set_role(user_id, ADMIN)
        self.set_disabled(user_id, False)
        return done

    def _update(self, user_id: str, assignment: str, value) -> None:
        with self._connect() as connection:
            connection.execute(f"UPDATE users SET {assignment} WHERE user_id = ?", (value, user_id))
