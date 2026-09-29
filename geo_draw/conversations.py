"""Conversations about one math problem: the tutor chat and the figure drawn for it.

A conversation holds its ``problem`` plus two message channels:
- ``chat``: the student's messages and the tutor's hints or solution (``geo_draw.tutor``);
- ``figure``: drawing requests and the drawings made for them (``geo_draw.chat``).
Conversations from before the tutor existed only have ``figure`` messages.

Rows live in the shared PostgreSQL database when one is given, else in SQLite under
``root`` (``conversations.sqlite3``). Every message may own a folder
``<root>/<owner>/conversations/<conversation_id>/<message_id>/`` holding its files: the
pasted problem image for user messages, the scene and renders for drawings. File paths are
stored relative to ``root``, so the data folder can move (e.g. into a Docker volume).
"""

from __future__ import annotations

import json
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .db import Database, SqliteDatabase

USER = "user"
ASSISTANT = "assistant"
CHAT = "chat"
FIGURE = "figure"
HINT = "hint"
SOLUTION = "solution"
TITLE_LENGTH = 60

_CONVERSATION_COLUMNS = "id, title, created_at, updated_at, problem, mode, hint_level, solved"
_MESSAGE_COLUMNS = ("id, conversation_id, role, text, image_path, scene_path, video_path, "
                    "log, created_at, channel, meta")


@dataclass
class Conversation:
    id: str
    title: str
    created_at: float
    updated_at: float
    problem: str = ""
    mode: str = HINT
    hint_level: int = 1
    solved: bool = False  # the student reached the final answer in hint mode

    def __post_init__(self) -> None:
        self.solved = bool(self.solved)  # SQLite stores 0/1


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
    channel: str = FIGURE
    meta: dict = field(default_factory=dict)

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
    # Titles are plain text in the sidebar: drop the LaTeX math delimiters.
    title = " ".join(text.replace("$", "").split())
    return title if len(title) <= TITLE_LENGTH else title[:TITLE_LENGTH].rstrip() + "…"


