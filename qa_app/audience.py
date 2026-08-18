"""Password-free audience view opened by each room's QR code."""

from __future__ import annotations

import streamlit as st

from qa_app.storage import QADatabase, RoomNotFoundError
from qa_app.ui import render_question_feed
from qa_app.validation import ValidationError, validate_public_id, validate_viewer_id
from qa_app.web import create_viewer_id


def _viewer_id() -> str:
    candidate = st.query_params.get("viewer")
    try:
        viewer_id = validate_viewer_id(candidate)
    except ValidationError:
        viewer_id = create_viewer_id()
        st.query_params["viewer"] = viewer_id
    st.session_state["viewer_id"] = viewer_id
    return viewer_id


def render_audience(database: QADatabase, room_parameter: object) -> None:
    """Render room instructions, submission form, and the live question feed."""

    try:
        room_id = validate_public_id(room_parameter)
        room = database.get_room(room_id)
    except ValidationError:
        room = None

    if room is None:
        st.title("Room not found")
        st.error("This presentation link is invalid or no longer available.")
        st.caption("Ask the presenter for the current QR code.")
        return

    viewer_id = _viewer_id()
    st.caption("LIVE PRESENTATION Q&A")
    st.title(room.title)
    st.write("Ask a question or support one that someone else has already asked.")

    with st.form("question_form", clear_on_submit=True, border=True):
        question_text = st.text_area(
            "Your question",
            key="audience_question",
            max_chars=280,
            height=104,
            placeholder="What would you like the presenter to answer?",
        )
        submitted = st.form_submit_button(
            "Send question",
            key="submit_question",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        try:
            database.create_question(room.public_id, question_text)
        except (ValidationError, RoomNotFoundError) as error:
            st.error(str(error))
        else:
            st.success("Your question was added.")

    st.subheader("Questions")
    st.caption("Oldest questions appear first. The list updates automatically.")
    render_question_feed(
        database.path,
        room.public_id,
        viewer_id=viewer_id,
        interactive=True,
    )
