from dataclasses import dataclass
from datetime import date
from typing import Literal

from config import STRIKE_INTERVAL


OptionType = Literal["CE", "PE"]
StrikeMode = Literal["ATM", "ITM", "OTM"]


@dataclass(frozen=True)
class OptionContract:
    expiry: date
    strike: float
    option_type: str
    selection_mode: str = "ATM"

    @property
    def symbol_suffix(self) -> str:
        return f"{int(self.strike)}{self.option_type}"


def round_to_strike(
    nifty_price: float,
) -> float:
    if nifty_price <= 0:
        raise ValueError(
            "NIFTY price must be positive."
        )

    if STRIKE_INTERVAL <= 0:
        raise ValueError(
            "STRIKE_INTERVAL must be positive."
        )

    return (
        round(
            nifty_price / STRIKE_INTERVAL
        )
        * STRIKE_INTERVAL
    )


def _validate_option_type(
    option_type: str,
) -> str:
    option_type = option_type.upper()

    if option_type not in {"CE", "PE"}:
        raise ValueError(
            "option_type must be CE or PE."
        )

    return option_type


def _validate_selection_mode(
    selection_mode: str,
) -> str:
    selection_mode = selection_mode.upper()

    if selection_mode not in {
        "ATM",
        "ITM",
        "OTM",
    }:
        raise ValueError(
            "selection_mode must be ATM, ITM or OTM."
        )

    return selection_mode


def _strike_for_mode(
    atm_strike: float,
    option_type: str,
    selection_mode: str,
) -> float:
    """
    Calculate the strike relative to ATM.

    CE:
        ATM = ATM
        ITM = ATM - interval
        OTM = ATM + interval

    PE:
        ATM = ATM
        ITM = ATM + interval
        OTM = ATM - interval
    """

    if selection_mode == "ATM":
        return atm_strike

    if option_type == "CE":
        if selection_mode == "ITM":
            return atm_strike - STRIKE_INTERVAL

        return atm_strike + STRIKE_INTERVAL

    if selection_mode == "ITM":
        return atm_strike + STRIKE_INTERVAL

    return atm_strike - STRIKE_INTERVAL


def select_contract(
    nifty_price: float,
    expiry: date,
    option_type: str,
    selection_mode: str = "ATM",
) -> OptionContract:
    """
    Select a NIFTY option contract relative to ATM.

    This function performs contract selection only.

    It does not:
        - fetch option prices
        - evaluate liquidity
        - calculate target/stop
        - calculate quantity

    Those responsibilities are implemented in later steps.
    """

    if nifty_price <= 0:
        raise ValueError(
            "NIFTY price must be positive."
        )

    if not isinstance(expiry, date):
        raise ValueError(
            "expiry must be a datetime.date."
        )

    option_type = _validate_option_type(
        option_type
    )

    selection_mode = _validate_selection_mode(
        selection_mode
    )

    atm_strike = round_to_strike(
        nifty_price
    )

    strike = _strike_for_mode(
        atm_strike=atm_strike,
        option_type=option_type,
        selection_mode=selection_mode,
    )

    if strike <= 0:
        raise ValueError(
            "Calculated strike must be positive."
        )

    return OptionContract(
        expiry=expiry,
        strike=strike,
        option_type=option_type,
        selection_mode=selection_mode,
    )


def select_atm_contract(
    nifty_price: float,
    expiry: date,
    option_type: str,
) -> OptionContract:
    """
    Backward-compatible ATM selector.
    """

    return select_contract(
        nifty_price=nifty_price,
        expiry=expiry,
        option_type=option_type,
        selection_mode="ATM",
    )


def select_itm_contract(
    nifty_price: float,
    expiry: date,
    option_type: str,
) -> OptionContract:
    """
    Select one strike ITM.
    """

    return select_contract(
        nifty_price=nifty_price,
        expiry=expiry,
        option_type=option_type,
        selection_mode="ITM",
    )


def select_otm_contract(
    nifty_price: float,
    expiry: date,
    option_type: str,
) -> OptionContract:
    """
    Select one strike OTM.
    """

    return select_contract(
        nifty_price=nifty_price,
        expiry=expiry,
        option_type=option_type,
        selection_mode="OTM",
    )