from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping


class OptionSelectionError(ValueError):
    """Raised when a suitable option contract cannot be selected."""


@dataclass(frozen=True)
class OptionContract:
    expiry: date
    strike: int
    option_type: str


def _validate_option_type(option_type: str) -> str:
    normalized = str(option_type).strip().upper()

    if normalized not in {"CE", "PE"}:
        raise OptionSelectionError(
            "option_type must be CE or PE."
        )

    return normalized


def _validate_selection_mode(selection_mode: str) -> str:
    normalized = str(selection_mode).strip().upper()

    if normalized not in {"ATM", "ITM", "OTM"}:
        raise OptionSelectionError(
            "selection_mode must be ATM, ITM, or OTM."
        )

    return normalized


def _validate_strike_interval(strike_interval: int) -> int:
    if strike_interval <= 0:
        raise OptionSelectionError(
            "strike_interval must be positive."
        )

    return int(strike_interval)


def round_to_strike(
    nifty_price: float,
    strike_interval: int = 50,
) -> int:
    """Backward-compatible NIFTY strike rounding."""
    if nifty_price <= 0:
        raise OptionSelectionError(
            "nifty_price must be positive."
        )

    interval = _validate_strike_interval(
        strike_interval
    )

    return int(
        round(
            float(nifty_price) / interval
        ) * interval
    )


def select_atm_strike(
    nifty_price: float,
    strike_interval: int = 50,
) -> int:
    return round_to_strike(
        nifty_price=nifty_price,
        strike_interval=strike_interval,
    )


def select_strike(
    nifty_price: float,
    option_type: str,
    selection_mode: str = "ATM",
    strike_interval: int = 50,
) -> int:
    """
    Select ATM / ITM / OTM strike for a directional option.

    CE:
        ITM = lower strike
        OTM = higher strike

    PE:
        ITM = higher strike
        OTM = lower strike
    """
    normalized_type = _validate_option_type(
        option_type
    )

    mode = _validate_selection_mode(
        selection_mode
    )

    atm = select_atm_strike(
        nifty_price=nifty_price,
        strike_interval=strike_interval,
    )

    interval = _validate_strike_interval(
        strike_interval
    )

    if mode == "ATM":
        return atm

    if normalized_type == "CE":
        if mode == "ITM":
            return atm - interval

        return atm + interval

    if mode == "ITM":
        return atm + interval

    return atm - interval


def select_atm_contract(
    nifty_price: float,
    expiry: date,
    option_type: str,
    strike_interval: int = 50,
) -> OptionContract:
    return select_contract(
        nifty_price=nifty_price,
        expiry=expiry,
        option_type=option_type,
        selection_mode="ATM",
        strike_interval=strike_interval,
    )


def select_contract(
    nifty_price: float,
    expiry: date,
    option_type: str,
    selection_mode: str = "ATM",
    strike_interval: int = 50,
) -> OptionContract:
    """
    Backward-compatible general contract selector.

    Supports ATM, ITM and OTM selection.
    """
    normalized_type = _validate_option_type(
        option_type
    )

    if not isinstance(expiry, date):
        raise OptionSelectionError(
            "expiry must be a date."
        )

    strike = select_strike(
        nifty_price=nifty_price,
        option_type=normalized_type,
        selection_mode=selection_mode,
        strike_interval=strike_interval,
    )

    return OptionContract(
        expiry=expiry,
        strike=strike,
        option_type=normalized_type,
    )


def _row_expiry(
    row: Mapping[str, Any],
) -> date | None:
    value = row.get("expiryDate")

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if value is None:
        return None

    text = str(value).strip()

    for fmt in (
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(
                text,
                fmt,
            ).date()
        except ValueError:
            continue

    return None


def _available_contracts(
    payload: Mapping[str, Any],
    expiry: date,
) -> list[OptionContract]:
    records = payload.get(
        "records",
        {},
    )

    if not isinstance(
        records,
        Mapping,
    ):
        raise OptionSelectionError(
            "Option-chain records are invalid."
        )

    rows = records.get(
        "data",
        [],
    )

    if not isinstance(
        rows,
        list,
    ):
        raise OptionSelectionError(
            "Option-chain data is invalid."
        )

    contracts: list[OptionContract] = []

    for row in rows:
        if not isinstance(
            row,
            Mapping,
        ):
            continue

        if _row_expiry(row) != expiry:
            continue

        try:
            strike = int(
                float(
                    row["strikePrice"]
                )
            )
        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            continue

        for option_type in ("CE", "PE"):
            leg = row.get(option_type)

            if not isinstance(
                leg,
                Mapping,
            ):
                continue

            last_price = (
                leg.get("lastPrice")
                if leg.get("lastPrice") is not None
                else leg.get("close")
            )

            if last_price is None:
                continue

            try:
                price = float(last_price)
            except (
                TypeError,
                ValueError,
            ):
                continue

            if price <= 0:
                continue

            contracts.append(
                OptionContract(
                    expiry=expiry,
                    strike=strike,
                    option_type=option_type,
                )
            )

    return contracts


def select_live_contract(
    option_chain_payload: Mapping[str, Any],
    nifty_price: float,
    expiry: date,
    option_type: str,
    selection_mode: str = "ATM",
    strike_interval: int = 50,
) -> OptionContract:
    """
    Select the requested contract only when it actually exists
    in the live NSE option-chain payload with a valid price.
    """
    candidate = select_contract(
        nifty_price=nifty_price,
        expiry=expiry,
        option_type=option_type,
        selection_mode=selection_mode,
        strike_interval=strike_interval,
    )

    available = _available_contracts(
        option_chain_payload,
        expiry,
    )

    if candidate in available:
        return candidate

    raise OptionSelectionError(
        "Requested option contract is not available "
        "with a valid live price: "
        f"{candidate.option_type} "
        f"{candidate.strike} "
        f"{candidate.expiry}."
    )