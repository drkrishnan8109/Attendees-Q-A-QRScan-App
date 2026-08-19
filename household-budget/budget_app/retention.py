"""Calendar-based retention rules."""

import calendar
from datetime import date


def retention_cutoff(as_of: date, months: int = 6) -> date:
    """Return the inclusive earliest date retained after subtracting calendar months."""
    if months < 1:
        raise ValueError("Retention months must be positive.")

    absolute_month = as_of.year * 12 + (as_of.month - 1) - months
    target_year, zero_based_month = divmod(absolute_month, 12)
    target_month = zero_based_month + 1
    target_day = min(as_of.day, calendar.monthrange(target_year, target_month)[1])
    return date(target_year, target_month, target_day)
