"""
Yahoo Finance NIFTY data provider.

Provides both:
- current NIFTY quote
- historical NIFTY daily prices

Used as a fallback when NSE live data is unavailable.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import yfinance as yf

from live_market_data import LiveMarketDataError


YAHOO_SYMBOL = "^NSEI"

MIN_HISTORY_DAYS = 60
MIN_HISTORY_ROWS = 20


def _normalise_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        result = value
    else:
        try:
            result = datetime.fromisoformat(
                str(value).replace(
                    "Z",
                    "+00:00",
                )
            )
        except ValueError as exc:
            raise LiveMarketDataError(
                f"Unsupported Yahoo Finance timestamp: {value}"
            ) from exc

    if result.tzinfo is not None:
        result = result.replace(
            tzinfo=None
        )

    return result


def fetch_nifty_quote() -> float:
    """
    Fetch the latest NIFTY 50 price from Yahoo Finance.

    Returns:
        Current NIFTY price as a positive float.
    """

    try:
        ticker = yf.Ticker(
            YAHOO_SYMBOL
        )

        history = ticker.history(
            period="1d",
            interval="1m",
            auto_adjust=False,
            prepost=False,
        )

        if history is not None and not history.empty:
            if "Close" in history.columns:
                closes = history["Close"].dropna()

                if not closes.empty:
                    price = float(
                        closes.iloc[-1]
                    )

                    if price > 0:
                        return price

        # Fallback for environments where the 1-minute
        # endpoint is unavailable.
        fast_info = getattr(
            ticker,
            "fast_info",
            None,
        )

        if fast_info is not None:
            for key in (
                "last_price",
                "regularMarketPrice",
            ):
                try:
                    value = fast_info.get(
                        key
                    )

                    if value is None:
                        continue

                    price = float(value)

                    if price > 0:
                        return price
                except (
                    AttributeError,
                    TypeError,
                    ValueError,
                ):
                    continue

    except Exception as exc:
        raise LiveMarketDataError(
            f"Yahoo Finance NIFTY quote request failed: {exc}"
        ) from exc

    raise LiveMarketDataError(
        "Yahoo Finance returned no valid NIFTY quote."
    )


def load_nifty_history(
    days: int = 120,
) -> list[dict[str, Any]]:
    """
    Load daily NIFTY history required by the live signal engine.
    """

    if days < MIN_HISTORY_DAYS:
        raise ValueError(
            f"days must be at least {MIN_HISTORY_DAYS}."
        )

    try:
        ticker = yf.Ticker(
            YAHOO_SYMBOL
        )

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
        except (
            TypeError,
            ValueError,
        ):
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

    if len(rows) < MIN_HISTORY_ROWS:
        raise LiveMarketDataError(
            "Fewer than "
            f"{MIN_HISTORY_ROWS} valid NIFTY historical prices "
            "were returned by Yahoo Finance."
        )

    rows.sort(
        key=lambda item: item["timestamp"]
    )

    return rows


def fetch_nifty_history(
    days: int = 120,
) -> list[dict[str, Any]]:
    """
    Backward-compatible history alias.
    """
    return load_nifty_history(
        days=days
    )


__all__ = [
    "YAHOO_SYMBOL",
    "MIN_HISTORY_DAYS",
    "MIN_HISTORY_ROWS",
    "fetch_nifty_quote",
    "load_nifty_history",
    "fetch_nifty_history",
]