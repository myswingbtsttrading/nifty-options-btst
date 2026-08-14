from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from data_loader import (
    load_option_data,
    load_underlying_data,
)


def load_nifty_history(
    path: str | Path,
) -> List[Dict[str, Any]]:
    return load_underlying_data(path)


def load_nifty_option_history(
    path: str | Path,
) -> List[Dict[str, Any]]:
    return load_option_data(path)


def filter_session(
    rows: List[Dict[str, Any]],
    start_hour: int,
    start_minute: int,
    end_hour: int,
    end_minute: int,
) -> List[Dict[str, Any]]:
    result = []

    for row in rows:
        timestamp: datetime = row["timestamp"]

        minutes = (
            timestamp.hour * 60
            + timestamp.minute
        )

        start = (
            start_hour * 60
            + start_minute
        )

        end = (
            end_hour * 60
            + end_minute
        )

        if start <= minutes <= end:
            result.append(row)

    return result


def group_by_date(
    rows: List[Dict[str, Any]],
) -> Dict[Any, List[Dict[str, Any]]]:
    grouped: Dict[Any, List[Dict[str, Any]]] = {}

    for row in rows:
        key = row["timestamp"].date()

        grouped.setdefault(
            key,
            [],
        ).append(row)

    return grouped


def validate_historical_data(
    underlying_rows: List[Dict[str, Any]],
    option_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    underlying_dates = {
        row["timestamp"].date()
        for row in underlying_rows
    }

    option_dates = {
        row["timestamp"].date()
        for row in option_rows
    }

    option_types = {
        row["option_type"]
        for row in option_rows
    }

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
        "option_types": sorted(
            option_types
        ),
        "overlapping_dates": len(
            underlying_dates
            & option_dates
        ),
    }