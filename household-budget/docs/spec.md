# Spec: Household budget

## Objective

Build a mobile-first Streamlit app for one household to record daily expenses and see how each payment changes the money available in two accounts:

- Online payments deduct from the bank balance.
- Offline payments deduct from cash in hand.
- A selected day's summary shows online spend, offline spend, closing bank balance, and closing cash balance.
- Transaction history is retained for six calendar months from its transaction date.

The first release is a single-household app with no built-in login. It is intended for local use or a private Streamlit Community Cloud app.

## Tech stack

- Python 3.12+
- Streamlit 1.60+
- SQLAlchemy 2.x
- PostgreSQL through `psycopg` in production (Supabase Free)
- SQLite only as a local-development fallback
- Pytest and Streamlit AppTest

## Commands

```bash
uv sync --extra dev
uv run streamlit run streamlit_app.py
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Project structure

```text
streamlit_app.py       Streamlit UI
budget_app/            Tested domain and persistence code
tests/                 Unit, database integration, and AppTest tests
docs/decisions/        Architecture decision records
tasks/                 Implementation plan and checklist
.streamlit/            Non-secret app configuration and a secrets example
```

## Functional requirements

1. On first use, the user selects a currency and enters opening bank and cash balances.
2. The home view always displays the current bank balance, cash in hand, and combined available balance.
3. Separate, clearly titled forms accept online and offline expenses.
4. An expense includes a date, positive amount, category, and optional note.
5. An expense cannot exceed the selected account's current balance.
6. A funds form can add money to either account without rewriting history.
7. The daily summary displays spend by payment method and the closing balance of each account for the selected day.
8. Recent activity and a daily-spend chart cover the retained six-month window.
9. Records older than six calendar months are deleted automatically; current account balances are not altered by retention cleanup.
10. Database errors are shown as safe, actionable UI messages without credentials or stack traces.

## Code style

- Use type hints and descriptive names.
- Store money as integer minor units (cents/paise), never binary floating-point values.
- Keep Streamlit code UI-focused and domain behavior in `budget_app/`.
- Use parameterized SQLAlchemy expressions only.

```python
amount_cents = parse_amount_to_cents("12.50")
repository.record_expense(
    account=Account.BANK,
    amount_cents=amount_cents,
    transaction_date=selected_date,
    category="Groceries",
    note="Weekly shop",
)
```

## Testing strategy

- Unit tests: money parsing, six-calendar-month cutoff, balance calculations, and validation.
- SQLite integration tests: setup, expense deduction, deposits, insufficient funds, daily closing balances, and retention cleanup.
- Streamlit AppTest: first-run setup and the configured dashboard's critical rendered sections.
- Runtime check: launch the app, verify HTTP health, and inspect the mobile UI in a browser when browser tooling is available.

## Threat model

- Trust boundary: all form fields and database responses are untrusted.
- Assets: household transaction history and database credentials.
- Controls: strict length/value allowlists, positive amount validation, parameterized database access, atomic balance updates, generic UI errors, and secrets excluded from Git.
- Known boundary: there is no app-level authentication in v1. Public deployment would let any visitor view and change the household data, so deployment must remain private until authentication is added.

## Boundaries

- Always: validate inputs, use atomic database transactions, keep credentials in Streamlit secrets, retain only six months of transaction history, and run tests before commits.
- Ask first: add authentication, support multiple households, change the retention period, or introduce another hosted service.
- Never: commit a real database URL, render user input as HTML, use local SQLite as cloud persistence, or log transaction details/credentials.

## Success criteria

- Online and offline expenses can be entered independently on a 320px-wide screen.
- Each expense deducts exactly once from the correct account.
- Current and historical day-end balances remain correct after backdated entries.
- History outside the six-calendar-month window is removed without changing current balances.
- The app runs locally without external credentials and is configurable for Supabase Free through one secret.
- Automated tests and static checks pass.

## Open questions deferred from v1

- Authentication and multiple household members.
- Transfers between bank and cash.
- Editing or deleting previously recorded transactions.
- Recurring expenses, budgets by category, and data export.

