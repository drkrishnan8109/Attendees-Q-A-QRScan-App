"""Mobile-first Streamlit interface for the household budget ledger."""

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from budget_app.config import ConfigurationError, database_url_from_environment
from budget_app.models import Account, BudgetError, TransactionKind
from budget_app.money import (
    AmountError,
    format_money,
    parse_amount_to_cents,
    parse_balance_to_cents,
)
from budget_app.retention import retention_cutoff
from budget_app.storage import BudgetRepository

APP_ROOT = Path(__file__).resolve().parent
TODAY = date.today()
CATEGORIES = [
    "Groceries",
    "Rent or mortgage",
    "Utilities",
    "Transport",
    "Health",
    "Education",
    "Shopping",
    "Entertainment",
    "Other",
]
CURRENCIES = ["EUR", "INR", "USD", "GBP"]

st.set_page_config(
    page_title="Household budget",
    page_icon=":material/account_balance_wallet:",
    layout="centered",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def get_repository(database_url: str) -> BudgetRepository:
    """Create one shared, thread-safe database repository per URL."""
    repository = BudgetRepository(database_url)
    repository.create_schema()
    return repository


def render_setup(repository: BudgetRepository) -> None:
    st.header("Set your opening balances")
    st.caption("Enter the money currently available before recording expenses.")
    with st.form("opening_balances", border=True):
        currency = st.selectbox("Currency", CURRENCIES, key="opening_currency")
        bank_amount = st.text_input(
            "Bank balance",
            value="0.00",
            placeholder="0.00",
            key="opening_bank_amount",
            max_chars=20,
        )
        cash_amount = st.text_input(
            "Cash in hand",
            value="0.00",
            placeholder="0.00",
            key="opening_cash_amount",
            max_chars=20,
        )
        submitted = st.form_submit_button(
            "Save opening balances",
            icon=":material/check_circle:",
            type="primary",
        )

    if submitted:
        try:
            repository.setup_household(
                opening_bank_cents=parse_balance_to_cents(bank_amount),
                opening_cash_cents=parse_balance_to_cents(cash_amount),
                currency=currency,
            )
        except (AmountError, BudgetError) as exc:
            st.error(str(exc), icon=":material/error:")
        except SQLAlchemyError:
            st.error(
                "The balances could not be saved. Check the database connection and try again.",
                icon=":material/error:",
            )
        else:
            st.toast("Opening balances saved", icon=":material/check_circle:")
            st.rerun()


def render_current_balances(repository: BudgetRepository, currency: str) -> None:
    balances = repository.get_balances()
    with st.container(horizontal=True):
        st.metric(
            "Bank balance",
            format_money(balances.bank_cents, currency),
            icon=":material/account_balance:",
            border=True,
        )
        st.metric(
            "Cash in hand",
            format_money(balances.cash_cents, currency),
            icon=":material/payments:",
            border=True,
        )
        st.metric(
            "Total available",
            format_money(balances.total_cents, currency),
            icon=":material/account_balance_wallet:",
            border=True,
        )


def render_expense_form(
    repository: BudgetRepository,
    *,
    account: Account,
    heading: str,
    caption: str,
    key_prefix: str,
) -> None:
    st.header(heading)
    st.caption(caption)
    with st.form(f"{key_prefix}_expense_form", border=True):
        transaction_date = st.date_input(
            "Expense date",
            value=TODAY,
            min_value=retention_cutoff(TODAY),
            max_value=TODAY,
            format="DD/MM/YYYY",
            key=f"{key_prefix}_date",
        )
        amount = st.text_input(
            "Amount",
            placeholder="0.00",
            key=f"{key_prefix}_amount",
            max_chars=20,
        )
        category = st.selectbox(
            "Category",
            CATEGORIES,
            key=f"{key_prefix}_category",
        )
        note = st.text_input(
            "Note (optional)",
            placeholder="What was this for?",
            key=f"{key_prefix}_note",
            max_chars=200,
        )
        submitted = st.form_submit_button(
            "Add expense",
            icon=":material/add_circle:",
            type="primary",
        )

    if submitted:
        try:
            repository.record_expense(
                account=account,
                amount_cents=parse_amount_to_cents(amount),
                transaction_date=transaction_date,
                category=category,
                note=note,
            )
        except (AmountError, BudgetError) as exc:
            st.error(str(exc), icon=":material/error:")
        except SQLAlchemyError:
            st.error(
                "The expense could not be saved. Check the database connection and try again.",
                icon=":material/error:",
            )
        else:
            st.toast("Expense saved", icon=":material/check_circle:")
            st.rerun()


def render_funds_form(repository: BudgetRepository) -> None:
    with st.expander("Add money to an account", icon=":material/add_card:"):
        st.caption("Use this for salary, cash top-ups, refunds, or other money received.")
        with st.form("add_funds", border=False):
            account_label = st.selectbox("Add to", ["Bank", "Cash"], key="funds_account")
            transaction_date = st.date_input(
                "Funds date",
                value=TODAY,
                min_value=retention_cutoff(TODAY),
                max_value=TODAY,
                format="DD/MM/YYYY",
                key="funds_date",
            )
            amount = st.text_input(
                "Amount",
                placeholder="0.00",
                key="funds_amount",
                max_chars=20,
            )
            note = st.text_input(
                "Note (optional)",
                placeholder="For example: salary",
                key="funds_note",
                max_chars=200,
            )
            submitted = st.form_submit_button(
                "Add funds",
                icon=":material/add:",
                type="primary",
            )

        if submitted:
            try:
                repository.add_funds(
                    account=Account.BANK if account_label == "Bank" else Account.CASH,
                    amount_cents=parse_amount_to_cents(amount),
                    transaction_date=transaction_date,
                    note=note,
                )
            except (AmountError, BudgetError) as exc:
                st.error(str(exc), icon=":material/error:")
            except SQLAlchemyError:
                st.error(
                    "The funds could not be saved. Check the database connection and try again.",
                    icon=":material/error:",
                )
            else:
                st.toast("Funds added", icon=":material/check_circle:")
                st.rerun()


def render_daily_summary(repository: BudgetRepository, currency: str) -> None:
    st.header("Daily summary")
    selected_date = st.date_input(
        "Choose a day",
        value=TODAY,
        min_value=retention_cutoff(TODAY),
        max_value=TODAY,
        format="DD/MM/YYYY",
        key="summary_date",
    )
    summary = repository.get_daily_summary(selected_date)

    with st.container(horizontal=True):
        st.metric(
            "Online spent",
            format_money(summary.online_spend_cents, currency),
            icon=":material/credit_card:",
            border=True,
        )
        st.metric(
            "Offline spent",
            format_money(summary.offline_spend_cents, currency),
            icon=":material/payments:",
            border=True,
        )
    with st.container(horizontal=True):
        st.metric(
            "Bank at day end",
            format_money(summary.bank_closing_cents, currency),
            icon=":material/account_balance:",
            border=True,
        )
        st.metric(
            "Cash at day end",
            format_money(summary.cash_closing_cents, currency),
            icon=":material/wallet:",
            border=True,
        )


def render_history(repository: BudgetRepository, currency: str) -> None:
    st.header("Spending history")
    cutoff = retention_cutoff(TODAY)
    st.caption(f"Transactions are kept from {cutoff:%d %B %Y} onward.")
    daily_spending = repository.get_daily_spending(cutoff)
    history = repository.list_transactions(start_date=cutoff)

    if not history:
        st.info(
            "No transactions yet. Add an online or offline expense to start your history.",
            icon=":material/receipt_long:",
        )
        return

    if daily_spending:
        st.subheader("Daily spending")
        chart_data = pd.DataFrame(
            [
                {
                    "Date": spending.transaction_date,
                    "Online": spending.online_spend_cents / 100,
                    "Offline": spending.offline_spend_cents / 100,
                }
                for spending in daily_spending
            ]
        )
        st.bar_chart(
            chart_data,
            x="Date",
            y=["Online", "Offline"],
            color=["blue", "orange"],
            stack=True,
            height=260,
            x_label="Date",
            y_label=f"Amount ({currency})",
        )

    st.subheader("Recent activity")
    history_data = pd.DataFrame(
        [
            {
                "Date": transaction.transaction_date,
                "Payment": "Online" if transaction.account is Account.BANK else "Offline",
                "Type": (
                    "Expense" if transaction.kind is TransactionKind.EXPENSE else "Funds added"
                ),
                "Category": transaction.category,
                "Note": transaction.note or "—",
                "Amount": (
                    ("−" if transaction.kind is TransactionKind.EXPENSE else "+")
                    + format_money(transaction.amount_cents, currency)
                ),
            }
            for transaction in history
        ]
    )
    st.dataframe(
        history_data,
        hide_index=True,
        column_config={"Date": st.column_config.DateColumn("Date", format="DD MMM YYYY")},
        key="transaction_history",
    )


st.title("Household budget")
st.caption("Track online payments, cash spending, and what remains at the end of each day.")

try:
    database_url = database_url_from_environment(APP_ROOT)
    repository = get_repository(database_url)
    repository.purge_expired(TODAY)
except (ConfigurationError, SQLAlchemyError):
    st.error(
        "The budget database is unavailable. Check BUDGET_DATABASE_URL and try again.",
        icon=":material/database_off:",
    )
    st.stop()

if not repository.is_initialized():
    render_setup(repository)
    st.stop()

currency = repository.get_currency()
render_current_balances(repository, currency)
render_expense_form(
    repository,
    account=Account.BANK,
    heading="Online payments",
    caption="Paid from your bank balance.",
    key_prefix="online",
)
render_expense_form(
    repository,
    account=Account.CASH,
    heading="Offline payments",
    caption="Paid from cash in hand.",
    key_prefix="offline",
)
render_daily_summary(repository, currency)
render_funds_form(repository)
render_history(repository, currency)
