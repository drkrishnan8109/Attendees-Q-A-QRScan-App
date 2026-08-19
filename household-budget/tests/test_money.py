from datetime import date
from decimal import Decimal

import pytest

from budget_app.money import (
    AmountError,
    format_money,
    parse_amount_to_cents,
    parse_balance_to_cents,
)
from budget_app.retention import retention_cutoff


@pytest.mark.parametrize(
    ("raw_amount", "expected_cents"),
    [
        ("0.01", 1),
        ("12.50", 1_250),
        (Decimal("999.99"), 99_999),
        (12, 1_200),
        (12.5, 1_250),
    ],
)
def test_parse_amount_to_cents_uses_exact_minor_units(raw_amount, expected_cents):
    assert parse_amount_to_cents(raw_amount) == expected_cents


@pytest.mark.parametrize("raw_amount", ["", "0", "-1", "1.005", "abc", float("inf")])
def test_parse_amount_to_cents_rejects_invalid_values(raw_amount):
    with pytest.raises(AmountError):
        parse_amount_to_cents(raw_amount)


@pytest.mark.parametrize(
    ("cents", "currency", "expected"),
    [
        (123_456, "EUR", "€1,234.56"),
        (-250, "INR", "-₹2.50"),
        (500, "CAD", "CAD 5.00"),
    ],
)
def test_format_money_uses_the_household_currency(cents, currency, expected):
    assert format_money(cents, currency) == expected


@pytest.mark.parametrize(("raw_amount", "expected_cents"), [("0", 0), ("50.25", 5_025)])
def test_parse_balance_to_cents_allows_zero(raw_amount, expected_cents):
    assert parse_balance_to_cents(raw_amount) == expected_cents


def test_parse_balance_to_cents_rejects_negative_values():
    with pytest.raises(AmountError):
        parse_balance_to_cents("-0.01")


def test_retention_cutoff_is_six_calendar_months_and_clamps_month_end():
    assert retention_cutoff(date(2026, 8, 19)) == date(2026, 2, 19)
    assert retention_cutoff(date(2025, 8, 31)) == date(2025, 2, 28)
    assert retention_cutoff(date(2024, 8, 31)) == date(2024, 2, 29)
