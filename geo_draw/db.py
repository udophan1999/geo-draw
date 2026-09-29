"""Database access shared by the stores: PostgreSQL in production, SQLite files otherwise.

``database_from_url(url)`` gives a ``PostgresDatabase`` (one pool for the whole server) when
``DATABASE_URL`` is set. Without it, every store keeps its own SQLite file as before, which
is what local development and the tests use.

Stores write SQL once for both: ``?`` placeholders (turned into ``%s`` for PostgreSQL),
``INSERT … ON CONFLICT DO NOTHING``, and the dialect tokens below in their schemas and
queries (``{FLOAT}``, ``{BLOB}``, ``{SEQ_COLUMN}``, ``{ROW_ORDER}``).
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class Connection:
    """One connection inside a transaction (committed when the ``with`` block ends)."""

    def __init__(self, raw, placeholder: str):
        self._raw = raw
        self._placeholder = placeholder

    def execute(self, sql: str, params: tuple | list = ()):
        if self._placeholder != "?":
            sql = sql.replace("%", "%%").replace("?", self._placeholder)
        return self._raw.execute(sql, params)


class Database:
    dialect = ""
    FLOAT = BLOB = SEQ_COLUMN = ROW_ORDER = ""
    IntegrityError: type[Exception] = Exception

    def __init__(self) -> None:
        self._ready: set[str] = set()
        self._lock = threading.Lock()

    def sql(self, text: str) -> str:
        """Fill the dialect tokens in a schema statement or query."""
        # Plain replaces, not str.format: schemas contain literal braces (DEFAULT '{}').
        for token in ("FLOAT", "BLOB", "SEQ_COLUMN", "ROW_ORDER"):
            text = text.replace("{" + token + "}", getattr(self, token))
        return text

    @contextmanager
    def connect(self) -> Iterator[Connection]:
        raise NotImplementedError
        yield  # pragma: no cover

    def ensure_schema(self, key: str, statements: list[str],
                      added_columns: dict[str, list[tuple[str, str]]] | None = None) -> None:
        """Create a store's tables (once per database object), then add newer columns."""
        if key in self._ready:
            return
        with self._lock:
            if key in self._ready:
                return
            with self.connect() as connection:
                self._lock_schema(connection)
                for statement in statements:
                    connection.execute(self.sql(statement))
                for table, columns in (added_columns or {}).items():
                    self._add_columns(connection, table,
                                      [(name, self.sql(kind)) for name, kind in columns])
            self._ready.add(key)

    def _lock_schema(self, connection: Connection) -> None:
        pass

    def _add_columns(self, connection: Connection, table: str,
                     columns: list[tuple[str, str]]) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class SqliteDatabase(Database):
    dialect = "sqlite"
    FLOAT, BLOB, SEQ_COLUMN, ROW_ORDER = "REAL", "BLOB", "", "rowid"
    IntegrityError = sqlite3.IntegrityError

    def __init__(self, path: Path):
        super().__init__()
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        raw = sqlite3.connect(self.path)
        try:
            with raw:
                yield Connection(raw, "?")
        finally:
            raw.close()

    def _add_columns(self, connection, table, columns) -> None:
        existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        for name, definition in columns:
            if name not in existing:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


class PostgresDatabase(Database):
    dialect = "postgres"
    # DOUBLE PRECISION, not REAL: REAL is 4 bytes and would round timestamps to minutes.
    FLOAT, BLOB, SEQ_COLUMN, ROW_ORDER = "DOUBLE PRECISION", "BYTEA", "seq BIGSERIAL,", "seq"

    def __init__(self, url: str, *, max_size: int = 10):
        """A schema other than ``public`` goes in the URL: ``…/db?options=-csearch_path%3Dname``."""
        super().__init__()
        import psycopg
        from psycopg_pool import ConnectionPool

        self.IntegrityError = psycopg.IntegrityError
        self.pool = ConnectionPool(url, min_size=1, max_size=max_size, open=True,
                                   name="mathmate")

    @contextmanager
    def connect(self) -> Iterator[Connection]:
        with self.pool.connection() as raw:  # commits on success, rolls back on error
            yield Connection(raw, "%s")

    def _lock_schema(self, connection) -> None:
        # Two processes creating the same tables at once would otherwise collide.
        connection.execute("SELECT pg_advisory_xact_lock(815412001)")

    def _add_columns(self, connection, table, columns) -> None:
        for name, definition in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {definition}")

    def close(self) -> None:
        self.pool.close()


def database_from_url(url: str | None) -> Database | None:
    """The shared PostgreSQL database for ``url``, or None to keep per-store SQLite files."""
    if not url:
        return None
    if not url.startswith(("postgres://", "postgresql://")):
        raise ValueError("DATABASE_URL phải có dạng postgresql://user:mật-khẩu@máy-chủ:5432/tên-db")
    return PostgresDatabase(url)
