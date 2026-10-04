"""Copy the SQLite data of a data folder into the PostgreSQL database in DATABASE_URL.

    DATABASE_URL=postgresql://… python -m api.migrate_sqlite generated

In Docker, copy the old data folder into the volume first, then run it inside the container
(``docker compose run --rm app python -m api.migrate_sqlite /data``).

Copies accounts and login sessions, every conversation and message (users and guests), and
today's usage. Photos and drawings stay files in the data folder; their paths are rewritten
relative to it, so they resolve wherever the folder now lives. Running it again only adds
what is missing.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

from geo_draw.accounts import AccountStore
from geo_draw.conversations import ConversationStore
from geo_draw.db import PostgresDatabase, database_from_url

from .quota import QuotaStore


def _rows(path: Path, query: str) -> list[tuple]:
    if not path.is_file():
        return []
    connection = sqlite3.connect(path)
    try:
        return connection.execute(query).fetchall()
    except sqlite3.OperationalError:  # the table does not exist in this file
        return []
    finally:
        connection.close()


def _relative(path: str | None, owner: str) -> str | None:
    """Files live at ``<root>/<owner>/…``: keep the part from ``<owner>/`` on."""
    if not path or not Path(path).is_absolute():
        return path
    marker = f"/{owner}/"
    index = path.rfind(marker)
    return path[index + 1:] if index >= 0 else path


def _copy_conversations(db: PostgresDatabase, source: Path, owner_for) -> tuple[int, int]:
    """``owner_for(old_owner)`` gives the owner in PostgreSQL (guests become unique)."""
    conversations = _rows(source, "SELECT id, owner, title, created_at, updated_at, problem, mode, "
                                  "hint_level, solved FROM conversations")
    if not conversations:
        # Older files lack the tutor columns.
        conversations = [(*row, "", "hint", 1, 0) for row in _rows(
            source, "SELECT id, owner, title, created_at, updated_at FROM conversations")]
    owners = {row[0]: row[1] for row in conversations}
    messages = _rows(source, "SELECT id, conversation_id, role, text, image_path, scene_path, "
                             "video_path, log, created_at, channel, meta FROM messages")
    if not messages:
        messages = [(*row, "figure", "{}") for row in _rows(
            source, "SELECT id, conversation_id, role, text, image_path, scene_path, video_path, "
                    "log, created_at FROM messages")]
    with db.connect() as connection:
        for (cid, owner, title, created, updated, problem, mode, level,
             solved) in conversations:
            connection.execute(
                "INSERT INTO conversations (id, owner, title, created_at, updated_at, problem, "
                "mode, hint_level, solved) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT DO NOTHING",
                (cid, owner_for(owner), title, created, updated, problem or "", mode or "hint",
                 level or 1, int(bool(solved))))
        for (mid, cid, role, text, image, scene, video, log, created, channel,
             meta) in messages:
            owner = owners.get(cid)
            if owner is None:
                continue  # a message whose conversation was deleted
            connection.execute(
                "INSERT INTO messages (id, conversation_id, role, text, image_path, scene_path, "
                "video_path, log, created_at, channel, meta) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                (mid, cid, role, text, _relative(image, owner), _relative(scene, owner),
                 _relative(video, owner), log or "", created, channel or "figure", meta or "{}"))
    return len(conversations), len(messages)


def migrate(data_dir: Path, db: PostgresDatabase) -> dict[str, int]:
    users_dir, sessions_dir = data_dir / "users", data_dir / "sessions"
    # The tables the running server uses, created the same way.
    AccountStore(users_dir, db).create_tables()
    ConversationStore(users_dir, db).create_tables()
    QuotaStore(data_dir / "usage.sqlite3", db).create_tables()
    counts = {"users": 0, "sessions": 0, "conversations": 0, "messages": 0, "usage": 0}

    accounts = users_dir / "accounts.sqlite3"
    users = _rows(accounts, "SELECT user_id, name, code_hash, salt, failed_attempts, locked_until, "
                            "created_at FROM users")
    sessions = _rows(accounts, "SELECT token, user_id, created_at FROM sessions")
    with db.connect() as connection:
        for row in users:
            connection.execute(
                "INSERT INTO users (user_id, name, code_hash, salt, failed_attempts, locked_until, "
                "created_at) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING", row)
        for row in sessions:
            connection.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?) "
                               "ON CONFLICT DO NOTHING", row)
    counts["users"], counts["sessions"] = len(users), len(sessions)

    found = _copy_conversations(db, users_dir / "conversations.sqlite3", lambda owner: owner)
    counts["conversations"] += found[0]
    counts["messages"] += found[1]
    if sessions_dir.is_dir():
        for guest_dir in sorted(p for p in sessions_dir.iterdir() if p.is_dir()):
            found = _copy_conversations(db, guest_dir / "conversations.sqlite3",
                                        lambda owner, gid=guest_dir.name: f"guest-{gid}")
            counts["conversations"] += found[0]
            counts["messages"] += found[1]

    usage = _rows(data_dir / "usage.sqlite3", "SELECT owner, day, count FROM usage")
    with db.connect() as connection:
        for row in usage:
            connection.execute("INSERT INTO usage (owner, day, count) VALUES (?, ?, ?) "
                               "ON CONFLICT DO NOTHING", row)
    counts["usage"] = len(usage)
    return counts


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Cách dùng: DATABASE_URL=postgresql://… python -m api.migrate_sqlite <thư mục dữ liệu>")
        return 2
    data_dir = Path(argv[1])
    db = database_from_url(os.environ.get("DATABASE_URL"))
    if db is None:
        print("Chưa đặt DATABASE_URL.")
        return 2
    try:
        counts = migrate(data_dir, db)
    finally:
        db.close()
    print("Đã chép sang PostgreSQL (dòng đã có thì bỏ qua): "
          + ", ".join(f"{name} {count}" for name, count in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
