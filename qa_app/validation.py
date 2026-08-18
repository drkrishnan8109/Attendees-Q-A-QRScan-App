"""Validation functions for untrusted browser and backup inputs."""

from __future__ import annotations

import re
import unicodedata

ROOM_TITLE_MAX_LENGTH = 100
QUESTION_MAX_LENGTH = 280

_PUBLIC_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_VIEWER_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
_MARKDOWN_SPECIAL_CHARACTERS = frozenset(r"\`*_{}[]<>()#+-.!|>~")


class ValidationError(ValueError):
    """Raised when data does not meet the application's public contract."""


def _validate_text(value: object, *, label: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{label} must be text.")

    clean_value = unicodedata.normalize("NFC", value).strip()
    if not clean_value:
        raise ValidationError(f"{label} cannot be empty.")
    if len(clean_value) > max_length:
        raise ValidationError(f"{label} must be {max_length} characters or fewer.")
    if any(
        unicodedata.category(character) == "Cc" and character not in "\n\t"
        for character in clean_value
    ):
        raise ValidationError(f"{label} contains unsupported control characters.")
    return clean_value


def validate_room_title(value: object) -> str:
    """Return a normalized presenter-created room title."""

    return _validate_text(
        value,
        label="The room title",
        max_length=ROOM_TITLE_MAX_LENGTH,
    )


def validate_question(value: object) -> str:
    """Return a normalized attendee question."""

    return _validate_text(
        value,
        label="The question",
        max_length=QUESTION_MAX_LENGTH,
    )


def validate_public_id(value: object) -> str:
    """Validate a room identifier received through a public URL."""

    if not isinstance(value, str) or not _PUBLIC_ID_PATTERN.fullmatch(value):
        raise ValidationError("The room link is invalid.")
    return value


def validate_viewer_id(value: object) -> str:
    """Validate the anonymous identifier used for soft per-browser voting."""

    if not isinstance(value, str) or not _VIEWER_ID_PATTERN.fullmatch(value):
        raise ValidationError("The browser identifier is invalid.")
    return value


def escape_markdown(value: str) -> str:
    """Escape Markdown control characters so attendee text renders literally."""

    return "".join(
        f"\\{character}" if character in _MARKDOWN_SPECIAL_CHARACTERS else character
        for character in value
    )
