"""SQLite persistence for presentation rooms, questions, and reactions."""

from __future__ import annotations

import csv
import io
import json
import secrets
import sqlite3
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from qa_app.models import ImportSummary, Question, Room
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


class BackupFormatError(StorageError):
    """Raised when an uploaded backup does not match the supported format."""


class BackupConflictError(StorageError):
    """Raised when a restore would merge with existing application data."""


BACKUP_FORMAT = "live-presentation-qa"
BACKUP_VERSION = 1
MAX_BACKUP_BYTES = 1_000_000
MAX_BACKUP_ROOMS = 1_000
MAX_BACKUP_QUESTIONS = 10_000
MAX_BACKUP_REACTIONS = 50_000
_SPREADSHEET_FORMULA_PREFIXES = ("=", "+", "-", "@")


def utc_now_iso() -> str:
    """Return a lexically sortable UTC timestamp."""

    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def generate_public_id() -> str:
    """Return an opaque URL-safe identifier with enough entropy for public links."""

    return secrets.token_urlsafe(12)


def csv_safe_cell(value: object) -> object:
    """Prevent exported attendee text from becoming a spreadsheet formula."""

    if isinstance(value, str) and value.lstrip().startswith(
        _SPREADSHEET_FORMULA_PREFIXES
    ):
        return f"'{value}"
    return value


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

    def toggle_reaction(self, question_id: object, viewer_id: object) -> bool:
        """Toggle one viewer's reaction and return the new liked state."""

        clean_question_id = validate_public_id(question_id)
        clean_viewer_id = validate_viewer_id(viewer_id)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            question_exists = connection.execute(
                "SELECT 1 FROM questions WHERE public_id = ?",
                (clean_question_id,),
            ).fetchone()
            if question_exists is None:
                raise QuestionNotFoundError("This question no longer exists.")

            existing_reaction = connection.execute(
                """
                SELECT 1 FROM reactions
                WHERE question_id = ? AND viewer_id = ?
                """,
                (clean_question_id, clean_viewer_id),
            ).fetchone()
            if existing_reaction:
                connection.execute(
                    "DELETE FROM reactions WHERE question_id = ? AND viewer_id = ?",
                    (clean_question_id, clean_viewer_id),
                )
                return False

            connection.execute(
                """
                INSERT INTO reactions(question_id, viewer_id, created_at)
                VALUES (?, ?, ?)
                """,
                (clean_question_id, clean_viewer_id, self._clock()),
            )
            return True

    def export_backup_json(self) -> bytes:
        """Return a complete, restorable versioned backup."""

        with self._connect() as connection:
            rooms = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT public_id, title, created_at
                    FROM rooms ORDER BY created_at ASC, rowid ASC
                    """
                ).fetchall()
            ]
            questions = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT sort_order, public_id, room_id, body, created_at
                    FROM questions ORDER BY sort_order ASC
                    """
                ).fetchall()
            ]
            reactions = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT question_id, viewer_id, created_at
                    FROM reactions ORDER BY question_id ASC, viewer_id ASC
                    """
                ).fetchall()
            ]

        payload = {
            "format": BACKUP_FORMAT,
            "version": BACKUP_VERSION,
            "exported_at": self._clock(),
            "rooms": rooms,
            "questions": questions,
            "reactions": reactions,
        }
        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

    def export_questions_csv(self) -> str:
        """Return a human-readable chronological question export."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    rooms.title AS room_title,
                    questions.room_id,
                    questions.body AS question,
                    questions.public_id AS question_id,
                    questions.created_at AS submitted_at,
                    COUNT(reactions.viewer_id) AS likes
                FROM questions
                JOIN rooms ON rooms.public_id = questions.room_id
                LEFT JOIN reactions
                    ON reactions.question_id = questions.public_id
                GROUP BY questions.sort_order
                ORDER BY questions.sort_order ASC
                """
            ).fetchall()

        output = io.StringIO(newline="")
        fieldnames = [
            "room_title",
            "room_id",
            "question",
            "question_id",
            "submitted_at",
            "likes",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(
            {field: csv_safe_cell(value) for field, value in dict(row).items()}
            for row in rows
        )
        return output.getvalue()

    def restore_backup_json(self, payload: bytes | str) -> ImportSummary:
        """Restore a complete backup into an empty initialized database."""

        rooms, questions, reactions = self._parse_backup(payload)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                has_existing_data = connection.execute(
                    """
                    SELECT
                        EXISTS(SELECT 1 FROM rooms)
                        OR EXISTS(SELECT 1 FROM questions)
                        OR EXISTS(SELECT 1 FROM reactions)
                    """
                ).fetchone()[0]
                if has_existing_data:
                    raise BackupConflictError(
                        "Backups can only be restored into an empty app database."
                    )

                connection.executemany(
                    "INSERT INTO rooms(public_id, title, created_at) VALUES (?, ?, ?)",
                    [
                        (room["public_id"], room["title"], room["created_at"])
                        for room in rooms
                    ],
                )
                connection.executemany(
                    """
                    INSERT INTO questions(
                        sort_order, public_id, room_id, body, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            question["sort_order"],
                            question["public_id"],
                            question["room_id"],
                            question["body"],
                            question["created_at"],
                        )
                        for question in questions
                    ],
                )
                connection.executemany(
                    """
                    INSERT INTO reactions(question_id, viewer_id, created_at)
                    VALUES (?, ?, ?)
                    """,
                    [
                        (
                            reaction["question_id"],
                            reaction["viewer_id"],
                            reaction["created_at"],
                        )
                        for reaction in reactions
                    ],
                )
        except sqlite3.IntegrityError as error:
            raise BackupFormatError("The backup contains inconsistent data.") from error

        return ImportSummary(
            rooms=len(rooms),
            questions=len(questions),
            reactions=len(reactions),
        )

    @staticmethod
    def _parse_backup(
        payload: bytes | str,
    ) -> tuple[
        list[Mapping[str, object]],
        list[Mapping[str, object]],
        list[Mapping[str, object]],
    ]:
        text = QADatabase._decode_backup(payload)
        try:
            document = json.loads(text)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise BackupFormatError("The selected file is not valid JSON.") from error

        if not isinstance(document, dict):
            raise BackupFormatError("The backup root must be a JSON object.")
        if document.get("format") != BACKUP_FORMAT or document.get("version") != 1:
            raise BackupFormatError("This is not a supported Live Q&A backup.")

        rooms = QADatabase._bounded_list(
            document.get("rooms"),
            label="rooms",
            limit=MAX_BACKUP_ROOMS,
        )
        questions = QADatabase._bounded_list(
            document.get("questions"),
            label="questions",
            limit=MAX_BACKUP_QUESTIONS,
        )
        reactions = QADatabase._bounded_list(
            document.get("reactions"),
            label="reactions",
            limit=MAX_BACKUP_REACTIONS,
        )
        QADatabase._validate_backup_records(rooms, questions, reactions)
        return rooms, questions, reactions

    @staticmethod
    def _decode_backup(payload: bytes | str) -> str:
        if isinstance(payload, bytes):
            if len(payload) > MAX_BACKUP_BYTES:
                raise BackupFormatError("The backup is larger than 1 MB.")
            try:
                return payload.decode("utf-8")
            except UnicodeDecodeError as error:
                raise BackupFormatError(
                    "The backup must use UTF-8 encoding."
                ) from error
        if isinstance(payload, str):
            if len(payload.encode("utf-8")) > MAX_BACKUP_BYTES:
                raise BackupFormatError("The backup is larger than 1 MB.")
            return payload
        raise BackupFormatError("The backup must be a JSON file.")

    @staticmethod
    def _bounded_list(
        value: object, *, label: str, limit: int
    ) -> list[Mapping[str, object]]:
        if not isinstance(value, list) or len(value) > limit:
            raise BackupFormatError(f"The backup has an invalid number of {label}.")
        if not all(isinstance(item, dict) for item in value):
            raise BackupFormatError(f"Every {label} entry must be an object.")
        return value

    @staticmethod
    def _validate_backup_records(
        rooms: list[Mapping[str, object]],
        questions: list[Mapping[str, object]],
        reactions: list[Mapping[str, object]],
    ) -> None:
        room_ids: set[str] = set()
        question_ids: set[str] = set()
        sort_orders: set[int] = set()
        reaction_keys: set[tuple[str, str]] = set()
        try:
            for room in rooms:
                room_id = validate_public_id(room["public_id"])
                validate_room_title(room["title"])
                QADatabase._validate_timestamp(room["created_at"])
                if room_id in room_ids:
                    raise BackupFormatError("The backup contains duplicate rooms.")
                room_ids.add(room_id)

            for question in questions:
                question_id = validate_public_id(question["public_id"])
                room_id = validate_public_id(question["room_id"])
                validate_question(question["body"])
                QADatabase._validate_timestamp(question["created_at"])
                sort_order = question["sort_order"]
                if type(sort_order) is not int or sort_order < 1:
                    raise BackupFormatError(
                        "Question order values must be positive integers."
                    )
                if room_id not in room_ids:
                    raise BackupFormatError(
                        "A backup question references an unknown room."
                    )
                if question_id in question_ids or sort_order in sort_orders:
                    raise BackupFormatError("The backup contains duplicate questions.")
                question_ids.add(question_id)
                sort_orders.add(sort_order)

            for reaction in reactions:
                question_id = validate_public_id(reaction["question_id"])
                viewer_id = validate_viewer_id(reaction["viewer_id"])
                QADatabase._validate_timestamp(reaction["created_at"])
                reaction_key = (question_id, viewer_id)
                if question_id not in question_ids:
                    raise BackupFormatError(
                        "A reaction references an unknown question."
                    )
                if reaction_key in reaction_keys:
                    raise BackupFormatError("The backup contains duplicate reactions.")
                reaction_keys.add(reaction_key)
        except (KeyError, TypeError, ValidationError) as error:
            raise BackupFormatError("The backup contains invalid records.") from error

    @staticmethod
    def _validate_timestamp(value: object) -> str:
        if not isinstance(value, str) or not value.endswith("Z") or len(value) > 40:
            raise BackupFormatError("The backup contains an invalid timestamp.")
        try:
            datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
        except ValueError as error:
            raise BackupFormatError(
                "The backup contains an invalid timestamp."
            ) from error
        return value

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
    "BackupConflictError",
    "BackupFormatError",
    "QADatabase",
    "QuestionNotFoundError",
    "RoomNotFoundError",
    "StorageError",
    "ValidationError",
]
