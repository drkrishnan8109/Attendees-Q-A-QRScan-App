"""Entrypoint and URL router for the Live Presentation Q&A app."""

from __future__ import annotations

import sqlite3

import streamlit as st

from qa_app.app_config import database_path, presenter_password
from qa_app.audience import render_audience
from qa_app.presenter import render_presenter
from qa_app.storage import QADatabase
from qa_app.ui import apply_app_styles

st.set_page_config(
    page_title="Live Presentation Q&A",
    page_icon="❔",
    layout="centered",
    initial_sidebar_state="collapsed",
)
apply_app_styles()

database = QADatabase(database_path())
try:
    database.initialize()
except (OSError, sqlite3.Error):
    st.title("Live Presentation Q&A")
    st.error("The question store could not be opened. Please contact the presenter.")
    st.stop()

if "room" in st.query_params:
    render_audience(database, st.query_params.get("room"))
else:
    render_presenter(database, presenter_password())
