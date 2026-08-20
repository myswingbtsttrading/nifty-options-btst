from datetime import datetime

from backtest import _find_next_morning
from backtest_config import BacktestConfig


def test_btst_exit_uses_next_available_trading_date():
    rows = [
        {
            "timestamp": datetime(
                2017, 10, 26, 15, 0
            ),
            "strike": 10050.0,
            "option_type": "PE",
            "expiry": "2017-11-30",
            "close": 55.55,
        },
        {
            "timestamp": datetime(
                2017, 10, 27, 9, 15
            ),
            "strike": 10050.0,
            "option_type": "PE",
            "expiry": "2017-11-30",
            "close": 49.65,
        },
    ]

    result = _find_next_morning(
        option_rows=rows,
        entry_time=datetime(
            2017, 10, 26, 15, 0
        ),
        strike=10050.0,
        option_type="PE",
        expiry="2017-11-30",
        config=BacktestConfig(),
    )

    assert result is not None
    assert result["timestamp"] == datetime(
        2017, 10, 27, 9, 15
    )
    assert result["close"] == 49.65


def test_btst_exit_skips_weekend():
    rows = [
        {
            "timestamp": datetime(
                2017, 10, 27, 15, 0
            ),
            "strike": 10050.0,
            "option_type": "PE",
            "expiry": "2017-11-30",
            "close": 50.0,
        },
        {
            "timestamp": datetime(
                2017, 10, 30, 9, 15
            ),
            "strike": 10050.0,
            "option_type": "PE",
            "expiry": "2017-11-30",
            "close": 48.0,
        },
    ]

    result = _find_next_morning(
        option_rows=rows,
        entry_time=datetime(
            2017, 10, 27, 15, 0
        ),
        strike=10050.0,
        option_type="PE",
        expiry="2017-11-30",
        config=BacktestConfig(),
    )

    assert result is not None
    assert result["timestamp"] == datetime(
        2017, 10, 30, 9, 15
    )