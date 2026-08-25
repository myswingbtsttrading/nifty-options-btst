from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping


class OptionSelectionError(ValueError):
    """Raised when an option contract cannot be selected."""


@dataclass(frozen=True)
class OptionContract:
    expiry: date
    strike: int
    option_type: str
    selection_mode: str = "ATM"


def _validate_option_type(option_type: str) -> str:
    value = str(option_type).strip().upper()

    if value not in {"CE", "PE"}:
        raise OptionSelectionError(
            "option_type must be CE or PE."
        )

    return value


def _validate_selection_mode(selection_mode: str) -> str:
    value = str(selection_mode).strip().upper()

    if value not in {"ATM", "ITM", "OTM"}:
        raise OptionSelectionError(
            "selection_mode must be ATM, ITM, or OTM."
        )

    return value


def round_to_strike(
    nifty_price: float,
    strike_interval: int = 50,
) -> int:
    if nifty_price <= 0:
        raise OptionSelectionError(
            "nifty_price must be positive."
        )

    if strike_interval <= 0:
        raise OptionSelectionError(
            "strike_interval must be positive."
        )

    return int(
        round(
            float(nifty_price) / strike_interval
        ) * strike_interval
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
    option_type = _validate_option_type(option_type)
    selection_mode = _validate_selection_mode(selection_mode)

    atm = select_atm_strike(
        nifty_price=nifty_price,
        strike_interval=strike_interval,
    )

    if selection_mode == "ATM":
        return atm

    if option_type == "CE":
        if selection_mode == "ITM":
            return atm - strike_interval
        return atm + strike_interval

    if selection_mode == "ITM":
        return atm + strike_interval

    return atm - strike_interval


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
    option_type = _validate_option_type(option_type)
    selection_mode = _validate_selection_mode(selection_mode)

    if not isinstance(expiry, date):
        raise OptionSelectionError(
            "expiry must be a date."
        )

    strike = select_strike(
        nifty_price=nifty_price,
        option_type=option_type,
        selection_mode=selection_mode,
        strike_interval=strike_interval,
    )

    return OptionContract(
        expiry=expiry,
        strike=strike,
        option_type=option_type,
        selection_mode=selection_mode,
    )


def _parse_expiry(value: Any) -> date | None:
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
    records = payload.get("records", {})

    if not isinstance(records, Mapping):
        raise OptionSelectionError(
            "Option-chain records are invalid."
        )

    rows = records.get("data", [])

    if not isinstance(rows, list):
        raise OptionSelectionError(
            "Option-chain data is invalid."
        )

    contracts: list[OptionContract] = []

    for row in rows:
        if not isinstance(row, Mapping):
            continue

        row_expiry = _parse_expiry(
            row.get("expiryDate")
        )

        if row_expiry != expiry:
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

            if not isinstance(leg, Mapping):
                continue

            last_price = leg.get("lastPrice")

            if last_price is None:
                last_price = leg.get("close")

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
                    selection_mode="ATM",
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
    Select a requested contract only if it exists in the
    supplied live option-chain payload and has a valid price.
    """
    requested = select_contract(
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

    for contract in available:
        if (
            contract.strike == requested.strike
            and contract.option_type == requested.option_type
            and contract.expiry == requested.expiry
        ):
            return OptionContract(
                expiry=contract.expiry,
                strike=contract.strike,
                option_type=contract.option_type,
                selection_mode=selection_mode,
            )

    raise OptionSelectionError(
        "Requested option contract is not available "
        "with a valid live price: "
        f"{requested.option_type} "
        f"{requested.strike} "
        f"{requested.expiry}."
    )