from budget_app.config import ConfigurationError, database_url_from_environment


def test_local_database_url_creates_a_development_data_directory(monkeypatch, tmp_path):
    monkeypatch.delenv("BUDGET_DATABASE_URL", raising=False)

    database_url = database_url_from_environment(tmp_path)

    assert database_url == f"sqlite+pysqlite:///{tmp_path / 'data' / 'household_budget.db'}"
    assert (tmp_path / "data").is_dir()


def test_postgres_url_uses_the_psycopg_sqlalchemy_driver(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "BUDGET_DATABASE_URL",
        "postgresql://budget_user:encoded-password@db.example.com:5432/budget",
    )

    database_url = database_url_from_environment(tmp_path)

    assert database_url.startswith("postgresql+psycopg://")


def test_unsupported_database_scheme_is_rejected_without_echoing_the_url(monkeypatch, tmp_path):
    monkeypatch.setenv("BUDGET_DATABASE_URL", "mysql://user:sensitive@example.com/budget")

    try:
        database_url_from_environment(tmp_path)
    except ConfigurationError as exc:
        assert "sensitive" not in str(exc)
    else:
        raise AssertionError("Expected an unsupported database URL to be rejected")
