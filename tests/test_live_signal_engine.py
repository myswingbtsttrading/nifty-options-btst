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


def _mixed_rows():
    prices = [
        24000,
        24100,
        23950,
        24150,
        24050,
        24200,
        24100,
        24300,
        24150,
        24250,
        24100,
        24400,
        24200,
        24350,
        24250,
        24500,
        24300,
        24450,
        24350,
        24600,
        24400,
        24550,
        24450,
        24700,
        24500,
        24650,
        24550,
        24800,
        24600,
        24750,
        24650,
        24900,
        24700,
        24850,
        24750,
        25000,
        24800,
        24950,
        24850,
        25100,
        24900,
        25050,
        24950,
        25200,
        25000,
        25150,
        25050,
        25300,
        25100,
        25250,
        25050,
        25100,
        24950,
        25000,
        24850,
        24950,
        24750,
        24850,
        24650,
        24750,
    ]

    return [
        {
            "timestamp": datetime(
                2026,
                8,
                1 + (index // 5),
                9,
                15,
            ),
            "close": price,
        }
        for index, price in enumerate(prices)
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
    rows = _mixed_rows()

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