"""SQLite persistence for presentation rooms, questions, and reactions."""

from __future__ import annotations

import secrets
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from qa_app.models import Question, Room
from qa_app.validation import (
    ValidationError,
    validate_public_id,
    validate_question,
    validate_room_title,
    validate_viewer_id,
)


class StorageError(RuntimeError):
    """Base error for expected persistence failures."""


class RoomNotFoundError(StorageError):
    """Raised when a requested room does not exist."""


class QuestionNotFoundError(StorageError):
    """Raised when a requested question does not exist."""


def utc_now_iso() -> str:
    """Return a lexically sortable UTC timestamp."""

    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def generate_public_id() -> str:
    """Return an opaque URL-safe identifier with enough entropy for public links."""

    return secrets.token_urlsafe(12)


class QADatabase:
    """Small connection-per-operation SQLite repository."""

    def __init__(
        self,
        path: str | Path,
        *,
        clock: Callable[[], str] = utc_now_iso,
        id_factory: Callable[[], str] = generate_public_id,
    ) -> None:
        self.path = str(path)
        self._clock = clock
        self._id_factory = id_factory

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create the data directory and idempotent schema."""

        if self.path != ":memory:":
            Path(self.path).expanduser().parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS rooms (
                    public_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 100),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS questions (
                    sort_order INTEGER PRIMARY KEY AUTOINCREMENT,
                    public_id TEXT NOT NULL UNIQUE,
                    room_id TEXT NOT NULL REFERENCES rooms(public_id) ON DELETE CASCADE,
                    body TEXT NOT NULL CHECK(length(body) BETWEEN 1 AND 280),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reactions (
                    question_id TEXT NOT NULL
                        REFERENCES questions(public_id) ON DELETE CASCADE,
                    viewer_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (question_id, viewer_id)
                );

                CREATE INDEX IF NOT EXISTS questions_room_order
                    ON questions(room_id, sort_order);
                CREATE INDEX IF NOT EXISTS reactions_question
                    ON reactions(question_id);
                """
            )

    def create_room(self, title: object) -> Room:
        """Validate and persist a new presentation room."""

        room = Room(
            public_id=validate_public_id(self._id_factory()),
            title=validate_room_title(title),
            created_at=self._clock(),
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO rooms(public_id, title, created_at) VALUES (?, ?, ?)",
                (room.public_id, room.title, room.created_at),
            )
        return room

    def get_room(self, room_id: object) -> Room | None:
        """Return one room, or None when a valid identifier is unknown."""

        clean_room_id = validate_public_id(room_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT public_id, title, created_at FROM rooms WHERE public_id = ?",
                (clean_room_id,),
            ).fetchone()
        return self._room_from_row(row) if row else None

    def list_rooms(self) -> list[Room]:
        """Return rooms newest first for presenter selection."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT public_id, title, created_at
                FROM rooms
                ORDER BY created_at DESC, rowid DESC
                """
            ).fetchall()
        return [self._room_from_row(row) for row in rows]

    def create_question(self, room_id: object, body: object) -> Question:
        """Validate and append a question to an existing room."""

        clean_room_id = validate_public_id(room_id)
        clean_body = validate_question(body)
        if self.get_room(clean_room_id) is None:
            raise RoomNotFoundError("This presentation room no longer exists.")

        question = Question(
            public_id=validate_public_id(self._id_factory()),
            room_id=clean_room_id,
            body=clean_body,
            created_at=self._clock(),
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO questions(public_id, room_id, body, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    question.public_id,
                    question.room_id,
                    question.body,
                    question.created_at,
                ),
            )
        return question

    def list_questions(
        self,
        room_id: object,
        *,
        viewer_id: object | None = None,
    ) -> list[Question]:
        """Return a room's questions oldest first with reaction counts."""

        clean_room_id = validate_public_id(room_id)
        clean_viewer_id = ""
        if viewer_id is not None:
            clean_viewer_id = validate_viewer_id(viewer_id)

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    q.public_id,
                    q.room_id,
                    q.body,
                    q.created_at,
                    COUNT(r.viewer_id) AS like_count,
                    COALESCE(MAX(r.viewer_id = ?), 0) AS liked_by_viewer
                FROM questions AS q
                LEFT JOIN reactions AS r ON r.question_id = q.public_id
                WHERE q.room_id = ?
                GROUP BY q.sort_order
                ORDER BY q.sort_order ASC
                """,
                (clean_viewer_id, clean_room_id),
            ).fetchall()
        return [self._question_from_row(row) for row in rows]

    @staticmethod
    def _room_from_row(row: sqlite3.Row) -> Room:
        return Room(
            public_id=row["public_id"],
            title=row["title"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _question_from_row(row: sqlite3.Row) -> Question:
        return Question(
            public_id=row["public_id"],
            room_id=row["room_id"],
            body=row["body"],
            created_at=row["created_at"],
            like_count=int(row["like_count"]),
            liked_by_viewer=bool(row["liked_by_viewer"]),
        )

__all__ = [
    "QADatabase",
    "QuestionNotFoundError",
    "RoomNotFoundError",
    "StorageError",
    "ValidationError",
]
