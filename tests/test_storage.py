from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from qa_app.storage import QADatabase, RoomNotFoundError


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
        self.assertTrue(all(question.room_id == first_room.public_id for question in questions))
        self.assertTrue(all(question.like_count == 0 for question in questions))
        self.assertTrue(all(question.liked_by_viewer is False for question in questions))

    def test_question_creation_rejects_an_unknown_room(self) -> None:
        with self.assertRaises(RoomNotFoundError):
            self.database.create_question("missing_room", "Can anyone see this?")


if __name__ == "__main__":
    unittest.main()
