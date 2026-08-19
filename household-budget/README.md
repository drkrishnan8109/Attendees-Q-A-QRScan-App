# Household budget

A mobile-first Streamlit app for daily household expenses. Online payments reduce the bank balance, offline payments reduce cash in hand, and every retained day shows its closing bank and cash balances.

## What it includes

- Separate online and offline expense forms
- Current bank, cash, and combined available balances
- Daily online/offline totals and closing balances
- Funds added to either account without rewriting history
- Daily spending chart and recent activity table
- Exact integer money arithmetic
- Automatic six-calendar-month transaction retention
- Local SQLite development and hosted PostgreSQL deployment

## Run locally

Install [uv](https://docs.astral.sh/uv/), then run:

```bash
uv sync --extra dev
uv run streamlit run streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501). Without a database secret, the app creates `data/household_budget.db`. This SQLite file is durable on your computer, but it is not suitable as cloud persistence.

Run the checks with:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Free persistent database: Supabase

Supabase Free is a good fit for a single household. As of August 2026, the free plan includes a 500 MB PostgreSQL database and up to two active free projects. Free projects pause after one week of inactivity and do not include automatic backups. Those limits are far above the size of six months of ordinary household expense rows, but the pause and backup limitations are worth knowing. See the official [Supabase pricing page](https://supabase.com/pricing) and [billing guide](https://supabase.com/docs/guides/platform/billing-on-supabase).

### 1. Create the database

1. Create a free project at [Supabase](https://supabase.com/).
2. Open the project and select **Connect**.
3. Copy the **Session pooler** connection string on port `5432`. This mode works with persistent application servers on IPv4 networks. Supabase documents the connection choices in [Connect to your database](https://supabase.com/docs/guides/database/connecting-to-postgres).
4. Replace the password placeholder with the URL-encoded database password when necessary.

The app creates its own three small tables on first start. For PostgreSQL, it also enables row-level security and revokes public, `anon`, and `authenticated` table access. The app itself uses the trusted server-side database connection.

### 2. Add the secret locally

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` and paste the real connection URI:

```toml
BUDGET_DATABASE_URL = "postgresql://USER:URL_ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require"
```

Never commit this file. Streamlit recommends keeping local secrets outside Git and entering them through the cloud app settings; see [Streamlit secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

## Free mobile-browser deployment

[Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud) hosts personal Streamlit apps for free.

1. Make this `household-budget` directory the root of its own GitHub repository. This keeps `streamlit_app.py`, `uv.lock`, and `.streamlit/config.toml` in the locations Community Cloud expects.
2. In Streamlit Community Cloud, choose **Create app** and select `streamlit_app.py` as the entrypoint.
3. In **Advanced settings**, choose Python 3.12 and paste the `BUDGET_DATABASE_URL` secret.
4. Deploy, then open the resulting `*.streamlit.app` URL on your phone.
5. Keep the app private. This first release is for one household and has no built-in login.

Community Cloud recognizes `uv.lock` in the entrypoint directory and installs the locked dependencies. Its deployment flow and dependency-file priority are documented in [App dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).

## How balances and retention work

The `accounts` table holds the authoritative current bank and cash balances. Every expense or funds addition updates one account and inserts one ledger row in the same database transaction.

The app deletes ledger rows older than six calendar months on each run. It never changes the account balances during cleanup. A historical day-end balance is calculated by starting with today's balance and reversing all retained transactions after the selected day, so backdated entries remain accurate.

## Security boundary

- Database credentials exist only in Streamlit secrets/environment variables.
- SQL statements use SQLAlchemy parameters; form values are validated and length-limited.
- Database errors shown in the browser never include the connection string or traceback.
- Supabase Data API roles are denied access to the app tables.
- There is no application login in v1. Do not publish the app to an unrestricted public URL.

Authentication, multiple households, transfers between bank and cash, edits/deletions, recurring expenses, and exports are intentionally deferred.

## Project layout

```text
budget_app/          Exact money, retention, models, config, and SQL storage
streamlit_app.py     Mobile-first Streamlit interface
tests/               Unit, SQLite integration, and Streamlit AppTest coverage
docs/                Product spec and architecture decision
tasks/               Implementation plan and completion checklist
```

