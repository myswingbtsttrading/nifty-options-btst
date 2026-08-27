from __future__ import annotations

from datetime import datetime
from typing import Any

import yfinance as yf

from live_market_data import (
    LiveMarketDataError,
    LiveUnderlyingQuote,
)


YAHOO_SYMBOL = "^NSEI"


def _validate_positive(
    value: Any,
    field: str,
) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise LiveMarketDataError(
            f"Invalid {field}: {value!r}"
        ) from exc

    if result <= 0:
        raise LiveMarketDataError(
            f"{field} must be positive."
        )

    return result


def _normalise_timestamp(
    value: Any,
) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value

    try:
        timestamp = value.to_pydatetime()
    except AttributeError:
        timestamp = datetime.now()

    if timestamp.tzinfo is not None:
        timestamp = timestamp.replace(tzinfo=None)

    return timestamp


def fetch_nifty_quote() -> LiveUnderlyingQuote:
    """
    Fetch the live NIFTY 50 underlying quote from Yahoo Finance.

    Yahoo Finance is intentionally the primary underlying-price
    provider for the production GitHub Actions runner.

    NSE remains responsible for the option-chain data.
    """

    try:
        ticker = yf.Ticker(YAHOO_SYMBOL)

        intraday = ticker.history(
            period="1d",
            interval="1m",
            auto_adjust=False,
            prepost=False,
        )

        daily = ticker.history(
            period="5d",
            interval="1d",
            auto_adjust=False,
            prepost=False,
        )
    except Exception as exc:
        raise LiveMarketDataError(
            f"Yahoo Finance NIFTY request failed: {exc}"
        ) from exc

    if intraday is None or intraday.empty:
        raise LiveMarketDataError(
            "Yahoo Finance returned no intraday NIFTY data."
        )

    if "Close" not in intraday.columns:
        raise LiveMarketDataError(
            "Yahoo Finance intraday NIFTY data has no Close column."
        )

    intraday_close = intraday["Close"].dropna()

    if intraday_close.empty:
        raise LiveMarketDataError(
            "Yahoo Finance returned no valid intraday NIFTY prices."
        )

    current_price = _validate_positive(
        intraday_close.iloc[-1],
        "NIFTY price",
    )

    timestamp = _normalise_timestamp(
        intraday_close.index[-1]
    )

    previous_close: float | None = None

    if (
        daily is not None
        and not daily.empty
        and "Close" in daily.columns
    ):
        daily_close = daily["Close"].dropna()

        if len(daily_close) >= 2:
            previous_close = _validate_positive(
                daily_close.iloc[-2],
                "previous close",
            )

    if previous_close is None:
        try:
            fast_info = ticker.fast_info
            previous_close = _validate_positive(
                fast_info.get("previous_close"),
                "previous close",
            )
        except Exception:
            previous_close = None

    if previous_close is None:
        raise LiveMarketDataError(
            "Yahoo Finance could not determine NIFTY previous close."
        )

    return LiveUnderlyingQuote(
        timestamp=timestamp,
        price=current_price,
        previous_close=previous_close,
    )


def load_nifty_history(
    days: int = 120,
) -> list[dict[str, Any]]:
    """
    Load daily NIFTY history required by the live signal engine.
    """

    if days < 60:
        raise ValueError(
            "days must be at least 60."
        )

    try:
        ticker = yf.Ticker(YAHOO_SYMBOL)

        history = ticker.history(
            period=f"{days}d",
            interval="1d",
            auto_adjust=False,
            prepost=False,
        )
    except Exception as exc:
        raise LiveMarketDataError(
            f"Yahoo Finance NIFTY history request failed: {exc}"
        ) from exc

    if history is None or history.empty:
        raise LiveMarketDataError(
            "Yahoo Finance returned no NIFTY historical data."
        )

    if "Close" not in history.columns:
        raise LiveMarketDataError(
            "Yahoo Finance NIFTY history has no Close column."
        )

    rows: list[dict[str, Any]] = []

    for timestamp, row in history.iterrows():
        close = row.get("Close")

        if close is None:
            continue

        try:
            price = float(close)
        except (TypeError, ValueError):
            continue

        if price <= 0:
            continue

        rows.append(
            {
                "timestamp": _normalise_timestamp(
                    timestamp
                ),
                "close": price,
            }
        )

    if len(rows) < 50:
        raise LiveMarketDataError(
            "Fewer than 50 valid NIFTY historical prices "
            "were returned by Yahoo Finance."
        )

    return rows