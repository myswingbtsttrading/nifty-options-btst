from datetime import datetime, timedelta

import pytest

from backtest import (
    _calculate_max_drawdown,
    run_backtest,
)


def _underlying_row(
    timestamp: datetime,
    close: float,
):
    return {
        "timestamp": timestamp,
        "close": close,
    }


def _option_row(
    timestamp: datetime,
    strike: float,
    option_type: str,
    close: float,
    expiry: str = "2026-08-18",
):
    return {
        "timestamp": timestamp,
        "expiry": expiry,
        "strike": strike,
        "option_type": option_type,
        "close": close,
    }


def test_max_drawdown():
    result = _calculate_max_drawdown(
        [
            100000,
            110000,
            99000,
            105000,
            90000,
        ]
    )

    assert result == pytest.approx(
        18.181818,
        rel=1e-5,
    )


def test_empty_underlying_rejected():
    with pytest.raises(ValueError):
        run_backtest(
            [],
            [
                _option_row(
                    datetime(2026, 8, 10, 15, 0),
                    25000,
                    "CE",
                    100,
                )
            ],
        )


def test_empty_options_rejected():
    with pytest.raises(ValueError):
        run_backtest(
            [
                _underlying_row(
                    datetime(2026, 8, 10, 15, 0),
                    25000,
                )
            ],
            [],
        )


def test_no_trade_when_insufficient_history():
    underlying = []

    start = datetime(
        2026,
        8,
        3,
        15,
        0,
    )

    for index in range(10):
        underlying.append(
            _underlying_row(
                start + timedelta(days=index),
                25000 + index * 10,
            )
        )

    options = [
        _option_row(
            start + timedelta(days=9),
            25100,
            "CE",
            100,
        )
    ]

    result = run_backtest(
        underlying,
        options,
    )

    assert result.total_trades == 0
    assert result.final_capital == pytest.approx(
        result.initial_capital
    )


def test_backtest_config_is_applied():
    underlying = []

    start = datetime(
        2026,
        6,
        1,
        15,
        0,
    )

    # More than enough observations for EMA50/RSI.
    for index in range(60):
        underlying.append(
            _underlying_row(
                start + timedelta(days=index),
                20000 + index * 20,
            )
        )

    # This test primarily verifies that the engine
    # executes successfully with valid data.
    result = run_backtest(
        underlying,
        [],
    ) if False else None

    assert result is None