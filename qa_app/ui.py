"""Shared, accessible Streamlit presentation components."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from qa_app.app_config import read_secret
from qa_app.storage import QADatabase, QuestionNotFoundError
from qa_app.validation import escape_markdown


def apply_app_styles() -> None:
    """Add a small responsive layer on top of the configured Streamlit theme."""

    st.markdown(
        """
        <style>
        .stMainBlockContainer {
            max-width: 56rem;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }
        [data-testid="stForm"] {
            background: #ffffff;
            border-color: #d7e1e5;
        }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #d7e1e5;
            padding: 0.75rem 1rem;
        }
        @media (max-width: 40rem) {
            .stMainBlockContainer {
                padding-top: 1rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
            h1 { font-size: 1.75rem !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_utc_timestamp(value: str) -> str:
    """Format an application timestamp without guessing the viewer's timezone."""

    try:
        timestamp = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        return "recently"
    return timestamp.strftime("%H:%M UTC")


def render_question_feed(
    database_path: str,
    room_id: str,
    *,
    viewer_id: str | None = None,
    interactive: bool = False,
) -> None:
    """Render an automatically refreshing oldest-first question feed."""

    run_every = None if read_secret("disable_live_refresh", False) else "2s"

    @st.fragment(run_every=run_every)
    def live_feed() -> None:
        database = QADatabase(database_path)
        questions = database.list_questions(room_id, viewer_id=viewer_id)
        if not questions:
            st.info("No questions yet. Be the first to ask one.")
            return

        for position, question in enumerate(questions, start=1):
            with st.container(border=True):
                st.markdown(escape_markdown(question.body))
                metadata, reaction = st.columns([4, 1], vertical_alignment="center")
                with metadata:
                    asked_at = format_utc_timestamp(question.created_at)
                    st.caption(f"Question {position} · Asked {asked_at}")
                with reaction:
                    if interactive and viewer_id:
                        icon = "♥" if question.liked_by_viewer else "♡"
                        label = f"{icon} {question.like_count}"
                        if st.button(
                            label,
                            key=f"reaction_{question.public_id}",
                            help="Unlike this question"
                            if question.liked_by_viewer
                            else "Like this question",
                            width="stretch",
                        ):
                            try:
                                database.toggle_reaction(question.public_id, viewer_id)
                            except QuestionNotFoundError:
                                st.warning("That question is no longer available.")
                            st.rerun()
                    else:
                        st.caption(f"♥ {question.like_count}")

    live_feed()
