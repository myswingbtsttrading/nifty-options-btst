from datetime import datetime

import pytest

from data_provider import (
    DataProviderError,
    normalize_option_data,
    normalize_option_row,
    normalize_underlying_data,
    normalize_underlying_row,
)


def test_normalize_underlying_row():
    row = normalize_underlying_row(
        {
            "datetime": "2026-08-10 15:00:00",
            "Close": "25000.50",
        }
    )

    assert row == {
        "timestamp": datetime(
            2026,
            8,
            10,
            15,
            0,
        ),
        "close": 25000.50,
    }


def test_normalize_option_row():
    row = normalize_option_row(
        {
            "datetime": "2026-08-10 15:00:00",
            "Expiry": "2026-08-13",
            "StrikePrice": "25000",
            "OptionType": "ce",
            "LastPrice": "125.50",
        }
    )

    assert row["timestamp"] == datetime(
        2026,
        8,
        10,
        15,
        0,
    )

    assert row["expiry"] == "2026-08-13"
    assert row["strike"] == 25000.0
    assert row["option_type"] == "CE"
    assert row["close"] == 125.50


def test_normalize_option_rejects_invalid_type():
    with pytest.raises(DataProviderError):
        normalize_option_row(
            {
                "timestamp": "2026-08-10 15:00:00",
                "expiry": "2026-08-13",
                "strike": "25000",
                "option_type": "FUT",
                "close": "100",
            }
        )


def test_normalize_option_rejects_missing_fields():
    with pytest.raises(DataProviderError):
        normalize_option_row(
            {
                "timestamp": "2026-08-10 15:00:00",
                "strike": "25000",
                "option_type": "CE",
                "close": "100",
            }
        )


def test_normalize_underlying_data_sorts():
    rows = normalize_underlying_data(
        [
            {
                "timestamp": "2026-08-11 15:00:00",
                "close": 25100,
            },
            {
                "timestamp": "2026-08-10 15:00:00",
                "close": 25000,
            },
        ]
    )

    assert rows[0]["close"] == 25000
    assert rows[1]["close"] == 25100


def test_normalize_option_data_sorts():
    rows = normalize_option_data(
        [
            {
                "timestamp": "2026-08-11 15:00:00",
                "expiry": "2026-08-13",
                "strike": 25100,
                "option_type": "PE",
                "close": 110,
            },
            {
                "timestamp": "2026-08-10 15:00:00",
                "expiry": "2026-08-13",
                "strike": 25000,
                "option_type": "CE",
                "close": 100,
            },
        ]
    )

    assert rows[0]["strike"] == 25000
    assert rows[1]["strike"] == 25100