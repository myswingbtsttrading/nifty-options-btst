from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Iterable, List, Optional, Set

from expiry_calendar import get_monthly_expiry_for_trade


def extract_contract_expiries(
    rows: Iterable[Dict[str, object]],
) -> Set[date]:
    """
    Extract explicit expiry dates from normalized option rows.

    Rows may contain expiry as:
        - datetime.date
        - datetime.datetime
        - ISO date string
    """

    expiries: Set[date] = set()

    for row in rows:
        value = row.get("expiry")

        if isinstance(value, datetime):
            expiries.add(value.date())

        elif isinstance(value, date):
            expiries.add(value)

        elif isinstance(value, str):
            try:
                expiries.add(
                    date.fromisoformat(value)
                )
            except ValueError:
                continue

    return expiries


def validate_expected_expiry(
    trading_date: date,
    available_expiries: Iterable[date],
) -> date:
    """
    Validate that the calendar-selected expiry actually exists
    in the supplied contract universe.
    """

    expected = get_monthly_expiry_for_trade(
        trading_date
    )

    available = set(
        available_expiries
    )

    if expected not in available:
        raise ValueError(
            "Expected expiry "
            f"{expected.isoformat()} "
            "is not present in the available "
            "contract universe."
        )

    if expected < trading_date:
        raise ValueError(
            "Selected expiry is before "
            "the trading date."
        )

    return expected


def validate_contract_expiry(
    trading_date: date,
    expiry: date,
) -> bool:
    """
    Confirm that a contract expiry is valid for
    the supplied trading date.
    """

    if expiry < trading_date:
        return False

    return True


def validate_trade_contract(
    trading_date: date,
    expiry: date,
    option_type: str,
    strike: float,
) -> None:
    """
    Validate the basic contract identity used by
    the BTST strategy.
    """

    if not isinstance(
        trading_date,
        date,
    ):
        raise TypeError(
            "trading_date must be a date"
        )

    if not isinstance(
        expiry,
        date,
    ):
        raise TypeError(
            "expiry must be a date"
        )

    if expiry < trading_date:
        raise ValueError(
            "Contract expiry cannot be "
            "before the trading date."
        )

    normalized_type = option_type.upper()

    if normalized_type not in {
        "CE",
        "PE",
    }:
        raise ValueError(
            "option_type must be CE or PE"
        )

    if float(strike) <= 0:
        raise ValueError(
            "strike must be positive"
        )


def expiry_is_usable_for_overnight_trade(
    trading_date: date,
    next_trading_date: date,
    expiry: date,
) -> bool:
    """
    An overnight contract must remain valid on both
    the entry day and the following trading day.
    """

    if next_trading_date <= trading_date:
        return False

    if expiry < trading_date:
        return False

    if expiry < next_trading_date:
        return False

    return True