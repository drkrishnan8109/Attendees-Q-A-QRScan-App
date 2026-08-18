from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from qa_app.storage import QADatabase

APP_PATH = Path(__file__).parents[1] / "streamlit_app.py"
TEST_PASSWORD = "correct horse battery staple"


class StreamlitAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.database_path = Path(self.temporary_directory.name) / "app.sqlite3"

    def create_app_test(self) -> AppTest:
        app = AppTest.from_file(APP_PATH, default_timeout=5)
        app.secrets["database_path"] = str(self.database_path)
        app.secrets["presenter_password"] = TEST_PASSWORD
        app.secrets["app_base_url"] = "https://questions.streamlit.app/"
        app.secrets["disable_live_refresh"] = True
        return app

    def test_missing_presenter_secret_shows_configuration_help(self) -> None:
        app = AppTest.from_file(APP_PATH, default_timeout=5)
        app.secrets["database_path"] = str(self.database_path)

        app.run()

        self.assertFalse(app.exception)
        self.assertIn("not configured", app.error[0].value.lower())

    def test_presenter_can_sign_in_and_create_a_room(self) -> None:
        app = self.create_app_test().run()

        app.text_input(key="presenter_password").input(TEST_PASSWORD)
        app.button(key="presenter_login").click().run()
        app.text_input(key="new_room_title").input("Product review")
        app.button(key="create_room").click().run()

        self.assertFalse(app.exception)
        self.assertEqual(
            QADatabase(self.database_path).list_rooms()[0].title, "Product review"
        )
        rendered_text = " ".join(element.value for element in app.markdown)
        self.assertIn("Audience QR code", rendered_text)

    def test_audience_can_submit_and_react_without_signing_in(self) -> None:
        database = QADatabase(self.database_path)
        database.initialize()
        room = database.create_room("Engineering all-hands")

        app = self.create_app_test()
        app.query_params["room"] = room.public_id
        app.run()

        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, room.title)
        self.assertNotEqual(app.query_params.get("viewer"), None)

        app.text_area(key="audience_question").input("When do we ship?")
        app.button(key="submit_question").click().run()

        question = database.list_questions(room.public_id)[0]
        self.assertEqual(question.body, "When do we ship?")

        app.button(key=f"reaction_{question.public_id}").click().run()

        self.assertFalse(app.exception)
        reacted_question = database.list_questions(room.public_id)[0]
        self.assertEqual(reacted_question.like_count, 1)


if __name__ == "__main__":
    unittest.main()
