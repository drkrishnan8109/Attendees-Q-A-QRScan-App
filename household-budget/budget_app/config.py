"""Environment-based database configuration."""

import os
from pathlib import Path


class ConfigurationError(ValueError):
    """Raised when deployment configuration is unsupported."""


def database_url_from_environment(app_root: Path) -> str:
    """Return a safe SQLAlchemy URL, defaulting to local-development SQLite."""
    configured_url = os.environ.get("BUDGET_DATABASE_URL", "").strip()
    if not configured_url:
        data_directory = app_root / "data"
        data_directory.mkdir(parents=True, exist_ok=True)
        return f"sqlite+pysqlite:///{data_directory / 'household_budget.db'}"

    if configured_url.startswith("postgresql+psycopg://"):
        return configured_url
    if configured_url.startswith("postgresql://"):
        return configured_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if configured_url.startswith("postgres://"):
        return configured_url.replace("postgres://", "postgresql+psycopg://", 1)
    if configured_url.startswith("sqlite+pysqlite:///"):
        return configured_url
    raise ConfigurationError("BUDGET_DATABASE_URL must use PostgreSQL or SQLite.")
