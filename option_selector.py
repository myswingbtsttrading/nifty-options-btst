from __future__ import annotations

from dataclasses import dataclass
from datetime import date


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
    option_type = _validate_option_type(
        option_type
    )

    selection_mode = _validate_selection_mode(
        selection_mode
    )

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
    option_type = _validate_option_type(
        option_type
    )

    selection_mode = _validate_selection_mode(
        selection_mode
    )

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