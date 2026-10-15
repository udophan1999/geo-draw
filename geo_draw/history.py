"""Per-user drawing history stored in SQLite, with copies of each scene and image."""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HistoryEntry:
    id: str
    problem: str
    summary: str
    scene_path: Path
    image_path: Path
    created_at: float


def user_id_for(identity: str) -> str:
    """Turn a login identity (OIDC subject or email) into a stable, path-safe folder name."""
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


class HistoryStore:
    """History lives under ``root``: one SQLite file plus ``<user_id>/history/<entry_id>/``."""

    def __init__(self, root: Path):
        self.root = root
        self.db_path = root / "history.sqlite3"

    @contextmanager
    def _connect(self):
        self.root.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.execute(
            """CREATE TABLE IF NOT EXISTS history (
                   id TEXT PRIMARY KEY,
                   user_id TEXT NOT NULL,
                   problem TEXT NOT NULL,
                   summary TEXT NOT NULL,
                   scene_path TEXT NOT NULL,
                   image_path TEXT NOT NULL,
                   created_at REAL NOT NULL
               )"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS history_user ON history (user_id, created_at)"
        )
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def add(self, user_id: str, problem: str, summary: str,
            scene_path: Path, image_path: Path) -> HistoryEntry:
        # The workspace scene.py is overwritten by the next drawing, so keep copies.
        entry_id = uuid.uuid4().hex[:16]
        entry_dir = self.root / user_id / "history" / entry_id
        entry_dir.mkdir(parents=True, exist_ok=True)
        saved_scene = Path(shutil.copy2(scene_path, entry_dir / "scene.py"))
        saved_image = Path(shutil.copy2(image_path, entry_dir / f"figure{image_path.suffix}"))
        entry = HistoryEntry(entry_id, problem, summary, saved_scene, saved_image, time.time())
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO history VALUES (?, ?, ?, ?, ?, ?, ?)",
                (entry.id, user_id, entry.problem, entry.summary,
                 str(entry.scene_path), str(entry.image_path), entry.created_at),
            )
        return entry

    def list(self, user_id: str, limit: int = 20) -> list[HistoryEntry]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, problem, summary, scene_path, image_path, created_at FROM history "
                "WHERE user_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [_entry(row) for row in rows]

    def get(self, user_id: str, entry_id: str) -> HistoryEntry | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, problem, summary, scene_path, image_path, created_at FROM history "
                "WHERE user_id = ? AND id = ?",
                (user_id, entry_id),
            ).fetchone()
        return _entry(row) if row else None


def _entry(row) -> HistoryEntry:
    entry_id, problem, summary, scene_path, image_path, created_at = row
    return HistoryEntry(entry_id, problem, summary, Path(scene_path), Path(image_path), created_at)


def import_into_conversations(history: HistoryStore, conversations, user_id: str) -> None:
    """Turn drawings saved before chat existed into one-turn conversations (idempotent)."""
    from .conversations import ASSISTANT, USER

    for entry in reversed(history.list(user_id, limit=1000)):
        conversation_id = f"h{entry.id}"
        if conversations.get(user_id, conversation_id):
            continue
        conversations.import_conversation(
            user_id, conversation_id, entry.problem, entry.created_at,
            [(USER, entry.problem, None, None),
             (ASSISTANT, entry.summary, entry.image_path, entry.scene_path)],
        )
