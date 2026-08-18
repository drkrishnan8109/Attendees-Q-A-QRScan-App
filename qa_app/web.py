"""Pure helpers for Streamlit URL state and presenter authentication."""

from __future__ import annotations

import hmac
import math
import uuid
from urllib.parse import urlencode, urlsplit, urlunsplit

from qa_app.validation import ValidationError, validate_public_id, validate_viewer_id

AUTH_MAX_ATTEMPTS = 5
AUTH_LOCK_SECONDS = 30
MIN_PRESENTER_PASSWORD_LENGTH = 12


def build_audience_url(base_url: object, room_id: object) -> str:
    """Build a clean public room link from the configured or current app URL."""

    clean_room_id = validate_public_id(room_id)
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValidationError("The app URL is not configured.")

    try:
        parts = urlsplit(base_url.strip())
        port = parts.port
    except ValueError as error:
        raise ValidationError("The app URL is invalid.") from error

    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
    ):
        raise ValidationError("The app URL must be a public HTTP or HTTPS URL.")

    host = parts.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = f"{host}:{port}" if port is not None else host
    path = parts.path or "/"
    return urlunsplit(
        (
            parts.scheme,
            netloc,
            path,
            urlencode({"room": clean_room_id}),
            "",
        )
    )


def create_viewer_id() -> str:
    """Return a new anonymous token for soft per-browser reaction tracking."""

    return validate_viewer_id(uuid.uuid4().hex)


def password_matches(submitted: object, configured: object) -> bool:
    """Compare a presenter password without leaking character-by-character timing."""

    if (
        not isinstance(submitted, str)
        or not isinstance(configured, str)
        or len(configured) < MIN_PRESENTER_PASSWORD_LENGTH
    ):
        return False
    return hmac.compare_digest(submitted.encode(), configured.encode())


def register_failed_login(failed_attempts: int, *, now: float) -> tuple[int, float]:
    """Increment session-local failures or start a short lock after five attempts."""

    next_attempt_count = max(0, failed_attempts) + 1
    if next_attempt_count >= AUTH_MAX_ATTEMPTS:
        return 0, now + AUTH_LOCK_SECONDS
    return next_attempt_count, 0.0


def remaining_lock_seconds(locked_until: float, *, now: float) -> int:
    """Return whole seconds remaining in a temporary presenter login lock."""

    return max(0, math.ceil(locked_until - now))
