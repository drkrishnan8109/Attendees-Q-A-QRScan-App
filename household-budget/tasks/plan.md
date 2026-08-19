# Implementation plan: Household budget

## Overview

Create a small ledger-backed Streamlit application. Account rows hold the authoritative current bank and cash balances; retained transaction rows provide six months of audit history and allow historical day-end balances to be reconstructed from the current balance.

## Architecture decisions

- Use integer minor units for exact money arithmetic.
- Use a single SQLAlchemy repository for both local SQLite and hosted PostgreSQL.
- Update the account and insert its ledger entry in one database transaction.
- Reconstruct a historical closing balance by reversing all retained transactions dated after the requested day.
- Use native Streamlit forms and responsive horizontal containers; avoid custom HTML/CSS.

## Dependency order

```text
Specification
  -> money and retention rules
    -> database ledger
      -> Streamlit forms and summaries
        -> deployment docs and runtime verification
```

## Phases

### Phase 1: Foundation

- Write failing tests for money parsing, retention, account setup, expenses, deposits, and historical balances.
- Implement the smallest domain and repository code that passes those tests.

### Checkpoint: Foundation

- Unit and SQLite integration tests pass.
- No float arithmetic or interpolated SQL is present.

### Phase 2: Core experience

- Add first-run setup, balance cards, separate online/offline forms, daily summary, history, and funds form.
- Add AppTest coverage for setup and dashboard rendering.

### Checkpoint: Core experience

- The complete flow works against a temporary/local database.
- Empty and database-error states are meaningful.

### Phase 3: Delivery

- Add Supabase/Streamlit Community Cloud configuration instructions and ADR.
- Run tests, static checks, secret scan, app startup, HTTP health, and browser checks where available.
- Review for correctness, simplicity, security, performance, accessibility, and mobile behavior.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Concurrent expenses overspend an account | High | Lock the account row and update it in one transaction. |
| Retention cleanup corrupts balances | High | Delete ledger history only; never recalculate or change account rows during cleanup. |
| Streamlit cloud filesystem resets | High | Require hosted PostgreSQL for deployment; label SQLite local-only. |
| Public URL exposes household data | High | Document private deployment requirement; keep authentication out of v1 pending approval. |
| Free database pauses when idle | Low | Explain the Supabase Free inactivity limitation in the README. |

## Open questions

None blocking. Defaults and deferred features are recorded in the spec.