_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS conversations (
           {SEQ_COLUMN}
           id TEXT PRIMARY KEY,
           owner TEXT NOT NULL,
           title TEXT NOT NULL,
           created_at {FLOAT} NOT NULL,
           updated_at {FLOAT} NOT NULL
       )""",
    "CREATE INDEX IF NOT EXISTS conversations_owner ON conversations (owner, updated_at)",
    """CREATE TABLE IF NOT EXISTS messages (
           {SEQ_COLUMN}
           id TEXT PRIMARY KEY,
           conversation_id TEXT NOT NULL,
           role TEXT NOT NULL,
           text TEXT NOT NULL,
           image_path TEXT,
           scene_path TEXT,
           video_path TEXT,
           log TEXT NOT NULL DEFAULT '',
           created_at {FLOAT} NOT NULL
       )""",
    "CREATE INDEX IF NOT EXISTS messages_conversation ON messages (conversation_id, created_at)",
]


class ConversationStore:
    """``db`` is the shared PostgreSQL database; without it, SQLite under ``root``."""

    def __init__(self, root: Path, db: Database | None = None):
        self.root = root
        self.db = db or SqliteDatabase(root / "conversations.sqlite3")

    def create_tables(self) -> None:
        self.db.ensure_schema("conversations", _SCHEMA, _ADDED_COLUMNS)

    def _connect(self):
        self.create_tables()
        return self.db.connect()

    # Conversations -----------------------------------------------------------------

    def create(self, owner: str, title: str, problem: str = "") -> Conversation:
        now = time.time()
        conversation = Conversation(uuid.uuid4().hex[:16], make_title(title) or "Đề mới", now,
                                    now, problem.strip())
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO conversations (id, owner, title, created_at, updated_at, problem) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (conversation.id, owner, conversation.title, now, now, conversation.problem),
            )
        return conversation

    def list(self, owner: str, limit: int = 50) -> list[Conversation]:
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT {_CONVERSATION_COLUMNS} FROM conversations "
                + self.db.sql("WHERE owner = ? ORDER BY updated_at DESC, {ROW_ORDER} DESC LIMIT ?"),
                (owner, limit),
            ).fetchall()
        return [Conversation(*row) for row in rows]

    def get(self, owner: str, conversation_id: str) -> Conversation | None:
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT {_CONVERSATION_COLUMNS} FROM conversations WHERE owner = ? AND id = ?",
                (owner, conversation_id),
            ).fetchone()
        return Conversation(*row) if row else None

    def update(self, owner: str, conversation_id: str, *, problem: str | None = None,
               mode: str | None = None, hint_level: int | None = None,
               solved: bool | None = None) -> None:
        """Change the problem text, the tutor mode, the hint level or the solved flag."""
        changes = {key: value for key, value in
                   (("problem", problem), ("mode", mode), ("hint_level", hint_level),
                    ("solved", None if solved is None else int(solved)))
                   if value is not None}
        if not changes:
            return
        assignments = ", ".join(f"{key} = ?" for key in changes)
        with self._connect() as connection:
            connection.execute(
                f"UPDATE conversations SET {assignments} WHERE owner = ? AND id = ?",
                (*changes.values(), owner, conversation_id),
            )

    def problem_of(self, conversation: Conversation) -> str:
        """The problem text; older drawing-only conversations used their first request."""
        if conversation.problem:
            return conversation.problem
        first = next((m for m in self.messages(conversation.id) if m.role == USER and m.text),
                     None)
        return first.text if first else ""

    def import_conversation(self, owner: str, conversation_id: str, title: str,
                            created_at: float,
                            messages: list[tuple[str, str, Path | None, Path | None]]) -> None:
        """Insert a finished conversation with a fixed id (used to import older history).

        ``messages`` holds ``(role, text, image_path, scene_path)`` tuples in order.
        """
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO conversations (id, owner, title, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                (conversation_id, owner, make_title(title) or "Đề mới", created_at, created_at),
            )
            for offset, (role, text, image_path, scene_path) in enumerate(messages):
                connection.execute(
                    "INSERT INTO messages (id, conversation_id, role, text, image_path, "
                    "scene_path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                    (f"{conversation_id}-{offset}", conversation_id, role, text,
                     self._path_text(image_path), self._path_text(scene_path),
                     created_at + offset * 1e-3),
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
                    log: str = "", channel: str = FIGURE, meta: dict | None = None) -> Message:
        now = time.time()
        message = Message(message_id or uuid.uuid4().hex[:16], conversation_id, role, text,
                          image_path, scene_path, video_path, log, now, channel, meta or {})
        with self._connect() as connection:
            connection.execute(
                f"INSERT INTO messages ({_MESSAGE_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (message.id, conversation_id, role, text,
                 self._path_text(image_path), self._path_text(scene_path),
                 self._path_text(video_path),
                 log, now, channel, json.dumps(message.meta, ensure_ascii=False)),
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
                (self._path_text(image_path), self._path_text(video_path), message_id),
            )

    def get_message(self, message_id: str) -> Message | None:
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT {_MESSAGE_COLUMNS} FROM messages WHERE id = ?", (message_id,),
            ).fetchone()
        return self._message(row) if row else None

    def messages(self, conversation_id: str, channel: str | None = None) -> list[Message]:
        """Messages in order; ``channel`` keeps only ``chat`` or ``figure`` ones."""
        query = f"SELECT {_MESSAGE_COLUMNS} FROM messages WHERE conversation_id = ?"
        params: tuple = (conversation_id,)
        if channel:
            query += " AND channel = ?"
            params += (channel,)
        with self._connect() as connection:
            rows = connection.execute(query + self.db.sql(" ORDER BY created_at, {ROW_ORDER}"),
                                      params).fetchall()
        return [self._message(row) for row in rows]

    # Files are stored relative to root (older rows hold absolute paths, still accepted).

    def _path_text(self, path: Path | None) -> str | None:
        if not path:
            return None
        try:
            return Path(path).relative_to(self.root).as_posix()
        except ValueError:
            return str(path)

    def _path(self, text: str | None) -> Path | None:
        if not text:
            return None
        path = Path(text)
        return path if path.is_absolute() else self.root / path

    def _message(self, row) -> Message:
        (message_id, conversation_id, role, text, image, scene, video, log, created_at, channel,
         meta) = row
        try:
            meta = json.loads(meta) if meta else {}
        except ValueError:
            meta = {}
        return Message(message_id, conversation_id, role, text, self._path(image),
                       self._path(scene), self._path(video), log, created_at, channel or FIGURE,
                       meta)


# Columns added after the first release; older databases get them on open.
_ADDED_COLUMNS = {
    "conversations": [("problem", "TEXT NOT NULL DEFAULT ''"),
                      ("mode", f"TEXT NOT NULL DEFAULT '{HINT}'"),
                      ("hint_level", "INTEGER NOT NULL DEFAULT 1"),
                      ("solved", "INTEGER NOT NULL DEFAULT 0")],
    "messages": [("channel", f"TEXT NOT NULL DEFAULT '{FIGURE}'"),
                 ("meta", "TEXT NOT NULL DEFAULT '{}'")],
}

