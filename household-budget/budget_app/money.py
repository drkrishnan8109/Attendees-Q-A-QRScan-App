"""Exact money parsing and display helpers."""

from decimal import Decimal, InvalidOperation

MINOR_UNIT = Decimal("0.01")
MAX_AMOUNT_CENTS = 99_999_999_999_999
CURRENCY_SYMBOLS = {
    "EUR": "€",
    "GBP": "£",
    "INR": "₹",
    "USD": "$",
}


class AmountError(ValueError):
    """Raised when a money amount cannot be represented safely."""


def parse_amount_to_cents(raw_amount: str | int | float | Decimal) -> int:
    """Convert a positive decimal amount to exact integer minor units."""
    return _parse_to_cents(raw_amount, allow_zero=False)


def parse_balance_to_cents(raw_amount: str | int | float | Decimal) -> int:
    """Convert a nonnegative opening balance to exact integer minor units."""
    return _parse_to_cents(raw_amount, allow_zero=True)


def _parse_to_cents(
    raw_amount: str | int | float | Decimal,
    *,
    allow_zero: bool,
) -> int:
    if isinstance(raw_amount, str) and not raw_amount.strip():
        raise AmountError("Enter an amount.")

    try:
        amount = Decimal(str(raw_amount).strip())
    except (InvalidOperation, ValueError) as exc:
        raise AmountError("Enter a valid amount.") from exc

    minimum_is_valid = amount >= 0 if allow_zero else amount > 0
    if not amount.is_finite() or not minimum_is_valid:
        requirement = "zero or more" if allow_zero else "greater than zero"
        raise AmountError(f"Amount must be {requirement}.")

    try:
        rounded_amount = amount.quantize(MINOR_UNIT)
    except InvalidOperation as exc:
        raise AmountError("Enter a valid amount.") from exc

    if amount != rounded_amount:
        raise AmountError("Use no more than two decimal places.")

    cents = int(rounded_amount * 100)
    if cents > MAX_AMOUNT_CENTS:
        raise AmountError("Amount is too large.")
    return cents


def format_money(cents: int, currency: str) -> str:
    """Format integer minor units using a compact currency label."""
    sign = "-" if cents < 0 else ""
    major_units = Decimal(abs(cents)) / 100
    currency_code = currency.upper()
    symbol = CURRENCY_SYMBOLS.get(currency_code)
    if symbol:
        return f"{sign}{symbol}{major_units:,.2f}"
    return f"{sign}{currency_code} {major_units:,.2f}"
