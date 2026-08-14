from datetime import datetime

from historical_dataset import (
    find_exact_timestamp,
    find_first_timestamp_at_or_after,
    next_trading_date,
    trading_dates,
    validate_intraday_dataset,
)


def _row(timestamp):
    return {
        "timestamp": datetime.fromisoformat(
            timestamp
        ),
        "close": 100.0,
    }


def test_find_exact_timestamp():
    rows = [
        _row("2026-08-10 15:00:00"),
        _row("2026-08-10 15:05:00"),
    ]

    result = find_exact_timestamp(
        rows,
        datetime(
            2026,
            8,
            10,
            15,
            0,
        ),
    )

    assert result is not None
    assert result["close"] == 100.0


def test_find_first_timestamp_at_or_after():
    rows = [
        _row("2026-08-10 15:00:00"),
        _row("2026-08-10 15:05:00"),
        _row("2026-08-10 15:10:00"),
    ]

    result = find_first_timestamp_at_or_after(
        rows,
        datetime(
            2026,
            8,
            10,
            15,
            2,
        ),
    )

    assert result is not None
    assert result["timestamp"].minute == 5


def test_trading_dates():
    rows = [
        _row("2026-08-10 15:00:00"),
        _row("2026-08-10 15:05:00"),
        _row("2026-08-11 09:30:00"),
    ]

    assert trading_dates(rows) == [
        datetime(
            2026,
            8,
            10,
        ).date(),
        datetime(
            2026,
            8,
            11,
        ).date(),
    ]


def test_next_trading_date():
    rows = [
        _row("2026-08-10 15:00:00"),
        _row("2026-08-12 15:00:00"),
    ]

    result = next_trading_date(
        rows,
        datetime(
            2026,
            8,
            10,
        ).date(),
    )

    assert result == datetime(
        2026,
        8,
        12,
    ).date()


def test_validate_intraday_dataset():
    underlying = [
        _row("2026-08-10 15:00:00"),
        _row("2026-08-10 15:05:00"),
    ]

    options = [
        {
            "timestamp": datetime(
                2026,
                8,
                10,
                15,
                0,
            ),
            "expiry": "2026-08-13",
            "strike": 25000.0,
            "option_type": "CE",
            "close": 100.0,
        },
        {
            "timestamp": datetime(
                2026,
                8,
                10,
                15,
                5,
            ),
            "expiry": "2026-08-13",
            "strike": 25000.0,
            "option_type": "CE",
            "close": 102.0,
        },
    ]

    result = validate_intraday_dataset(
        underlying,
        options,
    )

    assert result["underlying_rows"] == 2
    assert result["option_rows"] == 2
    assert result["overlapping_dates"] == 1
    assert result["has_intraday_data"] is True