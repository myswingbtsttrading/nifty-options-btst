from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class DatasetRequirements:
    entry_hour: int = 15
    entry_minute: int = 0

    exit_hour: int = 9
    exit_minute: int = 30

    required_option_types: tuple[str, ...] = (
        "CE",
        "PE",
    )


def inspect_dataset(
    underlying_rows: List[Dict[str, Any]],
    option_rows: List[Dict[str, Any]],
    requirements: DatasetRequirements | None = None,
) -> Dict[str, Any]:

    if requirements is None:
        requirements = DatasetRequirements()

    underlying_timestamps = {
        row["timestamp"]
        for row in underlying_rows
        if row.get("timestamp") is not None
    }

    option_timestamps = {
        row["timestamp"]
        for row in option_rows
        if row.get("timestamp") is not None
    }

    entry_timestamps = {
        timestamp
        for timestamp in option_timestamps
        if (
            timestamp.hour
            == requirements.entry_hour
            and timestamp.minute
            == requirements.entry_minute
        )
    }

    option_types = {
        str(row.get("option_type", "")).upper()
        for row in option_rows
    }

    option_dates = {
        row["timestamp"].date()
        for row in option_rows
        if row.get("timestamp") is not None
    }

    underlying_dates = {
        row["timestamp"].date()
        for row in underlying_rows
        if row.get("timestamp") is not None
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
        "overlapping_dates": len(
            underlying_dates & option_dates
        ),
        "option_types": sorted(
            option_types
        ),
        "has_ce": "CE" in option_types,
        "has_pe": "PE" in option_types,
        "entry_timestamp_count": len(
            entry_timestamps
        ),
        "has_exact_3pm_data": bool(
            entry_timestamps
        ),
        "has_intraday_data": (
            len(option_timestamps) > 1
        ),
    }


def dataset_is_suitable(
    inspection: Dict[str, Any],
) -> bool:

    return bool(
        inspection["overlapping_dates"] > 0
        and inspection["has_ce"]
        and inspection["has_pe"]
        and inspection["has_intraday_data"]
        and inspection["has_exact_3pm_data"]
    )