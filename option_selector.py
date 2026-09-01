```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping


class OptionSelectionError(Exception):
    """Raised when a suitable option contract cannot be selected."""


@dataclass(frozen=True)
class OptionContract:
    expiry: date
    strike: float
    option_type: str
    premium: float = 0.0
    lot_size: int = 65
    selection_mode: str = "ATM"

    @property
    def symbol(self) -> str:
        return (
            f"NIFTY {self.expiry.isoformat()} "
            f"{self.strike:g}{self.option_type.upper()}"
        )


def _normalise_option_type(option_type: str) -> str:
    value = str(option_type).strip().upper()

    if value not in {"CE", "PE"}:
        raise OptionSelectionError(
            "option_type must be CE or PE."
        )

    return value


def _normalise_selection_mode(selection_mode: str) -> str:
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
        (float(nifty_price) / strike_interval + 0.5)
    ) * strike_interval


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
    option_type = _normalise_option_type(option_type)
    selection_mode = _normalise_selection_mode(selection_mode)

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


def _parse_expiry(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if value is None:
        return None

    text = str(value).strip()

    for fmt in (
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    return None


def _payload_rows(
    option_chain_payload: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    records = option_chain_payload.get("records", {})

    if not isinstance(records, Mapping):
        raise OptionSelectionError(
            "Option-chain records are invalid."
        )

    rows = records.get("data", [])

    if not isinstance(rows, list):
        raise OptionSelectionError(
            "Option-chain data is invalid."
        )

    return [
        row
        for row in rows
        if isinstance(row, Mapping)
    ]


def _find_live_contract(
    option_chain_payload: Mapping[str, Any],
    nifty_price: float,
    expiry: date,
    option_type: str,
    selection_mode: str,
    strike_interval: int,
    lot_size: int,
) -> OptionContract:
    option_type = _normalise_option_type(option_type)
    selection_mode = _normalise_selection_mode(selection_mode)

    requested_strike = select_strike(
        nifty_price=nifty_price,
        option_type=option_type,
        selection_mode=selection_mode,
        strike_interval=strike_interval,
    )

    candidates: list[OptionContract] = []

    for row in _payload_rows(option_chain_payload):
        row_expiry = _parse_expiry(
            row.get("expiryDate")
            or row.get("expiry")
        )

        if row_expiry != expiry:
            continue

        try:
            strike = float(row["strikePrice"])
        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            continue

        leg = row.get(option_type)

        if not isinstance(leg, Mapping):
            continue

        premium = leg.get("lastPrice")

        if premium is None:
            premium = leg.get("close")

        try:
            premium = float(premium)
        except (
            TypeError,
            ValueError,
        ):
            continue

        if premium <= 0:
            continue

        candidates.append(
            OptionContract(
                expiry=expiry,
                strike=strike,
                option_type=option_type,
                premium=premium,
                lot_size=lot_size,
                selection_mode=selection_mode,
            )
        )

    if not candidates:
        raise OptionSelectionError(
            "Requested option contract is not available "
            "with a valid live price."
        )

    exact = [
        contract
        for contract in candidates
        if contract.strike == requested_strike
    ]

    if exact:
        return exact[0]

    nearest = min(
        candidates,
        key=lambda contract: abs(
            contract.strike - requested_strike
        ),
    )

    raise OptionSelectionError(
        "Requested option contract is not available "
        f"at strike {requested_strike}."
    )


def select_contract(
    nifty_price: float,
    expiry: date,
    option_type: str,
    selection_mode: str = "ATM",
    strike_interval: int = 50,
    option_chain: Any = None,
    lot_size: int = 65,
) -> OptionContract:
    """
    Backward-compatible historical contract selector.

    The existing repository API uses nifty_price= and expiry=.
    An option-chain payload is optional for compatibility.
    """
    option_type = _normalise_option_type(option_type)
    selection_mode = _normalise_selection_mode(selection_mode)

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

    if option_chain is None:
        return OptionContract(
            expiry=expiry,
            strike=strike,
            option_type=option_type,
            premium=0.0,
            lot_size=lot_size,
            selection_mode=selection_mode,
        )

    return select_live_contract(
        option_chain_payload=option_chain,
        nifty_price=nifty_price,
        expiry=expiry,
        option_type=option_type,
        selection_mode=selection_mode,
        strike_interval=strike_interval,
        lot_size=lot_size,
    )


def select_atm_contract(
    nifty_price: float,
    expiry: date,
    option_type: str,
    strike_interval: int = 50,
    lot_size: int = 65,
) -> OptionContract:
    return select_contract(
        nifty_price=nifty_price,
        expiry=expiry,
        option_type=option_type,
        selection_mode="ATM",
        strike_interval=strike_interval,
        lot_size=lot_size,
    )


def select_live_contract(
    option_chain_payload: Mapping[str, Any],
    nifty_price: float,
    expiry: date,
    option_type: str,
    selection_mode: str = "ATM",
    strike_interval: int = 50,
    lot_size: int = 65,
) -> OptionContract:
    if not isinstance(
        option_chain_payload,
        Mapping,
    ):
        raise OptionSelectionError(
            "option_chain_payload must be a mapping."
        )

    if nifty_price <= 0:
        raise OptionSelectionError(
            "nifty_price must be positive."
        )

    return _find_live_contract(
        option_chain_payload=option_chain_payload,
        nifty_price=nifty_price,
        expiry=expiry,
        option_type=option_type,
        selection_mode=selection_mode,
        strike_interval=strike_interval,
        lot_size=lot_size,
    )
```
