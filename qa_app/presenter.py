"""Password-protected presenter console."""

from __future__ import annotations

import io
import time

import qrcode
import streamlit as st

from qa_app.app_config import app_base_url
from qa_app.backups_ui import render_backups
from qa_app.models import Room
from qa_app.storage import QADatabase
from qa_app.ui import render_question_feed
from qa_app.validation import ValidationError
from qa_app.web import (
    MIN_PRESENTER_PASSWORD_LENGTH,
    build_audience_url,
    password_matches,
    register_failed_login,
    remaining_lock_seconds,
)


def _render_login(configured_password: object) -> bool:
    if (
        not isinstance(configured_password, str)
        or len(configured_password) < MIN_PRESENTER_PASSWORD_LENGTH
    ):
        st.title("Presenter sign-in")
        st.error("The presenter password is not configured securely.")
        st.code(
            'presenter_password = "replace-with-a-long-random-password"',
            language="toml",
        )
        st.caption(
            "Add this setting to .streamlit/secrets.toml locally or to your "
            "Community Cloud app Secrets. Use at least 12 characters."
        )
        return False

    if st.session_state.get("presenter_authenticated", False):
        return True

    st.title("Presenter sign-in")
    st.write("Use the private presenter password to manage rooms and backups.")
    failed_attempts = int(st.session_state.get("presenter_failed_attempts", 0))
    locked_until = float(st.session_state.get("presenter_locked_until", 0.0))
    now = time.monotonic()
    remaining = remaining_lock_seconds(locked_until, now=now)
    if remaining:
        st.error(f"Too many attempts. Try again in {remaining} seconds.")

    with st.form("presenter_login_form", border=True):
        submitted_password = st.text_input(
            "Presenter password",
            key="presenter_password",
            type="password",
            disabled=remaining > 0,
        )
        submitted = st.form_submit_button(
            "Sign in",
            key="presenter_login",
            type="primary",
            use_container_width=True,
            disabled=remaining > 0,
        )

    if submitted and password_matches(submitted_password, configured_password):
        st.session_state["presenter_authenticated"] = True
        st.session_state["presenter_failed_attempts"] = 0
        st.session_state["presenter_locked_until"] = 0.0
        st.rerun()
    if submitted:
        attempts, new_lock = register_failed_login(failed_attempts, now=now)
        st.session_state["presenter_failed_attempts"] = attempts
        st.session_state["presenter_locked_until"] = new_lock
        st.error("That password is not correct.")
    return False


def _create_room(database: QADatabase) -> None:
    st.header("Presentation rooms")
    with st.form("create_room_form", border=True, clear_on_submit=True):
        title = st.text_input(
            "Room name",
            key="new_room_title",
            max_chars=100,
            placeholder="e.g. August product review",
        )
        submitted = st.form_submit_button(
            "Create room",
            key="create_room",
            type="primary",
            use_container_width=True,
        )
    if submitted:
        try:
            room = database.create_room(title)
        except ValidationError as error:
            st.error(str(error))
        else:
            st.session_state["selected_room_id"] = room.public_id
            st.success(f'Room "{room.title}" created.')


def _selected_room(rooms: list[Room]) -> Room | None:
    if not rooms:
        return None

    room_lookup = {room.public_id: room for room in rooms}
    selected_id = st.session_state.get("selected_room_id")
    if selected_id not in room_lookup:
        st.session_state["selected_room_id"] = rooms[0].public_id

    selected_id = st.selectbox(
        "Active room",
        options=list(room_lookup),
        key="selected_room_id",
        format_func=lambda room_id: room_lookup[room_id].title,
    )
    return room_lookup[selected_id]


@st.cache_data(show_spinner=False)
def _qr_code_png(url: str) -> bytes:
    qr_code = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
    )
    qr_code.add_data(url)
    qr_code.make(fit=True)
    image = qr_code.make_image(fill_color="#172B36", back_color="white")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _render_live_room(database: QADatabase, room: Room) -> None:
    try:
        audience_url = build_audience_url(app_base_url(), room.public_id)
    except ValidationError as error:
        st.error(str(error))
        return

    st.header(room.title)
    question_count = len(database.list_questions(room.public_id))
    details, qr_column = st.columns([3, 2], vertical_alignment="top")
    with details:
        st.markdown("### Share this room")
        st.write("Display the QR code or copy the link into your presentation.")
        st.code(audience_url, language=None)
        st.link_button(
            "Open audience view",
            audience_url,
            use_container_width=True,
        )
        st.metric("Questions received", question_count)
    with qr_column:
        st.markdown("### Audience QR code")
        st.image(
            _qr_code_png(audience_url),
            caption=f"Scan to join {room.title}",
            width="stretch",
        )

    st.divider()
    st.subheader("Live questions")
    st.caption("Oldest questions appear first. This list updates every two seconds.")
    render_question_feed(database.path, room.public_id)


def render_presenter(database: QADatabase, configured_password: object) -> None:
    """Render authentication, room management, live questions, and backups."""

    if not _render_login(configured_password):
        return

    header, action = st.columns([4, 1], vertical_alignment="center")
    with header:
        st.caption("LIVE Q&A CONTROL ROOM")
    with action:
        if st.button("Sign out", key="presenter_logout", use_container_width=True):
            st.session_state["presenter_authenticated"] = False
            st.rerun()

    st.title("Presenter console")
    st.write("Create a room for each presentation and keep every Q&A separate.")
    _create_room(database)
    rooms = database.list_rooms()
    selected_room = _selected_room(rooms)

    live_tab, backup_tab = st.tabs(["Live room", "Backups"])
    with live_tab:
        if selected_room is None:
            st.info("Create your first room to generate an audience QR code.")
        else:
            _render_live_room(database, selected_room)
    with backup_tab:
        render_backups(database, rooms)
