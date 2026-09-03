from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Optional

from option_selector import select_live_contract
from live_market_data import LiveMarketDataError
from nse_live_data import (
    build_option_chain_snapshot,
    fetch_nifty_option_chain,
    find_option_quote,
    nearest_nifty_expiry,
)
from yahoo_nifty_data import fetch_nifty_quote
from option_strategy import NiftySignal, generate_signal
from signal_builder import (
    BTSTSignal,
    SignalInput,
    build_btst_signal,
)


@dataclass(frozen=True)
class NiftyIndicators:
    ema20: float
    ema50: float
    rsi: float
    previous_close: float
    adx: Optional[float] = None
    vwap: Optional[float] = None


@dataclass(frozen=True)
class LiveSignalResult:
    signal: BTSTSignal
    nifty_signal: NiftySignal
    indicators: NiftyIndicators


def _validate_prices(
    prices: list[float],
) -> list[float]:
    if len(prices) < 50:
        raise LiveMarketDataError(
            "At least 50 NIFTY prices are required "
            "to calculate EMA20 and EMA50."
        )

    result = []

    for price in prices:
        value = float(price)

        if value <= 0:
            raise LiveMarketDataError(
                "NIFTY historical prices must be positive."
            )

        result.append(value)

    return result


def _ema(
    prices: list[float],
    period: int,
) -> float:
    if len(prices) < period:
        raise LiveMarketDataError(
            f"At least {period} prices are required "
            f"for EMA{period}."
        )

    multiplier = 2.0 / (period + 1)

    value = sum(
        prices[:period]
    ) / period

    for price in prices[period:]:
        value = (
            (price - value) * multiplier
            + value
        )

    return value


def _rsi(
    prices: list[float],
    period: int = 14,
) -> float:
    if len(prices) < period + 1:
        raise LiveMarketDataError(
            f"At least {period + 1} prices are required "
            f"for RSI."
        )

    gains = []
    losses = []

    for previous, current in zip(
        prices[:-1],
        prices[1:],
    ):
        change = current - previous

        gains.append(
            max(change, 0.0)
        )
        losses.append(
            max(-change, 0.0)
        )

    average_gain = (
        sum(gains[:period]) / period
    )

    average_loss = (
        sum(losses[:period]) / period
    )

    for index in range(
        period,
        len(gains),
    ):
        average_gain = (
            (
                average_gain * (period - 1)
            )
            + gains[index]
        ) / period

        average_loss = (
            (
                average_loss * (period - 1)
            )
            + losses[index]
        ) / period

    if average_loss == 0:
        return 100.0

    relative_strength = (
        average_gain / average_loss
    )

    return (
        100.0
        - (
            100.0
            / (1.0 + relative_strength)
        )
    )


def _extract_close(
    row: Mapping[str, Any],
) -> float:
    for name in (
        "close",
        "Close",
        "ltp",
        "price",
        "lastPrice",
    ):
        value = row.get(name)

        if value is not None:
            return float(value)

    raise LiveMarketDataError(
        "Historical NIFTY row has no close price."
    )


def _extract_timestamp(
    row: Mapping[str, Any],
) -> Optional[datetime]:
    value = row.get(
        "timestamp"
    )

    if isinstance(value, datetime):
        return value

    return None


def calculate_indicators(
    historical_rows: list[Mapping[str, Any]],
    current_price: float,
    previous_close: float,
) -> NiftyIndicators:
    if not historical_rows:
        raise LiveMarketDataError(
            "No historical NIFTY data supplied."
        )

    rows = list(historical_rows)

    rows.sort(
        key=lambda row: (
            _extract_timestamp(row)
            or datetime.min
        )
    )

    prices = [
        _extract_close(row)
        for row in rows
    ]

    prices.append(
        float(current_price)
    )

    prices = _validate_prices(
        prices
    )

    return NiftyIndicators(
        ema20=_ema(
            prices,
            20,
        ),
        ema50=_ema(
            prices,
            50,
        ),
        rsi=_rsi(
            prices,
            14,
        ),
        previous_close=float(
            previous_close
        ),
    )


def build_live_signal(
    historical_rows: list[Mapping[str, Any]],
    capital: float,
    lot_size: int,
    session=None,
    today: Optional[date] = None,
) -> LiveSignalResult:
    """
    Build the complete live BTST signal.

    Underlying NIFTY:
        Yahoo Finance

    Option chain:
        NSE

    Signal:
        NIFTY indicators + NSE option-chain confirmation

    Contract:
        NSE option-chain contract

    Risk:
        BTST risk manager
    """

    quote = fetch_nifty_quote()

    option_chain = fetch_nifty_option_chain(
        session=session
    )

    effective_today = today

    if effective_today is None:
        effective_today = quote.timestamp.date()

    expiry = nearest_nifty_expiry(
        option_chain,
        today=effective_today,
    )

    indicators = calculate_indicators(
        historical_rows=historical_rows,
        current_price=quote.price,
        previous_close=quote.previous_close,
    )

    chain_snapshot = (
        build_option_chain_snapshot(
            option_chain_payload=option_chain,
            nifty_price=quote.price,
            expiry=expiry,
            strikes_each_side=5,
        )
    )

    nifty_signal = generate_signal(
        nifty_price=quote.price,
        ema20=indicators.ema20,
        ema50=indicators.ema50,
        rsi=indicators.rsi,
        previous_close=indicators.previous_close,
        adx=indicators.adx,
        vwap=indicators.vwap,
        option_chain=chain_snapshot,
    )

    option_type = nifty_signal.direction

    if nifty_signal.decision != "BUY":
        option_type = (
            "CE"
            if nifty_signal.direction == "CE"
            else "PE"
        )

    contract = select_live_contract(
        option_chain_payload=option_chain,
        nifty_price=quote.price,
        expiry=expiry,
        option_type=option_type,
        selection_mode="ATM",
    )

    option_quote = find_option_quote(
        option_chain,
        expiry=expiry,
        strike=contract.strike,
        option_type=contract.option_type,
    )

    signal_input = SignalInput(
        timestamp=quote.timestamp,
        nifty_price=quote.price,
        option_contract=contract,
        option_price=option_quote.price,
        expiry=expiry,
        signal=nifty_signal,
    )

    btst_signal = build_btst_signal(
        signal_input=signal_input,
        capital=capital,
        lot_size=lot_size,
    )

    return LiveSignalResult(
        signal=btst_signal,
        nifty_signal=nifty_signal,
        indicators=indicators,
    )