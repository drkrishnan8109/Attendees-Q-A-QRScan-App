import unittest

from qa_app.validation import ValidationError
from qa_app.web import (
    AUTH_LOCK_SECONDS,
    build_audience_url,
    create_viewer_id,
    password_matches,
    register_failed_login,
)


class AudienceUrlTests(unittest.TestCase):
    def test_builds_a_clean_room_url_from_the_current_app_url(self) -> None:
        audience_url = build_audience_url(
            "https://questions.streamlit.app/?presenter=true#top",
            "room_AAAA",
        )

        self.assertEqual(
            audience_url,
            "https://questions.streamlit.app/?room=room_AAAA",
        )

    def test_rejects_a_non_http_base_url(self) -> None:
        with self.assertRaises(ValidationError):
            build_audience_url("javascript:alert(1)", "room_AAAA")

    def test_rejects_credentials_embedded_in_the_base_url(self) -> None:
        with self.assertRaises(ValidationError):
            build_audience_url("https://user:pass@example.com", "room_AAAA")


class BrowserIdentityTests(unittest.TestCase):
    def test_generated_viewer_ids_are_distinct_valid_hex_tokens(self) -> None:
        first_id = create_viewer_id()
        second_id = create_viewer_id()

        self.assertRegex(first_id, r"^[a-f0-9]{32}$")
        self.assertNotEqual(first_id, second_id)


class PresenterAuthenticationTests(unittest.TestCase):
    def test_matches_only_a_configured_password_of_sufficient_length(self) -> None:
        self.assertTrue(password_matches("correct horse", "correct horse"))
        self.assertFalse(password_matches("wrong password", "correct horse"))
        self.assertFalse(password_matches("short", "short"))

    def test_fifth_failure_starts_a_temporary_lock(self) -> None:
        attempts, locked_until = register_failed_login(4, now=100.0)

        self.assertEqual(attempts, 0)
        self.assertEqual(locked_until, 100.0 + AUTH_LOCK_SECONDS)

    def test_earlier_failure_increments_without_locking(self) -> None:
        attempts, locked_until = register_failed_login(2, now=100.0)

        self.assertEqual(attempts, 3)
        self.assertEqual(locked_until, 0.0)


if __name__ == "__main__":
    unittest.main()
