from pathlib import Path

from streamlit.testing.v1 import AppTest

from budget_app.storage import BudgetRepository

APP_PATH = Path(__file__).parents[1] / "streamlit_app.py"


def _database_url(tmp_path) -> str:
    return f"sqlite+pysqlite:///{tmp_path / 'ui-test.db'}"


def test_first_run_shows_opening_balance_setup(monkeypatch, tmp_path):
    database_url = _database_url(tmp_path)
    monkeypatch.setenv("BUDGET_DATABASE_URL", database_url)

    app = AppTest.from_file(APP_PATH, default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value == "Household budget"
    assert "Set your opening balances" in [heading.value for heading in app.header]
    assert "Save opening balances" in [button.label for button in app.button]

    app.text_input(key="opening_bank_amount").input("1000.00")
    app.text_input(key="opening_cash_amount").input("250.00")
    app.button[0].click().run()

    repository = BudgetRepository(database_url)
    assert repository.get_balances().bank_cents == 100_000
    assert repository.get_balances().cash_cents == 25_000
    repository.close()


def test_configured_household_shows_mobile_dashboard_sections(monkeypatch, tmp_path):
    database_url = _database_url(tmp_path)
    repository = BudgetRepository(database_url)
    repository.create_schema()
    repository.setup_household(100_000, 25_000, "EUR")
    repository.close()
    monkeypatch.setenv("BUDGET_DATABASE_URL", database_url)

    app = AppTest.from_file(APP_PATH, default_timeout=10).run()

    assert not app.exception
    headings = [heading.value for heading in app.header]
    assert "Online payments" in headings
    assert "Offline payments" in headings
    assert "Daily summary" in headings
    metric_labels = [metric.label for metric in app.metric]
    assert metric_labels[:3] == ["Bank balance", "Cash in hand", "Total available"]
    assert "Bank at day end" in metric_labels
    assert "Cash at day end" in metric_labels


def test_online_and_offline_forms_save_to_their_own_accounts(monkeypatch, tmp_path):
    database_url = _database_url(tmp_path)
    repository = BudgetRepository(database_url)
    repository.create_schema()
    repository.setup_household(10_000, 5_000, "EUR")
    repository.close()
    monkeypatch.setenv("BUDGET_DATABASE_URL", database_url)
    app = AppTest.from_file(APP_PATH, default_timeout=10).run()

    app.text_input(key="online_amount").input("12.50")
    app.text_input(key="online_note").input("Online order")
    app.button[0].click().run()
    app.text_input(key="offline_amount").input("5.00")
    app.text_input(key="offline_note").input("Cash purchase")
    app.button[1].click().run()

    repository = BudgetRepository(database_url)
    balances = repository.get_balances()
    assert balances.bank_cents == 8_750
    assert balances.cash_cents == 4_500
    repository.close()
