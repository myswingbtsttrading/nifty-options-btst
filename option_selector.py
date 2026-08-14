from dataclasses import dataclass
from datetime import date

from config import STRIKE_INTERVAL


@dataclass
class OptionContract:
    expiry: date
    strike: float
    option_type: str


def round_to_strike(
    nifty_price: float,
) -> float:
    if nifty_price <= 0:
        raise ValueError(
            "NIFTY price must be positive."
        )

    return (
        round(
            nifty_price / STRIKE_INTERVAL
        )
        * STRIKE_INTERVAL
    )


def select_atm_contract(
    nifty_price: float,
    expiry: date,
    option_type: str,
) -> OptionContract:
    option_type = option_type.upper()

    if option_type not in {"CE", "PE"}:
        raise ValueError(
            "option_type must be CE or PE."
        )

    return OptionContract(
        expiry=expiry,
        strike=round_to_strike(
            nifty_price
        ),
        option_type=option_type,
    )