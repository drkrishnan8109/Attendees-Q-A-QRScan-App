"""Domain types shared by persistence and UI code."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class Account(StrEnum):
    BANK = "bank"
    CASH = "cash"


class TransactionKind(StrEnum):
    EXPENSE = "expense"
    DEPOSIT = "deposit"


class BudgetError(Exception):
    """Base exception for expected budget operations."""


class NotInitializedError(BudgetError):
    """Raised when household setup has not been completed."""


class AlreadyInitializedError(BudgetError):
    """Raised when household setup is attempted more than once."""


class InsufficientFundsError(BudgetError):
    """Raised when an expense exceeds the selected account balance."""


class InputValidationError(BudgetError):
    """Raised when an operation contains invalid external input."""


@dataclass(frozen=True)
class Balances:
    bank_cents: int
    cash_cents: int

    @property
    def total_cents(self) -> int:
        return self.bank_cents + self.cash_cents


@dataclass(frozen=True)
class TransactionRecord:
    id: int
    transaction_date: date
    account: Account
    kind: TransactionKind
    amount_cents: int
    category: str
    note: str
    created_at: datetime


@dataclass(frozen=True)
class DailySummary:
    transaction_date: date
    online_spend_cents: int
    offline_spend_cents: int
    bank_closing_cents: int
    cash_closing_cents: int


@dataclass(frozen=True)
class DailySpending:
    transaction_date: date
    online_spend_cents: int
    offline_spend_cents: int
