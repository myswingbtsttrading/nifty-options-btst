from __future__ import annotations

from datetime import date, timedelta
from typing import Optional


def last_thursday(year: int, month: int) -> date:
    """Return the last Thursday of a given month."""

    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)

    current = next_month - timedelta(days=1)

    while current.weekday() != 3:  # Thursday
        current -= timedelta(days=1)

    return current


def standard_monthly_expiry(
    year: int,
    month: int,
) -> date:
    """
    Return the standard monthly NIFTY expiry used by the
    historical dataset.

    For the historical period covered by our initial dataset,
    the monthly expiry is the last Thursday of the month.
    """

    return last_thursday(year, month)


def previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12

    return year, month - 1


def next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1

    return year, month + 1


def candidate_monthly_expiries(
    trading_date: date,
) -> list[date]:
    """
    Return monthly expiry candidates around a trading date.

    The list is ordered chronologically.
    """

    candidates = []

    for year, month in (
        previous_month(
            trading_date.year,
            trading_date.month,
        ),
        (trading_date.year, trading_date.month),
        next_month(
            trading_date.year,
            trading_date.month,
        ),
    ):
        candidates.append(
            standard_monthly_expiry(
                year,
                month,
            )
        )

    return sorted(
        set(candidates)
    )


def get_nearest_expiry(
    trading_date: date,
) -> Optional[date]:
    """
    Return the first monthly expiry on or after
    the trading date.
    """

    candidates = candidate_monthly_expiries(
        trading_date
    )

    valid = [
        expiry
        for expiry in candidates
        if expiry >= trading_date
    ]

    if not valid:
        return None

    return min(valid)


def get_monthly_expiry_for_trade(
    trading_date: date,
) -> date:
    """
    Return the monthly expiry applicable to a trade
    opened on the supplied trading date.

    The expiry cannot be earlier than the trade date.
    """

    expiry = get_nearest_expiry(
        trading_date
    )

    if expiry is None:
        raise ValueError(
            f"No expiry found for {trading_date}"
        )

    return expiry