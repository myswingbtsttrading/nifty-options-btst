from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Optional

from live_market_data import (
    LiveMarketDataError,
    LiveOptionQuote,
    LiveUnderlyingQuote,
)
from nse_live_data import (
    build_option_chain_snapshot,
    fetch_nifty_option_chain,
    fetch_nifty_quote,
    find_option_quote,
    nearest_nifty_expiry,
)


@dataclass(frozen=True)
class LiveSignalSnapshot:
    timestamp: datetime
    nifty_price: float
    previous_close: float
    expiry: date
    option_chain: Any


def build_live_signal_snapshot(
    session=None,
    today: Optional[date] = None,
) -> LiveSignalSnapshot:
    """
    Obtain the complete 3 PM decision snapshot.

    This function deliberately stops before strategy execution.
    It only assembles validated live inputs.
    """

    quote = fetch_nifty_quote(
        session=session
    )

    option_chain = fetch_nifty_option_chain(
        session=session
    )

    expiry = nearest_nifty_expiry(
        option_chain,
        today=today,
    )

    snapshot = build_option_chain_snapshot(
        option_chain_payload=option_chain,
        nifty_price=quote.price,
        expiry=expiry,
        strikes_each_side=5,
    )

    return LiveSignalSnapshot(
        timestamp=quote.timestamp,
        nifty_price=quote.price,
        previous_close=quote.previous_close,
        expiry=expiry,
        option_chain=snapshot,
    )


def select_atm_strike(
    nifty_price: float,
    strike_interval: int = 50,
) -> int:
    if nifty_price <= 0:
        raise ValueError(
            "nifty_price must be positive."
        )

    if strike_interval <= 0:
        raise ValueError(
            "strike_interval must be positive."
        )

    return int(
        round(
            nifty_price / strike_interval
        )
        * strike_interval
    )


def get_atm_option_quote(
    option_chain_payload: Mapping[str, Any],
    nifty_price: float,
    expiry: date,
    option_type: str,
    strike_interval: int = 50,
) -> LiveOptionQuote:
    strike = select_atm_strike(
        nifty_price=nifty_price,
        strike_interval=strike_interval,
    )

    return find_option_quote(
        option_chain_payload=option_chain_payload,
        expiry=expiry,
        strike=strike,
        option_type=option_type,
    )