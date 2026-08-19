from datetime import date, timedelta

import pytest

from budget_app.models import Account, InsufficientFundsError, TransactionKind
from budget_app.retention import retention_cutoff
from budget_app.storage import BudgetRepository


@pytest.fixture
def repository(tmp_path):
    database_path = tmp_path / "budget.db"
    repo = BudgetRepository(f"sqlite+pysqlite:///{database_path}")
    repo.create_schema()
    yield repo
    repo.close()


def test_setup_creates_bank_and_cash_balances_with_currency(repository):
    repository.setup_household(
        opening_bank_cents=120_000,
        opening_cash_cents=25_000,
        currency="EUR",
    )

    assert repository.is_initialized()
    assert repository.get_balances().bank_cents == 120_000
    assert repository.get_balances().cash_cents == 25_000
    assert repository.get_currency() == "EUR"


def test_online_and_offline_expenses_deduct_from_the_correct_accounts(repository):
    repository.setup_household(100_000, 20_000, "EUR")
    transaction_date = date(2026, 8, 19)

    repository.record_expense(
        account=Account.BANK,
        amount_cents=1_250,
        transaction_date=transaction_date,
        category="Groceries",
        note="Weekly order",
    )
    repository.record_expense(
        account=Account.CASH,
        amount_cents=800,
        transaction_date=transaction_date,
        category="Transport",
        note="Bus tickets",
    )

    balances = repository.get_balances()
    assert balances.bank_cents == 98_750
    assert balances.cash_cents == 19_200

    transactions = repository.list_transactions()
    assert [transaction.account for transaction in transactions] == [Account.CASH, Account.BANK]
    assert all(transaction.kind is TransactionKind.EXPENSE for transaction in transactions)


def test_expense_larger_than_balance_is_rejected_without_mutation(repository):
    repository.setup_household(1_000, 500, "EUR")

    with pytest.raises(InsufficientFundsError):
        repository.record_expense(
            account=Account.CASH,
            amount_cents=501,
            transaction_date=date(2026, 8, 19),
            category="Other",
            note="Too much",
        )

    assert repository.get_balances().cash_cents == 500
    assert repository.list_transactions() == []


def test_funds_are_added_without_rewriting_prior_transactions(repository):
    repository.setup_household(10_000, 5_000, "EUR")

    repository.add_funds(
        account=Account.BANK,
        amount_cents=20_000,
        transaction_date=date(2026, 8, 19),
        note="Salary",
    )

    assert repository.get_balances().bank_cents == 30_000
    transaction = repository.list_transactions()[0]
    assert transaction.kind is TransactionKind.DEPOSIT
    assert transaction.category == "Funds added"


def test_daily_summary_reconstructs_closing_balances_after_later_activity(repository):
    first_day = date(2026, 8, 18)
    second_day = first_day + timedelta(days=1)
    repository.setup_household(10_000, 5_000, "EUR")
    repository.record_expense(Account.BANK, 1_200, first_day, "Groceries", "Food")
    repository.record_expense(Account.CASH, 800, first_day, "Transport", "Bus")
    repository.add_funds(Account.BANK, 2_000, second_day, "Refund")
    repository.record_expense(Account.BANK, 500, second_day, "Utilities", "Phone")

    first_summary = repository.get_daily_summary(first_day)
    assert first_summary.online_spend_cents == 1_200
    assert first_summary.offline_spend_cents == 800
    assert first_summary.bank_closing_cents == 8_800
    assert first_summary.cash_closing_cents == 4_200

    before_activity = repository.get_daily_summary(first_day - timedelta(days=1))
    assert before_activity.bank_closing_cents == 10_000
    assert before_activity.cash_closing_cents == 5_000


def test_backdated_expense_updates_current_and_historical_balances(repository):
    first_day = date(2026, 8, 10)
    later_day = date(2026, 8, 15)
    repository.setup_household(10_000, 5_000, "EUR")
    repository.record_expense(Account.BANK, 1_000, later_day, "Utilities", "Power")
    repository.record_expense(Account.BANK, 500, first_day, "Groceries", "Backdated")

    assert repository.get_balances().bank_cents == 8_500
    assert repository.get_daily_summary(first_day).bank_closing_cents == 9_500
    assert repository.get_daily_summary(later_day).bank_closing_cents == 8_500


def test_retention_cleanup_deletes_only_expired_history(repository):
    as_of = date(2026, 8, 19)
    cutoff = retention_cutoff(as_of)
    repository.setup_household(10_000, 5_000, "EUR")
    repository.record_expense(Account.BANK, 1_000, cutoff - timedelta(days=1), "Other", "Old")
    repository.record_expense(Account.CASH, 500, cutoff, "Other", "Keep")

    balances_before_cleanup = repository.get_balances()
    deleted_count = repository.purge_expired(as_of)

    assert deleted_count == 1
    assert repository.get_balances() == balances_before_cleanup
    assert [transaction.note for transaction in repository.list_transactions()] == ["Keep"]


def test_daily_spending_groups_expenses_but_not_deposits(repository):
    day = date(2026, 8, 19)
    repository.setup_household(10_000, 5_000, "EUR")
    repository.record_expense(Account.BANK, 1_000, day, "Other", "Online")
    repository.record_expense(Account.CASH, 500, day, "Other", "Cash")
    repository.add_funds(Account.BANK, 2_000, day, "Refund")

    spending = repository.get_daily_spending(start_date=day)

    assert len(spending) == 1
    assert spending[0].transaction_date == day
    assert spending[0].online_spend_cents == 1_000
    assert spending[0].offline_spend_cents == 500
