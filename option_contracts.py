from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Iterable, List, Optional, Set, Tuple

from expiry_calendar import get_monthly_expiry_for_trade


ContractKey = Tuple[date, date, str, float]


def normalize_option_type(option_type: str) -> str:
    value = option_type.strip().upper()

    if value not in {"CE", "PE"}:
        raise ValueError("option_type must be CE or PE")

    return value


def normalize_strike(strike: float) -> float:
    value = float(strike)

    if value <= 0:
        raise ValueError("strike must be positive")

    return value


def normalize_expiry(value: object) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None

    return None


def get_row_expiry(
    row: Dict[str, object],
) -> Optional[date]:
    return normalize_expiry(
        row.get("expiry")
    )


def get_row_contract_key(
    row: Dict[str, object],
) -> Optional[ContractKey]:
    timestamp = row.get("timestamp")

    if not isinstance(
        timestamp,
        datetime,
    ):
        return None

    expiry = get_row_expiry(row)

    if expiry is None:
        return None

    try:
        option_type = normalize_option_type(
            str(row.get("option_type", ""))
        )

        strike = normalize_strike(
            float(row.get("strike", 0))
        )

    except (TypeError, ValueError):
        return None

    return (
        timestamp.date(),
        expiry,
        option_type,
        strike,
    )


def discover_contracts(
    rows: Iterable[Dict[str, object]],
) -> Set[ContractKey]:
    contracts: Set[ContractKey] = set()

    for row in rows:
        key = get_row_contract_key(row)

        if key is not None:
            contracts.add(key)

    return contracts


def contracts_for_date(
    rows: Iterable[Dict[str, object]],
    trading_date: date,
) -> List[ContractKey]:
    contracts = discover_contracts(rows)

    return sorted(
        key
        for key in contracts
        if key[0] == trading_date
    )


def contracts_for_expiry(
    rows: Iterable[Dict[str, object]],
    trading_date: date,
    expiry: date,
) -> List[ContractKey]:
    contracts = discover_contracts(rows)

    return sorted(
        key
        for key in contracts
        if key[0] == trading_date
        and key[1] == expiry
    )


def find_contract(
    rows: Iterable[Dict[str, object]],
    trading_date: date,
    expiry: date,
    option_type: str,
    strike: float,
) -> Optional[ContractKey]:
    option_type = normalize_option_type(
        option_type
    )

    strike = normalize_strike(
        strike
    )

    target = (
        trading_date,
        expiry,
        option_type,
        strike,
    )

    contracts = discover_contracts(rows)

    if target not in contracts:
        return None

    return target


def find_monthly_contract(
    rows: Iterable[Dict[str, object]],
    trading_date: date,
    option_type: str,
    strike: float,
) -> Optional[ContractKey]:
    """
    Find the monthly contract selected by the historical
    expiry calendar.

    The contract must actually exist in the supplied rows.
    """

    expiry = get_monthly_expiry_for_trade(
        trading_date
    )

    return find_contract(
        rows,
        trading_date,
        expiry,
        option_type,
        strike,
    )


def available_strikes(
    rows: Iterable[Dict[str, object]],
    trading_date: date,
    expiry: date,
    option_type: str,
) -> List[float]:
    option_type = normalize_option_type(
        option_type
    )

    contracts = contracts_for_expiry(
        rows,
        trading_date,
        expiry,
    )

    return sorted(
        {
            strike
            for _, _, contract_type, strike
            in contracts
            if contract_type == option_type
        }
    )


def has_contract(
    rows: Iterable[Dict[str, object]],
    trading_date: date,
    expiry: date,
    option_type: str,
    strike: float,
) -> bool:
    return (
        find_contract(
            rows,
            trading_date,
            expiry,
            option_type,
            strike,
        )
        is not None
    )