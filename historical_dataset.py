from datetime import date, datetime
from typing import Any, Dict, List, Optional


def find_exact_timestamp(
    rows: List[Dict[str, Any]],
    timestamp: datetime,
) -> Optional[Dict[str, Any]]:
    for row in rows:
        if row.get("timestamp") == timestamp:
            return row

    return None


def find_first_timestamp_at_or_after(
    rows: List[Dict[str, Any]],
    timestamp: datetime,
) -> Optional[Dict[str, Any]]:
    candidates = [
        row
        for row in rows
        if row.get("timestamp") >= timestamp
    ]

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda row: row["timestamp"],
    )


def trading_dates(
    rows: List[Dict[str, Any]],
) -> List[date]:
    dates = {
        row["timestamp"].date()
        for row in rows
        if row.get("timestamp") is not None
    }

    return sorted(dates)


def next_trading_date(
    rows: List[Dict[str, Any]],
    current_date: date,
) -> Optional[date]:
    dates = trading_dates(rows)

    for trading_date in dates:
        if trading_date > current_date:
            return trading_date

    return None


def validate_intraday_dataset(
    underlying_rows: List[Dict[str, Any]],
    option_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    underlying_dates = set(
        trading_dates(underlying_rows)
    )

    option_dates = set(
        trading_dates(option_rows)
    )

    timestamps = [
        row["timestamp"]
        for row in option_rows
        if row.get("timestamp") is not None
    ]

    return {
        "underlying_rows": len(
            underlying_rows
        ),
        "option_rows": len(
            option_rows
        ),
        "underlying_dates": len(
            underlying_dates
        ),
        "option_dates": len(
            option_dates
        ),
        "overlapping_dates": len(
            underlying_dates
            & option_dates
        ),
        "option_timestamps": len(
            timestamps
        ),
        "has_intraday_data": (
            len(set(timestamps)) > 1
        ),
    }