"""SQLAlchemy-backed account and six-month ledger storage."""

from datetime import date

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    func,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.engine import Connection, Engine

from budget_app.models import (
    Account,
    AlreadyInitializedError,
    Balances,
    DailySpending,
    DailySummary,
    InputValidationError,
    InsufficientFundsError,
    NotInitializedError,
    TransactionKind,
    TransactionRecord,
)
from budget_app.retention import retention_cutoff

metadata = MetaData()

accounts = Table(
    "accounts",
    metadata,
    Column("account", String(10), primary_key=True),
    Column("balance_cents", BigInteger, nullable=False),
    Column("updated_at", DateTime, nullable=False, server_default=func.now()),
    CheckConstraint("account IN ('bank', 'cash')", name="valid_account"),
    CheckConstraint("balance_cents >= 0", name="nonnegative_balance"),
)

settings = Table(
    "settings",
    metadata,
    Column("key", String(50), primary_key=True),
    Column("value", String(100), nullable=False),
)

transactions = Table(
    "transactions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("transaction_date", Date, nullable=False),
    Column("account", String(10), nullable=False),
    Column("kind", String(10), nullable=False),
    Column("amount_cents", BigInteger, nullable=False),
    Column("category", String(50), nullable=False),
    Column("note", String(200), nullable=False, server_default=""),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    CheckConstraint("account IN ('bank', 'cash')", name="transaction_valid_account"),
    CheckConstraint("kind IN ('expense', 'deposit')", name="valid_transaction_kind"),
    CheckConstraint("amount_cents > 0", name="positive_transaction_amount"),
)
Index("ix_transactions_date", transactions.c.transaction_date)


