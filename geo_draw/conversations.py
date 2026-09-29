"""Chat conversations: a first problem, follow-up requests and the drawings made for them.

Stored in SQLite under ``root`` (``conversations.sqlite3``). Every message may own a
folder ``<root>/<owner>/conversations/<conversation_id>/<message_id>/`` holding its
files: the pasted problem image for user messages, the scene and renders for drawings.
"""

from __future__ import annotations

import shutil
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

USER = "user"
ASSISTANT = "assistant"
TITLE_LENGTH = 60


@dataclass
class Conversation:
    id: str
    title: str
    created_at: float
    updated_at: float


@dataclass
class Message:
    id: str
    conversation_id: str
    role: str
    text: str
    image_path: Path | None
    scene_path: Path | None
    video_path: Path | None
    log: str
    created_at: float

    @property
    def has_drawing(self) -> bool:
        return (self.role == ASSISTANT and self.image_path is not None
                and self.scene_path is not None)


def compose_problem(requests: list[str]) -> str:
    """Turn the user turns of a conversation into one problem for a full redraw.

    The first turn is the problem; later turns are extra requests applied in order.
    """
    requests = [text.strip() for text in requests if text and text.strip()]
    if len(requests) <= 1:
        return requests[0] if requests else ""
    extra = "\n".join(f"{index}. {text}" for index, text in enumerate(requests[1:], start=1))
    return f"{requests[0]}\n\nYêu cầu bổ sung (áp dụng theo thứ tự):\n{extra}"


def make_title(text: str) -> str:
    title = " ".join(text.split())
    return title if len(title) <= TITLE_LENGTH else title[:TITLE_LENGTH].rstrip() + "…"


class ConversationStore:
    def __init__(self, root: Path):
        self.root = root
        self.db_path = root / "conversations.sqlite3"

    @contextmanager
    def _connect(self):
        self.root.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.executescript(
            """CREATE TABLE IF NOT EXISTS conversations (
                   id TEXT PRIMARY KEY,
                   owner TEXT NOT NULL,
                   title TEXT NOT NULL,
                   created_at REAL NOT NULL,
                   updated_at REAL NOT NULL
               );
               CREATE INDEX IF NOT EXISTS conversations_owner
                   ON conversations (owner, updated_at);
               CREATE TABLE IF NOT EXISTS messages (
                   id TEXT PRIMARY KEY,
                   conversation_id TEXT NOT NULL,
                   role TEXT NOT NULL,
                   text TEXT NOT NULL,
                   image_path TEXT,
                   scene_path TEXT,
                   video_path TEXT,
                   log TEXT NOT NULL DEFAULT '',
                   created_at REAL NOT NULL
               );
               CREATE INDEX IF NOT EXISTS messages_conversation
                   ON messages (conversation_id, created_at);"""
        )
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    # Conversations -----------------------------------------------------------------

    def create(self, owner: str, title: str) -> Conversation:
        now = time.time()
        conversation = Conversation(uuid.uuid4().hex[:16], make_title(title) or "Đề mới", now, now)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO conversations VALUES (?, ?, ?, ?, ?)",
                (conversation.id, owner, conversation.title, now, now),
            )
        return conversation

    def list(self, owner: str, limit: int = 50) -> list[Conversation]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, title, created_at, updated_at FROM conversations "
                "WHERE owner = ? ORDER BY updated_at DESC, rowid DESC LIMIT ?",
                (owner, limit),
            ).fetchall()
        return [Conversation(*row) for row in rows]

    def get(self, owner: str, conversation_id: str) -> Conversation | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, title, created_at, updated_at FROM conversations "
                "WHERE owner = ? AND id = ?",
                (owner, conversation_id),
            ).fetchone()
        return Conversation(*row) if row else None

    def import_conversation(self, owner: str, conversation_id: str, title: str,
                            created_at: float,
                            messages: list[tuple[str, str, Path | None, Path | None]]) -> None:
        """Insert a finished conversation with a fixed id (used to import older history).

        ``messages`` holds ``(role, text, image_path, scene_path)`` tuples in order.
        """
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO conversations VALUES (?, ?, ?, ?, ?)",
                (conversation_id, owner, make_title(title) or "Đề mới", created_at, created_at),
            )
            for offset, (role, text, image_path, scene_path) in enumerate(messages):
                connection.execute(
                    "INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?, ?, NULL, '', ?)",
                    (f"{conversation_id}-{offset}", conversation_id, role, text,
                     _path_text(image_path), _path_text(scene_path), created_at + offset * 1e-3),
                )

    def rename(self, owner: str, conversation_id: str, title: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE conversations SET title = ? WHERE owner = ? AND id = ?",
                (make_title(title) or "Đề mới", owner, conversation_id),
            )

    def delete(self, owner: str, conversation_id: str) -> None:
        if self.get(owner, conversation_id) is None:
            return
        with self._connect() as connection:
            connection.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            connection.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        shutil.rmtree(self.conversation_dir(owner, conversation_id), ignore_errors=True)

    def conversation_dir(self, owner: str, conversation_id: str) -> Path:
        return self.root / owner / "conversations" / conversation_id

    # Messages ----------------------------------------------------------------------

    def new_message_dir(self, owner: str, conversation_id: str) -> tuple[str, Path]:
        """Reserve an id and a folder for a message whose files are created first."""
        message_id = uuid.uuid4().hex[:16]
        folder = self.conversation_dir(owner, conversation_id) / message_id
        folder.mkdir(parents=True, exist_ok=True)
        return message_id, folder

    def add_message(self, conversation_id: str, role: str, text: str, *,
                    message_id: str | None = None, image_path: Path | None = None,
                    scene_path: Path | None = None, video_path: Path | None = None,
                    log: str = "") -> Message:
        now = time.time()
        message = Message(message_id or uuid.uuid4().hex[:16], conversation_id, role, text,
                          image_path, scene_path, video_path, log, now)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (message.id, conversation_id, role, text,
                 _path_text(image_path), _path_text(scene_path), _path_text(video_path),
                 log, now),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id)
            )
        return message

    def update_drawing(self, message_id: str, image_path: Path, video_path: Path | None) -> None:
        """Point a drawing message at a re-rendered image (manual edits)."""
        with self._connect() as connection:
            connection.execute(
                "UPDATE messages SET image_path = ?, video_path = ? WHERE id = ?",
                (str(image_path), _path_text(video_path), message_id),
            )

    def get_message(self, message_id: str) -> Message | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, conversation_id, role, text, image_path, scene_path, video_path, "
                "log, created_at FROM messages WHERE id = ?",
                (message_id,),
            ).fetchone()
        return _message(row) if row else None

    def messages(self, conversation_id: str) -> list[Message]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, conversation_id, role, text, image_path, scene_path, video_path, "
                "log, created_at FROM messages WHERE conversation_id = ? "
                "ORDER BY created_at, rowid",
                (conversation_id,),
            ).fetchall()
        return [_message(row) for row in rows]


def _path_text(path: Path | None) -> str | None:
    return str(path) if path else None


def _message(row) -> Message:
    message_id, conversation_id, role, text, image, scene, video, log, created_at = row
    return Message(message_id, conversation_id, role, text,
                   Path(image) if image else None, Path(scene) if scene else None,
                   Path(video) if video else None, log, created_at)
