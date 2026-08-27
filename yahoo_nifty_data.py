"""
Yahoo Finance NIFTY data provider.

Provides:
- current NIFTY quote
- daily NIFTY historical prices

Used as the Yahoo Finance fallback when NSE live data is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import yfinance as yf

from live_market_data import LiveMarketDataError


YAHOO_SYMBOL = "^NSEI"

MIN_HISTORY_DAYS = 60
MIN_HISTORY_ROWS = 1


@dataclass(frozen=True)
class NiftyQuote:
    """
    Normalized current NIFTY quote.
    """

    timestamp: datetime
    price: float
    previous_close: float | None = None


def _normalise_timestamp(
    value: Any,
) -> datetime:
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


def _extract_previous_close(
    ticker: Any,
) -> float | None:
    """
    Extract the previous close when Yahoo exposes it.
    """

    try:
        fast_info = getattr(
            ticker,
            "fast_info",
            None,
        )

        if fast_info is not None:
            for key in (
                "previous_close",
                "regularMarketPreviousClose",
            ):
                try:
                    value = fast_info.get(key)

                    if value is None:
                        continue

                    value = float(value)

                    if value > 0:
                        return value

                except (
                    AttributeError,
                    TypeError,
                    ValueError,
                ):
                    continue

    except Exception:
        pass

    return None


def fetch_nifty_quote() -> NiftyQuote:
    """
    Fetch the latest NIFTY 50 quote from Yahoo Finance.
    """

    try:
        ticker = yf.Ticker(
            YAHOO_SYMBOL
        )

        intraday = ticker.history(
            period="1d",
            interval="1m",
            auto_adjust=False,
            prepost=False,
        )

    except Exception as exc:
        raise LiveMarketDataError(
            f"Yahoo Finance NIFTY quote request failed: {exc}"
        ) from exc

    if intraday is None or intraday.empty:
        raise LiveMarketDataError(
            "Yahoo Finance returned no intraday NIFTY data."
        )

    if "Close" not in intraday.columns:
        raise LiveMarketDataError(
            "Yahoo Finance intraday NIFTY data has no Close column."
        )

    valid = intraday["Close"].dropna()

    if valid.empty:
        raise LiveMarketDataError(
            "Yahoo Finance returned no intraday NIFTY prices."
        )

    try:
        price = float(
            valid.iloc[-1]
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise LiveMarketDataError(
            "Yahoo Finance returned an invalid NIFTY price."
        ) from exc

    if price <= 0:
        raise LiveMarketDataError(
            "Yahoo Finance returned an invalid NIFTY price."
        )

    timestamp = _normalise_timestamp(
        intraday.index[-1]
    )

    return NiftyQuote(
        timestamp=timestamp,
        price=price,
        previous_close=_extract_previous_close(
            ticker
        ),
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
    "NiftyQuote",
    "fetch_nifty_quote",
    "load_nifty_history",
    "fetch_nifty_history",
]