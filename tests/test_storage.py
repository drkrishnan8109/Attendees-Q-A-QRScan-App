from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from qa_app.storage import (
    BackupConflictError,
    BackupFormatError,
    QADatabase,
    QuestionNotFoundError,
    RoomNotFoundError,
)


class StorageQuestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.database_path = Path(self.temporary_directory.name) / "questions.sqlite3"
        self.identifiers = iter(
            [
                "room_AAAA",
                "room_BBBB",
                "question_CCCC",
                "question_DDDD",
                "question_EEEE",
            ]
        )
        self.database = QADatabase(
            self.database_path,
            clock=lambda: "2026-08-18T12:00:00.000000Z",
            id_factory=lambda: next(self.identifiers),
        )
        self.database.initialize()

    def test_rooms_persist_across_database_instances(self) -> None:
        first_room = self.database.create_room("First presentation")
        second_room = self.database.create_room("Second presentation")

        reopened_database = QADatabase(self.database_path)
        reopened_database.initialize()

        self.assertEqual(reopened_database.get_room(first_room.public_id), first_room)
        self.assertEqual(
            [room.public_id for room in reopened_database.list_rooms()],
            [second_room.public_id, first_room.public_id],
        )

    def test_questions_are_isolated_and_returned_in_insertion_order(self) -> None:
        first_room = self.database.create_room("First presentation")
        second_room = self.database.create_room("Second presentation")
        first_question = self.database.create_question(first_room.public_id, "First?")
        second_question = self.database.create_question(first_room.public_id, "Second?")
        self.database.create_question(second_room.public_id, "Other room?")

        questions = self.database.list_questions(first_room.public_id)

        self.assertEqual(
            [question.public_id for question in questions],
            [first_question.public_id, second_question.public_id],
        )
        self.assertTrue(
            all(question.room_id == first_room.public_id for question in questions)
        )
        self.assertTrue(all(question.like_count == 0 for question in questions))
        self.assertTrue(
            all(question.liked_by_viewer is False for question in questions)
        )

    def test_question_creation_rejects_an_unknown_room(self) -> None:
        with self.assertRaises(RoomNotFoundError):
            self.database.create_question("missing_room", "Can anyone see this?")


class ReactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        identifiers = iter(["room_AAAA", "question_BBBB", "question_CCCC"])
        self.database = QADatabase(
            Path(self.temporary_directory.name) / "questions.sqlite3",
            id_factory=lambda: next(identifiers),
        )
        self.database.initialize()
        self.room = self.database.create_room("Reaction test")
        self.question = self.database.create_question(self.room.public_id, "Like me?")

    def test_a_viewer_can_like_and_unlike_one_question(self) -> None:
        viewer_id = "a" * 32

        self.assertTrue(
            self.database.toggle_reaction(self.question.public_id, viewer_id)
        )
        liked_question = self.database.list_questions(
            self.room.public_id,
            viewer_id=viewer_id,
        )[0]
        self.assertEqual(liked_question.like_count, 1)
        self.assertTrue(liked_question.liked_by_viewer)

        self.assertFalse(
            self.database.toggle_reaction(self.question.public_id, viewer_id)
        )
        unliked_question = self.database.list_questions(
            self.room.public_id,
            viewer_id=viewer_id,
        )[0]
        self.assertEqual(unliked_question.like_count, 0)
        self.assertFalse(unliked_question.liked_by_viewer)

    def test_each_viewer_contributes_at_most_one_like(self) -> None:
        self.database.toggle_reaction(self.question.public_id, "a" * 32)
        self.database.toggle_reaction(self.question.public_id, "b" * 32)

        question = self.database.list_questions(self.room.public_id)[0]

        self.assertEqual(question.like_count, 2)

    def test_reaction_rejects_an_unknown_question(self) -> None:
        with self.assertRaises(QuestionNotFoundError):
            self.database.toggle_reaction("missing_question", "a" * 32)


class BackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        identifiers = iter(["room_AAAA", "question_BBBB", "question_CCCC"])
        self.database = QADatabase(
            Path(self.temporary_directory.name) / "source.sqlite3",
            clock=lambda: "2026-08-18T12:00:00.000000Z",
            id_factory=lambda: next(identifiers),
        )
        self.database.initialize()
        self.room = self.database.create_room("Backup test")
        self.question = self.database.create_question(
            self.room.public_id,
            "Can CSV preserve commas, and newlines?\nYes.",
        )
        self.database.toggle_reaction(self.question.public_id, "a" * 32)

    def test_json_backup_round_trips_all_data(self) -> None:
        payload = self.database.export_backup_json()
        restored_database = QADatabase(
            Path(self.temporary_directory.name) / "restored.sqlite3"
        )
        restored_database.initialize()

        summary = restored_database.restore_backup_json(payload)

        self.assertEqual(
            (summary.rooms, summary.questions, summary.reactions), (1, 1, 1)
        )
        self.assertEqual(restored_database.list_rooms(), [self.room])
        restored_question = restored_database.list_questions(
            self.room.public_id,
            viewer_id="a" * 32,
        )[0]
        self.assertEqual(restored_question.body, self.question.body)
        self.assertEqual(restored_question.like_count, 1)
        self.assertTrue(restored_question.liked_by_viewer)

    def test_csv_export_is_readable_and_quotes_question_content(self) -> None:
        csv_text = self.database.export_questions_csv()

        self.assertIn("room_title,room_id,question", csv_text)
        self.assertIn('"Can CSV preserve commas, and newlines?\nYes."', csv_text)

    def test_csv_export_neutralizes_spreadsheet_formulas(self) -> None:
        self.database.create_question(self.room.public_id, "=2+2")

        csv_text = self.database.export_questions_csv()

        self.assertIn("'=2+2", csv_text)

    def test_restore_refuses_to_merge_into_a_nonempty_database(self) -> None:
        payload = self.database.export_backup_json()

        with self.assertRaises(BackupConflictError):
            self.database.restore_backup_json(payload)

    def test_restore_rejects_invalid_json_without_changing_data(self) -> None:
        empty_database = QADatabase(
            Path(self.temporary_directory.name) / "empty.sqlite3"
        )
        empty_database.initialize()

        with self.assertRaises(BackupFormatError):
            empty_database.restore_backup_json(b"not JSON")

        self.assertEqual(empty_database.list_rooms(), [])


if __name__ == "__main__":
    unittest.main()
