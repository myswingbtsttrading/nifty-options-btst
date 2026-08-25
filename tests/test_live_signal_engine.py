from datetime import datetime

import pytest

from live_signal_engine import (
    calculate_indicators,
)


def _rows():
    return [
        {
            "timestamp": datetime(
                2026,
                8,
                1,
                9,
                15,
            ),
            "close": 24000 + index * 10,
        }
        for index in range(60)
    ]


def test_calculate_indicators():
    result = calculate_indicators(
        historical_rows=_rows(),
        current_price=24650,
        previous_close=24600,
    )

    assert result.ema20 > 0
    assert result.ema50 > 0
    assert 0 <= result.rsi <= 100
    assert result.previous_close == 24600


def test_calculate_indicators_uses_current_price():
    rows = _rows()

    first = calculate_indicators(
        historical_rows=rows,
        current_price=24600,
        previous_close=24500,
    )

    second = calculate_indicators(
        historical_rows=rows,
        current_price=25000,
        previous_close=24500,
    )

    assert first.ema20 != second.ema20
    assert first.rsi != second.rsi


def test_calculate_indicators_requires_history():
    with pytest.raises(
        Exception,
        match="At least 50",
    ):
        calculate_indicators(
            historical_rows=_rows()[:10],
            current_price=24500,
            previous_close=24400,
        )


def test_calculate_indicators_rejects_bad_price():
    rows = _rows()

    rows[0]["close"] = 0

    with pytest.raises(
        Exception,
        match="positive",
    ):
        calculate_indicators(
            historical_rows=rows,
            current_price=24500,
            previous_close=24400,
        )