class BudgetRepository:
    """Persist balances and a time-limited transaction ledger."""

    def __init__(self, database_url: str):
        engine_options: dict = {"pool_pre_ping": True}
        if database_url.startswith("sqlite"):
            engine_options["connect_args"] = {"check_same_thread": False}
        else:
            engine_options.update(pool_size=2, max_overflow=1, pool_recycle=300)
        self.engine: Engine = create_engine(database_url, **engine_options)

    def create_schema(self) -> None:
        metadata.create_all(self.engine)
        self._harden_postgres_tables()

    def close(self) -> None:
        self.engine.dispose()

    def is_initialized(self) -> bool:
        with self.engine.connect() as connection:
            account_count = connection.scalar(select(func.count()).select_from(accounts))
        return account_count == len(Account)

    def setup_household(
        self,
        opening_bank_cents: int,
        opening_cash_cents: int,
        currency: str,
    ) -> None:
        self._validate_nonnegative_balance(opening_bank_cents)
        self._validate_nonnegative_balance(opening_cash_cents)
        normalized_currency = currency.strip().upper()
        if len(normalized_currency) != 3 or not normalized_currency.isalpha():
            raise InputValidationError("Choose a valid three-letter currency.")

        with self.engine.begin() as connection:
            account_count = connection.scalar(select(func.count()).select_from(accounts))
            if account_count:
                raise AlreadyInitializedError("Household balances are already set up.")
            connection.execute(
                insert(accounts),
                [
                    {"account": Account.BANK.value, "balance_cents": opening_bank_cents},
                    {"account": Account.CASH.value, "balance_cents": opening_cash_cents},
                ],
            )
            connection.execute(insert(settings).values(key="currency", value=normalized_currency))

    def get_balances(self) -> Balances:
        with self.engine.connect() as connection:
            rows = connection.execute(select(accounts.c.account, accounts.c.balance_cents)).all()
        balance_by_account = {Account(row.account): row.balance_cents for row in rows}
        if set(balance_by_account) != set(Account):
            raise NotInitializedError("Set up the household balances first.")
        return Balances(
            bank_cents=balance_by_account[Account.BANK],
            cash_cents=balance_by_account[Account.CASH],
        )

    def get_currency(self) -> str:
        with self.engine.connect() as connection:
            currency = connection.scalar(
                select(settings.c.value).where(settings.c.key == "currency")
            )
        if currency is None:
            raise NotInitializedError("Set up the household balances first.")
        return currency

    def record_expense(
        self,
        account: Account,
        amount_cents: int,
        transaction_date: date,
        category: str,
        note: str,
    ) -> int:
        return self._record_transaction(
            account=account,
            kind=TransactionKind.EXPENSE,
            amount_cents=amount_cents,
            transaction_date=transaction_date,
            category=category,
            note=note,
        )

    def add_funds(
        self,
        account: Account,
        amount_cents: int,
        transaction_date: date,
        note: str,
    ) -> int:
        return self._record_transaction(
            account=account,
            kind=TransactionKind.DEPOSIT,
            amount_cents=amount_cents,
            transaction_date=transaction_date,
            category="Funds added",
            note=note,
        )

    def _record_transaction(
        self,
        *,
        account: Account,
        kind: TransactionKind,
        amount_cents: int,
        transaction_date: date,
        category: str,
        note: str,
    ) -> int:
        normalized_account = self._validate_account(account)
        self._validate_positive_amount(amount_cents)
        normalized_category = self._validate_text(category, "Category", maximum_length=50)
        normalized_note = self._validate_text(note, "Note", maximum_length=200, allow_empty=True)
        if not isinstance(transaction_date, date):
            raise InputValidationError("Choose a valid date.")

        with self.engine.begin() as connection:
            balance = self._locked_balance(connection, normalized_account)
            if kind is TransactionKind.EXPENSE:
                if amount_cents > balance:
                    raise InsufficientFundsError(
                        f"This expense exceeds the {normalized_account.value} balance."
                    )
                new_balance = balance - amount_cents
            else:
                new_balance = balance + amount_cents

            connection.execute(
                update(accounts)
                .where(accounts.c.account == normalized_account.value)
                .values(balance_cents=new_balance, updated_at=func.now())
            )
            result = connection.execute(
                insert(transactions).values(
                    transaction_date=transaction_date,
                    account=normalized_account.value,
                    kind=kind.value,
                    amount_cents=amount_cents,
                    category=normalized_category,
                    note=normalized_note,
                )
            )
            return int(result.inserted_primary_key[0])

    def list_transactions(
        self,
        *,
        start_date: date | None = None,
        limit: int = 500,
    ) -> list[TransactionRecord]:
        if not 1 <= limit <= 1_000:
            raise InputValidationError("History limit must be between 1 and 1,000.")
        statement = select(transactions)
        if start_date is not None:
            statement = statement.where(transactions.c.transaction_date >= start_date)
        statement = statement.order_by(
            transactions.c.transaction_date.desc(),
            transactions.c.created_at.desc(),
            transactions.c.id.desc(),
        ).limit(limit)
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [
            TransactionRecord(
                id=row["id"],
                transaction_date=row["transaction_date"],
                account=Account(row["account"]),
                kind=TransactionKind(row["kind"]),
                amount_cents=row["amount_cents"],
                category=row["category"],
                note=row["note"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def get_daily_summary(self, transaction_date: date) -> DailySummary:
        balances = self.get_balances()
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(
                    transactions.c.transaction_date,
                    transactions.c.account,
                    transactions.c.kind,
                    transactions.c.amount_cents,
                ).where(transactions.c.transaction_date >= transaction_date)
            ).all()

        online_spend = 0
        offline_spend = 0
        bank_closing = balances.bank_cents
        cash_closing = balances.cash_cents

        for row in rows:
            account = Account(row.account)
            kind = TransactionKind(row.kind)
            if row.transaction_date == transaction_date and kind is TransactionKind.EXPENSE:
                if account is Account.BANK:
                    online_spend += row.amount_cents
                else:
                    offline_spend += row.amount_cents
            if row.transaction_date > transaction_date:
                reversal = (
                    row.amount_cents if kind is TransactionKind.EXPENSE else -row.amount_cents
                )
                if account is Account.BANK:
                    bank_closing += reversal
                else:
                    cash_closing += reversal

        return DailySummary(
            transaction_date=transaction_date,
            online_spend_cents=online_spend,
            offline_spend_cents=offline_spend,
            bank_closing_cents=bank_closing,
            cash_closing_cents=cash_closing,
        )

    def get_daily_spending(self, start_date: date) -> list[DailySpending]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(
                    transactions.c.transaction_date,
                    transactions.c.account,
                    func.sum(transactions.c.amount_cents).label("spent_cents"),
                )
                .where(
                    transactions.c.kind == TransactionKind.EXPENSE.value,
                    transactions.c.transaction_date >= start_date,
                )
                .group_by(transactions.c.transaction_date, transactions.c.account)
                .order_by(transactions.c.transaction_date)
            ).all()

        spending_by_date: dict[date, dict[Account, int]] = {}
        for row in rows:
            daily_accounts = spending_by_date.setdefault(row.transaction_date, {})
            daily_accounts[Account(row.account)] = row.spent_cents
        return [
            DailySpending(
                transaction_date=transaction_date,
                online_spend_cents=account_spending.get(Account.BANK, 0),
                offline_spend_cents=account_spending.get(Account.CASH, 0),
            )
            for transaction_date, account_spending in spending_by_date.items()
        ]

    def purge_expired(self, as_of: date) -> int:
        cutoff = retention_cutoff(as_of)
        with self.engine.begin() as connection:
            result = connection.execute(
                delete(transactions).where(transactions.c.transaction_date < cutoff)
            )
        return result.rowcount or 0

    @staticmethod
    def _locked_balance(connection: Connection, account: Account) -> int:
        balance = connection.scalar(
            select(accounts.c.balance_cents)
            .where(accounts.c.account == account.value)
            .with_for_update()
        )
        if balance is None:
            raise NotInitializedError("Set up the household balances first.")
        return balance

    def _harden_postgres_tables(self) -> None:
        """Keep direct-connection tables inaccessible through Supabase's public API roles."""
        if self.engine.dialect.name != "postgresql":
            return

        with self.engine.begin() as connection:
            exposed_roles = set(
                connection.scalars(
                    text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')")
                )
            )
            for table_name in (accounts.name, settings.name, transactions.name):
                connection.exec_driver_sql(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY')
                connection.exec_driver_sql(
                    f'REVOKE ALL PRIVILEGES ON TABLE "{table_name}" FROM PUBLIC'
                )
                for role_name in sorted(exposed_roles):
                    connection.exec_driver_sql(
                        f'REVOKE ALL PRIVILEGES ON TABLE "{table_name}" FROM "{role_name}"'
                    )

    @staticmethod
    def _validate_account(account: Account) -> Account:
        try:
            return Account(account)
        except ValueError as exc:
            raise InputValidationError("Choose bank or cash.") from exc

    @staticmethod
    def _validate_positive_amount(amount_cents: int) -> None:
        if isinstance(amount_cents, bool) or not isinstance(amount_cents, int) or amount_cents <= 0:
            raise InputValidationError("Amount must be a positive whole number of cents.")

    @staticmethod
    def _validate_nonnegative_balance(balance_cents: int) -> None:
        if (
            isinstance(balance_cents, bool)
            or not isinstance(balance_cents, int)
            or balance_cents < 0
        ):
            raise InputValidationError("Opening balances cannot be negative.")

    @staticmethod
    def _validate_text(
        value: str,
        label: str,
        *,
        maximum_length: int,
        allow_empty: bool = False,
    ) -> str:
        if not isinstance(value, str):
            raise InputValidationError(f"{label} must be text.")
        normalized = value.strip()
        if not normalized and not allow_empty:
            raise InputValidationError(f"{label} is required.")
        if len(normalized) > maximum_length:
            raise InputValidationError(f"{label} is too long.")
        return normalized
