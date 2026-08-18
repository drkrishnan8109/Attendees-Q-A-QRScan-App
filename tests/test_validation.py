import unittest

from qa_app.validation import (
    ValidationError,
    escape_markdown,
    validate_public_id,
    validate_question,
    validate_room_title,
    validate_viewer_id,
)


class RoomTitleValidationTests(unittest.TestCase):
    def test_trims_and_normalizes_a_room_title(self) -> None:
        self.assertEqual(validate_room_title("  Quarterly Q&A  "), "Quarterly Q&A")

    def test_rejects_an_empty_room_title(self) -> None:
        with self.assertRaisesRegex(ValidationError, "room title"):
            validate_room_title(" \n ")

    def test_rejects_a_room_title_over_100_characters(self) -> None:
        with self.assertRaisesRegex(ValidationError, "100"):
            validate_room_title("a" * 101)


class QuestionValidationTests(unittest.TestCase):
    def test_preserves_safe_multiline_plain_text(self) -> None:
        self.assertEqual(
            validate_question("  First line\nSecond line  "), "First line\nSecond line"
        )

    def test_rejects_an_empty_question(self) -> None:
        with self.assertRaisesRegex(ValidationError, "question"):
            validate_question(" \t\n ")

    def test_rejects_a_question_over_280_characters(self) -> None:
        with self.assertRaisesRegex(ValidationError, "280"):
            validate_question("a" * 281)

    def test_rejects_hidden_control_characters(self) -> None:
        with self.assertRaisesRegex(ValidationError, "unsupported"):
            validate_question("hello\x00world")


class TokenValidationTests(unittest.TestCase):
    def test_accepts_generated_public_and_viewer_ids(self) -> None:
        self.assertEqual(validate_public_id("Abc_1234-xyz"), "Abc_1234-xyz")
        self.assertEqual(validate_viewer_id("a" * 32), "a" * 32)

    def test_rejects_query_parameter_injection(self) -> None:
        with self.assertRaises(ValidationError):
            validate_public_id("room?presenter=true")
        with self.assertRaises(ValidationError):
            validate_viewer_id("not-a-browser-token")


class MarkdownEscapingTests(unittest.TestCase):
    def test_escapes_formatting_links_and_html_markers(self) -> None:
        source = "**bold** [link](https://example.com) <script>"
        escaped = r"\*\*bold\*\* \[link\]\(https://example\.com\) \<script\>"
        self.assertEqual(escape_markdown(source), escaped)

    def test_escapes_inline_math_markers(self) -> None:
        self.assertEqual(escape_markdown("Does $x$ equal 2?"), r"Does \$x\$ equal 2?")


if __name__ == "__main__":
    unittest.main()
