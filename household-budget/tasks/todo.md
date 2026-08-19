# Household budget tasks

## Task 1: Implement exact money and retention rules

- [x] Parse positive decimal amounts into integer minor units.
- [x] Calculate a clamped six-calendar-month cutoff.
- [x] Verify with focused unit tests.
- Dependencies: none
- Files: `budget_app/money.py`, `budget_app/retention.py`, `tests/test_money.py`

## Task 2: Implement the persistent ledger

- [x] Initialize one household with bank, cash, and currency settings.
- [x] Atomically record expenses/deposits and reject insufficient funds.
- [x] Produce daily summaries and purge expired history without changing balances.
- [x] Verify with SQLite integration tests.
- Dependencies: Task 1
- Files: `budget_app/models.py`, `budget_app/storage.py`, `tests/test_storage.py`

## Task 3: Implement the mobile Streamlit experience

- [x] Render setup and responsive current-balance cards.
- [x] Render separate online/offline expense forms and funds form.
- [x] Render daily closing balances, recent activity, and retained-history chart.
- [x] Verify critical UI states with Streamlit AppTest.
- Dependencies: Task 2
- Files: `streamlit_app.py`, `tests/test_streamlit_app.py`, `.streamlit/config.toml`

## Task 4: Document and verify delivery

- [x] Add Supabase Free and Streamlit Community Cloud setup instructions.
- [x] Record the database decision and security boundary.
- [ ] Run tests, lint/format checks, startup/health check, secret scan, and browser verification where supported.
- Dependencies: Tasks 1-3
- Files: `README.md`, `docs/decisions/001-hosted-postgres.md`, configuration files
