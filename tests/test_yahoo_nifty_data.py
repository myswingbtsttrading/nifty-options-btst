from datetime import datetime

import pandas as pd
import pytest

from live_market_data import LiveMarketDataError
from yahoo_nifty_data import (
    fetch_nifty_quote,
    load_nifty_history,
)


class FakeTicker:
    def __init__(
        self,
        intraday,
        daily,
    ):
        self._intraday = intraday
        self._daily = daily

    def history(
        self,
        period,
        interval,
        auto_adjust,
        prepost,
    ):
        if interval == "1m":
            return self._intraday

        return self._daily


def _intraday():
    index = pd.DatetimeIndex(
        [
            datetime(
                2026,
                8,
                27,
                14,
                59,
            ),
            datetime(
                2026,
                8,
                27,
                15,
                0,
            ),
        ]
    )

    return pd.DataFrame(
        {
            "Close": [
                25010.0,
                25020.0,
            ]
        },
        index=index,
    )


def _daily():
    index = pd.DatetimeIndex(
        [
            datetime(2026, 8, 25),
            datetime(2026, 8, 26),
            datetime(2026, 8, 27),
        ]
    )

    return pd.DataFrame(
        {
            "Close": [
                24800.0,
                24900.0,
                25020.0,
            ]
        },
        index=index,
    )


def test_fetch_nifty_quote_uses_yahoo():
    import yahoo_nifty_data

    original = yahoo_nifty_data.yf.Ticker

    yahoo_nifty_data.yf.Ticker = (
        lambda symbol: FakeTicker(
            _intraday(),
            _daily(),
        )
    )

    try:
        result = fetch_nifty_quote()

        assert result.price == 25020.0
        assert result.previous_close == 24900.0
        assert result.timestamp == datetime(
            2026,
            8,
            27,
            15,
            0,
        )
    finally:
        yahoo_nifty_data.yf.Ticker = original


def test_load_nifty_history():
    import yahoo_nifty_data

    original = yahoo_nifty_data.yf.Ticker

    yahoo_nifty_data.yf.Ticker = (
        lambda symbol: FakeTicker(
            _intraday(),
            _daily(),
        )
    )

    try:
        result = load_nifty_history(
            days=60
        )

        assert len(result) == 3
        assert result[-1]["close"] == 25020.0
    finally:
        yahoo_nifty_data.yf.Ticker = original


def test_load_nifty_history_rejects_small_window():
    with pytest.raises(
        ValueError,
        match="at least 60",
    ):
        load_nifty_history(
            days=30
        )


def test_fetch_nifty_quote_rejects_empty_intraday():
    import yahoo_nifty_data

    original = yahoo_nifty_data.yf.Ticker

    empty = pd.DataFrame(
        columns=["Close"]
    )

    yahoo_nifty_data.yf.Ticker = (
        lambda symbol: FakeTicker(
            empty,
            _daily(),
        )
    )

    try:
        with pytest.raises(
            LiveMarketDataError,
            match="no intraday",
        ):
            fetch_nifty_quote()
    finally:
        yahoo_nifty_data.yf.Ticker = original