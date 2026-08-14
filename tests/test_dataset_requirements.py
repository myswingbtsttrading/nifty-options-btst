from datetime import datetime

from dataset_requirements import (
    dataset_is_suitable,
    inspect_dataset,
)


def test_dataset_with_3pm_ce_pe_is_suitable():

    underlying = [
        {
            "timestamp": datetime(
                2026,
                8,
                10,
                15,
                0,
            ),
            "close": 25000,
        }
    ]

    options = [
        {
            "timestamp": datetime(
                2026,
                8,
                10,
                14,
                55,
            ),
            "expiry": "2026-08-13",
            "strike": 25000,
            "option_type": "CE",
            "close": 100,
        },
        {
            "timestamp": datetime(
                2026,
                8,
                10,
                15,
                0,
            ),
            "expiry": "2026-08-13",
            "strike": 25000,
            "option_type": "CE",
            "close": 105,
        },
        {
            "timestamp": datetime(
                2026,
                8,
                10,
                15,
                0,
            ),
            "expiry": "2026-08-13",
            "strike": 25000,
            "option_type": "PE",
            "close": 95,
        },
    ]

    result = inspect_dataset(
        underlying,
        options,
    )

    assert result["has_exact_3pm_data"]
    assert result["has_ce"]
    assert result["has_pe"]
    assert result["has_intraday_data"]
    assert dataset_is_suitable(result)


def test_daily_data_is_not_suitable():

    underlying = [
        {
            "timestamp": datetime(
                2026,
                8,
                10,
                0,
                0,
            ),
            "close": 25000,
        }
    ]

    options = [
        {
            "timestamp": datetime(
                2026,
                8,
                10,
                0,
                0,
            ),
            "expiry": "2026-08-13",
            "strike": 25000,
            "option_type": "CE",
            "close": 100,
        },
        {
            "timestamp": datetime(
                2026,
                8,
                11,
                0,
                0,
            ),
            "expiry": "2026-08-13",
            "strike": 25000,
            "option_type": "PE",
            "close": 95,
        },
    ]

    result = inspect_dataset(
        underlying,
        options,
    )

    assert not result["has_exact_3pm_data"]
    assert not dataset_is_suitable(result)