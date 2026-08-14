from datetime import datetime

from historical_data import (
    filter_session,
    group_by_date,
    validate_historical_data,
)


def _row(timestamp: str):
    return {
        "timestamp": datetime.fromisoformat(
            timestamp
        ),
        "close": 100.0,
    }


def test_filter_session():
    rows = [
        _row("2026-08-10 09:15"),
        _row("2026-08-10 14:59"),
        _row("2026-08-10 15:00"),
        _row("2026-08-10 15:30"),
    ]

    result = filter_session(
        rows,
        15,
        0,
        15,
        0,
    )

    assert len(result) == 1
    assert result[0]["timestamp"].hour == 15
    assert result[0]["timestamp"].minute == 0


def test_group_by_date():
    rows = [
        _row("2026-08-10 15:00"),
        _row("2026-08-10 15:05"),
        _row("2026-08-11 15:00"),
    ]

    result = group_by_date(rows)

    assert len(result) == 2
    assert len(result[datetime(2026, 8, 10).date()]) == 2
    assert len(result[datetime(2026, 8, 11).date()]) == 1


def test_validate_historical_data():
    underlying = [
        _row("2026-08-10 15:00"),
        _row("2026-08-11 15:00"),
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
                11,
                15,
                0,
            ),
            "expiry": "2026-08-13",
            "strike": 25000.0,
            "option_type": "PE",
            "close": 110.0,
        },
    ]

    result = validate_historical_data(
        underlying,
        options,
    )

    assert result["underlying_rows"] == 2
    assert result["option_rows"] == 2
    assert result["underlying_dates"] == 2
    assert result["option_dates"] == 2
    assert result["overlapping_dates"] == 2
    assert result["option_types"] == [
        "CE",
        "PE",
    ]