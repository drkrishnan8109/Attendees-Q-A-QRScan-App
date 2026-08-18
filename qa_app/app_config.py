"""Runtime configuration sourced safely from Streamlit Secrets."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

DEFAULT_DATABASE_PATH = Path(".qa_data/questions.sqlite3")


def read_secret(name: str, default: object = None) -> object:
    """Read one optional secret without failing when no secrets file exists."""

    try:
        return st.secrets.get(name, default)
    except StreamlitSecretNotFoundError:
        return default


def database_path() -> Path:
    """Return the configured SQLite path or the safe project-local default."""

    configured_path = read_secret("database_path")
    if isinstance(configured_path, str) and configured_path.strip():
        return Path(configured_path.strip()).expanduser()
    return DEFAULT_DATABASE_PATH


def presenter_password() -> object:
    """Return the configured presenter password without introducing a default."""

    return read_secret("presenter_password")


def app_base_url() -> str:
    """Return an explicit public URL or the URL serving the current session."""

    configured_url = read_secret("app_base_url")
    if isinstance(configured_url, str) and configured_url.strip():
        return configured_url.strip()
    return str(st.context.url)
