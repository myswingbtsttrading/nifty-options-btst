from datetime import datetime

import pytest

from backtest import (
    _calculate_max_drawdown,
    run_backtest,
)
from backtest_config import BacktestConfig


def _underlying_row(
    timestamp: str,
    close: float,
):
    return {
        "timestamp": datetime.fromisoformat(
            timestamp
        ),
        "close": close,
    }


def _option_row(
    timestamp: str,
    strike: float,
    option_type: str,
    close: float,
    expiry: str = "2026-08-18",
):
    return {
        "timestamp": datetime.fromisoformat(
            timestamp
        ),
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
                    "2026-08-10 15:00",
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
                    "2026-08-10 15:00",
                    25000,
                )
            ],
            [],
        )


def test_backtest_result_structure():
    # Build enough historical underlying observations
    # for EMA20, EMA50 and RSI14.

    underlying = []

    for index in range(60):
        hour = 15
        minute = 0

        day = index + 1

        underlying.append(
            _underlying_row(
                f"2026-07-{day:02d} "
                f"{hour:02d}:{minute:02d}",
                25000 + index * 10,
            )
        )

    option_rows = [
        _option_row(
            "2026-07-60 15:00",
            25600,
            "CE",
            100,
        )
    ]

    # The synthetic date above is intentionally invalid
    # and should never be silently accepted.
    with pytest.raises(ValueError):
        run_backtest(
            underlying,
            option_rows,
        )